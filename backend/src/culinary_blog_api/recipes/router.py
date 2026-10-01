import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.model import User
from ..db import get_session
from .cache import recipe_list_cache
from .dependencies import get_optional_recipe_viewer, require_author_or_admin
from .problem import ProblemDetails
from .schemas import (
    PagedRecipeResponse,
    RecipeCreateRequest,
    RecipeCreateResponse,
    RecipeDifficultyFilter,
    RecipeListQuery,
    RecipeListSort,
)
from .service import create_recipe, list_recipes, set_publication_status

router = APIRouter(prefix="/api/v1/recipes", tags=["recipes"])


async def recipe_list_query(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 12,
    category_id: Annotated[uuid.UUID | None, Query(alias="categoryId")] = None,
    difficulty: RecipeDifficultyFilter | None = None,
    max_cook_time: Annotated[int | None, Query(alias="maxCookTime", ge=0)] = None,
    min_servings: Annotated[int | None, Query(alias="minServings", ge=1)] = None,
    sort: RecipeListSort = "-createdAt",
) -> RecipeListQuery:
    return RecipeListQuery(
        page=page,
        page_size=page_size,
        category_id=category_id,
        difficulty=difficulty,
        max_cook_time=max_cook_time,
        min_servings=min_servings,
        sort=sort,
    )


@router.get(
    "",
    response_model=PagedRecipeResponse,
    response_model_by_alias=True,
    responses={
        401: {"model": ProblemDetails, "description": "Invalid access token"},
        422: {"model": ProblemDetails, "description": "Invalid query parameters"},
    },
)
async def get_recipes(
    request: Request,
    query: Annotated[RecipeListQuery, Depends(recipe_list_query)],
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User | None, Depends(get_optional_recipe_viewer)],
) -> PagedRecipeResponse:
    """List published recipes publicly, with private rows only for their owner/Admin."""
    cache_key = f"{request.url.path}?{request.url.query}"
    if current_user is None:
        cached = recipe_list_cache.get(cache_key)
        if cached is not None:
            return cached

    result = await list_recipes(session, query, current_user)
    if current_user is None:
        recipe_list_cache.set(cache_key, result)
    return result


@router.post(
    "",
    response_model=RecipeCreateResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {
            "model": ProblemDetails,
            "description": "Missing or invalid access token",
        },
        403: {
            "model": ProblemDetails,
            "description": "User is not an Author or Admin",
        },
        409: {
            "model": ProblemDetails,
            "description": "Generated slug already exists",
        },
        422: {
            "model": ProblemDetails,
            "description": "Request or category validation failed",
        },
    },
)
async def post_recipe(
    response: Response,
    request: RecipeCreateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
) -> RecipeCreateResponse:
    created = await create_recipe(session, request, current_user)
    response.headers["Location"] = f"/api/v1/recipes/{created.slug}"
    return created


@router.patch("/{recipe_id}/publish", response_model=RecipeCreateResponse)
async def publish_recipe(
    recipe_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
) -> RecipeCreateResponse:
    return await set_publication_status(session, recipe_id, current_user, publish=True)


@router.patch("/{recipe_id}/unpublish", response_model=RecipeCreateResponse)
async def unpublish_recipe(
    recipe_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
) -> RecipeCreateResponse:
    return await set_publication_status(session, recipe_id, current_user, publish=False)
