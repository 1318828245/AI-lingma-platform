from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()
_url = settings.database_url or settings.database_url_default
if _url.startswith("sqlite:///"):
    db_path = _url[len("sqlite:///"):]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    _url,
    connect_args={"check_same_thread": False} if _url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """开发环境使用 create_all；生产/正式迁移走 Alembic。"""
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    # Local development uses create_all instead of Alembic. Keep an existing
    # SQLite workspace forward-compatible with small additive migrations.
    if engine.dialect.name == "sqlite":
        columns = {column["name"] for column in inspect(engine).get_columns("deployments")}
        if "error" not in columns:
            with engine.begin() as connection:
                connection.exec_driver_sql("ALTER TABLE deployments ADD COLUMN error VARCHAR(2000)")
