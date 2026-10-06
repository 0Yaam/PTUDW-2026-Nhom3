from types import SimpleNamespace

from culinary_blog_api.api import health


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
