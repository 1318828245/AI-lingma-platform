from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Metric(Base):
    __tablename__ = "metrics"
    __table_args__ = (
        UniqueConstraint("ts", "metric_name", "labels_key", name="uq_metrics_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    labels_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    labels_key: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class DailyStat(Base):
    __tablename__ = "daily_stats"
    __table_args__ = (
        UniqueConstraint("date", "metric_name", "labels_key", name="uq_daily_stats_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    labels_key: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    total: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    avg: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    max: Mapped[float] = mapped_column(Float, default=0, nullable=False)
