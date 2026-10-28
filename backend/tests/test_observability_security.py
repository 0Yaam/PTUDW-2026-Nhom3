import json
import uuid
from types import SimpleNamespace

import pytest
from structlog.testing import capture_logs

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
    assert valid_response.headers["Content-Security-Policy"] == (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
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


async def test_recipe_image_upload_has_stricter_rate_limit(client) -> None:
    recipe_id = uuid.uuid4()
    responses = [
        await client.post(f"/api/v1/recipes/{recipe_id}/images") for _ in range(6)
    ]

    assert responses[-1].status_code == 429
    assert responses[-1].json()["type"] == "RATE_LIMIT_EXCEEDED"


async def test_authenticated_writes_emit_audit_event(client) -> None:
    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "fullName": "Nguyen Ngoc Truong Dan",
            "email": "audit@example.com",
            "userName": "audit_dan",
            "password": "StrongPass1!",
        },
    )
    body = registered.json()

    with capture_logs() as logs:
        response = await client.patch(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {body['accessToken']}"},
            json={
                "fullName": "Nguyễn Ngọc Trường Dân",
                "userName": "audit_dan",
                "avatarUrl": None,
            },
        )

    audit = next(item for item in logs if item["event"] == "audit_http_request")
    assert response.status_code == 200
    assert audit["correlation_id"] == response.headers["X-Correlation-ID"]
    assert audit["user_id"] == body["user"]["id"]
    assert audit["actor_id"] == body["user"]["id"]
    assert audit["actor_type"] == "authenticated"
    assert audit["action"] == "replace_profile"
    assert audit["resource"] == "/api/v1/auth/me"
    assert audit["result"] == "success"
    assert audit["method"] == "PATCH"
    assert audit["path"] == "/api/v1/auth/me"
    assert audit["status"] == 200
    assert audit["elapsed_ms"] >= 0


async def test_auth_audit_does_not_log_credentials_or_tokens(client) -> None:
    password = "Never-log-this-password-1!"
    bearer = "Never-log-this-bearer-token"

    with capture_logs() as logs:
        response = await client.post(
            "/api/v1/auth/login",
            headers={"Authorization": f"Bearer {bearer}"},
            json={"email": "missing@example.com", "password": password},
        )

    audit = next(item for item in logs if item["event"] == "audit_http_request")
    serialized_logs = json.dumps(logs)
    assert response.status_code == 401
    assert audit["actor_id"] is None
    assert audit["actor_type"] == "anonymous"
    assert audit["action"] == "login"
    assert audit["resource"] == "/api/v1/auth/login"
    assert audit["result"] == "denied"
    assert password not in serialized_logs
    assert bearer not in serialized_logs


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
