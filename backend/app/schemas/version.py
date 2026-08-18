from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    version_no: int
    source_type: str
    source_id: int | None
    summary: str | None
    file_count: int
    created_at: datetime


class VersionFileDiff(BaseModel):
    path: str
    status: str
    diff: str


class ProjectVersionDiffOut(BaseModel):
    version_id: int
    version_no: int
    files: list[VersionFileDiff]


class RollbackOut(BaseModel):
    version: ProjectVersionOut
    restored_files: list[str]
