import uuid

from sqlalchemy import select

from culinary_blog_api.auth import User
from culinary_blog_api.auth.security import create_access_token, hash_password
from culinary_blog_api.categories import Category
from culinary_blog_api.config import Settings
from culinary_blog_api.db import SessionFactory
from culinary_blog_api.recipes import Recipe, RecipeStatus
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


async def add_referenced_recipes(category_id: uuid.UUID) -> None:
    """Create draft and published recipes to prove every status blocks deletion."""
    author_id = uuid.uuid4()
    async with SessionFactory() as session:
        session.add(
            User(
                id=author_id,
                full_name="Recipe owner",
                email=f"{author_id}@example.com",
                user_name=f"author{author_id.hex[:10]}",
                password_hash=hash_password("StrongPass1!"),
                role="Author",
            )
        )
        for title, status in (
            ("Private draft", RecipeStatus.DRAFT),
            ("Public recipe", RecipeStatus.PUBLISHED),
        ):
            session.add(
                Recipe(
                    title=title,
                    slug=f"{title.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}",
                    description="Category deletion guard",
                    prep_time_minutes=10,
                    cook_time_minutes=5,
                    servings=2,
                    difficulty=1,
                    status=status,
                    category_id=category_id,
                    author_id=author_id,
                )
            )
        await session.commit()


async def test_create_category_requires_login(client) -> None:
    response = await client.post(
        "/api/v1/categories",
        json={"name": "Món Việt", "description": "Món ăn gia đình"},
    )
    assert response.status_code == 401
    assert response.json()["status"] == 401
    assert response.headers["content-type"].startswith("application/problem+json")

    delete = await client.delete(f"/api/v1/categories/{uuid.uuid4()}")
    assert delete.status_code == 401
    assert delete.headers["content-type"].startswith("application/problem+json")


async def test_category_writes_reject_non_admin(client) -> None:
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
    delete = await client.delete(f"/api/v1/categories/{category_id}", headers=headers)
    assert create.status_code == update.status_code == delete.status_code == 403
    assert create.json()["type"] == "FORBIDDEN"
    assert delete.headers["content-type"].startswith("application/problem+json")
    assert delete.json()["type"] == "FORBIDDEN"


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


async def test_admin_can_explicitly_change_slug(client) -> None:
    headers = await auth_headers("Admin")
    first = await client.post(
        "/api/v1/categories", json={"name": "Main dishes"}, headers=headers
    )
    await client.post(
        "/api/v1/categories", json={"name": "Family meals"}, headers=headers
    )
    category_id = first.json()["id"]

    updated = await client.put(
        f"/api/v1/categories/{category_id}",
        json={"name": "Main dishes", "slug": "featured-dishes"},
        headers=headers,
    )
    duplicate = await client.put(
        f"/api/v1/categories/{category_id}",
        json={"name": "Main dishes", "slug": "family-meals"},
        headers=headers,
    )
    invalid = await client.put(
        f"/api/v1/categories/{category_id}",
        json={"name": "Main dishes", "slug": "Invalid Slug"},
        headers=headers,
    )

    assert updated.status_code == 200
    assert updated.json()["slug"] == "featured-dishes"
    assert duplicate.status_code == 409
    assert duplicate.json()["type"] == "CATEGORY_SLUG_EXISTS"
    assert invalid.status_code == 422
    assert "slug" in invalid.json()["errors"]


async def test_admin_deletes_empty_category(client) -> None:
    headers = await auth_headers("Admin")
    created = await client.post(
        "/api/v1/categories", json={"name": "Temporary category"}, headers=headers
    )
    category_id = uuid.UUID(created.json()["id"])

    deleted = await client.delete(f"/api/v1/categories/{category_id}", headers=headers)

    assert deleted.status_code == 204
    assert deleted.content == b""
    async with SessionFactory() as session:
        assert await session.get(Category, category_id) is None

    missing = await client.delete(f"/api/v1/categories/{category_id}", headers=headers)
    assert missing.status_code == 404
    assert missing.headers["content-type"].startswith("application/problem+json")
    assert missing.json()["type"] == "CATEGORY_NOT_FOUND"


async def test_admin_cannot_delete_category_with_any_recipes(client) -> None:
    headers = await auth_headers("Admin")
    created = await client.post(
        "/api/v1/categories", json={"name": "Protected category"}, headers=headers
    )
    category_id = uuid.UUID(created.json()["id"])
    await add_referenced_recipes(category_id)

    updated = await client.put(
        f"/api/v1/categories/{category_id}",
        json={"name": "Protected category renamed"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["recipe_count"] == 2

    blocked = await client.delete(f"/api/v1/categories/{category_id}", headers=headers)

    assert blocked.status_code == 409
    assert blocked.headers["content-type"].startswith("application/problem+json")
    assert blocked.json()["type"] == "CATEGORY_IN_USE"
    assert "2 recipes" in blocked.json()["detail"]
    async with SessionFactory() as session:
        assert await session.get(Category, category_id) is not None

    categories = await client.get("/api/v1/categories")
    protected = next(item for item in categories.json() if item["id"] == str(category_id))
    assert protected["recipe_count"] == 2


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


async def test_docker_and_hot_reload_frontends_are_allowed_by_cors(client) -> None:
    for origin in ("http://localhost:3000", "http://localhost:3001"):
        response = await client.options(
            "/api/v1/categories",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin


def test_hot_reload_origin_is_development_only() -> None:
    settings = Settings(
        environment="production",
        frontend_origin="https://food.example.com",
        jwt_secret="test-production-secret",
    )

    assert settings.frontend_origins == ["https://food.example.com"]
