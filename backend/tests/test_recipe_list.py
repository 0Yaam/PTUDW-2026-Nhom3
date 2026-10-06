import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from culinary_blog_api.auth import User
from culinary_blog_api.categories import Category
from culinary_blog_api.db import SessionFactory
from culinary_blog_api.recipes import Recipe, RecipeStatus


async def create_user(client, *, email: str, role: str = "Author") -> tuple[User, dict[str, str]]:
    password = "StrongPass1!"
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "fullName": email.split("@")[0],
            "email": email,
            "userName": uuid.uuid4().hex[:16],
            "password": password,
        },
    )
    assert response.status_code == 201
    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = role
        await session.commit()
        await session.refresh(user)
        return user, {"Authorization": f"Bearer {response.json()['accessToken']}"}


async def create_category(name: str = "Món Việt") -> Category:
    async with SessionFactory() as session:
        category = Category(name=name, slug=uuid.uuid4().hex, description=None)
        session.add(category)
        await session.commit()
        await session.refresh(category)
        return category


async def add_recipe(
    category: Category,
    author: User,
    *,
    title: str,
    status: RecipeStatus = RecipeStatus.PUBLISHED,
    difficulty: int = 1,
    cook_time: int = 30,
    servings: int = 4,
    created_at: datetime | None = None,
    is_deleted: bool = False,
) -> Recipe:
    async with SessionFactory() as session:
        recipe = Recipe(
            title=title,
            slug=uuid.uuid4().hex,
            description=f"Mô tả {title}.",
            instructions="Nấu chín.",
            prep_time_minutes=10,
            cook_time_minutes=cook_time,
            servings=servings,
            difficulty=difficulty,
            status=status,
            category_id=category.id,
            author_id=author.id,
            published_at=datetime.now(UTC) if status == RecipeStatus.PUBLISHED else None,
            created_at=created_at or datetime.now(UTC),
            is_deleted=is_deleted,
        )
        session.add(recipe)
        await session.commit()
        await session.refresh(recipe)
        return recipe


async def test_guest_sees_only_published_non_deleted_recipes(client) -> None:
    category = await create_category()
    author, _ = await create_user(client, email="list-author@example.com")
    published = await add_recipe(category, author, title="Phở bò")
    await add_recipe(category, author, title="Bản nháp", status=RecipeStatus.DRAFT)
    await add_recipe(category, author, title="Đã lưu trữ", status=RecipeStatus.ARCHIVED)
    await add_recipe(category, author, title="Đã xoá", is_deleted=True)

    response = await client.get("/api/v1/recipes")

    assert response.status_code == 200
    body = response.json()
    assert body["totalCount"] == 1
    assert [item["id"] for item in body["items"]] == [str(published.id)]
    assert body["items"][0]["status"] == "Published"
    assert body["items"][0]["category"]["id"] == str(category.id)


async def test_author_sees_only_their_own_drafts_and_archived_recipes(client) -> None:
    category = await create_category()
    owner, owner_headers = await create_user(client, email="owner@example.com")
    other, _ = await create_user(client, email="other@example.com")
    public = await add_recipe(category, other, title="Công khai")
    draft = await add_recipe(category, owner, title="Nháp của tôi", status=RecipeStatus.DRAFT)
    archived = await add_recipe(
        category, owner, title="Lưu trữ của tôi", status=RecipeStatus.ARCHIVED
    )
    await add_recipe(category, other, title="Nháp người khác", status=RecipeStatus.DRAFT)
    await add_recipe(category, other, title="Lưu trữ người khác", status=RecipeStatus.ARCHIVED)

    response = await client.get("/api/v1/recipes?sort=title", headers=owner_headers)

    assert response.status_code == 200
    assert {item["id"] for item in response.json()["items"]} == {
        str(public.id),
        str(draft.id),
        str(archived.id),
    }


async def test_admin_sees_every_non_deleted_recipe(client) -> None:
    category = await create_category()
    admin, admin_headers = await create_user(client, email="admin@example.com", role="Admin")
    author, _ = await create_user(client, email="author@example.com")
    published = await add_recipe(category, author, title="Công khai")
    draft = await add_recipe(category, author, title="Bản nháp", status=RecipeStatus.DRAFT)
    archived = await add_recipe(category, admin, title="Lưu trữ", status=RecipeStatus.ARCHIVED)
    await add_recipe(category, author, title="Đã xoá", is_deleted=True)

    response = await client.get("/api/v1/recipes", headers=admin_headers)

    assert response.status_code == 200
    assert {item["id"] for item in response.json()["items"]} == {
        str(published.id),
        str(draft.id),
        str(archived.id),
    }


async def test_recipe_list_filters_sorts_and_paginates(client) -> None:
    category = await create_category()
    other_category = await create_category("Món chay")
    author, _ = await create_user(client, email="filters@example.com")
    base = datetime(2026, 9, 1, tzinfo=UTC)
    await add_recipe(
        category,
        author,
        title="Zeta",
        difficulty=1,
        cook_time=20,
        servings=2,
        created_at=base,
    )
    middle = await add_recipe(
        category,
        author,
        title="Alpha",
        difficulty=1,
        cook_time=15,
        servings=4,
        created_at=base + timedelta(days=1),
    )
    await add_recipe(
        category,
        author,
        title="Khó",
        difficulty=3,
        cook_time=10,
        servings=8,
        created_at=base + timedelta(days=2),
    )
    await add_recipe(other_category, author, title="Danh mục khác", cook_time=5)

    filtered = await client.get(
        "/api/v1/recipes",
        params={
            "categoryId": str(category.id),
            "difficulty": "Easy",
            "maxCookTime": 20,
            "minServings": 3,
            "sort": "title",
        },
    )
    page = await client.get("/api/v1/recipes?page=2&pageSize=1&sort=createdAt")
    missing_category = await client.get(f"/api/v1/recipes?categoryId={uuid.uuid4()}")

    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()["items"]] == [str(middle.id)]
    assert page.status_code == 200
    page_body = page.json()
    assert page_body["page"] == 2
    assert page_body["pageSize"] == 1
    assert page_body["totalCount"] == 4
    assert page_body["totalPages"] == 4
    assert page_body["hasPreviousPage"] is True
    assert page_body["hasNextPage"] is True
    assert missing_category.status_code == 200
    assert missing_category.json()["items"] == []


async def test_recipe_list_rejects_invalid_query_values(client) -> None:
    response = await client.get("/api/v1/recipes?page=0&pageSize=51&difficulty=Impossible")

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"] == "VALIDATION_ERROR"


async def test_recipe_list_reads_new_rows_when_redis_is_not_configured(client) -> None:
    category = await create_category()
    author, _ = await create_user(client, email="cache@example.com")
    await add_recipe(category, author, title="Lần đầu")

    first = await client.get("/api/v1/recipes?sort=title")
    await add_recipe(category, author, title="Sau cache")
    fresh = await client.get("/api/v1/recipes?sort=title")

    assert first.json()["totalCount"] == 1
    assert fresh.json()["totalCount"] == 2
