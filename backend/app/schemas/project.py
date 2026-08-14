from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    template: str = Field(default="blank", max_length=64)
    tech_stack: str = Field(default="static", max_length=32)
    style_preference: str = Field(default="", max_length=500)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    tech_stack: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, pattern=r"^(active|archived)$")


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    slug: str
    description: str
    template: str
    tech_stack: str
    status: str
    created_at: datetime
    updated_at: datetime
