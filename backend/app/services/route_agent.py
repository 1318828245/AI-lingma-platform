"""Route Agent: advise the initial project technology stack."""

from __future__ import annotations

import json

from app.prompts import load_prompt
from app.services.llm import LLMClient


def _normalize_stack(value: object) -> str:
    text = str(value or "").strip().lower()
    return "vue3" if text in {"vue", "vue3", "vue 3"} else "html"


def _fallback_route(requirement: str) -> dict[str, str]:
    text = requirement.lower()
    signals = (
        "多页面", "多页", "路由", "仪表盘", "后台管理", "登录", "注册",
        "状态管理", "实时", "筛选", "增删改查", "表单校验", "组件库",
        "spa", "single page application", "dashboard", "router",
    )
    matched = [signal for signal in signals if signal in text]
    if len(matched) >= 2 or any(signal in text for signal in ("vue", "vue3", "vite")):
        return {
            "recommended_stack": "vue3",
            "reason": "需求包含多视图或持续交互能力，Vue 工程更适合维护。",
        }
    return {
        "recommended_stack": "html",
        "reason": "需求以单页展示为主，静态多文件页面即可满足。",
    }


async def route_tech_stack(requirement: str, selected_stack: str) -> dict[str, object]:
    """Return a validated recommendation and fail open to local routing rules."""

    fallback = _fallback_route(requirement)
    client = LLMClient()
    recommendation = fallback
    if client.mode != "mock":
        try:
            content = await client._real_complete(
                [
                    {"role": "system", "content": load_prompt("route_agent.md")},
                    {"role": "user", "content": requirement},
                ],
                json_mode=True,
            )
            parsed = json.loads(content)
            recommendation = {
                "recommended_stack": _normalize_stack(parsed.get("recommended_stack")),
                "reason": str(parsed.get("reason") or fallback["reason"])[:120],
            }
        except Exception:
            pass

    selected = _normalize_stack(selected_stack)
    recommended = _normalize_stack(recommendation["recommended_stack"])
    return {
        "selected_stack": selected,
        "recommended_stack": recommended,
        "needs_confirmation": selected != recommended,
        "reason": recommendation["reason"],
    }
