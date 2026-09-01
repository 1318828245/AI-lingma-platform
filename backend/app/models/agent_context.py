"""Auditable context packages assembled before an Agent invocation."""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentContextSnapshot(Base):
    __tablename__ = "agent_context_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True, nullable=False)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True, nullable=False)
    generation_id: Mapped[int | None] = mapped_column(ForeignKey("generations.id"), index=True)
    modification_id: Mapped[int | None] = mapped_column(ForeignKey("modifications.id"), index=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
