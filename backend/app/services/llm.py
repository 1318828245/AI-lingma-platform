"""LLM 适配层。

P0 默认 mock 执行器（离线可跑通整条流水线）；配置 llm_base_url/llm_api_key 后
走 OpenAI 兼容协议（/chat/completions）。LangChain 封装待环境允许后接入。
"""

import json

import httpx

from app.core.config import get_settings


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def mode(self) -> str:
        if (
            self.settings.llm_model == "mock"
            or not self.settings.llm_base_url
            or not self.settings.llm_api_key
        ):
            return "mock"
        return "real"

    async def _real_complete(
        self,
        messages: list[dict],
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> str:
        payload = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": temperature,
        }
        if self.settings.llm_reasoning_effort:
            payload["reasoning_effort"] = self.settings.llm_reasoning_effort
        if self.settings.llm_thinking_enabled:
            payload["thinking"] = {"type": "enabled"}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        temperature: float = 0.2,
    ) -> dict:
        """带工具调用的对话补全，返回 choice.message（含 tool_calls/usage）。"""
        if self.mode == "mock":
            return {
                "content": None,
                "reasoning_content": "mock：不调用真实模型",
                "tool_calls": [
                    {
                        "id": "call_mock_finish",
                        "type": "function",
                        "function": {
                            "name": "finish",
                            "arguments": json.dumps(
                                {"summary": "mock 模式：生成完成"}
                            ),
                        },
                    }
                ],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0},
            }
        payload = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": temperature,
            "tools": tools,
            "tool_choice": "auto",
        }
        if self.settings.llm_reasoning_effort:
            payload["reasoning_effort"] = self.settings.llm_reasoning_effort
        if self.settings.llm_thinking_enabled:
            payload["thinking"] = {"type": "enabled"}
        url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            body = resp.json()
        return body["choices"][0]["message"]

    async def stream_complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        on_reasoning=None,
        on_content=None,
        temperature: float = 0.2,
    ) -> dict:
        """SSE 流式工具调用补全。

        逐块回调推理内容（reasoning_content）与正文（content），返回聚合后的完整 message
        （含 tool_calls），供 ReAct 循环执行工具。
        """
        if self.mode == "mock":
            reasoning = "mock：模拟真实模型的思考过程，这里会逐字流式展示。"
            content = "mock：开始生成页面。"
            if on_reasoning:
                for piece in _chunk_text(reasoning):
                    await on_reasoning(piece)
            if on_content:
                for piece in _chunk_text(content):
                    await on_content(piece)
            return {
                "content": content,
                "reasoning_content": reasoning,
                "tool_calls": [
                    {
                        "id": "call_mock_finish",
                        "type": "function",
                        "function": {
                            "name": "finish",
                            "arguments": json.dumps(
                                {"summary": "mock 模式：生成完成"}
                            ),
                        },
                    }
                ],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0},
            }

        payload = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": temperature,
            "tools": tools,
            "tool_choice": "auto",
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if self.settings.llm_reasoning_effort:
            payload["reasoning_effort"] = self.settings.llm_reasoning_effort
        if self.settings.llm_thinking_enabled:
            payload["thinking"] = {"type": "enabled"}

        url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        message: dict = {
            "content": "",
            "reasoning_content": "",
            "tool_calls": [],
            "usage": {},
        }
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST", url, json=payload, headers=headers
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if chunk.get("usage"):
                        message["usage"] = chunk["usage"]
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    reasoning = delta.get("reasoning_content")
                    if reasoning:
                        message["reasoning_content"] += reasoning
                        if on_reasoning:
                            await on_reasoning(reasoning)
                    text = delta.get("content")
                    if text:
                        message["content"] += text
                        if on_content:
                            await on_content(text)
                    for tool_call in delta.get("tool_calls") or []:
                        index = tool_call.get("index", 0)
                        while len(message["tool_calls"]) <= index:
                            message["tool_calls"].append(
                                {
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                }
                            )
                        target = message["tool_calls"][index]
                        if tool_call.get("id"):
                            target["id"] = tool_call["id"]
                        fn = tool_call.get("function") or {}
                        if fn.get("name"):
                            target["function"]["name"] += fn["name"]
                        if fn.get("arguments"):
                            target["function"]["arguments"] += fn["arguments"]
        return message

    async def parse_requirement(self, requirement: str, tech_stack: str) -> dict:
        if self.mode == "mock":
            lines = [
                line.strip().lstrip("-• ").strip()
                for line in requirement.splitlines()
                if line.strip()
            ]
            goal = lines[0] if lines else requirement.strip()
            return {
                "goal": goal[:200],
                "pages": ["主页"],
                "features": [line[:200] for line in lines[1:6]] or ["核心内容展示"],
                "interactions": ["页面加载与基础交互"],
                "style": "现代简洁、响应式",
                "constraints": [f"tech_stack={tech_stack}"],
            }
        from app.agents.generation.prompts import PROMPT_PARSE_REQUIREMENT

        content = await self._real_complete(
            [
                {"role": "system", "content": PROMPT_PARSE_REQUIREMENT},
                {"role": "user", "content": requirement},
            ],
            json_mode=True,
        )
        return json.loads(content)

    async def create_plan(self, parsed: dict, tech_stack: str) -> list[dict]:
        if self.mode == "mock":
            return [
                {"step": "解析需求", "detail": parsed.get("goal", "")},
                {"step": "基于模板改造", "detail": f"tech_stack={tech_stack}"},
                {"step": "生成/补充页面代码", "detail": "写入与修改工程文件"},
                {"step": "构建校验与修复", "detail": "运行构建并修复问题"},
                {"step": "交付总结", "detail": "生成会话总结"},
            ]
        from app.agents.generation.prompts import PROMPT_CREATE_PLAN

        content = await self._real_complete(
            [
                {"role": "system", "content": PROMPT_CREATE_PLAN},
                {"role": "user", "content": json.dumps(parsed, ensure_ascii=False)},
            ],
            json_mode=True,
        )
        return json.loads(content)

    async def summarize(self, state: dict) -> str:
        if self.mode == "mock":
            return (
                f"已完成前端工程生成：共 {len(state.get('files', []))} 个文件，"
                f"构建尝试 {state.get('build_attempt', 0)} 次后通过。"
                f"需求目标：{state.get('parsed_requirement', {}).get('goal', '')}"
            )
        from app.agents.generation.prompts import PROMPT_GENERATION_SUMMARY

        return await self._real_complete(
            [
                {"role": "system", "content": PROMPT_GENERATION_SUMMARY},
                {"role": "user", "content": json.dumps(state, ensure_ascii=False)},
            ]
        )


def _chunk_text(text: str, size: int = 6) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]
