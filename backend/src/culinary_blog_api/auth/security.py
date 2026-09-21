import base64
import binascii
import hashlib
import hmac
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from ..config import get_settings

PASSWORD_ITERATIONS = 210_000
ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=7)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha512", password.encode(), salt, PASSWORD_ITERATIONS
    )
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
    user_id: uuid.UUID, email: str, role: str
) -> tuple[str, datetime]:
    expires_at = datetime.now(UTC) + ACCESS_TOKEN_TTL
    header = _encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _encode(
        json.dumps(
            {
                "userId": str(user_id),
                "email": email,
                "roles": [role],
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


def read_access_token(token: str) -> uuid.UUID | None:
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

        return uuid.UUID(payload["userId"])
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, binascii.Error):
        return None


def create_refresh_token() -> tuple[str, str, datetime]:
    token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash, datetime.now(UTC) + REFRESH_TOKEN_TTL
