import uuid

from sqlalchemy import select

from culinary_blog_api.auth import User
from culinary_blog_api.auth.security import create_access_token, hash_password
from culinary_blog_api.categories import Category
from culinary_blog_api.db import SessionFactory
from culinary_blog_api.seed import seed


async def auth_headers(role: str) -> dict[str, str]:
    """Create a real database user and signed token for route permission tests."""
    user_id = uuid.uuid4()
    email = f"{user_id}@example.com"
    async with SessionFactory() as session:
        session.add(
            User(
                id=user_id,
                full_name="Category tester",
                email=email,
                user_name=f"user{user_id.hex[:12]}",
                password_hash=hash_password("StrongPass1!"),
                role=role,
            )
        )
        await session.commit()
    token, _ = create_access_token(user_id, email, role)
    return {"Authorization": f"Bearer {token}"}

async def test_create_category_requires_login(client) -> None:
    response = await client.post(
        "/api/v1/categories",
        json={"name": "Món Việt", "description": "Món ăn gia đình"},
    )
    assert response.status_code == 401
    assert response.json()["status"] == 401
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_create_and_update_reject_non_admin(client) -> None:
    headers = await auth_headers("Author")
    category_id = uuid.uuid4()
    create = await client.post(
        "/api/v1/categories", json={"name": "Món Việt"}, headers=headers
    )
    update = await client.put(
        f"/api/v1/categories/{category_id}",
        json={"name": "Món Việt"},
        headers=headers,
    )
    assert create.status_code == update.status_code == 403
    assert create.json()["type"] == "FORBIDDEN"


async def test_admin_creates_vietnamese_category_and_slug_collision(client) -> None:
    headers = await auth_headers("Admin")
    first = await client.post(
        "/api/v1/categories",
        json={"name": "Món Việt", "description": "Bữa cơm nhà"},
        headers=headers,
    )
    second = await client.post(
        "/api/v1/categories", json={"name": "Mon Viet"}, headers=headers
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["slug"] == "mon-viet"
    assert second.json()["slug"] == "mon-viet-2"
    assert first.headers["location"] == "/api/v1/categories/mon-viet"
    assert second.headers["location"] == "/api/v1/categories/mon-viet-2"


async def test_duplicate_and_invalid_category_values(client) -> None:
    headers = await auth_headers("Admin")
    await client.post("/api/v1/categories", json={"name": "Món Việt"}, headers=headers)
    duplicate = await client.post(
        "/api/v1/categories", json={"name": " món việt "}, headers=headers
    )
    invalid = await client.post(
        "/api/v1/categories", json={"name": "<b>Food</b>"}, headers=headers
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["type"] == "CATEGORY_NAME_EXISTS"
    assert invalid.status_code == 422
    assert "name" in invalid.json()["errors"]


async def test_admin_update_keeps_slug_and_checks_errors(client) -> None:
    headers = await auth_headers("Admin")
    first = await client.post(
        "/api/v1/categories", json={"name": "Breakfast"}, headers=headers
    )
    await client.post("/api/v1/categories", json={"name": "Dinner"}, headers=headers)
    category_id = first.json()["id"]
    updated = await client.put(
        f"/api/v1/categories/{category_id}",
        json={"name": "Morning Meals", "description": "Fast and simple"},
        headers=headers,
    )
    duplicate = await client.put(
        f"/api/v1/categories/{category_id}", json={"name": "Dinner"}, headers=headers
    )
    invalid = await client.put(
        f"/api/v1/categories/{category_id}", json={"name": "X"}, headers=headers
    )
    missing = await client.put(
        f"/api/v1/categories/{uuid.uuid4()}", json={"name": "Other"}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["slug"] == "breakfast"
    assert updated.json()["name"] == "Morning Meals"
    assert duplicate.status_code == 409
    assert invalid.status_code == 422
    assert missing.status_code == 404


async def test_seed_does_not_overwrite_admin_edit(client) -> None:
    await seed()
    async with SessionFactory() as session:
        category = await session.scalar(select(Category).where(Category.slug == "breakfast"))
        assert category is not None
        category.name = "Morning Meals"
        await session.commit()
    await seed()
    response = await client.get("/api/v1/categories")
    assert any(item["name"] == "Morning Meals" for item in response.json())

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
