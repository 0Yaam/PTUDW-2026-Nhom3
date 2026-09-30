from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..unit_of_work import UnitOfWork
from .model import RefreshToken, User
from .problem import AuthProblem
from .schemas import (
    AuthResponse,
    LoginRequest,
    ProfileUpdateRequest,
    RefreshTokenRequest,
    RegisterRequest,
    UserRead,
)
from .security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)

GENERIC_LOGIN_ERROR = "Email or password is incorrect."
LOCKOUT_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


def user_profile(user: User) -> UserRead:
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


async def _issue_tokens(unit_of_work: UnitOfWork, user: User) -> AuthResponse:
    access_token, access_expires_at = create_access_token(user.id, user.email, user.role)
    refresh_token, token_hash, refresh_expires_at = create_refresh_token()
    unit_of_work.refresh_tokens.add(
        RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=refresh_expires_at)
    )
    await unit_of_work.commit()
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=access_expires_at,
        user=user_profile(user),
    )


async def register_user(session: AsyncSession, request: RegisterRequest) -> AuthResponse:
    unit_of_work = UnitOfWork(session)
    existing = await unit_of_work.users.get_by_email_or_user_name(
        request.email, request.user_name
    )
    if existing is not None:
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
    unit_of_work.users.add(user)
    try:
        await unit_of_work.flush()
    except IntegrityError as error:
        await unit_of_work.rollback()
        raise AuthProblem(
            409,
            "ACCOUNT_ALREADY_EXISTS",
            "Conflict",
            "Email or user name is already registered.",
        ) from error
    return await _issue_tokens(unit_of_work, user)


async def login_user(session: AsyncSession, request: LoginRequest) -> AuthResponse:
    unit_of_work = UnitOfWork(session)
    user = await unit_of_work.users.get_by_email(request.email)
    if user is None:
        verify_password(request.password, DUMMY_PASSWORD_HASH)
        raise AuthProblem(401, "INVALID_CREDENTIALS", "Unauthorized", GENERIC_LOGIN_ERROR)

    now = datetime.now(UTC)
    lockout_until = user.lockout_until
    if lockout_until is not None and lockout_until.tzinfo is None:
        lockout_until = lockout_until.replace(tzinfo=UTC)
    if lockout_until is not None and lockout_until > now:
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
            await unit_of_work.commit()
            raise AuthProblem(
                423,
                "ACCOUNT_LOCKED",
                "Locked",
                "Account is temporarily locked. Try again later.",
            )
        await unit_of_work.commit()
        raise AuthProblem(401, "INVALID_CREDENTIALS", "Unauthorized", GENERIC_LOGIN_ERROR)

    user.access_failed_count = 0
    user.lockout_until = None
    return await _issue_tokens(unit_of_work, user)


async def refresh_tokens(
    session: AsyncSession, request: RefreshTokenRequest
) -> AuthResponse:
    unit_of_work = UnitOfWork(session)
    now = datetime.now(UTC)
    stored_token = await unit_of_work.refresh_tokens.get_by_hash(
        hash_refresh_token(request.refresh_token), for_update=True
    )
    expires_at = stored_token.expires_at if stored_token is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if (
        stored_token is None
        or stored_token.revoked_at is not None
        or expires_at is None
        or expires_at <= now
    ):
        raise AuthProblem(
            401,
            "INVALID_REFRESH_TOKEN",
            "Unauthorized",
            "Refresh token is invalid or expired.",
        )

    user = await unit_of_work.users.get(stored_token.user_id)
    if user is None:
        raise AuthProblem(
            401,
            "INVALID_REFRESH_TOKEN",
            "Unauthorized",
            "Refresh token is invalid or expired.",
        )

    stored_token.revoked_at = now
    return await _issue_tokens(unit_of_work, user)


async def logout_user(
    session: AsyncSession, user: User, request: RefreshTokenRequest
) -> None:
    unit_of_work = UnitOfWork(session)
    stored_token = await unit_of_work.refresh_tokens.get_by_hash(
        hash_refresh_token(request.refresh_token)
    )
    if (
        stored_token is None
        or stored_token.user_id != user.id
        or stored_token.revoked_at is not None
    ):
        return
    stored_token.revoked_at = datetime.now(UTC)
    await unit_of_work.commit()


async def update_profile(
    session: AsyncSession, user: User, request: ProfileUpdateRequest
) -> UserRead:
    unit_of_work = UnitOfWork(session)
    if request.user_name != user.user_name:
        taken = await unit_of_work.users.get_by_user_name_except(
            request.user_name, user.id
        )
        if taken is not None:
            raise AuthProblem(
                409, "USER_NAME_TAKEN", "Conflict", "User name is already taken."
            )

    user.full_name = request.full_name
    user.user_name = request.user_name
    user.avatar_url = request.avatar_url
    try:
        await unit_of_work.commit()
    except IntegrityError as error:
        await unit_of_work.rollback()
        raise AuthProblem(
            409, "USER_NAME_TAKEN", "Conflict", "User name is already taken."
        ) from error
    return user_profile(user)
