"""把生成/修改过程中的事件持久化为会话消息，供重新进入页面时回放。

SSE 实时事件仍照常推送；这里只把有回放价值的事件落库。
"""

from app.core.database import SessionLocal
from app.models.message import Message


def save_message(
    session_id: int,
    msg_type: str,
    content: str,
    tool_call_json: dict | None = None,
) -> None:
    with SessionLocal() as db:
        db.add(
            Message(
                session_id=session_id,
                role="assistant",
                content=content,
                msg_type=msg_type,
                tool_call_json=tool_call_json,
            )
        )
        db.commit()


def save_generation_event(session_id: int, event: dict) -> None:
    """按事件类型映射为会话消息；流式增量与 started 事件不落库（由完成点持久化）。"""
    etype = event.get("type")
    if etype == "stage":
        save_message(session_id, "stage", str(event.get("stage", "")))
    elif etype == "thought":
        content = str(event.get("content", "")).strip()
        if content:
            save_message(session_id, "think", content)
    elif etype == "tool_call":
        args = event.get("args") or {}
        path = str(args.get("path") or "") if isinstance(args, dict) else ""
        save_message(
            session_id,
            "tool_call",
            path,
            {"tool": str(event.get("tool", ""))},
        )
    elif etype == "tool_call_completed":
        save_message(
            session_id,
            "tool_call",
            str(event.get("detail") or ""),
            {
                "tool": str(event.get("tool", "")),
                "ok": event.get("ok", True),
                "error": str(event.get("error") or ""),
            },
        )
    elif etype == "file_written":
        save_message(session_id, "file_written", str(event.get("path", "")))
    elif etype == "build_log":
        line = str(event.get("line", "")).strip()
        if line:
            save_message(session_id, "build_log", line)
    elif etype == "error":
        save_message(session_id, "error", str(event.get("error", "任务失败")))
    elif etype == "cancelled":
        save_message(session_id, "info", "已取消这次生成")
