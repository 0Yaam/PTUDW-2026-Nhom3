from sqlalchemy import select

from culinary_blog_api.categories import Category
from culinary_blog_api.db import SessionFactory


async def test_categories_returns_empty_list(client) -> None:
    response = await client.get("/api/v1/categories")

    assert response.status_code == 200
    assert response.json() == []


async def test_categories_returns_database_rows(client) -> None:
    async with SessionFactory() as session:
        session.add(Category(name="Mon Viet", slug="mon-viet", description=None))
        await session.commit()
        assert await session.scalar(select(Category).where(Category.slug == "mon-viet"))

    response = await client.get("/api/v1/categories")

    assert response.status_code == 200
    assert response.json()[0]["slug"] == "mon-viet"
    assert response.json()[0]["recipe_count"] == 0


async def test_liveness_does_not_require_dependencies(client) -> None:
    response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "Healthy"}


async def test_readiness_checks_database(client) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["entries"]["database"] == "Healthy"


async def test_aggregate_health_uses_readiness(client) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "Healthy"


async def test_category_detail_returns_category_with_empty_recipes(client) -> None:
    async with SessionFactory() as session:
        session.add(Category(name="Banh", slug="banh", description="Sweet things."))
        await session.commit()

    response = await client.get("/api/v1/categories/banh")

    assert response.status_code == 200
    assert response.json()["name"] == "Banh"
    assert response.json()["recipes"] == []


async def test_category_detail_returns_problem_for_unknown_slug(client) -> None:
    response = await client.get("/api/v1/categories/not-a-category")

    assert response.status_code == 404
    assert response.json()["type"] == "CATEGORY_NOT_FOUND"
