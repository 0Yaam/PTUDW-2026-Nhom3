import re
import unicodedata
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import StaleDataError

from ..auth.model import User
from ..categories.model import Category
from .cache import invalidate_recipe_caches
from .model import Ingredient, Recipe, RecipeImage, RecipeIngredient, RecipeStatus, RecipeStep
from .problem import RecipeProblem
from .schemas import (
    NutritionResponse,
    PagedRecipeResponse,
    RecipeCreateRequest,
    RecipeCreateResponse,
    RecipeIngredientCreateRequest,
    RecipeIngredientResponse,
    RecipeIngredientUpdateRequest,
    RecipeListQuery,
    RecipeStepCreateRequest,
    RecipeStepResponse,
    RecipeStepUpdateRequest,
    RecipeSummaryResponse,
    RecipeUpdateRequest,
)

logger = structlog.get_logger()

_STATUS_LABELS = {
    RecipeStatus.DRAFT: "Draft",
    RecipeStatus.PUBLISHED: "Published",
    RecipeStatus.ARCHIVED: "Archived",
}


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
            "status": _STATUS_LABELS[RecipeStatus(recipe.status)],
            "nutrition": nutrition,
            "created_at": recipe.created_at,
            "row_version": recipe.row_version.hex(),
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
    await invalidate_recipe_caches()
    logger.info(
        "recipe_draft_created",
        recipe_id=str(recipe.id),
        author_id=str(recipe.author_id),
        category_id=str(recipe.category_id),
    )
    return _to_response(recipe)


async def set_publication_status(
    session: AsyncSession,
    recipe_id: uuid.UUID,
    current_user: User,
    *,
    publish: bool,
) -> RecipeCreateResponse:
    recipe = await session.get(Recipe, recipe_id)
    if recipe is None or recipe.is_deleted:
        raise RecipeProblem(
            status=404,
            error_code="RECIPE_NOT_FOUND",
            title="Not Found",
            detail="Recipe was not found.",
        )
    if current_user.role != "Admin" and recipe.author_id != current_user.id:
        raise RecipeProblem(
            status=403,
            error_code="RECIPE_FORBIDDEN",
            title="Forbidden",
            detail="Only the recipe owner or an Admin can change publication status.",
        )
    if recipe.status == RecipeStatus.ARCHIVED:
        raise RecipeProblem(
            status=422,
            error_code="RECIPE_ARCHIVED",
            title="Validation Error",
            detail="Archived recipes cannot be published or unpublished.",
        )

    if publish and recipe.status != RecipeStatus.PUBLISHED:
        ingredient_count = await session.scalar(
            select(func.count()).select_from(RecipeIngredient).where(
                RecipeIngredient.recipe_id == recipe.id
            )
        )
        step_count = await session.scalar(
            select(func.count()).select_from(RecipeStep).where(RecipeStep.recipe_id == recipe.id)
        )
        if not ingredient_count or not step_count:
            raise RecipeProblem(
                status=422,
                error_code="RECIPE_NOT_READY",
                title="Validation Error",
                detail="A recipe needs at least one ingredient and one step before publishing.",
            )
        recipe.status = RecipeStatus.PUBLISHED
        recipe.published_at = datetime.now(UTC)
    elif not publish and recipe.status == RecipeStatus.PUBLISHED:
        recipe.status = RecipeStatus.DRAFT
        recipe.published_at = None

    try:
        await session.commit()
    except StaleDataError as error:
        await session.rollback()
        raise _version_conflict() from error
    await session.refresh(recipe)
    await invalidate_recipe_caches()
    return _to_response(recipe)


def _recipe_not_found() -> RecipeProblem:
    return RecipeProblem(
        status=404,
        error_code="RECIPE_NOT_FOUND",
        title="Not Found",
        detail="Recipe was not found.",
    )


def _recipe_forbidden() -> RecipeProblem:
    return RecipeProblem(
        status=403,
        error_code="RECIPE_FORBIDDEN",
        title="Forbidden",
        detail="Only the recipe owner or an Admin can change this recipe.",
    )


def _version_conflict() -> RecipeProblem:
    return RecipeProblem(
        status=409,
        error_code="RECIPE_VERSION_CONFLICT",
        title="Conflict",
        detail="Recipe changed since it was loaded. Reload it and try again.",
    )


