"""Model-provider contracts and adapters."""

from app.services.model.contracts import ModelRequest, ModelResponse, ModelToolCall
from app.services.model.openai_compatible import ModelConnectionError, OpenAICompatibleProvider

__all__ = [
    "ModelConnectionError",
    "ModelRequest",
    "ModelResponse",
    "ModelToolCall",
    "OpenAICompatibleProvider",
]
