from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from .dependencies import get_current_user
from .model import User
from .schemas import (
    AuthResponse,
    GoogleLoginRequest,
    LoginRequest,
    ProfileUpdateRequest,
    RefreshTokenRequest,
    RegisterRequest,
    UserRead,
)
from .service import (
    google_login,
    login_user,
    logout_user,
    refresh_tokens,
    register_user,
    update_profile,
    user_profile,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthResponse:
    return await register_user(session, request)


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthResponse:
    return await login_user(session, request)


@router.post("/google", response_model=AuthResponse)
async def login_with_google(
    request: GoogleLoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthResponse:
    return await google_login(session, request)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: RefreshTokenRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthResponse:
    return await refresh_tokens(session, request)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: RefreshTokenRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    await logout_user(session, user, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserRead)
@router.get("/profile", response_model=UserRead, include_in_schema=False)
async def read_profile(
    user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    """Return the signed-in account (FR-AUTH-006). The token decides whose."""
    return user_profile(user)


@router.patch("/me", response_model=UserRead)
@router.put("/profile", response_model=UserRead, include_in_schema=False)
async def replace_profile(
    request: ProfileUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    """Update the signed-in account (FR-AUTH-007). No id in the path to tamper with."""
    return await update_profile(session, user, request)
