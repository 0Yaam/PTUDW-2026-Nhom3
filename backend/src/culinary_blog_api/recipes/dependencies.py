from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.model import User
from ..auth.security import read_access_token
from ..db import get_session
from .problem import RecipeProblem


def _invalid_token() -> RecipeProblem:
    return RecipeProblem(
        status=401,
        error_code="AUTH_TOKEN_INVALID",
        title="Unauthorized",
        detail="A valid access token is required.",
    )


async def get_optional_recipe_viewer(
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    """Use the shared token contract, including password-change session revocation."""
    if not authorization:
        return None
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise _invalid_token()
    claims = read_access_token(token.strip())
    if claims is None:
        raise _invalid_token()
    user = await session.get(User, claims.user_id)
    if user is None or user.session_version != claims.session_version:
        raise _invalid_token()
    return user


async def require_author_or_admin(
    user: Annotated[User | None, Depends(get_optional_recipe_viewer)],
) -> User:
    if user is None:
        raise _invalid_token()
    if user.role not in {"Author", "Admin"}:
        raise RecipeProblem(
            status=403,
            error_code="RECIPE_FORBIDDEN",
            title="Forbidden",
            detail="Only Authors and Admins can change recipes.",
        )
    return user
