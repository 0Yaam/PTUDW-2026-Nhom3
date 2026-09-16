from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .model import RefreshToken, User
from .problem import AuthProblem
from .schemas import AuthResponse, LoginRequest, RegisterRequest, UserRead
from .security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)

GENERIC_LOGIN_ERROR = "Email or password is incorrect."
LOCKOUT_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


def _user_read(user: User) -> UserRead:
    return UserRead.model_validate(
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "user_name": user.user_name,
            "avatar_url": user.avatar_url,
            "roles": [user.role],
        }
    )


async def _issue_tokens(session: AsyncSession, user: User) -> AuthResponse:
    access_token, expires_at = create_access_token(user.id, user.email, user.role)
    refresh_token, token_hash, refresh_expires_at = create_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id, token_hash=token_hash, expires_at=refresh_expires_at
        )
    )
    await session.commit()
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        user=_user_read(user),
    )


async def register_user(session: AsyncSession, request: RegisterRequest) -> AuthResponse:
    existing = await session.scalar(
        select(User).where(
            or_(User.email == request.email, User.user_name == request.user_name)
        )
    )
    if existing:
        raise AuthProblem(
            409,
            "ACCOUNT_ALREADY_EXISTS",
            "Conflict",
            "Email or user name is already registered.",
        )
    user = User(
        full_name=request.full_name,
        email=request.email,
        user_name=request.user_name,
        password_hash=hash_password(request.password),
        role="Author",
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as error:
        await session.rollback()
        raise AuthProblem(
            409,
            "ACCOUNT_ALREADY_EXISTS",
            "Conflict",
            "Email or user name is already registered.",
        ) from error
    return await _issue_tokens(session, user)


async def login_user(session: AsyncSession, request: LoginRequest) -> AuthResponse:
    user = await session.scalar(select(User).where(User.email == request.email))
    if user is None:
        verify_password(request.password, DUMMY_PASSWORD_HASH)
        raise AuthProblem(401, "INVALID_CREDENTIALS", "Unauthorized", GENERIC_LOGIN_ERROR)

    now = datetime.now(UTC)
    lockout_until = user.lockout_until
    if lockout_until and lockout_until.tzinfo is None:
        lockout_until = lockout_until.replace(tzinfo=UTC)
    if lockout_until and lockout_until > now:
        raise AuthProblem(
            423,
            "ACCOUNT_LOCKED",
            "Locked",
            "Account is temporarily locked. Try again later.",
        )

    if not verify_password(request.password, user.password_hash):
        user.access_failed_count += 1
        if user.access_failed_count >= LOCKOUT_ATTEMPTS:
            user.lockout_until = now + LOCKOUT_DURATION
            await session.commit()
            raise AuthProblem(
                423,
                "ACCOUNT_LOCKED",
                "Locked",
                "Account is temporarily locked. Try again later.",
            )
        await session.commit()
        raise AuthProblem(401, "INVALID_CREDENTIALS", "Unauthorized", GENERIC_LOGIN_ERROR)

    user.access_failed_count = 0
    user.lockout_until = None
    return await _issue_tokens(session, user)
