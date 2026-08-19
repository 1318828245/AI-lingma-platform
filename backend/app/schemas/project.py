from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validate_project_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise ValueError("项目名称不能为空")
    if name.isdecimal():
        raise ValueError("项目名称不能是纯数字，请使用有含义的名称")
    return name


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    template: str = Field(default="blank", max_length=64)
    tech_stack: str = Field(default="static", max_length=32)
    style_preference: str = Field(default="", max_length=500)

    _name_has_meaning = field_validator("name")(_validate_project_name)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    tech_stack: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, pattern=r"^(active|archived)$")

    _name_has_meaning = field_validator("name")(
        lambda value: _validate_project_name(value) if value is not None else value
    )


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
