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
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

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
