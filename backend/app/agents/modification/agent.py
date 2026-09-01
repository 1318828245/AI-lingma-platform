"""真实 LLM 局部编辑 Agent，工具协议与生成 Agent 保持一致。"""

import json
from pathlib import Path

from app.agents.modification.state import ModificationState
from app.agents.budget import AgentBudgetPaused, AgentNeedsReview, get_agent_budget
from app.agents.tooling.contracts import ToolCall
from app.agents.tooling.definitions import MODIFICATION_TOOL_NAMES, tool_schemas
from app.agents.tooling.executor import ToolExecutionContext, execute_tool
from app.agents.tooling.presentation import display_args, display_detail, error_hint
from app.agents.tools import edit_file, list_files, read_file, write_file
from app.core.database import SessionLocal
from app.prompts import render_prompt
from app.services.chat_log import save_generation_event
from app.services.agent_context import render_context_for_agent
from app.services.events import get_broker
from app.services.llm import LLMClient

MODIFICATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出项目文件，只用于确认相关源码文件",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取相关源码文件",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "局部替换源码；old 必须是文件中原样存在的片段，禁止改动无关代码",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old": {"type": "string"},
                    "new": {"type": "string"},
                },
                "required": ["path", "old", "new"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "仅当必须新增文件时使用，content 必须是完整文件内容",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "修改完成后给出简短总结",
            "parameters": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
                "additionalProperties": False,
            },
        },
    },
]

MODIFICATION_TOOLS = tool_schemas(MODIFICATION_TOOL_NAMES)


def _safe_output(content: str) -> None:
    lowered = content.lower()
    for pattern in ("rm -rf", "drop table", "os.system(", "subprocess.call"):
        if pattern in lowered:
            raise ValueError(f"修改结果命中输出护轨：{pattern}")


async def _emit(state: ModificationState, event: dict) -> None:
    await get_broker().publish(state["modification_id"], {**event, "modification_id": state["modification_id"]})
    if event.get("type") in {"asset_collection_started", "asset_collection_completed"}:
        save_generation_event(state["session_id"], event)


def _system_prompt(state: ModificationState) -> str:
    return render_prompt(
        "modification_agent.md",
        element_snapshot=json.dumps(state.get("element_snapshot", {}), ensure_ascii=False),
        related_files=json.dumps(state.get("related_files", []), ensure_ascii=False),
    )


async def run_modification_agent(
    state: ModificationState,
    max_model_steps: int | None = None,
    max_tool_calls: int | None = None,
) -> dict:
    llm = LLMClient()
    workspace = Path(state["workspace"])
    workspace.mkdir(parents=True, exist_ok=True)
    user_prompt = state["instruction"] + render_context_for_agent(state.get("context_package", {}))
    messages: list[dict] = [
        {"role": "system", "content": _system_prompt(state)},
        {"role": "user", "content": user_prompt},
    ]
    changed: list[str] = []
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0}
    budget = get_agent_budget()
    max_model_steps = max_model_steps or budget.max_model_steps
    max_tool_calls = max_tool_calls or budget.max_tool_calls
    tool_calls_used = 0
    no_progress_steps = 0
    soft_limit_announced = False

    async def on_reasoning(piece: str) -> None:
        await _emit(state, {"type": "reasoning_delta", "text": piece})

    async def on_content(piece: str) -> None:
        await _emit(state, {"type": "assistant_delta", "text": piece})

    for step in range(max_model_steps):
        message = await llm.stream_complete_with_tools(
            messages,
            MODIFICATION_TOOLS,
            on_reasoning=on_reasoning,
            on_content=on_content,
        )
        if not soft_limit_announced and step + 1 >= max(1, int(max_model_steps * budget.soft_limit_ratio)):
            soft_limit_announced = True
            await _emit(state, {"type": "budget_warning", "kind": "model_steps", "used": step + 1, "limit": max_model_steps})
        await _emit(state, {"type": "stream_end"})
        usage = message.get("usage") or {}
        usage_total["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
        usage_total["completion_tokens"] += int(usage.get("completion_tokens") or 0)
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            if message.get("content"):
                return {"summary": str(message["content"]), "changed_files": changed, "token_usage": usage_total}
            messages.append({"role": "assistant", "content": "Use the available tools to complete the requested source change."})
            no_progress_steps += 1
            if no_progress_steps >= budget.max_no_progress_steps:
                raise AgentNeedsReview("连续模型决策未产生可执行工具调用，请补充修改目标后继续")
            continue
        messages.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": tool_calls})
        executable_calls = [
            raw for raw in tool_calls
            if ToolCall.from_wire(raw, "budget_check").name != "finish"
        ]
        if tool_calls_used + len(executable_calls) > max_tool_calls:
            raise AgentBudgetPaused(f"工具调用达到上限（{max_tool_calls}）；当前进度已保存，可继续执行")
        for index, raw_call in enumerate(tool_calls):
            call = ToolCall.from_wire(raw_call, f"call_{step}_{index}")
            if call.name == "finish":
                return {"summary": str(call.arguments.get("summary") or "修改完成"), "changed_files": changed, "token_usage": usage_total}
            tool_calls_used += 1
            await _emit(state, {"type": "tool_call_started", "tool": call.name, "tool_call_id": call.id, "args": display_args(call)})

            async def on_file_written(path: str, content: str) -> None:
                if path not in changed:
                    changed.append(path)
                await _emit(state, {"type": "file_written", "path": path, "content": content[:16000]})

            result = await execute_tool(
                call,
                ToolExecutionContext(
                    agent="modification",
                    project_id=state["project_id"],
                    workspace=workspace,
                    output_guard=lambda _path, content: _safe_output(content),
                    on_file_written=on_file_written,
                    modification_id=state["modification_id"],
                    session_id=state["session_id"],
                    on_asset_event=lambda event: _emit(state, event),
                ),
            )
            if result.ok and call.name in {"write_file", "write_files", "edit_file", "collect_assets"}:
                no_progress_steps = 0
            else:
                no_progress_steps += 1
            if no_progress_steps >= budget.max_no_progress_steps:
                raise AgentNeedsReview(
                    f"连续 {no_progress_steps} 次工具调用未产生文件或素材进展，请人工确认后继续"
                )
            await _emit(state, {"type": "tool_call_completed", "tool": call.name, "tool_call_id": call.id, "ok": result.ok, "detail": display_detail(call), "error": error_hint(result)})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result.to_message_content()})
    raise AgentBudgetPaused(f"已使用完 {max_model_steps} 个模型决策轮次；当前进度已保存，可继续执行")
