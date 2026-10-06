"""Read a complete recipe by slug without loading nested rows one by one."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ..auth.model import User
from .model import Recipe, RecipeIngredient, RecipeStatus
from .problem import RecipeProblem
from .schemas import (
    RecipeAuthorSummary,
    RecipeCategorySummary,
    RecipeDetailResponse,
    RecipeImageResponse,
    RecipeIngredientDetail,
    RecipeStepResponse,
)
from .service import _to_response


async def get_recipe_detail(
    session: AsyncSession, slug: str, current_user: User | None
) -> RecipeDetailResponse:
    recipe = await session.scalar(
        select(Recipe)
        .options(
            joinedload(Recipe.category),
            joinedload(Recipe.author),
            selectinload(Recipe.ingredients).joinedload(RecipeIngredient.ingredient),
            selectinload(Recipe.steps),
            selectinload(Recipe.images),
        )
        .where(Recipe.slug == slug, Recipe.is_deleted.is_(False))
    )
    if recipe is None:
        raise RecipeProblem(
            status=404,
            error_code="RECIPE_NOT_FOUND",
            title="Not Found",
            detail="Recipe was not found.",
        )
    if recipe.status != RecipeStatus.PUBLISHED and (
        current_user is None
        or (current_user.role != "Admin" and recipe.author_id != current_user.id)
    ):
        raise RecipeProblem(
            status=403,
            error_code="RECIPE_FORBIDDEN",
            title="Forbidden",
            detail="Only the recipe owner or an Admin can view this recipe.",
        )

    return RecipeDetailResponse.model_validate(
        {
            **_to_response(recipe).model_dump(),
            "category": RecipeCategorySummary.model_validate(recipe.category),
            "author": RecipeAuthorSummary.model_validate(recipe.author),
            "ingredients": [
                RecipeIngredientDetail(
                    id=item.id,
                    ingredient_id=item.ingredient_id,
                    name=item.ingredient.name,
                    quantity=float(item.quantity),
                    unit=item.unit,
                    order_index=item.order_index,
                )
                for item in recipe.ingredients
            ],
            "steps": [RecipeStepResponse.model_validate(step) for step in recipe.steps],
            "images": [RecipeImageResponse.model_validate(image) for image in recipe.images],
            "published_at": recipe.published_at,
        }
    )
