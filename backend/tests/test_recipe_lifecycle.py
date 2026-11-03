"""Issue #90: one real-data authoring journey using existing REST contracts."""

import uuid

import pytest
from sqlalchemy import select
from test_recipe_features import PNG, FakeStorage
from test_recipe_list import create_user
from test_recipes import create_category, valid_payload

from culinary_blog_api.db import SessionFactory
from culinary_blog_api.main import app
from culinary_blog_api.recipes.model import (
    Recipe,
    RecipeImage,
    RecipeImageResizeJob,
    RecipeIngredient,
    RecipeStep,
)
from culinary_blog_api.recipes.router import get_recipe_storage
from culinary_blog_api.storage.model import FileDeletionJob


async def test_complete_authoring_lifecycle_preserves_contract_and_privacy(client):
    category = await create_category()
    owner, headers = await create_user(client, email="lifecycle@example.com")
    created = await client.post(
        "/api/v1/recipes", headers=headers, json=valid_payload(category.id)
    )
    assert created.status_code == 201
    draft = created.json()
    base = f"/api/v1/recipes/{draft['id']}"
    detail_url = f"/api/v1/recipes/{draft['slug']}"
    assert draft["authorId"] == str(owner.id)
    assert draft["status"] == "Draft"
    assert (await client.get(detail_url)).status_code == 403
    assert (await client.patch(f"{base}/publish", headers=headers)).status_code == 422

    ingredient = await client.post(
        f"{base}/ingredients", headers=headers,
        json={"ingredientName": "Rice", "quantity": 2, "unit": "cups"},
    )
    assert ingredient.status_code == 201
    steps = []
    for instruction in ("Prepare rice", "Cook rice"):
        added = await client.post(
            f"{base}/steps", headers=headers, json={"instruction": instruction}
        )
        assert added.status_code == 201
        steps.append(added.json())
    moved = await client.put(
        f"{base}/steps/{steps[1]['id']}", headers=headers,
        json={"instruction": "Cook rice", "stepNumber": 1},
    )
    assert moved.status_code == 200
    latest = (await client.get(detail_url, headers=headers)).json()
    assert [row["stepNumber"] for row in latest["steps"]] == [1, 2]
    assert latest["steps"][0]["instruction"] == "Cook rice"

    # Child writes advance the parent version; an old editor cannot overwrite them.
    stale = await client.put(
        base, headers={**headers, "If-Match": created.headers["etag"]},
        json=valid_payload(category.id),
    )
    assert stale.status_code == 409
    changed = await client.put(
        base, headers={**headers, "If-Match": f'"{latest["rowVersion"]}"'},
        json={**valid_payload(category.id), "title": "Rice lifecycle recipe"},
    )
    assert changed.status_code == 200
    assert changed.json()["slug"] == draft["slug"]

    for action, expected in (("publish", "Published"), ("unpublish", "Draft"),
                             ("publish", "Published"), ("archive", "Archived")):
        response = await client.patch(f"{base}/{action}", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == expected
        public_detail = await client.get(detail_url)
        assert public_detail.status_code == (200 if expected == "Published" else 403)
        listing = (await client.get("/api/v1/recipes")).json()["items"]
        search = (await client.get("/api/v1/recipes/search?q=Rice")).json()["items"]
        assert bool(listing) == bool(search) == (expected == "Published")
    assert (await client.patch(f"{base}/publish", headers=headers)).status_code == 422
    assert (await client.patch(f"{base}/unpublish", headers=headers)).status_code == 422

    storage = FakeStorage()
    app.dependency_overrides[get_recipe_storage] = lambda: storage
    try:
        uploaded = await client.post(
            f"{base}/images", headers=headers, files={"file": ("rice.png", PNG, "image/png")}
        )
        assert uploaded.status_code == 201
    finally:
        app.dependency_overrides.pop(get_recipe_storage, None)
    assert (await client.delete(base, headers=headers)).status_code == 204
    assert (await client.get(detail_url, headers=headers)).status_code == 404
    async with SessionFactory() as session:
        recipe_id = uuid.UUID(draft["id"])
        assert await session.get(Recipe, recipe_id) is None
        for model in (RecipeIngredient, RecipeStep, RecipeImage):
            assert not (await session.scalars(
                select(model).where(model.recipe_id == recipe_id)
            )).all()
        assert not (await session.scalars(select(RecipeImageResizeJob))).all()
        cleanup = await session.scalar(select(FileDeletionJob))
        assert cleanup is not None
        assert cleanup.original_url == uploaded.json()["originalUrl"]


@pytest.mark.parametrize("viewer", ["anonymous", "other_author"])
async def test_every_lifecycle_write_enforces_backend_owner_permissions(client, viewer):
    category = await create_category()
    _, owner_headers = await create_user(client, email="owner@example.com")
    created = await client.post(
        "/api/v1/recipes", headers=owner_headers, json=valid_payload(category.id)
    )
    recipe = created.json()
    base = f"/api/v1/recipes/{recipe['id']}"
    ingredient = (await client.post(
        f"{base}/ingredients", headers=owner_headers,
        json={"ingredientName": "Rice", "quantity": 1, "unit": "cup"},
    )).json()
    step = (await client.post(
        f"{base}/steps", headers=owner_headers, json={"instruction": "Cook"}
    )).json()
    headers = {}
    if viewer == "other_author":
        _, headers = await create_user(client, email="other@example.com")
    requests = [
        ("PUT", base, {**valid_payload(category.id), "rowVersion": recipe["rowVersion"]}),
        ("DELETE", base, None),
        *[("PATCH", f"{base}/{action}", None) for action in ("publish", "unpublish", "archive")],
        ("POST", f"{base}/ingredients", {"ingredientName": "Salt", "quantity": 1, "unit": "g"}),
        ("PUT", f"{base}/ingredients/{ingredient['id']}",
         {"ingredientName": "Rice", "quantity": 2, "unit": "cups"}),
        ("DELETE", f"{base}/ingredients/{ingredient['id']}", None),
        ("POST", f"{base}/steps", {"instruction": "Serve"}),
        ("PUT", f"{base}/steps/{step['id']}", {"instruction": "New instruction"}),
        ("DELETE", f"{base}/steps/{step['id']}", None),
    ]
    for method, path, payload in requests:
        response = await client.request(method, path, headers=headers, json=payload)
        assert response.status_code == (401 if viewer == "anonymous" else 403)
        assert response.headers["content-type"].startswith("application/problem+json")
    detail = (await client.get(f"/api/v1/recipes/{recipe['slug']}", headers=owner_headers)).json()
    assert detail["status"] == "Draft"
    assert len(detail["ingredients"]) == len(detail["steps"]) == 1


async def test_admin_can_complete_another_authors_lifecycle_without_taking_ownership(client):
    category = await create_category()
    owner, owner_headers = await create_user(client, email="author@example.com")
    _, admin_headers = await create_user(client, email="admin@example.com", role="Admin")
    created = await client.post(
        "/api/v1/recipes", headers=owner_headers, json=valid_payload(category.id)
    )
    recipe = created.json()
    base = f"/api/v1/recipes/{recipe['id']}"
    assert (await client.post(
        f"{base}/ingredients", headers=admin_headers,
        json={"ingredientName": "Rice", "quantity": 1, "unit": "cup"},
    )).status_code == 201
    assert (await client.post(
        f"{base}/steps", headers=admin_headers, json={"instruction": "Cook"}
    )).status_code == 201
    detail = (await client.get(
        f"/api/v1/recipes/{recipe['slug']}", headers=admin_headers
    )).json()
    updated = await client.put(
        base, headers=admin_headers,
        json={**valid_payload(category.id), "rowVersion": detail["rowVersion"]},
    )
    assert updated.status_code == 200
    assert updated.json()["authorId"] == str(owner.id)
    for action in ("publish", "unpublish", "archive"):
        assert (await client.patch(f"{base}/{action}", headers=admin_headers)).status_code == 200
    assert (await client.delete(base, headers=admin_headers)).status_code == 204


async def test_password_change_revokes_recipe_reads_and_writes(client):
    category = await create_category()
    _, headers = await create_user(client, email="revoked@example.com")
    created = (await client.post(
        "/api/v1/recipes", headers=headers, json=valid_payload(category.id)
    )).json()
    changed = await client.post(
        "/api/v1/auth/change-password", headers=headers,
        json={"currentPassword": "StrongPass1!", "newPassword": "NewStrongPass2!"},
    )
    assert changed.status_code == 204
    base = f"/api/v1/recipes/{created['id']}"
    requests = [
        ("GET", "/api/v1/recipes", None),
        ("GET", "/api/v1/recipes/search?q=Rice", None),
        ("GET", f"/api/v1/recipes/{created['slug']}", None),
        ("POST", "/api/v1/recipes", valid_payload(category.id)),
        ("PUT", base, {**valid_payload(category.id), "rowVersion": created["rowVersion"]}),
        ("PATCH", f"{base}/publish", None),
        ("PATCH", f"{base}/unpublish", None),
        ("PATCH", f"{base}/archive", None),
        ("DELETE", base, None),
        ("POST", f"{base}/steps", {"instruction": "Must not be saved"}),
        ("POST", f"{base}/ingredients", {"ingredientName": "Rice", "quantity": 1, "unit": "g"}),
    ]
    for method, path, payload in requests:
        response = await client.request(method, path, headers=headers, json=payload)
        assert response.status_code == 401
        assert response.json()["type"] == "AUTH_TOKEN_INVALID"
