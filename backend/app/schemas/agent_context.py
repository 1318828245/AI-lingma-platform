from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AgentContextSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    session_id: int
    generation_id: int | None
    modification_id: int | None
    kind: str
    payload_json: dict
    char_count: int
    created_at: datetime
