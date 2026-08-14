from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_db, require_admin
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import ResetPasswordRequest, UserAdminUpdate, UserOut
from app.services.settings_store import settings_store

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminSettingsIn(BaseModel):
    register_enabled: bool | None = None
    default_user_quota: int | None = Field(default=None, ge=0, le=100000)


class AdminSettingsOut(BaseModel):
    app_name: str
    environment: str
    register_enabled: bool
    default_user_quota: int


@router.get("/settings", response_model=AdminSettingsOut)
def get_settings_admin(
    admin: User = Depends(require_admin),
):
    settings = get_settings()
    return AdminSettingsOut(
        app_name=settings.app_name,
        environment=settings.environment,
        register_enabled=bool(
            settings_store.get("register_enabled", settings.register_enabled)
        ),
        default_user_quota=int(
            settings_store.get("default_user_quota", settings.default_user_quota)
        ),
    )


@router.put("/settings", response_model=AdminSettingsOut)
def update_settings_admin(
    payload: AdminSettingsIn,
    admin: User = Depends(require_admin),
):
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        settings_store.set(key, value)
    settings = get_settings()
    return AdminSettingsOut(
        app_name=settings.app_name,
        environment=settings.environment,
        register_enabled=bool(
            settings_store.get("register_enabled", settings.register_enabled)
        ),
        default_user_quota=int(
            settings_store.get("default_user_quota", settings.default_user_quota)
        ),
    )


@router.get("/users", response_model=list[UserOut])
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(User).order_by(User.created_at.asc()).all()


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserAdminUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.id == admin.id and (
        (payload.role is not None and payload.role != "admin")
        or (payload.status is not None and payload.status != "active")
    ):
        raise HTTPException(status_code=400, detail="不能降级或禁用当前登录的管理员")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if value is not None:
            setattr(target, key, value)
    db.commit()
    db.refresh(target)
    return UserOut.model_validate(target)


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    payload: ResetPasswordRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    target.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"ok": True}
