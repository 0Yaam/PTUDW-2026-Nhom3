import uuid

from culinary_blog_api.categories import Category
from culinary_blog_api.db import SessionFactory


async def test_author_can_publish_and_search_recipe_end_to_end(client) -> None:
    async with SessionFactory() as session:
        category = Category(name="Món Việt", slug="mon-viet-release", description=None)
        session.add(category)
        await session.commit()
        await session.refresh(category)
        category_id = category.id

    account = {
        "fullName": "Nguyen Ngoc Truong Dan",
        "email": "release-dan@example.com",
        "userName": "release_dan",
        "password": "StrongPass1!",
    }
    registered = await client.post("/api/v1/auth/register", json=account)
    logged_in = await client.post(
        "/api/v1/auth/login",
        json={"email": account["email"], "password": account["password"]},
    )
    headers = {"Authorization": f"Bearer {logged_in.json()['accessToken']}"}

    created = await client.post(
        "/api/v1/recipes",
        headers=headers,
        json={
            "title": "Bún chả Hà Nội",
            "description": "Món bún chả dùng cho kiểm tra tích hợp.",
            "categoryId": str(category_id),
            "prepTimeMinutes": 20,
            "cookTimeMinutes": 30,
            "servings": 4,
            "difficulty": 1,
            "instructions": "Chuẩn bị nguyên liệu và nướng thịt.",
            "nutrition": {"calories": 450, "protein": 24},
        },
    )
    recipe_id = uuid.UUID(created.json()["id"])
    ingredient = await client.post(
        f"/api/v1/recipes/{recipe_id}/ingredients",
        headers=headers,
        json={"ingredientName": "Thịt heo", "quantity": 500, "unit": "g"},
    )
    step = await client.post(
        f"/api/v1/recipes/{recipe_id}/steps",
        headers=headers,
        json={"instruction": "Ướp và nướng thịt đến khi chín."},
    )
    published = await client.patch(
        f"/api/v1/recipes/{recipe_id}/publish", headers=headers
    )
    found = await client.get("/api/v1/recipes/search", params={"q": "Bún chả"})

    assert registered.status_code == 201
    assert logged_in.status_code == 200
    assert created.status_code == 201
    assert ingredient.status_code == 201
    assert step.status_code == 201
    assert published.status_code == 200
    assert published.json()["status"] == "Published"
    assert found.status_code == 200
    assert [item["id"] for item in found.json()["items"]] == [str(recipe_id)]
