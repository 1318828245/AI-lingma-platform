"""OpenAI Chat Completions compatible provider implementation."""

import json
from collections.abc import Awaitable, Callable

import httpx

from app.services.model.contracts import ModelRequest, ModelResponse, ModelToolCall


class ModelConnectionError(RuntimeError):
    """A provider request could not be completed."""


class OpenAICompatibleProvider:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _payload(self, request: ModelRequest) -> dict:
        payload: dict = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
        }
        if request.tools:
            payload.update({"tools": request.tools, "tool_choice": "auto"})
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}
        if request.reasoning_effort:
            payload["reasoning_effort"] = request.reasoning_effort
        if request.thinking_enabled:
            payload["thinking"] = {"type": "enabled"}
        return payload

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def complete(self, request: ModelRequest) -> ModelResponse:
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=self._payload(request),
                    headers=self._headers,
                )
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError as exc:
            raise ModelConnectionError(str(exc)) from exc
        choices = body.get("choices") or []
        if not choices:
            raise ModelConnectionError("Model response contained no choices")
        return ModelResponse.from_wire(choices[0].get("message") or {}, body.get("usage"))

    async def stream(
        self,
        request: ModelRequest,
        on_reasoning: Callable[[str], Awaitable[None]] | None = None,
        on_content: Callable[[str], Awaitable[None]] | None = None,
    ) -> ModelResponse:
        payload = self._payload(request)
        payload.update({"stream": True, "stream_options": {"include_usage": True}})
        content = ""
        reasoning = ""
        usage: dict[str, int] = {}
        calls: dict[int, dict[str, str]] = {}
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream("POST", f"{self.base_url}/chat/completions", json=payload, headers=self._headers) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        if chunk.get("usage"):
                            # Providers may include nested details such as
                            # ``completion_tokens_details``.  Only the shared
                            # scalar counters belong to our contract.
                            usage = {
                                key: int(value or 0)
                                for key, value in chunk["usage"].items()
                                if key in {"prompt_tokens", "completion_tokens", "total_tokens"}
                            }
                        choices = chunk.get("choices") or []
                        if not choices:
                            continue
                        delta = choices[0].get("delta") or {}
                        piece = str(delta.get("reasoning_content") or "")
                        if piece:
                            reasoning += piece
                            if on_reasoning:
                                await on_reasoning(piece)
                        piece = str(delta.get("content") or "")
                        if piece:
                            content += piece
                            if on_content:
                                await on_content(piece)
                        for raw_call in delta.get("tool_calls") or []:
                            index = int(raw_call.get("index", 0))
                            target = calls.setdefault(index, {"id": "", "name": "", "arguments": ""})
                            target["id"] = str(raw_call.get("id") or target["id"])
                            function = raw_call.get("function") or {}
                            target["name"] += str(function.get("name") or "")
                            target["arguments"] += str(function.get("arguments") or "")
        except httpx.HTTPError as exc:
            raise ModelConnectionError(str(exc)) from exc
        return ModelResponse(
            content=content,
            reasoning=reasoning,
            tool_calls=[ModelToolCall(**calls[index]) for index in sorted(calls)],
            usage=usage,
        )
