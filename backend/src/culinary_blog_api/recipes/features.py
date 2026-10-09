"""Search, archive, and image operations owned by the recipe API."""

import re
import unicodedata
import uuid
from datetime import UTC, datetime

import structlog
from fastapi import UploadFile
from sqlalchemy import delete, func, literal, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import StaleDataError

from ..auth.model import User
from ..storage import FileStorage, InvalidImage, StorageUnavailable
from ..storage.cleanup import queue_image_cleanup
from ..storage.model import FileDeletionJob
from .cache import invalidate_recipe_caches
from .model import Recipe, RecipeImage, RecipeImageResizeJob, RecipeStatus
from .problem import RecipeProblem
from .schemas import (
    PagedRecipeSearchResponse,
    RecipeCreateResponse,
    RecipeImageResponse,
    RecipeSearchQuery,
    RecipeSearchSummaryResponse,
)
from .service import (
    _list_filters,
    _owned_recipe,
    _sort_columns,
    _to_response,
    _to_summary,
    _version_conflict,
)

logger = structlog.get_logger()


def _image_problem(error: Exception) -> RecipeProblem:
    if isinstance(error, InvalidImage):
        return RecipeProblem(
            status=400, error_code="INVALID_RECIPE_IMAGE", title="Bad Request", detail=str(error)
        )
    return RecipeProblem(
        status=503,
        error_code="IMAGE_STORAGE_UNAVAILABLE",
        title="Service Unavailable",
        detail="Image storage is unavailable. Try again later.",
    )


