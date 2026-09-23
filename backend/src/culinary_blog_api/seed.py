import asyncio
import random
import secrets
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import User
from .auth.security import hash_password
from .categories import Category
from .db import SessionFactory
from .recipes import Ingredient, Recipe, RecipeIngredient, RecipeStatus, RecipeStep

SEED_CATEGORIES = [
    ("Vietnamese Food", "vietnamese-food", "Home recipes from across Vietnam."),
    ("Breakfast", "breakfast", "Simple meals for a good start to the day."),
    ("Plant-Based", "plant-based", "Fresh recipes with vegetables and grains."),
    ("Baking and Desserts", "baking-and-desserts", "Sweet food to bake and share."),
    ("Healthy Meals", "healthy-meals", "Balanced everyday meals."),
    ("Quick and Easy", "quick-and-easy", "Recipes ready with little preparation."),
    ("Soups", "soups", "Warm and comforting soups."),
    ("Salads", "salads", "Fresh and colourful salads."),
    ("Noodles", "noodles", "Noodle dishes for every occasion."),
    ("Rice Dishes", "rice-dishes", "Comforting meals served with rice."),
    ("Seafood", "seafood", "Recipes featuring fish and shellfish."),
    ("Chicken", "chicken", "Simple and flavourful chicken dishes."),
    ("Beef", "beef", "Hearty recipes made with beef."),
    ("Pork", "pork", "Everyday pork recipes."),
    ("Vegetarian", "vegetarian", "Meat-free meals for the whole family."),
    ("Snacks", "snacks", "Small bites and afternoon snacks."),
    ("Drinks", "drinks", "Refreshing homemade drinks."),
    ("Street Food", "street-food", "Popular street-food favourites."),
    ("Family Meals", "family-meals", "Recipes made for sharing."),
    ("Festive Food", "festive-food", "Food for holidays and celebrations."),
]

SEED_INGREDIENTS = [
    "Rice",
    "Rice noodles",
    "Egg noodles",
    "Chicken breast",
    "Chicken thigh",
    "Beef",
    "Pork",
    "Shrimp",
    "White fish",
    "Egg",
    "Tofu",
    "Mushroom",
    "Carrot",
    "Potato",
    "Sweet potato",
    "Tomato",
    "Cucumber",
    "Cabbage",
    "Spinach",
    "Broccoli",
    "Bell pepper",
    "Onion",
    "Spring onion",
    "Garlic",
    "Ginger",
    "Lemongrass",
    "Chilli",
    "Coriander",
    "Basil",
    "Mint",
    "Lime",
    "Coconut milk",
    "Fish sauce",
    "Soy sauce",
    "Oyster sauce",
    "Cooking oil",
    "Sesame oil",
    "Sugar",
    "Salt",
    "Black pepper",
]

SEED_AUTHOR_EMAIL = "lab2-author@example.local"
SEED_RECIPE_COUNT = 100
INGREDIENTS_PER_RECIPE = 10
STEPS_PER_RECIPE = 5


async def _seed_categories(session: AsyncSession) -> list[Category]:
    slugs = [slug for _, slug, _ in SEED_CATEGORIES]
    existing = {
        category.slug: category
        for category in (
            await session.scalars(select(Category).where(Category.slug.in_(slugs)))
        ).all()
    }

    for order_index, (name, slug, description) in enumerate(SEED_CATEGORIES, start=1):
        if slug not in existing:
            existing[slug] = Category(
                name=name,
                slug=slug,
                description=description,
                order_index=order_index,
            )
            session.add(existing[slug])

    await session.flush()
    return [existing[slug] for slug in slugs]


async def _seed_author(session: AsyncSession) -> User:
    author = await session.scalar(select(User).where(User.email == SEED_AUTHOR_EMAIL))
    if author is None:
        author = User(
            full_name="Lab 2 Seed Author",
            email=SEED_AUTHOR_EMAIL,
            user_name="lab2-seed-author",
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role="Author",
        )
        session.add(author)
        await session.flush()
    return author


async def _seed_ingredients(session: AsyncSession) -> list[Ingredient]:
    existing = {
        ingredient.name: ingredient
        for ingredient in (
            await session.scalars(
                select(Ingredient).where(Ingredient.name.in_(SEED_INGREDIENTS))
            )
        ).all()
    }

    for name in SEED_INGREDIENTS:
        if name not in existing:
            existing[name] = Ingredient(name=name)
            session.add(existing[name])

    await session.flush()
    return [existing[name] for name in SEED_INGREDIENTS]


