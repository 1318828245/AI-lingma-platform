"""Safe, consistent event display values for tool calls."""

from app.agents.tooling.contracts import ToolCall, ToolResult


def display_args(call: ToolCall) -> dict:
    if call.name in {"read_file", "write_file", "edit_file"}:
        return {"path": call.arguments.get("path", "")}
    if call.name == "run_command":
        return {"command": call.arguments.get("command", [])}
    if call.name == "collect_assets":
        return {"kind": call.arguments.get("kind", ""), "query": call.arguments.get("query", "")}
    return {}


def display_detail(call: ToolCall) -> str:
    if call.name in {"read_file", "write_file", "edit_file"}:
        return str(call.arguments.get("path", ""))
    if call.name == "collect_assets":
        return str(call.arguments.get("query", ""))
    command = call.arguments.get("command")
    return command if isinstance(command, str) else " ".join(command or [])


def error_hint(result: ToolResult) -> str:
    return result.error[:300] if not result.ok else ""
