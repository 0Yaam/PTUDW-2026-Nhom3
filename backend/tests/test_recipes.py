import uuid

from sqlalchemy import select

from culinary_blog_api.auth import User
from culinary_blog_api.categories import Category
from culinary_blog_api.db import SessionFactory
from culinary_blog_api.recipes import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    RecipeStatus,
    RecipeStep,
)

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


async def add_publishable_content(recipe_id: uuid.UUID) -> None:
    async with SessionFactory() as session:
        ingredient = Ingredient(name="Fish sauce")
        session.add(ingredient)
        await session.flush()
        session.add_all(
            [
                RecipeIngredient(
                    recipe_id=recipe_id,
                    ingredient_id=ingredient.id,
                    quantity=1,
                    unit="tbsp",
                    order_index=0,
                ),
                RecipeStep(recipe_id=recipe_id, step_number=1, instruction="Mix well."),
            ]
        )
        await session.commit()


async def test_owner_publishes_and_unpublishes_ready_recipe(client) -> None:
    category = await create_category()
    headers = await author_headers(client)
    created = await client.post(
        "/api/v1/recipes", json=valid_payload(category.id), headers=headers
    )
    recipe_id = uuid.UUID(created.json()["id"])

    not_ready = await client.patch(f"/api/v1/recipes/{recipe_id}/publish", headers=headers)
    assert not_ready.status_code == 422
    assert not_ready.json()["type"] == "RECIPE_NOT_READY"

    await add_publishable_content(recipe_id)
    published = await client.patch(f"/api/v1/recipes/{recipe_id}/publish", headers=headers)
    unpublished = await client.patch(
        f"/api/v1/recipes/{recipe_id}/unpublish", headers=headers
    )

    assert published.status_code == 200
    assert published.json()["status"] == "Published"
    assert unpublished.status_code == 200
    assert unpublished.json()["status"] == "Draft"


async def test_non_owner_cannot_publish_recipe(client) -> None:
    category = await create_category()
    owner_headers = await author_headers(client)
    created = await client.post(
        "/api/v1/recipes", json=valid_payload(category.id), headers=owner_headers
    )
    recipe_id = created.json()["id"]
    other = await client.post(
        "/api/v1/auth/register",
        json={
            **REGISTER_PAYLOAD,
            "email": "other@example.com",
            "userName": "other_author",
        },
    )
    other_headers = {"Authorization": f"Bearer {other.json()['accessToken']}"}

    response = await client.patch(
        f"/api/v1/recipes/{recipe_id}/publish", headers=other_headers
    )

    assert response.status_code == 403
    assert response.json()["type"] == "RECIPE_FORBIDDEN"


async def _second_author_headers(client) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            **REGISTER_PAYLOAD,
            "email": "second@example.com",
            "userName": "secondauthor",
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


async def test_owner_updates_recipe_with_row_version_and_stable_slug(client) -> None:
    headers = await author_headers(client)
    category = await create_category()
    created = await client.post(
        "/api/v1/recipes", json=valid_payload(category.id), headers=headers
    )
    assert created.status_code == 201
    assert created.headers["etag"] == f'"{created.json()["rowVersion"]}"'
    recipe_id = created.json()["id"]
    changed = {**valid_payload(category.id), "title": "Gỏi cuốn phiên bản mới"}
    response = await client.put(
        f"/api/v1/recipes/{recipe_id}",
        json=changed,
        headers={**headers, "If-Match": created.headers["etag"]},
    )
    assert response.status_code == 200
    assert response.json()["title"] == changed["title"]
    assert response.json()["slug"] == created.json()["slug"]
    assert response.json()["rowVersion"] != created.json()["rowVersion"]
    assert response.headers["etag"] == f'"{response.json()["rowVersion"]}"'

    stale = await client.put(
        f"/api/v1/recipes/{recipe_id}",
        json=changed,
        headers={**headers, "If-Match": created.headers["etag"]},
    )
    assert stale.status_code == 409
    assert stale.json()["type"] == "RECIPE_VERSION_CONFLICT"
    assert stale.headers["content-type"].startswith("application/problem+json")


async def test_recipe_update_checks_precondition_validation_owner_and_missing(client) -> None:
    headers = await author_headers(client)
    category = await create_category()
    created = await client.post(
        "/api/v1/recipes", json=valid_payload(category.id), headers=headers
    )
    recipe_id = created.json()["id"]
    path = f"/api/v1/recipes/{recipe_id}"
    missing_version = await client.put(path, json=valid_payload(category.id), headers=headers)
    assert missing_version.status_code == 428
    assert missing_version.json()["type"] == "RECIPE_VERSION_REQUIRED"

    invalid = await client.put(
        path,
        json={**valid_payload(category.id), "prepTimeMinutes": 0},
        headers={**headers, "If-Match": created.headers["etag"]},
    )
    assert invalid.status_code == 422
    assert invalid.json()["type"] == "VALIDATION_ERROR"

    other = await _second_author_headers(client)
    forbidden = await client.put(
        path, json=valid_payload(category.id), headers=other | {"If-Match": created.headers["etag"]}
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["type"] == "RECIPE_FORBIDDEN"
    missing = await client.put(
        f"/api/v1/recipes/{uuid.uuid4()}",
        json=valid_payload(category.id),
        headers={**headers, "If-Match": created.headers["etag"]},
    )
    assert missing.status_code == 404


async def test_recipe_delete_cascades_and_checks_owner(client) -> None:
    headers = await author_headers(client)
    category = await create_category()
    created = await client.post(
        "/api/v1/recipes", json=valid_payload(category.id), headers=headers
    )
    recipe_id = uuid.UUID(created.json()["id"])
    await add_publishable_content(recipe_id)
    other = await _second_author_headers(client)
    path = f"/api/v1/recipes/{recipe_id}"
    denied = await client.delete(path, headers=other)
    assert denied.status_code == 403
    assert denied.json()["type"] == "RECIPE_FORBIDDEN"

    deleted = await client.delete(path, headers=headers)
    assert deleted.status_code == 204
    assert (await client.delete(path, headers=headers)).status_code == 404
    async with SessionFactory() as session:
        assert await session.get(Recipe, recipe_id) is None
        assert (await session.scalars(
            select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe_id)
        )).all() == []
        assert (await session.scalars(
            select(RecipeStep).where(RecipeStep.recipe_id == recipe_id)
        )).all() == []


