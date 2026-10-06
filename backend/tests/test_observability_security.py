import uuid
from types import SimpleNamespace

import pytest

from culinary_blog_api.api import health
from culinary_blog_api.config import Settings


async def test_readiness_lists_optional_dependencies(client) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["entries"] == {
        "database": "Healthy",
        "redis": "Disabled",
        "minio": "Disabled",
    }


async def test_readiness_fails_when_configured_redis_is_unhealthy(
    client, monkeypatch
) -> None:
    monkeypatch.setattr(
        health,
        "get_settings",
        lambda: SimpleNamespace(redis_url="redis://localhost:6379", minio_endpoint=""),
    )

    async def unavailable(_: str) -> bool:
        return False

    monkeypatch.setattr(health, "_redis_ready", unavailable)

    response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "Unhealthy"
    assert response.json()["entries"]["redis"] == "Unhealthy"


async def test_security_headers_and_correlation_ids(client) -> None:
    valid_id = "request-123_test"
    valid_response = await client.get(
        "/health", headers={"X-Correlation-ID": valid_id}
    )
    invalid_response = await client.get(
        "/health", headers={"X-Correlation-ID": "invalid correlation id"}
    )

    assert valid_response.headers["X-Correlation-ID"] == valid_id
    uuid.UUID(invalid_response.headers["X-Correlation-ID"])
    assert valid_response.headers["X-Content-Type-Options"] == "nosniff"
    assert valid_response.headers["X-Frame-Options"] == "DENY"
    assert valid_response.headers["Referrer-Policy"] == "no-referrer"
    assert valid_response.headers["Permissions-Policy"] == (
        "camera=(), microphone=(), geolocation=()"
    )


async def test_auth_responses_are_not_cached(client) -> None:
    response = await client.post("/api/v1/auth/login", json={})

    assert response.headers["Cache-Control"] == "no-store"


async def test_google_login_rate_limit_returns_problem_details(client) -> None:
    responses = [
        await client.post("/api/v1/auth/google", json={"idToken": "invalid"})
        for _ in range(6)
    ]

    response = responses[-1]
    assert response.status_code == 429
    assert response.headers["Content-Type"].startswith("application/problem+json")
    assert int(response.headers["Retry-After"]) >= 1
    assert response.json()["type"] == "RATE_LIMIT_EXCEEDED"


def test_production_rejects_default_jwt_secret() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET must be changed"):
        Settings(environment="production", _env_file=None)


def test_production_accepts_custom_jwt_secret() -> None:
    settings = Settings(
        environment="production",
        jwt_secret="a-production-secret",
        _env_file=None,
    )

    assert settings.environment == "production"
