from sqlalchemy import func, select
from test_recipe_list import add_recipe, create_user

from culinary_blog_api.categories import Category
from culinary_blog_api.db import SessionFactory
from culinary_blog_api.recipes import Recipe, RecipeIngredient, RecipeStatus, RecipeStep
from culinary_blog_api.recipes.service import generate_slug
from culinary_blog_api.seed import (
    INGREDIENTS_PER_RECIPE,
    SEED_CATEGORIES,
    SEED_RECIPE_COUNT,
    SEED_RECIPE_TITLES,
    SEED_RECIPES_PER_CATEGORY,
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
        category_by_title = dict(
            (
                await session.execute(
                    select(Recipe.title, Category.slug)
                    .join(Category, Recipe.category_id == Category.id)
                    .where(Recipe.title.in_(SEED_RECIPE_TITLES))
                )
            ).all()
        )

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
    assert all(
        category_by_title[title] == SEED_CATEGORIES[index // SEED_RECIPES_PER_CATEGORY][1]
        for index, title in enumerate(SEED_RECIPE_TITLES)
    )
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
        recipe.category_id = await session.scalar(
            select(Category.id).where(Category.slug == "beef")
        )
        await session.commit()

    await seed()

    async with SessionFactory() as session:
        recipe = await session.scalar(select(Recipe).where(Recipe.id == recipe_id))
        assert recipe is not None
        assert recipe.slug == "pho-bo-ha-noi"
        assert recipe.category_id == await session.scalar(
            select(Category.id).where(Category.slug == "vietnamese-food")
        )
        assert await session.scalar(
            select(func.count()).select_from(RecipeIngredient).where(
                RecipeIngredient.recipe_id == recipe_id
            )
        ) == INGREDIENTS_PER_RECIPE
        assert await session.scalar(
            select(func.count()).select_from(RecipeStep).where(RecipeStep.recipe_id == recipe_id)
        ) == STEPS_PER_RECIPE


async def test_seed_does_not_reassign_user_recipe(client) -> None:
    await seed()
    author, _ = await create_user(client, email="my-recipe@example.com")
    async with SessionFactory() as session:
        category = await session.scalar(select(Category).where(Category.slug == "vietnamese-food"))
        assert category is not None
    recipe = await add_recipe(category, author, title="Cơm rang", status=RecipeStatus.DRAFT)

    await seed()

    async with SessionFactory() as session:
        unchanged = await session.get(Recipe, recipe.id)
        assert unchanged is not None
        assert unchanged.category_id == category.id
        assert unchanged.status == RecipeStatus.DRAFT
