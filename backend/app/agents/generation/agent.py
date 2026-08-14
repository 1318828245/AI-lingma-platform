"""生成 Agent：ReAct 工具循环，让 LLM 自主读写文件完成前端工程。

工具集与提示词附录 A1 对齐：list_files / read_file / write_file / edit_file /
run_command / finish。写文件前必须过输出护轨。
"""

import json
from pathlib import Path

from app.agents.generation.nodes import (
    GenerationBlocked,
    GenerationCancelled,
    GenerationFailed,
    _check_cancel,
    _output_guardrail_check,
)
from app.agents.generation.prompts import PROMPT_GENERATION
from app.agents.generation.state import GenerationState
from app.agents.tools import edit_file, list_files, read_file, write_file
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.chat_log import save_generation_event, save_message
from app.services.events import get_broker
from app.services.llm import LLMClient
from app.services.sandbox import BuildError, run_command

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出项目工作区中的文件",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取项目中的某个文件内容",
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
            "name": "write_file",
            "description": "写入或覆盖一个文件，content 必须包含完整文件内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "局部替换文件中的一段文本，old 必须在文件中唯一存在",
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
            "name": "run_command",
            "description": "在项目目录执行白名单命令：npm/npx/node/python/python3（构建）、"
            "ls/cat/pwd/find/grep/where/dir/type/echo（只读检查）",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                    }
                },
                "required": ["command"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "完成生成，给出交付总结（summary）",
            "parameters": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
                "additionalProperties": False,
            },
        },
    },
]


def _build_system_prompt(state: GenerationState) -> str:
    parsed = state.get("parsed_requirement", {})
    plan = state.get("plan", [])
    return (
        PROMPT_GENERATION
        + "\n\n【当前项目】\n技术栈："
        + state["tech_stack"]
        + "\n需求解析："
        + json.dumps(parsed, ensure_ascii=False)
        + "\n实施计划："
        + json.dumps(plan, ensure_ascii=False)
    )


def _build_user_prompt(state: GenerationState) -> str:
    return (
        "用户需求：\n"
        + state["requirement"]
        + "\n\n请先 list_files / read_file 了解项目结构，再增量改造或新建文件，"
        "完成后调用 finish(summary) 给出交付总结。"
    )


async def _emit(state: GenerationState, event: dict) -> None:
    await get_broker().publish(state["generation_id"], event)
    # 流式增量与 started 事件由完成点统一持久化，避免碎片化
    if event.get("type") not in (
        "reasoning_delta",
        "assistant_delta",
        "tool_call_started",
    ):
        save_generation_event(state["session_id"], event)


