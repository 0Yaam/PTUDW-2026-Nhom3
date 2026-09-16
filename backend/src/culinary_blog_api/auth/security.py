import base64
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


def create_refresh_token() -> tuple[str, str, datetime]:
    token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash, datetime.now(UTC) + REFRESH_TOKEN_TTL
