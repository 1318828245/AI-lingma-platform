from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.message import Message
from app.models.agent_context import AgentContextSnapshot
from app.models.agent_memory import AgentMemory
from app.models.session import Session as ChatSession
from app.models.user import User
from app.schemas.session import MessageOut, SessionOut
from app.schemas.agent_context import AgentContextSnapshotOut

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _owned_session(db: Session, session_id: int, user: User) -> ChatSession:
    session = db.get(ChatSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


@router.get("", response_model=list[SessionOut])
def list_sessions(
    project_id: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ChatSession).filter(ChatSession.user_id == user.id)
    if project_id is not None:
        query = query.filter(ChatSession.project_id == project_id)
    return query.order_by(ChatSession.updated_at.desc()).all()


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def list_messages(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _owned_session(db, session_id, user)
    return (
        db.query(Message)
        .filter(Message.session_id == session.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )


@router.get("/{session_id}/agent-contexts", response_model=list[AgentContextSnapshotOut])
def list_agent_contexts(
    session_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _owned_session(db, session_id, user)
    return (
        db.query(AgentContextSnapshot)
        .filter(
            AgentContextSnapshot.session_id == session.id,
            AgentContextSnapshot.owner_id == user.id,
        )
        .order_by(AgentContextSnapshot.created_at.desc(), AgentContextSnapshot.id.desc())
        .limit(limit)
        .all()
    )


@router.delete("/{session_id}/agent-contexts")
def clear_session_agent_memory(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete auditable context snapshots and the derived session summary.

    Project versions/source files are deliberately not deleted: they are the
    product record, not conversational memory.
    """
    session = _owned_session(db, session_id, user)
    db.query(AgentContextSnapshot).filter(
        AgentContextSnapshot.session_id == session.id,
        AgentContextSnapshot.owner_id == user.id,
    ).delete(synchronize_session=False)
    db.query(AgentMemory).filter(
        AgentMemory.session_id == session.id,
        AgentMemory.owner_id == user.id,
        AgentMemory.scope == "session",
    ).delete(synchronize_session=False)
    db.commit()
    return {"ok": True}
