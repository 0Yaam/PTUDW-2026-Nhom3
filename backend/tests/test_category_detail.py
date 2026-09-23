import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from culinary_blog_api.auth import User
from culinary_blog_api.auth.security import hash_password
from culinary_blog_api.categories import Category
from culinary_blog_api.db import SessionFactory
from culinary_blog_api.recipes import Recipe, RecipeStatus


async def seed_category(slug: str = "mon-viet") -> uuid.UUID:
    async with SessionFactory() as session:
        category = Category(name="Món Việt", slug=slug, description="Bếp nhà.")
        session.add(category)
        await session.commit()
        return category.id


async def seed_recipe(category_id: uuid.UUID, title: str, status: int) -> None:
    async with SessionFactory() as session:
        author = User(
            full_name="Minh Anh",
            email=f"{uuid.uuid4().hex}@example.com",
            user_name=uuid.uuid4().hex[:20],
            password_hash=hash_password("StrongPass1!"),
            avatar_url=None,
        )
        session.add(author)
        await session.flush()
        session.add(
            Recipe(
                title=title,
                slug=title.lower().replace(" ", "-"),
                description="Một món ăn quen thuộc.",
                instructions="Nấu cho chín.",
                prep_time_minutes=15,
                cook_time_minutes=30,
                servings=4,
                difficulty=1,
                status=status,
                category_id=category_id,
                author_id=author.id,
                published_at=datetime.now(UTC) if status == RecipeStatus.PUBLISHED else None,
            )
        )
        await session.commit()


async def test_category_detail_returns_category_for_a_known_slug(client) -> None:
    await seed_category()

    response = await client.get("/api/v1/categories/mon-viet")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Món Việt"
    assert body["slug"] == "mon-viet"
    assert body["description"] == "Bếp nhà."


async def test_category_detail_treats_an_empty_recipe_list_as_normal(client) -> None:
    await seed_category()

    response = await client.get("/api/v1/categories/mon-viet")

    assert response.status_code == 200
    assert response.json()["recipes"] == []
    assert response.json()["recipe_count"] == 0


async def test_category_detail_returns_published_recipe_cards(client) -> None:
    category_id = await seed_category()
    await seed_recipe(category_id, "Bun Bo Hue", RecipeStatus.PUBLISHED)

    response = await client.get("/api/v1/categories/mon-viet")

    assert response.status_code == 200
    body = response.json()
    assert body["recipe_count"] == 1
    card = body["recipes"][0]
    assert card["title"] == "Bun Bo Hue"
    assert card["slug"] == "bun-bo-hue"
    assert card["cook_time_minutes"] == 30
    assert card["servings"] == 4


async def test_category_detail_hides_drafts_from_readers(client) -> None:
    category_id = await seed_category()
    await seed_recipe(category_id, "Cha Gio", RecipeStatus.DRAFT)

    response = await client.get("/api/v1/categories/mon-viet")

    assert response.status_code == 200
    assert response.json()["recipes"] == []


async def test_category_detail_hides_deleted_recipes(client) -> None:
    category_id = await seed_category()
    await seed_recipe(category_id, "Banh Mi", RecipeStatus.PUBLISHED)
    async with SessionFactory() as session:
        recipe = await session.scalar(select(Recipe))
        recipe.is_deleted = True
        await session.commit()

    response = await client.get("/api/v1/categories/mon-viet")

    assert response.status_code == 200
    assert response.json()["recipes"] == []


async def test_category_detail_returns_problem_for_an_unknown_slug(client) -> None:
    response = await client.get("/api/v1/categories/khong-ton-tai")

    assert response.status_code == 404
    body = response.json()
    assert body["type"] == "CATEGORY_NOT_FOUND"
    assert body["status"] == 404
    assert "traceback" not in response.text.lower()
