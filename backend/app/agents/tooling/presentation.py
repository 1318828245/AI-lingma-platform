"""Safe, consistent event display values for tool calls."""

from app.agents.tooling.contracts import ToolCall, ToolResult


def display_args(call: ToolCall) -> dict:
    if call.name in {"read_file", "write_file", "edit_file"}:
        return {"path": call.arguments.get("path", "")}
    if call.name == "search_codebase":
        return {"query": call.arguments.get("query", "")}
    if call.name == "run_command":
        return {"command": call.arguments.get("command", [])}
    if call.name == "collect_assets":
        return {"kind": call.arguments.get("kind", ""), "query": call.arguments.get("query", "")}
    return {}


def display_detail(call: ToolCall) -> str:
    if call.name in {"read_file", "write_file", "edit_file"}:
        return str(call.arguments.get("path", ""))
    if call.name == "search_codebase":
        return str(call.arguments.get("query", ""))
    if call.name == "collect_assets":
        return str(call.arguments.get("query", ""))
    command = call.arguments.get("command")
    return command if isinstance(command, str) else " ".join(command or [])


def error_hint(result: ToolResult) -> str:
    return result.error[:300] if not result.ok else ""


def result_hint(call: ToolCall, result: ToolResult) -> str:
    if not result.ok:
        return ""
    data = result.data or {}
    if call.name == "search_codebase":
        return f"找到 {len(data.get('matches') or [])} 处"
    if call.name == "read_files":
        return f"读取 {len(data.get('files') or {})} 个文件"
    if call.name == "list_files":
        return f"发现 {len(data.get('files') or [])} 个文件"
    return ""
