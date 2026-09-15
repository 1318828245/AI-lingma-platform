"""Detect repeated exploration without punishing useful inspection work."""

import json

from app.agents.tooling.contracts import ToolCall, ToolResult


_MUTATING_TOOLS = {"write_file", "write_files", "edit_file", "collect_assets"}
_EXPLORATION_TOOLS = {"list_files", "read_file", "read_files", "search_codebase", "run_command"}


def _signature(call: ToolCall, result: ToolResult) -> str:
    """Only equivalent requests with equivalent outcomes are considered repeats."""
    args = call.arguments
    if call.name == "read_file":
        payload = {"path": args.get("path")}
    elif call.name == "read_files":
        payload = {"paths": args.get("paths")}
    elif call.name == "search_codebase":
        payload = {"query": str(args.get("query") or "").strip().lower()}
    elif call.name == "run_command":
        payload = {"command": args.get("command")}
    else:
        payload = args
    return json.dumps({"tool": call.name, "args": payload, "ok": result.ok, "result": result.data}, ensure_ascii=False, sort_keys=True, default=str)[:8000]


class ExplorationProgress:
    """Track consecutive repeated observation calls inside one Agent invocation."""

    def __init__(self) -> None:
        self._last_signature: str | None = None
        self.repeat_streak = 0

    def observe(self, call: ToolCall, result: ToolResult) -> int:
        if call.name in _MUTATING_TOOLS and result.ok:
            self._last_signature = None
            self.repeat_streak = 0
            return 0
        if call.name not in _EXPLORATION_TOOLS:
            self._last_signature = None
            self.repeat_streak = 0
            return 0
        signature = _signature(call, result)
        if result.ok and signature != self._last_signature:
            self._last_signature = signature
            self.repeat_streak = 0
        else:
            self._last_signature = signature
            self.repeat_streak += 1
        return self.repeat_streak
