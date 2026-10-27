import base64
import binascii
import hashlib
import hmac
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ..config import get_settings

PASSWORD_ITERATIONS = 210_000
ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=7)
PASSWORD_RESET_TTL = timedelta(minutes=30)


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    session_version: int


@dataclass(frozen=True)
class PasswordResetClaims:
    user_id: uuid.UUID
    token_id: str
    expires_at: datetime


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha512", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha512${PASSWORD_ITERATIONS}${_encode(salt)}${_encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha512":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha512",
            password.encode(),
            base64.urlsafe_b64decode(salt + "=="),
            int(iterations),
        )
        return hmac.compare_digest(_encode(actual), expected)
    except (ValueError, TypeError):
        return False


DUMMY_PASSWORD_HASH = hash_password("Dummy-password-1!")


def create_access_token(
    user_id: uuid.UUID, email: str, role: str, session_version: int = 0
) -> tuple[str, datetime]:
    expires_at = datetime.now(UTC) + ACCESS_TOKEN_TTL
    header = _encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _encode(
        json.dumps(
            {
                "userId": str(user_id),
                "email": email,
                "roles": [role],
                "sessionVersion": session_version,
                "jti": str(uuid.uuid4()),
                "exp": int(expires_at.timestamp()),
            },
            separators=(",", ":"),
        ).encode()
    )
    message = f"{header}.{payload}".encode()
    secret = get_settings().jwt_secret.get_secret_value().encode()
    signature = _encode(hmac.new(secret, message, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}", expires_at


def read_access_token(token: str) -> AccessTokenClaims | None:
    """Xác minh access token và trả về user ID; token sai trả về None"""
    try:
        header_part, payload_part, signature_part = token.split(".")
        # Kiểm tra chữ ký trước khi tin dữ liệu chứa trong token
        message = f"{header_part}.{payload_part}".encode()
        secret = get_settings().jwt_secret.get_secret_value().encode()
        expected = _encode(hmac.new(secret, message, hashlib.sha256).digest())
        if not hmac.compare_digest(expected, signature_part):
            return None

        # JWT dùng HS256 — không chấp nhận thuật toán do client tự chọn
        header = json.loads(base64.urlsafe_b64decode(header_part + "=="))
        if header != {"alg": "HS256", "typ": "JWT"}:
            return None

        payload = json.loads(base64.urlsafe_b64decode(payload_part + "=="))
        if not isinstance(payload, dict):
            return None

        # Kiểm tra kiểu và giá trị thời gian hết hạn
        expires_at = payload.get("exp")
        if type(expires_at) is not int or expires_at <= datetime.now(UTC).timestamp():
            return None

        session_version = payload.get("sessionVersion")
        if type(session_version) is not int or session_version < 0:
            return None
        return AccessTokenClaims(uuid.UUID(payload["userId"]), session_version)
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, binascii.Error):
        return None


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_token() -> tuple[str, str, datetime]:
    token = secrets.token_urlsafe(64)
    return token, hash_refresh_token(token), datetime.now(UTC) + REFRESH_TOKEN_TTL


def create_password_reset_token(
    user_id: uuid.UUID,
    token_id: str | None = None,
    expires_at: datetime | None = None,
) -> tuple[str, str, datetime]:
    token_id = token_id or secrets.token_urlsafe(48)
    expires_at = expires_at or datetime.now(UTC) + PASSWORD_RESET_TTL
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    payload = _encode(
        json.dumps(
            {
                "userId": str(user_id),
                "tokenId": token_id,
                "purpose": "password-reset",
                "exp": int(expires_at.timestamp()),
            },
            separators=(",", ":"),
        ).encode()
    )
    secret = get_settings().jwt_secret.get_secret_value().encode()
    signature = _encode(hmac.new(secret, payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}", token_id, expires_at


def read_password_reset_token(token: str) -> PasswordResetClaims | None:
    try:
        payload_part, signature_part = token.split(".")
        secret = get_settings().jwt_secret.get_secret_value().encode()
        expected = _encode(hmac.new(secret, payload_part.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, signature_part):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_part + "=="))
        expires_at = payload.get("exp")
        token_id = payload.get("tokenId")
        if (
            payload.get("purpose") != "password-reset"
            or type(expires_at) is not int
            or expires_at <= datetime.now(UTC).timestamp()
            or not isinstance(token_id, str)
        ):
            return None
        return PasswordResetClaims(
            uuid.UUID(payload["userId"]), token_id, datetime.fromtimestamp(expires_at, UTC)
        )
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, binascii.Error):
        return None


def hash_password_reset_token_id(token_id: str) -> str:
    return hashlib.sha256(token_id.encode()).hexdigest()