async def test_recipe_step_crud_keeps_order_contiguous(client) -> None:
    headers = await author_headers(client)
    category = await create_category()
    created = await client.post(
        "/api/v1/recipes", json=valid_payload(category.id), headers=headers
    )
    recipe_id = created.json()["id"]
    base = f"/api/v1/recipes/{recipe_id}/steps"
    items = []
    for instruction in ("Wash vegetables", "Mix sauce", "Serve fresh"):
        response = await client.post(
            base,
            json={"instruction": instruction, "durationMinutes": 5},
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["stepNumber"] == len(items) + 1
        assert response.headers["location"].endswith(response.json()["id"])
        items.append(response.json())

    moved = await client.put(
        f"{base}/{items[2]['id']}",
        json={"instruction": "Serve chilled", "stepNumber": 1, "imageUrl": "/images/serve.jpg"},
        headers=headers,
    )
    assert moved.status_code == 200
    assert moved.json()["stepNumber"] == 1
    assert moved.json()["imageUrl"] == "/images/serve.jpg"

    removed = await client.delete(f"{base}/{items[0]['id']}", headers=headers)
    assert removed.status_code == 204
    async with SessionFactory() as session:
        steps = list(await session.scalars(
            select(RecipeStep).where(RecipeStep.recipe_id == uuid.UUID(recipe_id))
            .order_by(RecipeStep.step_number)
        ))
        assert [step.step_number for step in steps] == [1, 2]
        assert [step.instruction for step in steps] == ["Serve chilled", "Mix sauce"]


async def test_recipe_steps_validate_and_enforce_resource_permissions(client) -> None:
    headers = await author_headers(client)
    category = await create_category()
    created = await client.post(
        "/api/v1/recipes", json=valid_payload(category.id), headers=headers
    )
    recipe_id = created.json()["id"]
    base = f"/api/v1/recipes/{recipe_id}/steps"
    invalid = await client.post(base, json={"instruction": "  "}, headers=headers)
    assert invalid.status_code == 422
    assert invalid.json()["type"] == "VALIDATION_ERROR"
    created_step = await client.post(base, json={"instruction": "Prepare"}, headers=headers)
    step_id = created_step.json()["id"]
    out_of_range = await client.put(
        f"{base}/{step_id}", json={"instruction": "Prepare", "stepNumber": 2}, headers=headers
    )
    assert out_of_range.status_code == 422
    other = await _second_author_headers(client)
    assert (await client.post(base, json={"instruction": "No"}, headers=other)).status_code == 403
    assert (await client.delete(f"{base}/{step_id}", headers=other)).status_code == 403
    assert (await client.put(
        f"{base}/{uuid.uuid4()}", json={"instruction": "Missing"}, headers=headers
    )).status_code == 404
    assert (await client.post(
        f"/api/v1/recipes/{uuid.uuid4()}/steps",
        json={"instruction": "Missing"}, headers=headers
    )).status_code == 404


async def test_admin_can_manage_another_authors_recipe_and_anonymous_cannot(client) -> None:
    owner = await author_headers(client)
    category = await create_category()
    created = await client.post(
        "/api/v1/recipes", json=valid_payload(category.id), headers=owner
    )
    recipe_id = created.json()["id"]
    admin_registration = await client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "email": "admin@example.com", "userName": "recipeadmin"},
    )
    assert admin_registration.status_code == 201
    async with SessionFactory() as session:
        admin = await session.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        admin.role = "Admin"
        await session.commit()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": REGISTER_PAYLOAD["password"]},
    )
    admin_headers = {"Authorization": f"Bearer {login.json()['accessToken']}"}
    assert (await client.delete(f"/api/v1/recipes/{recipe_id}")).status_code == 401
    step = await client.post(
        f"/api/v1/recipes/{recipe_id}/steps",
        json={"instruction": "Admin adds a step"},
        headers=admin_headers,
    )
    assert step.status_code == 201
    updated = await client.put(
        f"/api/v1/recipes/{recipe_id}",
        json={**valid_payload(category.id), "rowVersion": created.json()["rowVersion"]},
        headers=admin_headers,
    )
    assert updated.status_code == 409  # Adding a step changed the recipe version.
    async with SessionFactory() as session:
        recipe = await session.get(Recipe, uuid.UUID(recipe_id))
        assert recipe is not None
        current_version = recipe.row_version.hex()
    updated = await client.put(
        f"/api/v1/recipes/{recipe_id}",
        json={**valid_payload(category.id), "rowVersion": current_version},
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert (await client.delete(
        f"/api/v1/recipes/{recipe_id}", headers=admin_headers
    )).status_code == 204
