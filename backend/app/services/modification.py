"""M2 点选修改任务：元素定位、局部文本编辑、构建前校验和版本快照。"""

import asyncio
import difflib
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.agents.tools import list_files, read_file
from app.agents.modification.agent import run_modification_agent
from app.core.database import SessionLocal
from app.models.message import Message
from app.models.modification import Modification
from app.models.project import Project
from app.services.events import get_broker
from app.services.project import project_workspace, write_project_file
from app.services.sandbox import validate_build
from app.services.version import snapshot_project
from app.services.llm import LLMClient


class ModificationCancelled(Exception):
    pass


def _publish_sync(session_id: int, modification_id: int, event: dict) -> None:
    """Persist replayable modification events without storing full source as chat text."""
    event_type = str(event.get("type") or "")
    mapping = {
        "stage": ("stage", str(event.get("stage") or "")),
        "thought": ("think", str(event.get("content") or "")),
        "tool_call_completed": ("tool_call", str(event.get("detail") or "")),
        "file_written": ("file_written", str(event.get("path") or "")),
        "diff": ("modification_diff", ""),
        "completed": ("modification_summary", str(event.get("summary") or "修改完成")),
        "task_error": ("error", str(event.get("error") or "修改失败")),
        "cancelled": ("info", "已取消这次修改"),
    }
    mapped = mapping.get(event_type)
    if mapped is None:
        return
    msg_type, content = mapped
    with SessionLocal() as db:
        db.add(Message(
            session_id=session_id,
            role="assistant",
            content=content,
            msg_type=msg_type,
            tool_call_json=event,
        ))
        db.commit()


async def _publish(session_id: int, modification_id: int, event: dict) -> None:
    await get_broker().publish(modification_id, {**event, "modification_id": modification_id})
    _publish_sync(session_id, modification_id, {**event, "modification_id": modification_id})


def _check_cancel(modification_id: int) -> None:
    with SessionLocal() as db:
        modification = db.get(Modification, modification_id)
        if modification is not None and modification.status == "cancel_requested":
            raise ModificationCancelled()


def _candidate_files(workspace: Path, related_files: list[str]) -> list[str]:
    allowed = set(list_files(workspace))
    requested = [path.replace("\\", "/").lstrip("/") for path in related_files]
    artifact_parts = {"dist", "build", ".vite", "node_modules"}
    selected = [
        path for path in requested
        if path in allowed and not set(path.split("/")) & artifact_parts
    ]
    return selected or sorted(
        path
        for path in allowed
        if Path(path).suffix.lower() in {".html", ".vue", ".jsx", ".tsx", ".js"}
        and not set(path.replace("\\", "/").split("/")) & {"dist", "build", ".vite", "node_modules"}
    )


def _locate_file(workspace: Path, snapshot: dict, related_files: list[str]) -> tuple[str, str]:
    text = str(snapshot.get("text") or "").strip()
    element_id = str(snapshot.get("id") or "").strip()
    class_name = str(snapshot.get("className") or snapshot.get("class") or "").strip()
    candidates = _candidate_files(workspace, related_files)
    # Direct chat modifications do not have a DOM selection.  Give the Agent a
    # deterministic project file instead of rejecting the request before it
    # can inspect and edit the source.
    if not (text or element_id or class_name) and candidates:
        path = candidates[0]
        return path, read_file(workspace, path)
    for path in candidates:
        content = read_file(workspace, path)
        if text and text in content:
            return path, content
        if element_id and re.search(rf"id=[\"']{re.escape(element_id)}[\"']", content):
            return path, content
        if class_name:
            first_class = class_name.split()[0]
            if re.search(rf"class=[\"'][^\"']*\b{re.escape(first_class)}\b", content):
                return path, content
    raise ValueError("无法定位选中元素对应的源码文件，请重新选择元素后再试")


def _replacement_text(instruction: str) -> str:
    match = re.search(r"(?:改成|改为|替换为|替换成)\s*[“\"']?(.+?)[”\"']?(?:[，。,；;。]|$)", instruction.strip())
    if match:
        value = match.group(1).strip().strip("“”\"'")
        if value:
            return value
    raise ValueError("当前修改器需要明确的文本替换指令，例如：把标题改成新品发布")


def _apply_mock_edit(content: str, snapshot: dict, instruction: str) -> tuple[str, str]:
    old_text = str(snapshot.get("text") or "").strip()
    if not old_text:
        direct_match = re.search(r"把\s*[“\"']?(.+?)[”\"']?\s*(?:改成|改为|替换为|替换成)", instruction.strip())
        if direct_match:
            old_text = direct_match.group(1).strip().strip("“”\"'")
    if not old_text:
        raise ValueError("直接修改请说明原文本与目标文本，例如：把旧标题改成新品发布")
    new_text = _replacement_text(instruction)
    if old_text not in content:
        raise ValueError("源码中未找到选中元素的文本，页面可能已刷新，请重新选择")
    return content.replace(old_text, new_text, 1), new_text


