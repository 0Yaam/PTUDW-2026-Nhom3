import re
import unicodedata

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.model import User
from ..categories.model import Category
from .model import Recipe, RecipeStatus
from .problem import RecipeProblem
from .schemas import NutritionResponse, RecipeCreateRequest, RecipeCreateResponse

logger = structlog.get_logger()


def generate_slug(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title.replace("đ", "d").replace("Đ", "D"))
    ascii_title = normalized.encode("ascii", "ignore").decode().lower()
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", ascii_title))


def _to_response(recipe: Recipe) -> RecipeCreateResponse:
    nutrition_values = {
        "calories": recipe.nutrition_calories,
        "protein": recipe.nutrition_protein,
        "carbohydrates": recipe.nutrition_carbohydrates,
        "fat": recipe.nutrition_fat,
        "fiber": recipe.nutrition_fiber,
        "sodium": recipe.nutrition_sodium,
    }
    nutrition = (
        NutritionResponse.model_validate(nutrition_values)
        if any(value is not None for value in nutrition_values.values())
        else None
    )
    return RecipeCreateResponse.model_validate(
        {
            "id": recipe.id,
            "title": recipe.title,
            "slug": recipe.slug,
            "description": recipe.description,
            "instructions": recipe.instructions,
            "category_id": recipe.category_id,
            "author_id": recipe.author_id,
            "prep_time_minutes": recipe.prep_time_minutes,
            "cook_time_minutes": recipe.cook_time_minutes,
            "servings": recipe.servings,
            "difficulty": recipe.difficulty,
            "status": "Draft",
            "nutrition": nutrition,
            "created_at": recipe.created_at,
        }
    )


async def create_recipe(
    session: AsyncSession,
    request: RecipeCreateRequest,
    current_user: User,
) -> RecipeCreateResponse:
    if await session.get(Category, request.category_id) is None:
        raise RecipeProblem(
            status=422,
            error_code="VALIDATION_ERROR",
            title="Validation Error",
            detail="One or more fields are invalid.",
            errors={"categoryId": ["Category does not exist."]},
        )

    slug = generate_slug(request.title)
    if not slug:
        raise RecipeProblem(
            status=422,
            error_code="VALIDATION_ERROR",
            title="Validation Error",
            detail="One or more fields are invalid.",
            errors={"title": ["Title must contain letters or numbers."]},
        )
    if await session.scalar(select(Recipe.id).where(Recipe.slug == slug)):
        raise RecipeProblem(
            status=409,
            error_code="RECIPE_SLUG_EXISTS",
            title="Conflict",
            detail="A recipe with this slug already exists.",
        )

    nutrition = request.nutrition
    recipe = Recipe(
        title=request.title,
        slug=slug,
        description=request.description,
        instructions=request.instructions,
        category_id=request.category_id,
        author_id=current_user.id,
        prep_time_minutes=request.prep_time_minutes,
        cook_time_minutes=request.cook_time_minutes,
        servings=request.servings,
        difficulty=request.difficulty.value,
        status=RecipeStatus.DRAFT,
        nutrition_calories=nutrition.calories if nutrition else None,
        nutrition_protein=nutrition.protein if nutrition else None,
        nutrition_carbohydrates=nutrition.carbohydrates if nutrition else None,
        nutrition_fat=nutrition.fat if nutrition else None,
        nutrition_fiber=nutrition.fiber if nutrition else None,
        nutrition_sodium=nutrition.sodium if nutrition else None,
    )
    session.add(recipe)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        if await session.scalar(select(Recipe.id).where(Recipe.slug == slug)):
            raise RecipeProblem(
                status=409,
                error_code="RECIPE_SLUG_EXISTS",
                title="Conflict",
                detail="A recipe with this slug already exists.",
            ) from error
        if await session.get(Category, request.category_id) is None:
            raise RecipeProblem(
                status=422,
                error_code="VALIDATION_ERROR",
                title="Validation Error",
                detail="One or more fields are invalid.",
                errors={"categoryId": ["Category does not exist."]},
            ) from error
        raise
    await session.refresh(recipe)
    logger.info(
        "recipe_draft_created",
        recipe_id=str(recipe.id),
        author_id=str(recipe.author_id),
        category_id=str(recipe.category_id),
    )
    return _to_response(recipe)
