from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentMemory(Base):
    __tablename__ = "agent_memories"
    __table_args__ = (UniqueConstraint("owner_id", "project_id", "session_id", "scope", name="uq_agent_memory_scope"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True, nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("sessions.id"), index=True)
    scope: Mapped[str] = mapped_column(String(24), nullable=False)  # session | project
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_message_id: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