def _diff_files(workspace: Path, before_files: dict[str, str], changed_files: list[str]) -> list[dict[str, str]]:
    result = []
    for path in changed_files:
        target = workspace / path
        after = target.read_text(encoding="utf-8") if target.exists() else ""
        before = before_files.get(path, "")
        status = "added" if path not in before_files else "modified"
        result.append({
            "path": path,
            "status": status,
            "diff": "".join(difflib.unified_diff(
                before.splitlines(keepends=True), after.splitlines(keepends=True),
                fromfile=f"before/{path}", tofile=f"after/{path}",
            )),
        })
    return result


async def run_modification_task(modification_id: int) -> None:
    broker = get_broker()
    session_id = 0
    try:
        with SessionLocal() as db:
            modification = db.get(Modification, modification_id)
            if modification is None:
                return
            session_id = modification.session_id
            project = db.get(Project, modification.project_id)
            if project is None:
                raise ValueError("项目不存在")
            modification.status = "running"
            modification.attempt += 1
            modification.started_at = datetime.now()
            db.commit()
            workspace = project_workspace(project)
            tech_stack = project.tech_stack
            snapshot = modification.element_snapshot or {}
            related_files = modification.related_files_json or []
            instruction = modification.instruction

        await _publish(session_id, modification_id, {"type": "stage", "stage": "locate"})
        _check_cancel(modification_id)
        await asyncio.sleep(0)
        path, before = _locate_file(workspace, snapshot, related_files)
        await _publish(session_id, modification_id, {"type": "thought", "content": f"已定位源码文件：{path}"})

        await _publish(session_id, modification_id, {"type": "stage", "stage": "edit"})
        _check_cancel(modification_id)
        # Capture the state immediately before editing so every successful
        # modification has a deterministic undo target.
        with SessionLocal() as db:
            snapshot_project(
                db,
                modification.project_id,
                source_type="modification_before",
                source_id=modification_id,
                summary="Modification pre-edit snapshot",
            )
            db.commit()
        if LLMClient().mode == "real":
            before_files = {
                candidate: read_file(workspace, candidate)
                for candidate in _candidate_files(workspace, related_files)
            }
            agent_result = await run_modification_agent({
                "modification_id": modification_id,
                "project_id": modification.project_id if modification else 0,
                "session_id": session_id,
                "workspace": str(workspace),
                "instruction": instruction,
                "element_snapshot": snapshot,
                "related_files": related_files or [path],
            })
            changed_files = agent_result.get("changed_files") or []
            if not changed_files:
                raise ValueError("修改 Agent 未写入任何文件")
            file_diffs = _diff_files(workspace, before_files, changed_files)
            summary = str(agent_result.get("summary") or "真实 Agent 修改完成")
        else:
            after, new_text = _apply_mock_edit(before, snapshot, instruction)
            if any(pattern in after.lower() for pattern in ("rm -rf", "drop table", "os.system(")):
                raise ValueError("修改结果命中输出护轨，已拦截写入")
            with SessionLocal() as db:
                write_project_file(db, modification.project_id, path, after)
            changed_files = [path]
            file_diffs = [{"path": path, "status": "modified", "diff": "".join(difflib.unified_diff(
                before.splitlines(keepends=True), after.splitlines(keepends=True),
                fromfile=f"before/{path}", tofile=f"after/{path}",
            ))}]
            summary = f"修改文本为：{new_text}"
        if tech_stack.lower().startswith("vue"):
            ok, _build_log, build_errors = await validate_build(workspace, tech_stack)
            if not ok:
                raise ValueError(f"修改后的预览构建失败：{'；'.join(build_errors[:3])}")
        with SessionLocal() as db:
            modification = db.get(Modification, modification_id)
            if modification is None:
                return
            modification.related_files_json = changed_files
            modification.diff_json = {"files": file_diffs}
            modification.status = "succeeded"
            modification.finished_at = datetime.now()
            version = snapshot_project(
                db,
                modification.project_id,
                source_type="modification",
                source_id=modification.id,
                summary=summary[:500],
            )
            version_id = version.id
            version_no = version.version_no
            modification.diff_json = {
                "files": file_diffs,
                "version_id": version_id,
                "review_status": "pending",
            }
            db.commit()

        for changed_path in changed_files:
            changed_content = read_file(workspace, changed_path)
            await _publish(session_id, modification_id, {"type": "file_written", "path": changed_path, "content": changed_content[:16000]})
        await _publish(session_id, modification_id, {"type": "diff", "files": file_diffs})
        await _publish(session_id, modification_id, {
            "type": "completed",
            "status": "succeeded",
            "summary": summary,
            "version_id": version_id,
            "version_no": version_no,
        })
    except ModificationCancelled:
        with SessionLocal() as db:
            modification = db.get(Modification, modification_id)
            if modification is not None:
                modification.status = "cancelled"
                modification.finished_at = datetime.now()
                db.commit()
        await _publish(session_id, modification_id, {"type": "cancelled"})
    except Exception as exc:  # noqa: BLE001
        with SessionLocal() as db:
            modification = db.get(Modification, modification_id)
            if modification is not None:
                modification.status = "failed"
                modification.finished_at = datetime.now()
                db.commit()
        await _publish(session_id, modification_id, {"type": "task_error", "error": str(exc)})
    finally:
        await broker.close(modification_id)