async def search_recipes(
    session: AsyncSession, query: RecipeSearchQuery
) -> PagedRecipeSearchResponse:
    """Use PostgreSQL GIN full-text search; SQLite provides a test-only fallback."""
    filters = _list_filters(query, None)  # Search is public even with an Authorization header.
    terms = re.findall(
        r"[a-z0-9]+",
        unicodedata.normalize("NFKD", query.q.replace("đ", "d").replace("Đ", "D"))
        .encode("ascii", "ignore")
        .decode()
        .lower(),
    )
    if not terms:
        return PagedRecipeSearchResponse(
            items=[],
            total_count=0,
            page=query.page,
            page_size=query.page_size,
            total_pages=0,
            has_next_page=False,
            has_previous_page=query.page > 1,
        )

    if session.bind.dialect.name == "postgresql":
        tsquery = func.to_tsquery("simple", " & ".join(f"{term}:*" for term in terms))
        filters.append(Recipe.search_vector.op("@@")(tsquery))
        relevance = func.ts_rank(Recipe.search_vector, tsquery)
        relevance_order = (relevance.desc(), Recipe.created_at.desc(), Recipe.id.desc())
    else:
        # The application's production database is PostgreSQL. SQLite is used by unit tests.
        for word in query.q.lower().split():
            filters.append(func.lower(Recipe.title + " " + Recipe.description).contains(word))
        relevance = literal(0.0)
        relevance_order = (Recipe.created_at.desc(), Recipe.id.desc())

    total_count = await session.scalar(select(func.count(Recipe.id)).where(*filters)) or 0
    total_pages = (total_count + query.page_size - 1) // query.page_size
    order = relevance_order if query.sort == "relevance" else _sort_columns(query.sort)
    recipes_with_scores = list(
        await session.execute(
            select(Recipe, relevance)
            .options(joinedload(Recipe.category))
            .where(*filters)
            .order_by(*order)
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
    )
    return PagedRecipeSearchResponse(
        items=[
            RecipeSearchSummaryResponse.model_validate(
                {**_to_summary(recipe).model_dump(), "relevance_score": float(score)}
            )
            for recipe, score in recipes_with_scores
        ],
        total_count=total_count,
        page=query.page,
        page_size=query.page_size,
        total_pages=total_pages,
        has_next_page=query.page < total_pages,
        has_previous_page=query.page > 1,
    )


async def archive_recipe(
    session: AsyncSession, recipe_id: uuid.UUID, current_user: User
) -> RecipeCreateResponse:
    recipe = await _owned_recipe(session, recipe_id, current_user, lock=True)
    if recipe.status != RecipeStatus.ARCHIVED:
        recipe.status = RecipeStatus.ARCHIVED
        recipe.updated_at = datetime.now(UTC)
        try:
            await session.commit()
        except StaleDataError as error:
            await session.rollback()
            raise RecipeProblem(
                status=409,
                error_code="RECIPE_VERSION_CONFLICT",
                title="Conflict",
                detail="Recipe changed since it was loaded. Reload it and try again.",
            ) from error
        await session.refresh(recipe)
        await invalidate_recipe_caches()
    return _to_response(recipe)


def _image_response(image: RecipeImage) -> RecipeImageResponse:
    return RecipeImageResponse.model_validate(image)


async def upload_recipe_image(
    session: AsyncSession,
    recipe_id: uuid.UUID,
    current_user: User,
    file: UploadFile,
    storage: FileStorage,
) -> RecipeImageResponse:
    recipe = await _owned_recipe(session, recipe_id, current_user, lock=True)
    try:
        url = await storage.upload_file(file, f"recipes/{recipe_id}")
    except (InvalidImage, StorageUnavailable) as error:
        raise _image_problem(error) from error
    count = (
        await session.scalar(
            select(func.count(RecipeImage.id)).where(RecipeImage.recipe_id == recipe_id)
        )
        or 0
    )
    image = RecipeImage(
        id=uuid.uuid4(),
        recipe_id=recipe_id,
        original_url=url,
        order_index=count,
        is_primary=count == 0,
    )
    session.add(image)
    session.add(RecipeImageResizeJob(image_id=image.id))
    recipe.updated_at = datetime.now(UTC)
    try:
        await session.commit()
    except (IntegrityError, StaleDataError) as error:
        await session.rollback()
        try:
            await storage.delete(url)
        except (InvalidImage, StorageUnavailable):
            # A conflict rolled back the image row; persist a cleanup request
            # if MinIO is also unavailable so this upload cannot remain orphaned.
            try:
                session.add(FileDeletionJob(
                    original_url=url, recipe_id=recipe_id, image_id=image.id
                ))
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception(
                    "recipe_image_upload_cleanup_queue_failed", recipe_id=str(recipe_id)
                )
        raise _version_conflict() from error
    await session.refresh(image)
    await invalidate_recipe_caches()
    return _image_response(image)


async def set_primary_recipe_image(
    session: AsyncSession,
    recipe_id: uuid.UUID,
    image_id: uuid.UUID,
    current_user: User,
) -> RecipeImageResponse:
    recipe = await _owned_recipe(session, recipe_id, current_user, lock=True)
    images = list(
        await session.scalars(
            select(RecipeImage)
            .where(RecipeImage.recipe_id == recipe_id)
            .order_by(RecipeImage.order_index, RecipeImage.id)
        )
    )
    target = next((image for image in images if image.id == image_id), None)
    if target is None:
        raise RecipeProblem(
            status=404,
            error_code="RECIPE_IMAGE_NOT_FOUND",
            title="Not Found",
            detail="Recipe image was not found.",
        )
    if not target.is_primary:
        for image in images:
            if image.is_primary:
                image.is_primary = False
        await session.flush()
        target.is_primary = True
        recipe.updated_at = datetime.now(UTC)
        try:
            await session.commit()
        except (IntegrityError, StaleDataError) as error:
            await session.rollback()
            raise _version_conflict() from error
        await session.refresh(target)
        await invalidate_recipe_caches()
    return _image_response(target)


async def delete_recipe_image(
    session: AsyncSession,
    recipe_id: uuid.UUID,
    image_id: uuid.UUID,
    current_user: User,
) -> None:
    recipe = await _owned_recipe(session, recipe_id, current_user, lock=True)
    images = list(
        await session.scalars(
            select(RecipeImage)
            .where(RecipeImage.recipe_id == recipe_id)
            .order_by(RecipeImage.order_index, RecipeImage.id)
        )
    )
    target = next((image for image in images if image.id == image_id), None)
    if target is None:
        raise RecipeProblem(
            status=404,
            error_code="RECIPE_IMAGE_NOT_FOUND",
            title="Not Found",
            detail="Recipe image was not found.",
        )
    # Commit metadata removal and durable object cleanup requests together.
    queue_image_cleanup(session, target)
    await session.execute(
        delete(RecipeImageResizeJob).where(RecipeImageResizeJob.image_id == image_id)
    )
    await session.delete(target)
    await session.flush()
    for index, image in enumerate(item for item in images if item.id != image_id):
        image.order_index = index
    if target.is_primary:
        next_image = next((image for image in images if image.id != image_id), None)
        if next_image is not None:
            next_image.is_primary = True
    recipe.updated_at = datetime.now(UTC)
    try:
        await session.commit()
    except (IntegrityError, StaleDataError) as error:
        await session.rollback()
        raise _version_conflict() from error
    await invalidate_recipe_caches()
