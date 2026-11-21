import json
import uuid

from sqlalchemy import func, select
from test_recipe_list import add_recipe, create_user

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
from culinary_blog_api.recipes.model import RecipeImage, RecipeImageResizeJob
from culinary_blog_api.seed import load_seed_data, seed


class MemoryStorage:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, int]] = []

    async def upload_image(self, data: bytes, folder: str, content_type: str) -> str:
        assert content_type == "image/jpeg" and data[:3] == b"\xff\xd8\xff"
        self.uploads.append((folder, len(data)))
        return f"http://minio.test/culinary/{folder}/{uuid.uuid4().hex}.jpg"


def test_dataset_meets_course_minimum() -> None:
    data = load_seed_data()
    category_slugs = {item["slug"] for item in data.categories}
    recipe_slugs = {item["slug"] for item in data.recipes}
    credits = json.loads(
        (data.directory / "images" / "credits.json").read_text(encoding="utf-8")
    )

    assert len(data.categories) >= 10
    assert len(data.recipes) >= 50
    assert len(recipe_slugs) == len(data.recipes)
    assert set(credits) == recipe_slugs
    for item in data.recipes:
        assert item["category"] in category_slugs
        assert len(item["ingredients"]) >= 4 and len(item["steps"]) >= 4
        assert all(quantity > 0 for _, quantity, _ in item["ingredients"])
        assert (data.directory / "images" / f"{item['slug']}.jpg").is_file(), item["slug"]
    for credit in credits.values():
        assert credit["file"] and credit["source"].startswith("https://")
        assert credit["license"].startswith(("CC0 ", "CC BY ", "CC BY-SA "))
        assert credit["artist"] or credit["license"].startswith("CC0 ")


async def test_seed_loads_complete_real_dataset_once(client) -> None:
    data = load_seed_data()
    storage = MemoryStorage()

    await seed(storage)
    await seed(storage)

    async with SessionFactory() as session:
        recipes = (await session.scalars(select(Recipe))).all()
        categories = await session.scalar(select(func.count()).select_from(Category))
        ingredient_counts = dict(
            (await session.execute(
                select(RecipeIngredient.recipe_id, func.count())
                .group_by(RecipeIngredient.recipe_id)
            )).all()
        )
        step_counts = dict(
            (await session.execute(
                select(RecipeStep.recipe_id, func.count()).group_by(RecipeStep.recipe_id)
            )).all()
        )
        images = (await session.scalars(select(RecipeImage))).all()
        jobs = await session.scalar(select(func.count()).select_from(RecipeImageResizeJob))
        pho = await session.scalar(select(Recipe).where(Recipe.slug == "pho-bo-ha-noi"))

    assert categories == len(data.categories)
    assert len(recipes) == len(data.recipes)
    assert all(recipe.status == RecipeStatus.PUBLISHED for recipe in recipes)
    assert all(ingredient_counts[recipe.id] >= 4 for recipe in recipes)
    assert all(step_counts[recipe.id] >= 4 for recipe in recipes)
    # One primary photo per recipe, uploaded only on the first run.
    assert len(storage.uploads) == len(data.recipes)
    assert len(images) == len(data.recipes) and all(image.is_primary for image in images)
    assert jobs == len(data.recipes)
    assert pho is not None and pho.title == "Phở bò Hà Nội"


async def test_seed_removes_generated_and_test_data(client) -> None:
    async with SessionFactory() as session:
        legacy_author = User(full_name="Lab 2 Seed Author", email="lab2-author@example.local",
                             user_name="lab2-seed-author", password_hash="x", role="Author")
        legacy_category = Category(name="Breakfast", slug="breakfast", description=None)
        e2e_category = Category(name="E2E abc123", slug="e2e-abc123", description=None)
        session.add_all([legacy_author, legacy_category, e2e_category, Ingredient(name="Rice")])
        await session.commit()
        legacy_category_id, legacy_author_id = legacy_category.id, legacy_author.id
    e2e_user, _ = await create_user(client, email="e2e-author-xyz@example.com")
    async with SessionFactory() as session:
        category = await session.get(Category, legacy_category_id)
        legacy_author = await session.get(User, legacy_author_id)
    await add_recipe(category, legacy_author, title="Prepare recipe 001")
    await add_recipe(category, e2e_user, title="Canh chua E2E", status=RecipeStatus.DRAFT)

    summary = await seed(upload_images=False)

    async with SessionFactory() as session:
        emails = set((await session.scalars(select(User.email))).all())
        category_slugs = set((await session.scalars(select(Category.slug))).all())
        titles = set((await session.scalars(select(Recipe.title))).all())
        rice = await session.scalar(select(Ingredient).where(Ingredient.name == "Rice"))

    assert summary["removed"]["users"] == 2 and summary["removed"]["recipes"] == 2
    assert "lab2-author@example.local" not in emails
    assert "e2e-author-xyz@example.com" not in emails
    assert {"breakfast", "e2e-abc123"}.isdisjoint(category_slugs)
    assert {"Prepare recipe 001", "Canh chua E2E"}.isdisjoint(titles)
    assert rice is None


async def test_seed_keeps_real_user_recipes_and_admin_edits(client) -> None:
    await seed(upload_images=False)
    author, _ = await create_user(client, email="my-recipe@example.com")
    async with SessionFactory() as session:
        category = await session.scalar(select(Category).where(Category.slug == "mon-an-sang"))
        category.name = "Ăn sáng mỗi ngày"
        await session.commit()
    recipe = await add_recipe(category, author, title="Cơm rang", status=RecipeStatus.DRAFT)

    await seed(upload_images=False)

    async with SessionFactory() as session:
        unchanged = await session.get(Recipe, recipe.id)
        edited = await session.scalar(select(Category).where(Category.slug == "mon-an-sang"))
        owner = await session.scalar(select(User).where(User.email == "my-recipe@example.com"))
    assert unchanged is not None and unchanged.status == RecipeStatus.DRAFT
    assert edited.name == "Ăn sáng mỗi ngày"
    assert owner is not None
