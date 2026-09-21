import uuid

from sqlalchemy import select

from culinary_blog_api.auth import User
from culinary_blog_api.categories import Category
from culinary_blog_api.db import SessionFactory
from culinary_blog_api.recipes import Recipe, RecipeStatus

REGISTER_PAYLOAD = {
    "fullName": "Tran Xuan Hieu",
    "email": "hieu@example.com",
    "userName": "thanhxuanhieu",
    "password": "StrongPass1!",
}


async def author_headers(client) -> dict[str, str]:
    response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


async def create_category() -> Category:
    async with SessionFactory() as session:
        category = Category(name="Món Việt", slug="mon-viet", description=None)
        session.add(category)
        await session.commit()
        await session.refresh(category)
        return category


def valid_payload(category_id: uuid.UUID) -> dict[str, object]:
    return {
        "title": "Gỏi cuốn tôm thịt",
        "description": "Món gỏi cuốn kiểu Việt Nam.",
        "categoryId": str(category_id),
        "prepTimeMinutes": 20,
        "cookTimeMinutes": 0,
        "servings": 4,
        "difficulty": 1,
        "instructions": "Chuẩn bị nguyên liệu trước khi cuốn.",
        "nutrition": {"calories": 210, "protein": 8},
    }


async def test_author_creates_persisted_draft_with_real_ownership(client) -> None:
    headers = await author_headers(client)
    category = await create_category()

    response = await client.post(
        "/api/v1/recipes", json=valid_payload(category.id), headers=headers
    )

    assert response.status_code == 201
    assert response.headers["location"] == "/api/v1/recipes/goi-cuon-tom-thit"
    body = response.json()
    assert body["status"] == "Draft"
    assert body["slug"] == "goi-cuon-tom-thit"
    assert body["cookTimeMinutes"] == 0
    assert body["nutrition"]["calories"] == 210.0

    async with SessionFactory() as session:
        recipe = await session.scalar(select(Recipe).where(Recipe.slug == body["slug"]))
        author = await session.scalar(select(User).where(User.email == REGISTER_PAYLOAD["email"]))
        assert recipe is not None
        assert author is not None
        assert recipe.author_id == author.id
        assert recipe.category_id == category.id
        assert recipe.status == RecipeStatus.DRAFT


async def test_create_recipe_requires_authentication(client) -> None:
    category = await create_category()

    response = await client.post("/api/v1/recipes", json=valid_payload(category.id))

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"] == "AUTH_TOKEN_INVALID"


async def test_create_recipe_rejects_malformed_token(client) -> None:
    category = await create_category()

    response = await client.post(
        "/api/v1/recipes",
        json=valid_payload(category.id),
        headers={"Authorization": "Bearer not-a-jwt"},
    )

    assert response.status_code == 401
    assert response.json()["type"] == "AUTH_TOKEN_INVALID"


async def test_create_recipe_rejects_non_author_role(client) -> None:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.email == REGISTER_PAYLOAD["email"]))
        assert user is not None
        user.role = "Reader"
        await session.commit()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    category = await create_category()

    response = await client.post(
        "/api/v1/recipes",
        json=valid_payload(category.id),
        headers={"Authorization": f"Bearer {login.json()['accessToken']}"},
    )

    assert response.status_code == 403
    assert response.json()["type"] == "RECIPE_FORBIDDEN"


async def test_create_recipe_reports_request_validation(client) -> None:
    headers = await author_headers(client)
    category = await create_category()

    response = await client.post(
        "/api/v1/recipes",
        json={**valid_payload(category.id), "title": "bad", "prepTimeMinutes": 0},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"] == "VALIDATION_ERROR"
    assert {"title", "prepTimeMinutes"} <= response.json()["errors"].keys()


async def test_create_recipe_rejects_missing_category(client) -> None:
    headers = await author_headers(client)

    response = await client.post(
        "/api/v1/recipes",
        json=valid_payload(uuid.uuid4()),
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["errors"]["categoryId"] == ["Category does not exist."]


async def test_create_recipe_rejects_duplicate_slug(client) -> None:
    headers = await author_headers(client)
    category = await create_category()
    payload = valid_payload(category.id)

    first = await client.post("/api/v1/recipes", json=payload, headers=headers)
    second = await client.post("/api/v1/recipes", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["type"] == "RECIPE_SLUG_EXISTS"