async def _execute_tool(state: GenerationState, name: str, args: dict) -> str:
    workspace = Path(state["workspace"])
    if name == "list_files":
        return json.dumps(list_files(workspace), ensure_ascii=False)
    if name == "read_file":
        try:
            content = read_file(workspace, args["path"])
            return json.dumps(
                {"ok": True, "content": content[:6000]},
                ensure_ascii=False,
            )
        except Exception as exc:
            return json.dumps({"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False)
    if name == "write_file":
        path = args["path"]
        content = args["content"]
        _output_guardrail_check(state, path, content)
        with SessionLocal() as db:
            write_file(db, state["project_id"], workspace, path, content)
        await _emit(state, {"type": "file_written", "path": path})
        return json.dumps({"ok": True, "path": path}, ensure_ascii=False)
    if name == "edit_file":
        path, old, new = args["path"], args["old"], args["new"]
        _output_guardrail_check(state, path, new)
        try:
            with SessionLocal() as db:
                edit_file(db, state["project_id"], workspace, path, old, new)
        except Exception as exc:
            return json.dumps({"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False)
        await _emit(state, {"type": "file_written", "path": path})
        return json.dumps({"ok": True, "path": path}, ensure_ascii=False)
    if name == "run_command":
        command = args.get("command") or []
        if isinstance(command, str):
            import shlex

            command = shlex.split(command)
        if not command:
            return json.dumps({"error": "command 不能为空"}, ensure_ascii=False)
        try:
            code, output = await run_command(command, workspace, timeout=180)
        except BuildError as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)
        return json.dumps(
            {"exit_code": code, "output": output[-4000:]}, ensure_ascii=False
        )
    return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)


async def run_generation_agent(
    state: GenerationState, max_iterations: int | None = None
) -> dict:
    settings = get_settings()
    llm = LLMClient()
    workspace = Path(state["workspace"])
    workspace.mkdir(parents=True, exist_ok=True)

    messages: list[dict] = [
        {"role": "system", "content": _build_system_prompt(state)},
        {"role": "user", "content": _build_user_prompt(state)},
    ]
    token_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    summary = ""
    max_iterations = max_iterations or settings.agent_max_iterations

    for step in range(max_iterations):
        _check_cancel(state)
        async def on_reasoning(piece: str) -> None:
            await _emit(state, {"type": "reasoning_delta", "text": piece})

        async def on_content(piece: str) -> None:
            await _emit(state, {"type": "assistant_delta", "text": piece})

        message = await llm.stream_complete_with_tools(
            messages,
            TOOL_SCHEMAS,
            on_reasoning=on_reasoning,
            on_content=on_content,
        )
        reasoning = (message.get("reasoning_content") or "").strip()
        if reasoning:
            save_message(state["session_id"], "think", reasoning)
        # 通知前端本段流式输出已结束（停止“思考中”/转圈并切换 Markdown）
        await _emit(state, {"type": "stream_end"})
        usage = message.get("usage") or {}
        token_usage["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
        token_usage["completion_tokens"] += int(usage.get("completion_tokens") or 0)

        reasoning = (message.get("reasoning_content") or "").strip()
        content = (message.get("content") or "").strip()

        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            content = (message.get("content") or "").strip()
            # 模型可能直接用正文给出交付总结而不是调用 finish，首轮后视为完成
            if content and step > 0:
                state["summary"] = content
                files = list_files(workspace)
                state["files"] = files
                await _emit(
                    state,
                    {
                        "type": "thought",
                        "content": f"生成完成：共 {len(files)} 个文件，工具轮次 {step + 1}",
                    },
                )
                return {
                    "files": files,
                    "summary": content,
                    "status": "generating",
                    "token_usage": token_usage,
                }
            messages.append(
                {
                    "role": "assistant",
                    "content": content or "（未调用工具）",
                }
            )
            messages.append(
                {
                    "role": "user",
                    "content": "请通过工具完成工作，不要只输出文字；完成后调用 finish(summary)。",
                }
            )
            continue

        assistant_msg = {
            "role": "assistant",
            "content": content or "",
            "tool_calls": tool_calls,
        }
        messages.append(assistant_msg)

        for tool_call in tool_calls:
            fn = tool_call.get("function") or {}
            name = fn.get("name", "")
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args)
                if not isinstance(args, dict):
                    args = {"_raw": raw_args}
            except json.JSONDecodeError:
                args = {"_parse_error": raw_args}

            if name == "finish":
                summary = str(args.get("summary", "")).strip()
                state["summary"] = summary
                files = list_files(workspace)
                state["files"] = files
                await _emit(
                    state,
                    {
                        "type": "thought",
                        "content": f"生成完成：共 {len(files)} 个文件，工具轮次 {step + 1}",
                    },
                )
                return {
                    "files": files,
                    "summary": summary,
                    "status": "generating",
                    "token_usage": token_usage,
                }

            try:
                safe_args = _safe_tool_args(name, args)
                await _emit(
                    state,
                    {
                        "type": "tool_call_started",
                        "tool": name,
                        "args": safe_args,
                    },
                )
                result = await _execute_tool(state, name, args)
            except GenerationBlocked as exc:
                result = json.dumps({"error": str(exc)}, ensure_ascii=False)
                ok = False
            except GenerationCancelled:
                raise
            except Exception as exc:
                result = json.dumps(
                    {"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False
                )
                ok = False
            else:
                ok = _is_ok(result)
            await _emit(
                state,
                {
                    "type": "tool_call_completed",
                    "tool": name,
                    "ok": ok,
                    "detail": _tool_result_detail(name, args),
                },
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", f"call_{step}_{name}"),
                    "content": result[:4000],
                }
            )
        await _emit(
            state,
            {
                "type": "thought",
                "content": f"第 {step + 1} 轮工具调用完成（{len(tool_calls)} 个）",
            },
        )

    raise GenerationFailed(
        f"生成未在 {max_iterations} 轮工具调用内完成，已停止避免无限循环"
    )


def _safe_tool_args(name: str, args: dict) -> dict:
    if name in ("write_file", "edit_file", "read_file"):
        return {"path": args.get("path", "")}
    if name == "run_command":
        return {"command": args.get("command") or []}
    return {}


def _tool_result_detail(name: str, args: dict) -> str:
    if name in ("write_file", "edit_file", "read_file"):
        return str(args.get("path", ""))
    if name == "run_command":
        return " ".join(args.get("command") or [])
    return ""


def _is_ok(result: str) -> bool:
    try:
        data = json.loads(result)
    except json.JSONDecodeError:
        # 非 JSON 的纯文本结果视为成功（兼容旧工具返回）
        return True
    if isinstance(data, dict):
        if data.get("error"):
            return False
        exit_code = data.get("exit_code")
        if exit_code is not None:
            return exit_code == 0
    return True
