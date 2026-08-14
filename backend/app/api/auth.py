from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenPair
from app.schemas.user import UserOut
from app.services.settings_store import settings_store

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LoginResponse(TokenPair):
    user: UserOut


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserOut:
    settings = get_settings()
    enabled = settings_store.get("register_enabled", settings.register_enabled)
    if not enabled:
        raise HTTPException(status_code=403, detail="注册未开放")
    exists = (
        db.query(User).filter(User.username == payload.username).first()
    )
    if exists is not None:
        raise HTTPException(status_code=409, detail="用户名已存在")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        email=payload.email,
        role="user",
        status="active",
        quota=int(settings_store.get("default_user_quota", settings.default_user_quota)),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号已被禁用")
    return LoginResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.post("/refresh")
def refresh(payload: RefreshRequest) -> TokenPair:
    try:
        data = decode_token(payload.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="刷新令牌无效或已过期")
    if data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="令牌类型错误")
    user_id = int(data["sub"])
    return TokenPair(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.post("/logout")
def logout() -> dict:
    # P0 无状态 JWT，登出由前端丢弃令牌；黑名单在 M5 权限强化时补齐。
    return {"ok": True}
