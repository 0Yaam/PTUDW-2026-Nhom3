from sqlalchemy import func, select

from culinary_blog_api.categories import Category
from culinary_blog_api.db import SessionFactory
from culinary_blog_api.recipes import Recipe, RecipeIngredient, RecipeStep
from culinary_blog_api.seed import (
    INGREDIENTS_PER_RECIPE,
    SEED_RECIPE_COUNT,
    STEPS_PER_RECIPE,
    seed,
)


async def test_seed_creates_complete_lab2_dataset(client) -> None:
    await seed()
    await seed()

    async with SessionFactory() as session:
        category_count = await session.scalar(select(func.count()).select_from(Category))
        recipe_count = await session.scalar(select(func.count()).select_from(Recipe))

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
    assert len(ingredient_counts) >= SEED_RECIPE_COUNT
    assert min(count for _, count in ingredient_counts) >= INGREDIENTS_PER_RECIPE
    assert len(step_counts) >= SEED_RECIPE_COUNT
    assert min(count for _, count in step_counts) >= STEPS_PER_RECIPE
