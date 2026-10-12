"""Admin overview returns real aggregates without exposing them publicly."""

import uuid

from test_recipe_list import add_recipe, create_category, create_user

from culinary_blog_api.db import SessionFactory
from culinary_blog_api.recipes.model import RecipeStatus
from culinary_blog_api.storage.model import FileDeletionJob


async def test_overview_requires_admin_and_reports_content(client) -> None:
    category = await create_category()
    author, author_headers = await create_user(client, email="overview-author@example.com")
    _, admin_headers = await create_user(
        client, email="overview-admin@example.com", role="Admin"
    )
    await add_recipe(category, author, title="Published overview recipe")
    await add_recipe(category, author, title="Draft overview recipe", status=RecipeStatus.DRAFT)
    async with SessionFactory() as session:
        session.add(FileDeletionJob(
            original_url="http://storage.test/recipes/orphan.png",
            recipe_id=uuid.uuid4(), image_id=uuid.uuid4(), status="Failed",
        ))
        await session.commit()

    url = "/api/v1/admin/overview"
    anonymous = await client.get(url)
    assert anonymous.status_code == 401
    assert anonymous.headers["content-type"].startswith("application/problem+json")
    assert (await client.get(url, headers=author_headers)).status_code == 403

    response = await client.get(url, headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["users"] == 2
    assert body["categories"] == 1
    assert body["recipes"] == {"total": 2, "draft": 1, "published": 1, "archived": 0}
    assert body["images"] == 0
    assert len(body["recentRecipes"]) == 2
    assert body["jobs"]["cleanup"] == {"pending": 0, "failed": 1}
    assert body["jobs"]["email"]["pending"] == 2
