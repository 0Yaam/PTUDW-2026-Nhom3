from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from .model import User
from .problem import AuthProblem
from .security import read_access_token

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Xác minh Bearer token và tải tài khoản hiện còn tồn tại."""
    user_id = read_access_token(credentials.credentials) if credentials else None
    if user_id is None:
        raise AuthProblem(401, "UNAUTHORIZED", "Unauthorized", "Sign in is required.")

    user = await session.get(User, user_id)
    if user is None:
        raise AuthProblem(401, "UNAUTHORIZED", "Unauthorized", "Sign in is required.")

    return user


async def require_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Chỉ cho Admin truy cập; role được đọc từ database."""
    if user.role != "Admin":
        raise AuthProblem(403, "FORBIDDEN", "Forbidden", "Admin access is required.")

    return user