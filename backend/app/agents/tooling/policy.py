"""Agent-specific tool permission and input validation layer."""

from app.agents.tooling.contracts import ToolCall
from app.agents.tooling.definitions import GENERATION_TOOL_NAMES, MODIFICATION_TOOL_NAMES

_SENSITIVE_PARTS = {".env", ".git", "node_modules", "__pycache__"}
_MODIFICATION_ARTIFACT_PARTS = {"dist", "build", ".vite"}
_MAX_WRITE_SIZE = 512_000


def validate_tool_call(agent: str, call: ToolCall) -> str | None:
    allowed = GENERATION_TOOL_NAMES if agent == "generation" else MODIFICATION_TOOL_NAMES
    if call.parse_error:
        return f"Invalid tool arguments: {call.parse_error}"
    if call.name not in allowed:
        return f"Tool '{call.name}' is not allowed for {agent}"
    if call.name == "collect_assets":
        kind = str(call.arguments.get("kind") or "")
        query = call.arguments.get("query")
        if kind not in {"icon", "photo", "illustration"}:
            return "Asset kind must be icon, photo, or illustration"
        if not isinstance(query, str) or not query.strip() or len(query) > 180:
            return "Asset query must be a non-empty string of at most 180 characters"
    path = str(call.arguments.get("path") or "")
    if path:
        parts = set(path.replace("\\", "/").split("/"))
        if ".." in parts or parts & _SENSITIVE_PARTS:
            return "Tool path is outside the permitted project workspace"
        if agent == "modification" and parts & _MODIFICATION_ARTIFACT_PARTS:
            return "Modification Agent must edit source files, not generated build artifacts"
    content = call.arguments.get("content", call.arguments.get("new", ""))
    if isinstance(content, str) and len(content.encode("utf-8")) > _MAX_WRITE_SIZE:
        return "Tool write exceeds the permitted size"
    return None
