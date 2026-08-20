"""Provider-neutral model request and response contracts."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModelToolCall:
    id: str
    name: str
    arguments: str = "{}"

    @classmethod
    def from_wire(cls, value: dict[str, Any], index: int = 0) -> "ModelToolCall":
        function = value.get("function") or {}
        return cls(
            id=str(value.get("id") or f"call_{index}_{function.get('name') or 'tool'}"),
            name=str(function.get("name") or ""),
            arguments=str(function.get("arguments") or "{}"),
        )

    def to_wire(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.name, "arguments": self.arguments},
        }


@dataclass(frozen=True)
class ModelRequest:
    model: str
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] = field(default_factory=list)
    temperature: float = 0.2
    json_mode: bool = False
    stream: bool = False
    reasoning_effort: str = ""
    thinking_enabled: bool = False


@dataclass(frozen=True)
class ModelResponse:
    content: str = ""
    reasoning: str = ""
    tool_calls: list[ModelToolCall] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_wire(cls, message: dict[str, Any], usage: dict[str, Any] | None = None) -> "ModelResponse":
        return cls(
            content=str(message.get("content") or ""),
            reasoning=str(message.get("reasoning_content") or ""),
            tool_calls=[
                ModelToolCall.from_wire(call, index)
                for index, call in enumerate(message.get("tool_calls") or [])
            ],
            usage={
                key: int(value or 0)
                for key, value in (usage or message.get("usage") or {}).items()
                if key in {"prompt_tokens", "completion_tokens", "total_tokens"}
            },
        )

    def to_wire(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "reasoning_content": self.reasoning,
            "tool_calls": [call.to_wire() for call in self.tool_calls],
            "usage": self.usage,
        }
