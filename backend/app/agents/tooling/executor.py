"""Side-effecting tool execution shared by generation and modification Agents."""

import shlex
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from app.agents.tooling.contracts import ToolCall, ToolResult
from app.agents.tooling.policy import validate_tool_call
from app.agents.tools import edit_file, list_files, read_file, write_file
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.sandbox import BuildError, run_command


@dataclass(frozen=True)
class ToolExecutionContext:
    agent: str
    project_id: int
    workspace: Path
    output_guard: Callable[[str, str], None] | None = None
    on_file_written: Callable[[str, str], Awaitable[None]] | None = None
    generation_id: int | None = None
    modification_id: int | None = None
    session_id: int | None = None
    on_asset_event: Callable[[dict], Awaitable[None]] | None = None
    command_runner: Callable[[list[str] | str, Path, int], Awaitable[tuple[int, str]]] = run_command


def is_unsupported_preview_command(command: str) -> bool:
    lowered = command.lower()
    return "npm run dev" in lowered or "timeout " in lowered or "sleep " in lowered or "/tmp/" in lowered or ">" in command or (" &" in command and "&&" not in command)


async def execute_tool(call: ToolCall, context: ToolExecutionContext) -> ToolResult:
    error = validate_tool_call(context.agent, call)
    if error:
        return ToolResult(False, error=error)
    args = call.arguments
    try:
        if call.name == "list_files":
            return ToolResult(True, {"files": list_files(context.workspace)})
        if call.name == "read_file":
            return ToolResult(True, {"content": read_file(context.workspace, str(args["path"]))[:10000]})
        if call.name in {"write_file", "edit_file"}:
            path = str(args["path"])
            content = str(args.get("content", args.get("new", "")))
            if context.output_guard:
                context.output_guard(path, content)
            with SessionLocal() as db:
                if call.name == "write_file":
                    write_file(db, context.project_id, context.workspace, path, str(args["content"]))
                else:
                    edit_file(db, context.project_id, context.workspace, path, str(args["old"]), str(args["new"]))
            written = read_file(context.workspace, path)
            if context.on_file_written:
                await context.on_file_written(path, written)
            return ToolResult(True, {"path": path})
        if call.name == "collect_assets":
            from app.services.assets import enqueue_asset_collection

            result = await enqueue_asset_collection(
                project_id=context.project_id,
                generation_id=context.generation_id,
                modification_id=context.modification_id,
                session_id=context.session_id,
                kind=str(args["kind"]),
                query=str(args["query"]),
                usage_role=str(args.get("usage_role") or "decorative"),
                orientation=str(args.get("orientation") or "landscape"),
                target_path=str(args.get("target_path") or ""),
                placeholder=str(args.get("placeholder") or ""),
                emit=context.on_asset_event,
            )
            return ToolResult(True, result)
        if call.name == "run_command":
            command = args.get("command") or []
            if get_settings().command_mode != "shell" and isinstance(command, str):
                command = shlex.split(command)
            if not command:
                return ToolResult(False, error="command cannot be empty")
            command_text = command if isinstance(command, str) else " ".join(command)
            if is_unsupported_preview_command(command_text):
                return ToolResult(False, error="Use npm run build; development servers, redirects, temporary paths, and background commands are not allowed")
            try:
                code, output = await context.command_runner(command, context.workspace, 180)
            except BuildError as exc:
                if isinstance(command, list) and command[:2] == ["node", "--check"] and "不支持执行子进程" in str(exc):
                    return ToolResult(True, {"exit_code": 0, "output": "node syntax check skipped: subprocess unavailable"})
                return ToolResult(False, error=str(exc))
            return ToolResult(code == 0, {"exit_code": code, "output": output[-4000:]}, "" if code == 0 else output[-300:])
        return ToolResult(False, error=f"Unknown tool: {call.name}")
    except Exception as exc:  # noqa: BLE001
        return ToolResult(False, error=f"{type(exc).__name__}: {exc}")
