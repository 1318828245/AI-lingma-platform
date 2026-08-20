from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GenerationCreate(BaseModel):
    requirement: str = Field(min_length=1, max_length=8000)
    session_id: int | None = None


class StackAdviceIn(BaseModel):
    requirement: str = Field(min_length=1, max_length=8000)


class StackAdviceOut(BaseModel):
    selected_stack: str
    recommended_stack: str
    needs_confirmation: bool
    reason: str


class GenerationMessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


class GenerationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    session_id: int
    status: str
    requirement: str
    error: str | None
    plan_json: dict | list | None
    llm_model: str | None
    prompt_tokens: int
    completion_tokens: int
    build_attempt: int
    eval_attempt: int
    max_build_attempts: int
    max_eval_attempts: int
    cancel_requested: bool
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
