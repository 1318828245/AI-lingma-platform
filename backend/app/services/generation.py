"""生成任务编排：创建/状态持久化/执行入口/重启恢复。"""

from datetime import datetime
from functools import partial

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.agents.generation.nodes import (
    GenerationBlocked,
    GenerationCancelled,
    GenerationFailed,
)
from app.agents.generation.workflow import run_generation_workflow
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.generation import Generation
from app.models.message import Message
from app.models.project import Project
from app.models.session import Session as ChatSession
from app.services.events import get_broker
from app.services.project import get_owned_project, project_workspace
from app.services.task_manager import get_task_manager


def add_message(
    db: Session,
    session_id: int,
    role: str,
    content: str,
    msg_type: str = "text",
    tool_call_json: dict | None = None,
) -> Message:
    message = Message(
        session_id=session_id,
        role=role,
        content=content,
        msg_type=msg_type,
        tool_call_json=tool_call_json,
    )
    db.add(message)
    return message


def get_generation_for_user(db: Session, generation_id: int, user_id: int) -> Generation:
    gen = db.get(Generation, generation_id)
    if gen is None:
        raise HTTPException(status_code=404, detail="生成任务不存在")
    project = db.get(Project, gen.project_id)
    if project is None or project.owner_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问该生成任务")
    return gen


def resolve_session(
    db: Session,
    project: Project,
    user_id: int,
    session_id: int | None,
) -> ChatSession:
    if session_id is not None:
        session = db.get(ChatSession, session_id)
        if (
            session is None
            or session.project_id != project.id
            or session.user_id != user_id
        ):
            raise HTTPException(status_code=404, detail="会话不存在")
        return session
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.project_id == project.id,
            ChatSession.user_id == user_id,
        )
        .order_by(ChatSession.updated_at.desc())
        .first()
    )
    if session is None:
        session = ChatSession(
            user_id=user_id,
            project_id=project.id,
            title=f"生成会话 {datetime.now():%m-%d %H:%M}",
        )
        db.add(session)
        db.flush()
    return session


def create_generation(
    db: Session,
    project: Project,
    session: ChatSession,
    requirement: str,
) -> Generation:
    settings = get_settings()
    gen = Generation(
        project_id=project.id,
        session_id=session.id,
        status="pending",
        requirement=requirement,
        llm_model=settings.llm_model,
        max_build_attempts=3,
        max_eval_attempts=2,
        cancel_requested=False,
    )
    db.add(gen)
    add_message(db, session.id, "user", requirement, msg_type="text")
    db.commit()
    db.refresh(gen)
    return gen


def mark_running(generation_id: int) -> None:
    with SessionLocal() as db:
        gen = db.get(Generation, generation_id)
        if gen is not None:
            gen.status = "running"
            gen.started_at = datetime.now()
            db.commit()


def mark_failed(generation_id: int, error: str) -> None:
    with SessionLocal() as db:
        gen = db.get(Generation, generation_id)
        if gen is not None:
            gen.status = "failed"
            gen.error = error[:2000]
            gen.finished_at = datetime.now()
            db.commit()


def mark_cancelled(generation_id: int) -> None:
    with SessionLocal() as db:
        gen = db.get(Generation, generation_id)
        if gen is not None:
            gen.status = "cancelled"
            gen.finished_at = datetime.now()
            db.commit()


def mark_timed_out(generation_id: int) -> None:
    with SessionLocal() as db:
        gen = db.get(Generation, generation_id)
        if gen is not None:
            gen.status = "timed_out"
            gen.error = "任务执行超时"
            gen.finished_at = datetime.now()
            db.commit()


def recover_interrupted_tasks() -> int:
    with SessionLocal() as db:
        rows = (
            db.query(Generation)
            .filter(Generation.status.in_(["pending", "running"]))
            .all()
        )
        for gen in rows:
            gen.status = "interrupted"
            gen.error = "服务重启，任务中断"
            gen.finished_at = datetime.now()
        db.commit()
        return len(rows)


async def run_generation_task(generation_id: int) -> None:
    broker = get_broker()
    try:
        with SessionLocal() as db:
            gen = db.get(Generation, generation_id)
            if gen is None:
                return
            project = db.get(Project, gen.project_id)
            session = db.get(ChatSession, gen.session_id)
            state = {
                "generation_id": gen.id,
                "project_id": gen.project_id,
                "session_id": gen.session_id,
                "user_id": session.user_id if session else 0,
                "workspace": str(project_workspace(project)),
                "requirement": gen.requirement,
                "tech_stack": project.tech_stack if project else "html",
                "llm_model": gen.llm_model or get_settings().llm_model,
                "parsed_requirement": {},
                "plan": [],
                "files": [],
                "guardrails": [],
                "build_log": [],
                "errors": [],
                "build_attempt": gen.build_attempt,
                "max_build_attempts": gen.max_build_attempts,
                "eval_attempt": gen.eval_attempt,
                "max_eval_attempts": gen.max_eval_attempts,
                "token_usage": {"prompt_tokens": 0, "completion_tokens": 0},
                "status": "pending",
                "cancel_requested": False,
                "summary": "",
            }
        mark_running(generation_id)
        await run_generation_workflow(state)
    except GenerationCancelled:
        mark_cancelled(generation_id)
        await broker.publish(
            generation_id, {"type": "cancelled", "generation_id": generation_id}
        )
    except (GenerationBlocked, GenerationFailed) as exc:
        mark_failed(generation_id, str(exc))
        await broker.publish(
            generation_id, {"type": "error", "error": str(exc)}
        )
    except Exception as exc:  # noqa: BLE001 兜底
        mark_failed(generation_id, f"内部错误: {exc}")
        await broker.publish(
            generation_id, {"type": "error", "error": f"内部错误: {exc}"}
        )
    finally:
        await broker.close(generation_id)


async def handle_generation_timeout(generation_id: int) -> None:
    mark_timed_out(generation_id)
    broker = get_broker()
    await broker.publish(
        generation_id, {"type": "error", "error": "任务执行超时"}
    )
    await broker.close(generation_id)
