import jwt as pyjwt
from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import decode_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="未登录")
    return get_user_from_token(db, credentials.credentials)


def get_user_from_token(db: Session, token: str) -> User:
    try:
        payload = decode_token(token)
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=401, detail="登录状态无效或已过期")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="令牌类型错误")
    user = db.get(User, int(payload["sub"]))
    if user is None or user.status != "active":
        raise HTTPException(status_code=401, detail="账号不存在或已被禁用")
    return user


def get_current_user_sse(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> User:
    """SSE/EventSource 场景：浏览器无法自定义 header，允许 ?token= 传访问令牌。"""
    if credentials is not None:
        return get_user_from_token(db, credentials.credentials)
    if token:
        return get_user_from_token(db, token)
    raise HTTPException(status_code=401, detail="未登录")


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
