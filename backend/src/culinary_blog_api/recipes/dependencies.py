import base64
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.model import User
from ..config import get_settings
from ..db import get_session
from .problem import RecipeProblem


def _decode_segment(segment: str) -> dict[str, object]:
    padding = "=" * (-len(segment) % 4)
    value = base64.urlsafe_b64decode(segment + padding)
    decoded = json.loads(value)
    if not isinstance(decoded, dict):
        raise ValueError("JWT segment must be an object")
    return decoded


def _invalid_token(error_code: str = "AUTH_TOKEN_INVALID") -> RecipeProblem:
    return RecipeProblem(
        status=401,
        error_code=error_code,
        title="Unauthorized",
        detail="A valid access token is required.",
    )


def _user_id_from_token(token: str) -> uuid.UUID:
    try:
        encoded_header, encoded_payload, supplied_signature = token.split(".")
        header = _decode_segment(encoded_header)
        claims = _decode_segment(encoded_payload)
        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            raise ValueError("Unsupported JWT header")

        message = f"{encoded_header}.{encoded_payload}".encode()
        secret = get_settings().jwt_secret.get_secret_value().encode()
        expected_signature = base64.urlsafe_b64encode(
            hmac.new(secret, message, hashlib.sha256).digest()
        ).rstrip(b"=").decode("ascii")
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise ValueError("Invalid JWT signature")

        expires_at = claims.get("exp")
        if not isinstance(expires_at, int):
            raise ValueError("Invalid JWT expiry")
        if expires_at <= int(datetime.now(UTC).timestamp()):
            raise _invalid_token("AUTH_TOKEN_EXPIRED")
        return uuid.UUID(str(claims["userId"]))
    except RecipeProblem:
        raise
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise _invalid_token() from error


async def require_author_or_admin(
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization:
        raise _invalid_token()
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise _invalid_token()

    user = await session.get(User, _user_id_from_token(token.strip()))
    if user is None:
        raise _invalid_token()
    if user.role not in {"Author", "Admin"}:
        raise RecipeProblem(
            status=403,
            error_code="RECIPE_FORBIDDEN",
            title="Forbidden",
            detail="Only Authors and Admins can create recipes.",
        )
    return user
