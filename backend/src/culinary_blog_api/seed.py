"""Load the real recipe dataset and remove generated or test-only data.

The dataset lives in ``backend/seed_data``: ``recipes.json`` holds categories and
recipes (ingredients with quantities, cooking steps, nutrition) and ``images/``
holds one freely licensed photo per recipe (sources in ``images/credits.json``).

Running ``seed`` is idempotent. Each run:
1. deletes the old generated Lab 2 dataset, accounts and content created by the
   end-to-end tests, and categories/ingredients that are no longer used;
2. creates or updates every category and recipe from the dataset;
3. uploads each recipe photo to object storage once and queues the resize job.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import structlog
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import User
from .auth.security import hash_password
from .categories import Category
from .db import SessionFactory
from .recipes import Ingredient, Recipe, RecipeIngredient, RecipeStatus, RecipeStep
from .recipes.cache import invalidate_recipe_caches
from .recipes.model import RecipeImage, RecipeImageResizeJob
from .storage import S3FileStorage
from .storage.model import FileDeletionJob
from .storage.service import StorageNotConfigured, StorageUnavailable

logger = structlog.get_logger()

SEED_AUTHOR_EMAIL = "bep@culinary-blog.local"
SEED_AUTHOR_NAME = "Bếp Culinary Blog"
SEED_AUTHOR_USERNAME = "bep_culinary"

# Generated data from earlier labs and data created by automated tests.
LEGACY_AUTHOR_EMAILS = ("lab2-author@example.local",)
TEST_USER_EMAIL_PATTERNS = ("e2e-%@example.com",)
TEST_CATEGORY_NAME_PATTERNS = ("E2E %",)
LEGACY_CATEGORY_SLUGS = (
    "vietnamese-food", "breakfast", "plant-based", "baking-and-desserts", "healthy-meals",
    "quick-and-easy", "soups", "salads", "noodles", "rice-dishes", "seafood", "chicken",
    "beef", "pork", "vegetarian", "snacks", "drinks", "street-food", "family-meals",
    "festive-food",
)


def _data_dir() -> Path:
    candidates = [
        Path(os.environ["SEED_DATA_DIR"]) if os.environ.get("SEED_DATA_DIR") else None,
        Path.cwd() / "seed_data",
        Path(__file__).resolve().parents[2] / "seed_data",
    ]
    for candidate in candidates:
        if candidate is not None and (candidate / "recipes.json").is_file():
            return candidate
    raise FileNotFoundError("seed_data/recipes.json was not found; set SEED_DATA_DIR.")


@dataclass(frozen=True)
class SeedData:
    directory: Path
    categories: list[dict]
    recipes: list[dict]


@lru_cache
def load_seed_data() -> SeedData:
    directory = _data_dir()
    raw = json.loads((directory / "recipes.json").read_text(encoding="utf-8"))
    return SeedData(directory, raw["categories"], raw["recipes"])


async def _delete_recipes(session: AsyncSession, recipe_ids: list[uuid.UUID]) -> int:
    """Delete recipes and queue their stored photos for durable cleanup."""
    if not recipe_ids:
        return 0
    images = (
        await session.scalars(select(RecipeImage).where(RecipeImage.recipe_id.in_(recipe_ids)))
    ).all()
    for image in images:
        session.add(
            FileDeletionJob(original_url=image.original_url, recipe_id=image.recipe_id,
                            image_id=image.id)
        )
    await session.execute(delete(Recipe).where(Recipe.id.in_(recipe_ids)))
    return len(recipe_ids)


async def remove_test_data(session: AsyncSession) -> dict[str, int]:
    """Remove generated and test-only users, recipes, categories and ingredients."""
    user_filter = or_(
        User.email.in_(LEGACY_AUTHOR_EMAILS),
        *(User.email.like(pattern) for pattern in TEST_USER_EMAIL_PATTERNS),
    )
    user_ids = list((await session.scalars(select(User.id).where(user_filter))).all())
    recipe_ids = list(
        (await session.scalars(select(Recipe.id).where(Recipe.author_id.in_(user_ids)))).all()
    ) if user_ids else []
    removed_recipes = await _delete_recipes(session, recipe_ids)
    if user_ids:
        await session.execute(delete(User).where(User.id.in_(user_ids)))

    used_categories = select(Recipe.category_id).distinct()
    category_result = await session.execute(
        delete(Category).where(
            or_(
                Category.slug.in_(LEGACY_CATEGORY_SLUGS),
                *(Category.name.like(pattern) for pattern in TEST_CATEGORY_NAME_PATTERNS),
            ),
            Category.id.not_in(used_categories),
        )
    )
    used_ingredients = select(RecipeIngredient.ingredient_id).distinct()
    ingredient_result = await session.execute(
        delete(Ingredient).where(Ingredient.id.not_in(used_ingredients))
    )
    await session.flush()
    return {
        "users": len(user_ids),
        "recipes": removed_recipes,
        "categories": category_result.rowcount or 0,
        "ingredients": ingredient_result.rowcount or 0,
    }


async def _seed_categories(session: AsyncSession, data: SeedData) -> dict[str, Category]:
    slugs = [item["slug"] for item in data.categories]
    existing = {
        category.slug: category
        for category in (
            await session.scalars(select(Category).where(Category.slug.in_(slugs)))
        ).all()
    }
    for order_index, item in enumerate(data.categories, start=1):
        if item["slug"] not in existing:
            # Admin edits to existing categories are kept; only missing ones are created.
            existing[item["slug"]] = Category(
                name=item["name"], slug=item["slug"], description=item["description"],
                order_index=order_index,
            )
            session.add(existing[item["slug"]])
    await session.flush()
    return existing


async def _seed_author(session: AsyncSession) -> User:
    author = await session.scalar(select(User).where(User.email == SEED_AUTHOR_EMAIL))
    if author is None:
        author = User(
            full_name=SEED_AUTHOR_NAME,
            email=SEED_AUTHOR_EMAIL,
            user_name=SEED_AUTHOR_USERNAME,
            # Editorial account: content owner only, nobody signs in with it.
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role="Author",
        )
        session.add(author)
        await session.flush()
    return author


async def _seed_ingredients(session: AsyncSession, data: SeedData) -> dict[str, Ingredient]:
    names = sorted({row[0] for recipe in data.recipes for row in recipe["ingredients"]})
    existing = {
        item.name: item
        for item in (await session.scalars(select(Ingredient).where(Ingredient.name.in_(names))))
    }
    for name in names:
        if name not in existing:
            existing[name] = Ingredient(name=name)
            session.add(existing[name])
    await session.flush()
    return existing


def _decimal(value: float | int | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


async def _seed_recipes(
    session: AsyncSession,
    data: SeedData,
    categories: dict[str, Category],
    author: User,
    ingredients: dict[str, Ingredient],
) -> list[Recipe]:
    slugs = [item["slug"] for item in data.recipes]
    existing = {
        recipe.slug: recipe
        for recipe in (await session.scalars(select(Recipe).where(Recipe.slug.in_(slugs))))
    }
    recipes: list[Recipe] = []
    for item in data.recipes:
        recipe = existing.get(item["slug"])
        if recipe is not None and recipe.author_id != author.id:
            # Never take over a recipe that a real user published with the same slug.
            logger.warning("seed_recipe_slug_taken", slug=item["slug"])
            continue
        calories, protein, carbs, fat, fiber, sodium = item["nutrition"]
        values = {
            "title": item["title"],
            "description": item["description"],
            "instructions": "",
            "prep_time_minutes": item["prep"],
            "cook_time_minutes": item["cook"],
            "servings": item["servings"],
            "difficulty": item["difficulty"],
            "category_id": categories[item["category"]].id,
            "nutrition_calories": _decimal(calories),
            "nutrition_protein": _decimal(protein),
            "nutrition_carbohydrates": _decimal(carbs),
            "nutrition_fat": _decimal(fat),
            "nutrition_fiber": _decimal(fiber),
            "nutrition_sodium": _decimal(sodium),
        }
        if recipe is None:
            recipe = Recipe(
                slug=item["slug"], author_id=author.id, status=RecipeStatus.PUBLISHED,
                published_at=datetime.now(UTC), **values,
            )
            session.add(recipe)
        else:
            changed = any(getattr(recipe, key) != value for key, value in values.items())
            if changed:
                for key, value in values.items():
                    setattr(recipe, key, value)
            if recipe.status != RecipeStatus.PUBLISHED:
                recipe.status = RecipeStatus.PUBLISHED
                recipe.published_at = recipe.published_at or datetime.now(UTC)
        recipes.append(recipe)
    await session.flush()

    by_slug = {item["slug"]: item for item in data.recipes}
    recipe_ids = [recipe.id for recipe in recipes]
    await session.execute(
        delete(RecipeIngredient).where(RecipeIngredient.recipe_id.in_(recipe_ids))
    )
    await session.execute(delete(RecipeStep).where(RecipeStep.recipe_id.in_(recipe_ids)))
    for recipe in recipes:
        item = by_slug[recipe.slug]
        for order_index, (name, quantity, unit) in enumerate(item["ingredients"]):
            session.add(
                RecipeIngredient(
                    recipe_id=recipe.id, ingredient_id=ingredients[name].id,
                    quantity=_decimal(quantity), unit=unit, order_index=order_index,
                )
            )
        for number, (instruction, minutes) in enumerate(item["steps"], start=1):
            session.add(
                RecipeStep(
                    recipe_id=recipe.id, step_number=number, instruction=instruction,
                    duration_minutes=minutes,
                )
            )
    await session.flush()
    return recipes


async def _seed_images(
    session: AsyncSession, data: SeedData, recipes: list[Recipe], storage: S3FileStorage | None
) -> int:
    """Upload one photo per recipe that has none yet and queue its resize job."""
    if storage is None:
        return 0
    with_images = set(
        (
            await session.scalars(
                select(RecipeImage.recipe_id)
                .where(RecipeImage.recipe_id.in_([recipe.id for recipe in recipes]))
                .distinct()
            )
        ).all()
    )
    uploaded = 0
    for recipe in recipes:
        path = data.directory / "images" / f"{recipe.slug}.jpg"
        if recipe.id in with_images or not path.is_file():
            continue
        url = await storage.upload_image(path.read_bytes(), f"recipes/{recipe.id}", "image/jpeg")
        image = RecipeImage(
            id=uuid.uuid4(), recipe_id=recipe.id, original_url=url,
            alt_text=recipe.title[:200], is_primary=True, order_index=0,
        )
        session.add(image)
        await session.flush()
        session.add(RecipeImageResizeJob(image_id=image.id))
        uploaded += 1
    return uploaded


def _storage() -> S3FileStorage | None:
    try:
        return S3FileStorage()
    except StorageNotConfigured:
        logger.warning("seed_images_skipped", reason="object storage is not configured")
        return None


async def seed(storage: S3FileStorage | None = None, *, upload_images: bool = True) -> dict:
    data = load_seed_data()
    async with SessionFactory() as session:
        removed = await remove_test_data(session)
        categories = await _seed_categories(session, data)
        author = await _seed_author(session)
        ingredients = await _seed_ingredients(session, data)
        recipes = await _seed_recipes(session, data, categories, author, ingredients)
        uploaded = 0
        if upload_images:
            try:
                uploaded = await _seed_images(session, data, recipes, storage or _storage())
            except StorageUnavailable:
                logger.warning("seed_images_skipped", reason="object storage is unavailable")
        await session.commit()
        recipe_count = await session.scalar(select(func.count()).select_from(Recipe))
    await invalidate_recipe_caches()
    summary = {"removed": removed, "recipes": len(recipes), "images_uploaded": uploaded,
               "total_recipes": recipe_count}
    logger.info("seed_completed", **summary)
    return summary


def main() -> None:
    print(json.dumps(asyncio.run(seed()), ensure_ascii=False))


if __name__ == "__main__":
    main()
