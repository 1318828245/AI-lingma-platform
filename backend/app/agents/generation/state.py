"""生成工作流状态（与提示词 6.1 状态字段对齐）。"""

from typing import Any, TypedDict


class GenerationState(TypedDict, total=False):
    generation_id: int
    project_id: int
    session_id: int
    user_id: int
    workspace: str
    requirement: str
    tech_stack: str
    llm_model: str
    parsed_requirement: dict[str, Any]
    plan: list[dict[str, str]]
    files: list[str]
    guardrails: list[dict[str, Any]]
    build_log: list[str]
    errors: list[str]
    build_attempt: int
    max_build_attempts: int
    eval_attempt: int
    max_eval_attempts: int
    token_usage: dict[str, int]
    status: str
    cancel_requested: bool
    repair_mode: bool
    summary: str
    error: str
