"""Contracts shared by every Agent tool loop."""

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    parse_error: str = ""

    @classmethod
    def from_wire(cls, value: dict[str, Any], fallback_id: str) -> "ToolCall":
        function = value.get("function") or {}
        raw = function.get("arguments") or "{}"
        try:
            arguments = json.loads(raw)
            if not isinstance(arguments, dict):
                raise ValueError("arguments must be an object")
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            return cls(str(value.get("id") or fallback_id), str(function.get("name") or ""), {}, str(exc))
        return cls(str(value.get("id") or fallback_id), str(function.get("name") or ""), arguments)


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def to_message_content(self, limit: int = 6000) -> str:
        payload = self.data if self.ok else {"error": self.error}
        return json.dumps(payload, ensure_ascii=False)[:limit]

    @classmethod
    def from_message_content(cls, content: str) -> "ToolResult":
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return cls(True, {"output": content})
        if isinstance(data, dict) and data.get("error"):
            return cls(False, {}, str(data["error"]))
        if isinstance(data, dict) and data.get("exit_code") not in (None, 0):
            return cls(False, data, str(data.get("output") or "Command failed"))
        return cls(True, data if isinstance(data, dict) else {"result": data})
