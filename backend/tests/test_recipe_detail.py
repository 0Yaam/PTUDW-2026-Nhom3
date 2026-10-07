"""A recipe card links to the complete, role-aware FR-RCP-002 resource."""

import uuid

from test_recipe_list import add_recipe, create_category, create_user

from culinary_blog_api.db import SessionFactory
from culinary_blog_api.recipes import Ingredient, RecipeIngredient, RecipeStep
from culinary_blog_api.recipes.model import RecipeImage, RecipeStatus


async def test_guest_reads_complete_published_recipe_in_order(client) -> None:
    category = await create_category()
    author, _ = await create_user(client, email="detail-author@example.com")
    recipe = await add_recipe(category, author, title="Phở bò chi tiết")
    async with SessionFactory() as session:
        loaded = await session.get(type(recipe), recipe.id)
        loaded.nutrition_calories = 320
        ingredient = Ingredient(name="Bánh phở")
        session.add_all(
            [
                ingredient,
                RecipeStep(recipe_id=recipe.id, step_number=2, instruction="Hoàn thành món ăn."),
                RecipeStep(recipe_id=recipe.id, step_number=1, instruction="Chuẩn bị nguyên liệu."),
                RecipeImage(
                    recipe_id=recipe.id,
                    original_url="http://storage.test/pho.png",
                    is_primary=True,
                    order_index=0,
                ),
            ]
        )
        await session.flush()
        session.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                quantity=2,
                unit="phần",
                order_index=0,
            )
        )
        await session.commit()

    response = await client.get(f"/api/v1/recipes/{recipe.slug}")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Phở bò chi tiết"
    assert body["category"]["id"] == str(category.id)
    assert body["author"]["id"] == str(author.id)
    assert body["nutrition"]["calories"] == 320
    assert body["ingredients"][0]["name"] == "Bánh phở"
    assert body["ingredients"][0]["quantity"] == 2
    assert [step["stepNumber"] for step in body["steps"]] == [1, 2]
    assert body["images"][0]["isPrimary"] is True


async def test_private_recipe_requires_owner_or_admin(client) -> None:
    category = await create_category()
    owner, owner_headers = await create_user(client, email="detail-owner@example.com")
    _, other_headers = await create_user(client, email="detail-other@example.com")
    _, admin_headers = await create_user(client, email="detail-admin@example.com", role="Admin")
    draft = await add_recipe(category, owner, title="Chi tiết bản nháp", status=RecipeStatus.DRAFT)
    archived = await add_recipe(
        category, owner, title="Chi tiết lưu trữ", status=RecipeStatus.ARCHIVED
    )
    deleted = await add_recipe(category, owner, title="Chi tiết đã xoá", is_deleted=True)

    for recipe in (draft, archived):
        url = f"/api/v1/recipes/{recipe.slug}"
        assert (await client.get(url)).status_code == 403
        assert (await client.get(url, headers=other_headers)).status_code == 403
        assert (await client.get(url, headers=owner_headers)).status_code == 200
        assert (await client.get(url, headers=admin_headers)).status_code == 200
    assert (
        await client.get(f"/api/v1/recipes/{deleted.slug}", headers=owner_headers)
    ).status_code == 404


async def test_detail_missing_invalid_token_and_archive_invalidation(client) -> None:
    category = await create_category()
    owner, headers = await create_user(client, email="detail-cache@example.com")
    recipe = await add_recipe(category, owner, title="Món cần lưu trữ")
    url = f"/api/v1/recipes/{recipe.slug}"

    assert (await client.get(f"/api/v1/recipes/{uuid.uuid4().hex}")).status_code == 404
    invalid = await client.get(url, headers={"Authorization": "Bearer bad"})
    assert invalid.status_code == 401
    assert invalid.headers["content-type"].startswith("application/problem+json")
    assert (await client.get(url)).status_code == 200
    assert (
        await client.patch(f"/api/v1/recipes/{recipe.id}/archive", headers=headers)
    ).status_code == 200
    private = await client.get(url)
    assert private.status_code == 403
    assert private.headers["content-type"].startswith("application/problem+json")
