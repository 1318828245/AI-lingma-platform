from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.message import Message
from app.models.session import Session as ChatSession
from app.models.user import User
from app.schemas.session import MessageOut, SessionOut

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
        .order_by(Message.created_at.asc())
        .all()
    )
