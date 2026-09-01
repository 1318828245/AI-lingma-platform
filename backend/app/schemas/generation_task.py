from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GenerationTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    generation_id: int
    sequence_no: int
    title: str
    detail: str
    status: str
    summary: str | None
    started_at: datetime | None
    finished_at: datetime | None
