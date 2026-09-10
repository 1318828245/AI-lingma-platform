"""Shared, bounded execution budgets for code Agents."""

from dataclasses import dataclass

from app.core.config import get_settings
from app.services.settings_store import settings_store


@dataclass(frozen=True)
class AgentBudget:
    max_model_steps: int
    max_tool_calls: int
    soft_limit_ratio: float
    max_no_progress_steps: int


class AgentBudgetPaused(Exception):
    """The Agent exhausted a fixed execution budget."""


class AgentNeedsReview(Exception):
    """The Agent repeatedly consumed tools without changing task state."""


def get_agent_budget() -> AgentBudget:
    """Read live admin overrides while retaining the legacy iteration setting."""
    settings = get_settings()
    legacy_steps = int(settings_store.get("agent_max_iterations", settings.agent_max_iterations))
    return AgentBudget(
        max_model_steps=int(settings_store.get("agent_max_model_steps", legacy_steps)),
        max_tool_calls=int(settings_store.get("agent_max_tool_calls", settings.agent_max_tool_calls)),
        soft_limit_ratio=float(settings_store.get("agent_soft_limit_ratio", settings.agent_soft_limit_ratio)),
        max_no_progress_steps=int(settings_store.get("agent_max_no_progress_steps", settings.agent_max_no_progress_steps)),
    )
