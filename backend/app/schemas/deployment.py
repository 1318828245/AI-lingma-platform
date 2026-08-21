from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeploymentCreate(BaseModel):
    version_id: int | None = Field(default=None, gt=0)


class DeploymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    version: int
    status: str
    url: str | None
    slug: str
    error: str | None
    is_active: bool
    site_url: str | None = None
    created_at: datetime
    updated_at: datetime
