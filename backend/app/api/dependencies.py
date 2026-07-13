from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, PermissionDeniedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.modules.models import User


def current_user(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError("AUTH_REQUIRED", "请先登录", 401)
    try:
        payload = decode_access_token(authorization.removeprefix("Bearer "))
        user = db.scalar(select(User).where(User.id == int(payload["sub"]), User.is_active.is_(True)))
    except (ValueError, KeyError):
        raise AppError("INVALID_TOKEN", "登录凭证无效或已过期", 401)
    if not user:
        raise AppError("INVALID_TOKEN", "用户不存在或已禁用", 401)
    return user


def require_roles(*roles: str):
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise PermissionDeniedError()
        return user
    return dependency


Teacher = Depends(require_roles("teacher", "admin"))

