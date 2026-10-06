from sqlalchemy import func, select

from culinary_blog_api.categories import Category
from culinary_blog_api.db import SessionFactory
from culinary_blog_api.recipes import Recipe, RecipeIngredient, RecipeStep
from culinary_blog_api.recipes.service import generate_slug
from culinary_blog_api.seed import (
    INGREDIENTS_PER_RECIPE,
    SEED_RECIPE_COUNT,
    SEED_RECIPE_TITLES,
    STEPS_PER_RECIPE,
    seed,
)


async def test_seed_creates_complete_lab2_dataset(client) -> None:
    await seed()
    await seed()

    async with SessionFactory() as session:
        category_count = await session.scalar(select(func.count()).select_from(Category))
        recipe_count = await session.scalar(select(func.count()).select_from(Recipe))
        titles = (
            await session.scalars(
                select(Recipe.title).where(
                    Recipe.slug.in_(("pho-bo-ha-noi", "xoi-gac"))
                )
            )
        ).all()
        seeded_slugs = (
            await session.scalars(
                select(Recipe.slug).where(Recipe.title.in_(SEED_RECIPE_TITLES))
            )
        ).all()

        ingredient_counts = (
            await session.execute(
                select(RecipeIngredient.recipe_id, func.count())
                .group_by(RecipeIngredient.recipe_id)
                .order_by(RecipeIngredient.recipe_id)
            )
        ).all()
        step_counts = (
            await session.execute(
                select(RecipeStep.recipe_id, func.count())
                .group_by(RecipeStep.recipe_id)
                .order_by(RecipeStep.recipe_id)
            )
        ).all()

    assert category_count is not None and category_count >= 20
    assert recipe_count is not None and recipe_count >= SEED_RECIPE_COUNT
    assert set(titles) == {"Phở bò Hà Nội", "Xôi gấc"}
    assert set(seeded_slugs) == {generate_slug(title) for title in SEED_RECIPE_TITLES}
    assert len(ingredient_counts) >= SEED_RECIPE_COUNT
    assert min(count for _, count in ingredient_counts) >= INGREDIENTS_PER_RECIPE
    assert len(step_counts) >= SEED_RECIPE_COUNT
    assert min(count for _, count in step_counts) >= STEPS_PER_RECIPE


async def test_seed_updates_legacy_recipe_slug_without_recreating_it(client) -> None:
    await seed()
    async with SessionFactory() as session:
        recipe = await session.scalar(select(Recipe).where(Recipe.slug == "pho-bo-ha-noi"))
        assert recipe is not None
        recipe_id = recipe.id
        recipe.slug = "lab2-recipe-001"
        await session.commit()

    await seed()

    async with SessionFactory() as session:
        recipe = await session.scalar(select(Recipe).where(Recipe.id == recipe_id))
        assert recipe is not None
        assert recipe.slug == "pho-bo-ha-noi"
        assert await session.scalar(
            select(func.count()).select_from(RecipeIngredient).where(
                RecipeIngredient.recipe_id == recipe_id
            )
        ) == INGREDIENTS_PER_RECIPE
        assert await session.scalar(
            select(func.count()).select_from(RecipeStep).where(RecipeStep.recipe_id == recipe_id)
        ) == STEPS_PER_RECIPE
