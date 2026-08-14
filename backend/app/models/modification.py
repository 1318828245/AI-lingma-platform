from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Modification(Base):
    __tablename__ = "modifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"), index=True, nullable=False
    )
    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.id"), index=True, nullable=False
    )
    generation_id: Mapped[int | None] = mapped_column(
        ForeignKey("generations.id"), nullable=True
    )
    selector_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    element_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    related_files_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    diff_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