async def _owned_recipe(
    session: AsyncSession,
    recipe_id: uuid.UUID,
    current_user: User,
    *,
    lock: bool = False,
) -> Recipe:
    query = select(Recipe).where(Recipe.id == recipe_id, Recipe.is_deleted.is_(False))
    if lock:
        query = query.with_for_update()
    recipe = await session.scalar(query)
    if recipe is None:
        raise _recipe_not_found()
    if current_user.role != "Admin" and recipe.author_id != current_user.id:
        raise _recipe_forbidden()
    return recipe


async def update_recipe(
    session: AsyncSession,
    recipe_id: uuid.UUID,
    data: RecipeUpdateRequest,
    current_user: User,
    if_match: str | None,
) -> RecipeCreateResponse:
    """Replace editable recipe fields with an optimistic concurrency check."""
    recipe = await _owned_recipe(session, recipe_id, current_user)
    supplied_version = if_match if if_match is not None else data.row_version
    if supplied_version is None:
        raise RecipeProblem(
            status=428,
            error_code="RECIPE_VERSION_REQUIRED",
            title="Precondition Required",
            detail="Send the current rowVersion in If-Match or the request body.",
        )
    if supplied_version.strip('"') != recipe.row_version.hex():
        raise _version_conflict()
    if await session.get(Category, data.category_id) is None:
        raise RecipeProblem(
            status=422,
            error_code="VALIDATION_ERROR",
            title="Validation Error",
            detail="One or more fields are invalid.",
            errors={"categoryId": ["Category does not exist."]},
        )

    nutrition = data.nutrition
    recipe.title = data.title
    recipe.description = data.description
    recipe.instructions = data.instructions
    recipe.category_id = data.category_id
    recipe.prep_time_minutes = data.prep_time_minutes
    recipe.cook_time_minutes = data.cook_time_minutes
    recipe.servings = data.servings
    recipe.difficulty = data.difficulty.value
    for field in ("calories", "protein", "carbohydrates", "fat", "fiber", "sodium"):
        setattr(recipe, f"nutrition_{field}", getattr(nutrition, field) if nutrition else None)
    recipe.updated_at = datetime.now(UTC)
    try:
        await session.commit()
    except StaleDataError as error:
        await session.rollback()
        raise _version_conflict() from error
    except IntegrityError as error:
        await session.rollback()
        raise RecipeProblem(
            status=409,
            error_code="RECIPE_CONFLICT",
            title="Conflict",
            detail="Recipe could not be updated because related data changed.",
        ) from error
    await session.refresh(recipe)
    await invalidate_recipe_caches()
    logger.info("recipe_updated", recipe_id=str(recipe.id), author_id=str(recipe.author_id))
    return _to_response(recipe)


async def delete_recipe(
    session: AsyncSession,
    recipe_id: uuid.UUID,
    current_user: User,
) -> None:
    """Hard-delete metadata and enqueue every image object for durable cleanup."""
    recipe = await _owned_recipe(session, recipe_id, current_user, lock=True)
    from ..storage.cleanup import queue_image_cleanup

    images = await session.scalars(select(RecipeImage).where(RecipeImage.recipe_id == recipe_id))
    for image in images:
        queue_image_cleanup(session, image)
    await session.delete(recipe)
    try:
        await session.commit()
    except StaleDataError as error:
        await session.rollback()
        raise _version_conflict() from error
    await invalidate_recipe_caches()
    logger.info("recipe_deleted", recipe_id=str(recipe_id))


def _ingredient_not_found() -> RecipeProblem:
    return RecipeProblem(
        status=404,
        error_code="RECIPE_INGREDIENT_NOT_FOUND",
        title="Not Found",
        detail="Recipe ingredient was not found.",
    )


def _ingredient_exists() -> RecipeProblem:
    return RecipeProblem(
        status=409,
        error_code="RECIPE_INGREDIENT_EXISTS",
        title="Conflict",
        detail="This ingredient is already on the recipe.",
    )


async def _get_or_create_ingredient(session: AsyncSession, name: str) -> Ingredient:
    ingredient = await session.scalar(select(Ingredient).where(Ingredient.name == name))
    if ingredient is None:
        ingredient = Ingredient(name=name)
        session.add(ingredient)
        await session.flush()
    return ingredient


