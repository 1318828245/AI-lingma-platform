"""LLM 适配层。

P0 默认 mock 执行器（离线可跑通整条流水线）；配置 llm_base_url/llm_api_key 后
走 OpenAI 兼容协议（/chat/completions）。LangChain 封装待环境允许后接入。
"""

import json

from app.core.config import get_settings
from app.services.model import ModelRequest, ModelResponse, ModelToolCall, OpenAICompatibleProvider


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.provider = OpenAICompatibleProvider(
            self.settings.llm_base_url, self.settings.llm_api_key
        )

    def _request(
        self, messages: list[dict], tools: list[dict] | None = None,
        json_mode: bool = False, temperature: float = 0.2, stream: bool = False,
    ) -> ModelRequest:
        return ModelRequest(
            model=self.settings.llm_model,
            messages=messages,
            tools=tools or [],
            json_mode=json_mode,
            temperature=temperature,
            stream=stream,
            reasoning_effort=self.settings.llm_reasoning_effort,
            thinking_enabled=self.settings.llm_thinking_enabled,
        )

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
        response = await self.provider.complete(
            self._request(messages, json_mode=json_mode, temperature=temperature)
        )
        return response.content

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
        return (await self.provider.complete(self._request(messages, tools, temperature=temperature))).to_wire()

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

        response = await self.provider.stream(
            self._request(messages, tools, temperature=temperature, stream=True),
            on_reasoning=on_reasoning,
            on_content=on_content,
        )
        return response.to_wire()

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
            goal = str(parsed.get("goal", ""))
            features = [str(f) for f in parsed.get("features", [])][:4]
            steps = [
                {"step": "解析需求", "detail": goal},
                {"step": "搭建页面骨架", "detail": f"按需求创建/调整页面结构（{tech_stack}）"},
            ]
            for feature in features:
                steps.append(
                    {"step": f"实现功能：{feature}", "detail": f"为「{feature}」编写交互与样式"}
                )
            steps.append({"step": "构建校验", "detail": "运行构建并修复发现的问题"})
            steps.append({"step": "交付总结", "detail": "生成会话总结"})
            return steps
        from app.agents.generation.prompts import PROMPT_CREATE_PLAN

        content = await self._real_complete(
            [
                {"role": "system", "content": PROMPT_CREATE_PLAN},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "tech_stack": tech_stack,
                            "parsed_requirement": parsed,
                        },
                        ensure_ascii=False,
                    ),
                },
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
