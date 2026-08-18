from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModificationCreate(BaseModel):
    generation_id: int | None = None
    session_id: int | None = None
    selector: dict = Field(default_factory=dict)
    element_snapshot: dict = Field(default_factory=dict)
    instruction: str = Field(min_length=1, max_length=4000)
    related_files: list[str] = Field(default_factory=list, max_length=20)


class ModificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    session_id: int
    generation_id: int | None
    selector_json: dict | None
    element_snapshot: dict | None
    instruction: str
    related_files_json: list | None
    diff_json: dict | None
    status: str
    attempt: int
    max_attempts: int
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