async def _recipe_ingredients(
    session: AsyncSession, recipe_id: uuid.UUID
) -> list[RecipeIngredient]:
    return list(
        await session.scalars(
            select(RecipeIngredient)
            .where(RecipeIngredient.recipe_id == recipe_id)
            .options(joinedload(RecipeIngredient.ingredient))
            .order_by(RecipeIngredient.order_index)
        )
    )


async def _renumber_ingredients(
    recipe_ingredients: list[RecipeIngredient],
) -> None:
    for index, row in enumerate(recipe_ingredients):
        row.order_index = index


def _to_ingredient_response(row: RecipeIngredient) -> RecipeIngredientResponse:
    return RecipeIngredientResponse.model_validate(
        {
            "id": row.id,
            "recipe_id": row.recipe_id,
            "ingredient_id": row.ingredient_id,
            "name": row.ingredient.name,
            "quantity": row.quantity,
            "unit": row.unit,
            "order_index": row.order_index,
        }
    )


async def create_recipe_ingredient(
    session: AsyncSession,
    recipe_id: uuid.UUID,
    data: RecipeIngredientCreateRequest,
    current_user: User,
) -> RecipeIngredientResponse:
    recipe = await _owned_recipe(session, recipe_id, current_user, lock=True)
    ingredient = await _get_or_create_ingredient(session, data.ingredient_name)
    already_used = await session.scalar(
        select(RecipeIngredient.id).where(
            RecipeIngredient.recipe_id == recipe_id,
            RecipeIngredient.ingredient_id == ingredient.id,
        )
    )
    if already_used is not None:
        raise _ingredient_exists()

    next_order = await session.scalar(
        select(func.count()).select_from(RecipeIngredient).where(
            RecipeIngredient.recipe_id == recipe_id
        )
    )
    row = RecipeIngredient(
        recipe_id=recipe_id,
        ingredient_id=ingredient.id,
        quantity=data.quantity,
        unit=data.unit,
        order_index=next_order or 0,
    )
    session.add(row)
    recipe.updated_at = datetime.now(UTC)
    try:
        await session.commit()
    except StaleDataError as error:
        await session.rollback()
        raise _version_conflict() from error
    await session.refresh(row, attribute_names=["ingredient"])
    return _to_ingredient_response(row)


async def update_recipe_ingredient(
    session: AsyncSession,
    recipe_id: uuid.UUID,
    ingredient_row_id: uuid.UUID,
    data: RecipeIngredientUpdateRequest,
    current_user: User,
) -> RecipeIngredientResponse:
    recipe = await _owned_recipe(session, recipe_id, current_user, lock=True)
    rows = await _recipe_ingredients(session, recipe_id)
    row = next((item for item in rows if item.id == ingredient_row_id), None)
    if row is None:
        raise _ingredient_not_found()

    ingredient = await _get_or_create_ingredient(session, data.ingredient_name)
    if ingredient.id != row.ingredient_id:
        clash = await session.scalar(
            select(RecipeIngredient.id).where(
                RecipeIngredient.recipe_id == recipe_id,
                RecipeIngredient.ingredient_id == ingredient.id,
            )
        )
        if clash is not None:
            raise _ingredient_exists()
        row.ingredient_id = ingredient.id

    row.quantity = data.quantity
    row.unit = data.unit
    if data.order_index is not None and data.order_index != row.order_index:
        if data.order_index >= len(rows):
            raise RecipeProblem(
                status=422,
                error_code="VALIDATION_ERROR",
                title="Validation Error",
                detail="Order index must be within the existing sequence.",
                errors={"orderIndex": [f"Must be between 0 and {len(rows) - 1}."]},
            )
        rows.remove(row)
        rows.insert(data.order_index, row)
        await _renumber_ingredients(rows)
    recipe.updated_at = datetime.now(UTC)
    try:
        await session.commit()
    except StaleDataError as error:
        await session.rollback()
        raise _version_conflict() from error
    await session.refresh(row, attribute_names=["ingredient"])
    return _to_ingredient_response(row)


