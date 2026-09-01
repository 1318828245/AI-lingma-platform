"""Small, transparent memory layer; no external vector store is required."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models.agent_memory import AgentMemory
from app.models.message import Message
from app.models.modification import Modification
from app.models.project_version import ProjectVersion


def _keywords(text: str) -> set[str]:
    return {word.lower() for word in re.findall(r"[\w\u4e00-\u9fff]{2,}", text or "")}


def _rank(rows: list, query: str, get_text) -> list:
    terms = _keywords(query)
    return sorted(rows, key=lambda row: len(terms & _keywords(get_text(row))), reverse=True)


def refresh_session_summary(db: Session, *, owner_id: int, project_id: int, session_id: int) -> AgentMemory:
    messages = (
        db.query(Message).filter(
            Message.session_id == session_id,
            Message.msg_type.in_({"text", "assistant", "modification_summary", "clarification"}),
        ).order_by(Message.created_at.desc(), Message.id.desc()).limit(16).all()
    )
    facts = []
    for row in reversed(messages):
        label = "用户" if row.role == "user" else "Agent"
        text = " ".join(row.content.split())[:360]
        if text:
            facts.append(f"{label}：{text}")
    content = "\n".join(facts)[-4000:] or "尚无可摘要的有效会话内容。"
    memory = db.query(AgentMemory).filter_by(
        owner_id=owner_id, project_id=project_id, session_id=session_id, scope="session"
    ).first()
    if memory is None:
        memory = AgentMemory(owner_id=owner_id, project_id=project_id, session_id=session_id, scope="session", content=content)
        db.add(memory)
    else:
        memory.content = content
    return memory


def refresh_project_summary(db: Session, *, owner_id: int, project_id: int) -> AgentMemory:
    versions = db.query(ProjectVersion).filter_by(project_id=project_id).order_by(ProjectVersion.version_no.desc()).limit(5).all()
    changes = db.query(Modification).filter_by(project_id=project_id, status="succeeded").order_by(Modification.id.desc()).limit(6).all()
    content = "版本：" + "；".join(f"v{row.version_no} {_clip(row.summary, 180)}" for row in reversed(versions))
    if changes:
        content += "\n近期修改：" + "；".join(_clip(row.instruction, 180) for row in reversed(changes))
    memory = db.query(AgentMemory).filter_by(
        owner_id=owner_id, project_id=project_id, session_id=None, scope="project"
    ).first()
    if memory is None:
        memory = AgentMemory(owner_id=owner_id, project_id=project_id, session_id=None, scope="project", content=content[-4000:])
        db.add(memory)
    else:
        memory.content = content[-4000:]
    return memory


def _clip(value: str | None, limit: int) -> str:
    return (value or "").replace("\n", " ")[:limit]


def relevant_changes(db: Session, *, project_id: int, instruction: str, limit: int) -> list[Modification]:
    rows = db.query(Modification).filter_by(project_id=project_id, status="succeeded").order_by(Modification.id.desc()).limit(30).all()
    return _rank(rows, instruction, lambda row: row.instruction)[:limit]
