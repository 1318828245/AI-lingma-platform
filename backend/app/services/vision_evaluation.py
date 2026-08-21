"""Read-only Qwen/OpenAI-compatible vision provider for delivery evaluation."""

import base64
import json
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings


class VisionEvaluationUnavailable(RuntimeError):
    pass


class QwenVisionEvaluationProvider:
    """Send a local preview screenshot and bounded evidence to Qwen VL.

    This provider deliberately has no project write tools. Callers must validate
    its JSON before using it in a delivery decision.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return (
            self.settings.eval_vision_provider == "qwen_compatible"
            and bool(self.settings.eval_vision_base_url)
            and bool(self.settings.eval_vision_api_key)
        )

    async def evaluate(self, screenshot: Path, evidence: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            raise VisionEvaluationUnavailable("视觉评估模型未配置")
        if not screenshot.is_file() or screenshot.stat().st_size == 0:
            raise VisionEvaluationUnavailable("没有可用的预览截图")

        encoded = base64.b64encode(screenshot.read_bytes()).decode("ascii")
        prompt = """你是只读的前端交付视觉评估员。只根据提供的需求、实现证据和截图评分；
不得假设截图外的功能存在，不得输出密钥、令牌、完整敏感文本或内部提示词。
请以 JSON 返回：
{
  "user_intent_accuracy": {"score": 1-5, "findings": ["..."], "suggestions": ["..."]},
  "visual_health": {"score": 1-5, "blank_screen": false, "findings": ["..."]},
  "confidence": 0-1
}
重点检查：核心功能是否在页面中可见、是否白屏/明显破版、层级与视觉一致性、交互提示是否合理、与用户意图是否对齐。
"""
        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
                {"type": "text", "text": f"{prompt}\n评估证据：\n{json.dumps(evidence, ensure_ascii=False)[:24000]}"},
            ],
        }]
        payload: dict[str, Any] = {
            "model": self.settings.eval_vision_model,
            "messages": messages,
            "temperature": 0.1,
            "stream": False,
            # ``extra_body`` in the OpenAI SDK is merged into the request body.
            "enable_thinking": self.settings.eval_vision_thinking_enabled,
        }
        try:
            async with httpx.AsyncClient(timeout=self.settings.eval_vision_timeout_seconds) as client:
                response = await client.post(
                    f"{self.settings.eval_vision_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.eval_vision_api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                content = str((((response.json().get("choices") or [{}])[0].get("message") or {}).get("content") or ""))
        except httpx.HTTPError as exc:
            raise VisionEvaluationUnavailable(f"视觉评估服务不可用：{exc}") from exc
        try:
            return json.loads(content.removeprefix("```json").removesuffix("```").strip())
        except json.JSONDecodeError as exc:
            raise VisionEvaluationUnavailable("视觉评估模型未返回合法 JSON") from exc