async def delete_recipe_ingredient(
    session: AsyncSession,
    recipe_id: uuid.UUID,
    ingredient_row_id: uuid.UUID,
    current_user: User,
) -> None:
    recipe = await _owned_recipe(session, recipe_id, current_user, lock=True)
    rows = await _recipe_ingredients(session, recipe_id)
    row = next((item for item in rows if item.id == ingredient_row_id), None)
    if row is None:
        raise _ingredient_not_found()
    rows.remove(row)
    await session.delete(row)
    await session.flush()
    await _renumber_ingredients(rows)
    recipe.updated_at = datetime.now(UTC)
    try:
        await session.commit()
    except StaleDataError as error:
        await session.rollback()
        raise _version_conflict() from error


def _step_not_found() -> RecipeProblem:
    return RecipeProblem(
        status=404,
        error_code="RECIPE_STEP_NOT_FOUND",
        title="Not Found",
        detail="Recipe step was not found.",
    )


async def _recipe_steps(session: AsyncSession, recipe_id: uuid.UUID) -> list[RecipeStep]:
    return list(
        await session.scalars(
            select(RecipeStep)
            .where(RecipeStep.recipe_id == recipe_id)
            .order_by(RecipeStep.step_number)
        )
    )


async def _renumber_steps(
    session: AsyncSession,
    recipe_id: uuid.UUID,
    ordered_steps: list[RecipeStep],
) -> None:
    """Move numbers above the current range before assigning 1..N.

    The temporary range avoids violating the (recipe_id, step_number) unique
    constraint while PostgreSQL checks each update statement.
    """
    if not ordered_steps:
        return
    highest = max(step.step_number for step in ordered_steps)
    await session.execute(
        update(RecipeStep)
        .where(RecipeStep.recipe_id == recipe_id)
        .values(step_number=RecipeStep.step_number + highest + len(ordered_steps))
        .execution_options(synchronize_session="fetch")
    )
    await session.flush()
    for number, step in enumerate(ordered_steps, 1):
        step.step_number = number
    await session.flush()


async def create_recipe_step(
    session: AsyncSession,
    recipe_id: uuid.UUID,
    data: RecipeStepCreateRequest,
    current_user: User,
) -> RecipeStepResponse:
    recipe = await _owned_recipe(session, recipe_id, current_user, lock=True)
    next_number = (await session.scalar(
        select(func.max(RecipeStep.step_number)).where(RecipeStep.recipe_id == recipe_id)
    ) or 0) + 1
    step = RecipeStep(
        recipe_id=recipe_id,
        step_number=next_number,
        instruction=data.instruction,
        duration_minutes=data.duration_minutes,
        image_url=data.image_url,
    )
    session.add(step)
    recipe.updated_at = datetime.now(UTC)
    try:
        await session.commit()
    except StaleDataError as error:
        await session.rollback()
        raise _version_conflict() from error
    await session.refresh(step)
    await invalidate_recipe_caches()
    return RecipeStepResponse.model_validate(step)


async def update_recipe_step(
    session: AsyncSession,
    recipe_id: uuid.UUID,
    step_id: uuid.UUID,
    data: RecipeStepUpdateRequest,
    current_user: User,
) -> RecipeStepResponse:
    recipe = await _owned_recipe(session, recipe_id, current_user, lock=True)
    steps = await _recipe_steps(session, recipe_id)
    step = next((item for item in steps if item.id == step_id), None)
    if step is None:
        raise _step_not_found()
    if data.step_number is not None and data.step_number > len(steps):
        raise RecipeProblem(
            status=422,
            error_code="VALIDATION_ERROR",
            title="Validation Error",
            detail="Step number must be within the existing sequence.",
            errors={"stepNumber": [f"Must be between 1 and {len(steps)}."]},
        )
    step.instruction = data.instruction
    step.duration_minutes = data.duration_minutes
    step.image_url = data.image_url
    if data.step_number is not None and data.step_number != step.step_number:
        steps.remove(step)
        steps.insert(data.step_number - 1, step)
        await _renumber_steps(session, recipe_id, steps)
    recipe.updated_at = datetime.now(UTC)
    try:
        await session.commit()
    except StaleDataError as error:
        await session.rollback()
        raise _version_conflict() from error
    await session.refresh(step)
    await invalidate_recipe_caches()
    return RecipeStepResponse.model_validate(step)


