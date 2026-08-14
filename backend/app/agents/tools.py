"""Agent 工具集：list_files / read_file / write_file / edit_file / finish。

写文件统一走 services.project.write_project_file，保证路径校验与 files 元数据登记。
"""

from pathlib import Path

from sqlalchemy.orm import Session

from app.services.project import write_project_file


def safe_rel_path(workspace: Path, rel_path: str) -> Path:
    clean = rel_path.replace("\\", "/").lstrip("/")
    if clean in ("", ".", "..") or any(part == ".." for part in clean.split("/")):
        raise ValueError(f"非法文件路径: {rel_path}")
    target = (workspace / clean).resolve()
    if not target.is_relative_to(workspace.resolve()):
        raise ValueError(f"文件路径越界: {rel_path}")
    return target


def list_files(workspace: Path, max_depth: int = 8) -> list[str]:
    if not workspace.exists():
        return []
    result: list[str] = []
    for path in workspace.rglob("*"):
        if path.is_file() and path.name not in ("node_modules", ".git"):
            rel = path.relative_to(workspace).as_posix()
            if rel.count("/") < max_depth and "node_modules" not in rel.split("/"):
                result.append(rel)
    return sorted(result)


def read_file(workspace: Path, rel_path: str) -> str:
    target = safe_rel_path(workspace, rel_path)
    return target.read_text(encoding="utf-8")


def write_file(
    db: Session,
    project_id: int,
    workspace: Path,
    rel_path: str,
    content: str,
) -> str:
    safe_rel_path(workspace, rel_path)
    write_project_file(db, project_id, rel_path, content)
    return rel_path


def edit_file(
    db: Session,
    project_id: int,
    workspace: Path,
    rel_path: str,
    old: str,
    new: str,
) -> str:
    content = read_file(workspace, rel_path)
    if old not in content:
        raise ValueError(f"未在 {rel_path} 中找到待替换内容")
    updated = content.replace(old, new, 1)
    write_file(db, project_id, workspace, rel_path, updated)
    return rel_path


def finish(summary: str) -> dict:
    return {"summary": summary}
