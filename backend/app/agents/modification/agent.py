"""真实 LLM 局部编辑 Agent，工具协议与生成 Agent 保持一致。"""

import json
from pathlib import Path

from app.agents.modification.state import ModificationState
from app.agents.tools import edit_file, list_files, read_file, write_file
from app.core.database import SessionLocal
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


def _safe_output(content: str) -> None:
    lowered = content.lower()
    for pattern in ("rm -rf", "drop table", "os.system(", "subprocess.call"):
        if pattern in lowered:
            raise ValueError(f"修改结果命中输出护轨：{pattern}")


async def _emit(state: ModificationState, event: dict) -> None:
    await get_broker().publish(state["modification_id"], {**event, "modification_id": state["modification_id"]})


def _system_prompt(state: ModificationState) -> str:
    return (
        "你是前端局部修改 Agent。只处理用户选中的元素和修改指令，禁止重写无关文件。"
        "必须先读取源码，优先使用 edit_file 做最小替换；不能定位时不要虚构修改，调用 finish 说明原因。\n"
        f"元素快照：{json.dumps(state.get('element_snapshot', {}), ensure_ascii=False)}\n"
        f"候选文件：{json.dumps(state.get('related_files', []), ensure_ascii=False)}"
    )


async def run_modification_agent(state: ModificationState) -> dict:
    llm = LLMClient()
    workspace = Path(state["workspace"])
    workspace.mkdir(parents=True, exist_ok=True)
    user_prompt = f"修改指令：{state['instruction']}\n请完成修改后调用 finish(summary)。"
    messages: list[dict] = [
        {"role": "system", "content": _system_prompt(state)},
        {"role": "user", "content": user_prompt},
    ]
    changed: list[str] = []
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0}

    async def on_reasoning(piece: str) -> None:
        await _emit(state, {"type": "reasoning_delta", "text": piece})

    async def on_content(piece: str) -> None:
        await _emit(state, {"type": "assistant_delta", "text": piece})

    for step in range(20):
        message = await llm.stream_complete_with_tools(
            messages,
            MODIFICATION_TOOLS,
            on_reasoning=on_reasoning,
            on_content=on_content,
        )
        await _emit(state, {"type": "stream_end"})
        usage = message.get("usage") or {}
        usage_total["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
        usage_total["completion_tokens"] += int(usage.get("completion_tokens") or 0)
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            if message.get("content"):
                return {"summary": str(message["content"]), "changed_files": changed, "token_usage": usage_total}
            messages.append({"role": "assistant", "content": "请使用工具完成修改。"})
            continue
        messages.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": tool_calls})
        for call in tool_calls:
            fn = call.get("function") or {}
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            if name == "finish":
                return {"summary": str(args.get("summary") or "修改完成"), "changed_files": changed, "token_usage": usage_total}
            await _emit(state, {"type": "tool_call_started", "tool": name, "args": {"path": args.get("path", "")} })
            ok = True
            error = ""
            try:
                if name == "list_files":
                    result = json.dumps(list_files(workspace), ensure_ascii=False)
                elif name == "read_file":
                    result = json.dumps({"ok": True, "content": read_file(workspace, args["path"])[:10000]}, ensure_ascii=False)
                elif name == "edit_file":
                    _safe_output(str(args.get("new", "")))
                    with SessionLocal() as db:
                        edit_file(db, state["project_id"], workspace, args["path"], args["old"], args["new"])
                    path = str(args["path"])
                    if path not in changed:
                        changed.append(path)
                    content = read_file(workspace, path)
                    await _emit(state, {"type": "file_written", "path": path, "content": content[:16000]})
                    result = json.dumps({"ok": True, "path": path}, ensure_ascii=False)
                elif name == "write_file":
                    _safe_output(str(args.get("content", "")))
                    with SessionLocal() as db:
                        write_file(db, state["project_id"], workspace, args["path"], args["content"])
                    path = str(args["path"])
                    if path not in changed:
                        changed.append(path)
                    await _emit(state, {"type": "file_written", "path": path, "content": str(args["content"])[:16000]})
                    result = json.dumps({"ok": True, "path": path}, ensure_ascii=False)
                else:
                    raise ValueError(f"不支持的修改工具：{name}")
            except Exception as exc:  # noqa: BLE001
                ok = False
                error = str(exc)
                result = json.dumps({"error": error}, ensure_ascii=False)
            await _emit(state, {"type": "tool_call_completed", "tool": name, "ok": ok, "detail": str(args.get("path", "")), "error": error[:300]})
            messages.append({"role": "tool", "tool_call_id": call.get("id", f"call_{step}_{name}"), "content": result[:6000]})
    raise RuntimeError("修改 Agent 未在工具轮次内完成")