async def delete_recipe_step(
    session: AsyncSession,
    recipe_id: uuid.UUID,
    step_id: uuid.UUID,
    current_user: User,
) -> None:
    recipe = await _owned_recipe(session, recipe_id, current_user, lock=True)
    steps = await _recipe_steps(session, recipe_id)
    step = next((item for item in steps if item.id == step_id), None)
    if step is None:
        raise _step_not_found()
    steps.remove(step)
    await session.delete(step)
    await session.flush()
    await _renumber_steps(session, recipe_id, steps)
    recipe.updated_at = datetime.now(UTC)
    try:
        await session.commit()
    except StaleDataError as error:
        await session.rollback()
        raise _version_conflict() from error
    await invalidate_recipe_caches()


def _recipe_visibility_filter(current_user: User | None):
    """Return the SRS visibility rule for the caller's role."""
    if current_user is None or current_user.role not in {"Author", "Admin"}:
        return Recipe.status == RecipeStatus.PUBLISHED
    if current_user.role == "Admin":
        return None
    return or_(
        Recipe.status == RecipeStatus.PUBLISHED,
        (Recipe.author_id == current_user.id)
        & Recipe.status.in_((RecipeStatus.DRAFT, RecipeStatus.ARCHIVED)),
    )


def _list_filters(query: RecipeListQuery, current_user: User | None):
    filters = [Recipe.is_deleted.is_(False)]
    visibility = _recipe_visibility_filter(current_user)
    if visibility is not None:
        filters.append(visibility)
    if query.category_id is not None:
        filters.append(Recipe.category_id == query.category_id)
    if query.difficulty is not None:
        filters.append(Recipe.difficulty == query.difficulty.value_for_database.value)
    if query.max_cook_time is not None:
        filters.append(Recipe.cook_time_minutes <= query.max_cook_time)
    if query.min_servings is not None:
        filters.append(Recipe.servings >= query.min_servings)
    return filters


def _sort_columns(sort: str):
    sort_map = {
        "-createdAt": (Recipe.created_at.desc(), Recipe.id.desc()),
        "createdAt": (Recipe.created_at.asc(), Recipe.id.asc()),
        "title": (Recipe.title.asc(), Recipe.id.asc()),
        "-title": (Recipe.title.desc(), Recipe.id.desc()),
        "cookTime": (Recipe.cook_time_minutes.asc(), Recipe.id.asc()),
        "-cookTime": (Recipe.cook_time_minutes.desc(), Recipe.id.desc()),
    }
    return sort_map[sort]


def _to_summary(recipe: Recipe) -> RecipeSummaryResponse:
    # ``category`` is loaded with the list query below, so this mapping does not issue
    # one additional query per recipe.
    return RecipeSummaryResponse.model_validate(
        {
            "id": recipe.id,
            "title": recipe.title,
            "slug": recipe.slug,
            "description": recipe.description,
            "category": recipe.category,
            "prep_time_minutes": recipe.prep_time_minutes,
            "cook_time_minutes": recipe.cook_time_minutes,
            "servings": recipe.servings,
            "difficulty": recipe.difficulty,
            "status": _STATUS_LABELS[RecipeStatus(recipe.status)],
            "created_at": recipe.created_at,
        }
    )


async def list_recipes(
    session: AsyncSession,
    query: RecipeListQuery,
    current_user: User | None,
) -> PagedRecipeResponse:
    """Get a role-aware, filtered, sorted, offset-paginated recipe collection."""
    filters = _list_filters(query, current_user)

    total_count = await session.scalar(select(func.count(Recipe.id)).where(*filters))
    total_count = total_count or 0
    total_pages = (total_count + query.page_size - 1) // query.page_size
    recipes = list(
        await session.scalars(
            select(Recipe)
            .options(joinedload(Recipe.category))
            .where(*filters)
            .order_by(*_sort_columns(query.sort))
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
    )
    return PagedRecipeResponse(
        items=[_to_summary(recipe) for recipe in recipes],
        total_count=total_count,
        page=query.page,
        page_size=query.page_size,
        total_pages=total_pages,
        has_next_page=query.page < total_pages,
        has_previous_page=query.page > 1,
    )
