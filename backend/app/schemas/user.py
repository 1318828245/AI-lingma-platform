from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    status: str
    quota: int
    used_count: int
    created_at: datetime


class UserAdminUpdate(BaseModel):
    role: str | None = Field(default=None, pattern=r"^(admin|user)$")
    status: str | None = Field(default=None, pattern=r"^(active|disabled)$")
    quota: int | None = Field(default=None, ge=0, le=100000)


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=6, max_length=128)
