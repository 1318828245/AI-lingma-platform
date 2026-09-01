"""Optional PostgreSQL persistence for the LangGraph generation workflow."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings

_context_manager: Any = None
_checkpointer: Any = None


async def start_graph_checkpointing() -> None:
    global _context_manager, _checkpointer
    url = get_settings().database_url or get_settings().database_url_default
    if not url.startswith("postgres"):
        return
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        _context_manager = AsyncPostgresSaver.from_conn_string(url)
        _checkpointer = await _context_manager.__aenter__()
        await _checkpointer.setup()
    except Exception as exc:
        print(f"[startup] LangGraph PostgreSQL checkpoint disabled: {exc}")
        _context_manager = None
        _checkpointer = None


def get_generation_checkpointer() -> Any:
    return _checkpointer


async def stop_graph_checkpointing() -> None:
    global _context_manager, _checkpointer
    if _context_manager is not None:
        await _context_manager.__aexit__(None, None, None)
    _context_manager = None
    _checkpointer = None