async def _seed_recipes(
    session: AsyncSession,
    categories: list[Category],
    author: User,
    ingredients: list[Ingredient],
) -> None:
    slugs = [f"lab2-recipe-{number:03d}" for number in range(1, SEED_RECIPE_COUNT + 1)]
    recipes = {
        recipe.slug: recipe
        for recipe in (
            await session.scalars(select(Recipe).where(Recipe.slug.in_(slugs)))
        ).all()
    }

    for number, slug in enumerate(slugs, start=1):
        if slug in recipes:
            continue
        generator = random.Random(20260922 + number)
        recipe = Recipe(
            title=f"Lab 2 Recipe {number:03d}",
            slug=slug,
            description=f"Generated sample recipe number {number} for Lab 2.",
            instructions="Follow the five detailed preparation steps in order.",
            prep_time_minutes=generator.randint(5, 30),
            cook_time_minutes=generator.randint(10, 60),
            servings=generator.randint(2, 6),
            difficulty=generator.randint(1, 4),
            status=RecipeStatus.PUBLISHED,
            category_id=generator.choice(categories).id,
            author_id=author.id,
            nutrition_calories=Decimal(generator.randint(150, 700)),
            nutrition_protein=Decimal(generator.randint(5, 45)),
            nutrition_carbohydrates=Decimal(generator.randint(10, 90)),
            nutrition_fat=Decimal(generator.randint(2, 35)),
            nutrition_fiber=Decimal(generator.randint(1, 15)),
            nutrition_sodium=Decimal(generator.randint(50, 900)),
            published_at=datetime.now(UTC),
        )
        recipes[slug] = recipe
        session.add(recipe)

    await session.flush()
    recipe_list = [recipes[slug] for slug in slugs]
    recipe_ids = [recipe.id for recipe in recipe_list]

    ingredient_rows = (
        await session.scalars(
            select(RecipeIngredient).where(RecipeIngredient.recipe_id.in_(recipe_ids))
        )
    ).all()
    ingredient_ids_by_recipe: dict[object, set[object]] = defaultdict(set)
    for row in ingredient_rows:
        ingredient_ids_by_recipe[row.recipe_id].add(row.ingredient_id)

    step_rows = (
        await session.scalars(select(RecipeStep).where(RecipeStep.recipe_id.in_(recipe_ids)))
    ).all()
    step_numbers_by_recipe: dict[object, set[int]] = defaultdict(set)
    for row in step_rows:
        step_numbers_by_recipe[row.recipe_id].add(row.step_number)

    units = ["g", "ml", "tbsp", "tsp", "piece"]
    for number, recipe in enumerate(recipe_list, start=1):
        generator = random.Random(20260922 + number)
        selected = generator.sample(ingredients, INGREDIENTS_PER_RECIPE)
        existing_ingredient_ids = ingredient_ids_by_recipe[recipe.id]

        for order_index, ingredient in enumerate(selected, start=1):
            if len(existing_ingredient_ids) >= INGREDIENTS_PER_RECIPE:
                break
            if ingredient.id in existing_ingredient_ids:
                continue
            session.add(
                RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=ingredient.id,
                    quantity=Decimal(generator.randint(1, 500)),
                    unit=generator.choice(units),
                    order_index=order_index,
                )
            )
            existing_ingredient_ids.add(ingredient.id)

        existing_step_numbers = step_numbers_by_recipe[recipe.id]
        for step_number in range(1, STEPS_PER_RECIPE + 1):
            if step_number not in existing_step_numbers:
                session.add(
                    RecipeStep(
                        recipe_id=recipe.id,
                        step_number=step_number,
                        instruction=(
                            f"Prepare recipe {number:03d}, step {step_number}: "
                            "combine the ingredients and cook as described."
                        ),
                    )
                )


async def seed() -> None:
    async with SessionFactory() as session:
        categories = await _seed_categories(session)
        author = await _seed_author(session)
        ingredients = await _seed_ingredients(session)
        await _seed_recipes(session, categories, author, ingredients)
        await session.commit()


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
