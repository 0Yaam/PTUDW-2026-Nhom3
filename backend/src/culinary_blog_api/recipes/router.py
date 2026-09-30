import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
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
    RecipeDetailResponse,
    RecipeDifficultyFilter,
    RecipeIngredientCreateRequest,
    RecipeIngredientResponse,
    RecipeIngredientUpdateRequest,
    RecipeListQuery,
    RecipeListSort,
    RecipeStepCreateRequest,
    RecipeStepResponse,
    RecipeStepUpdateRequest,
    RecipeUpdateRequest,
)
from .service import (
    create_recipe,
    create_recipe_ingredient,
    create_recipe_step,
    delete_recipe,
    delete_recipe_ingredient,
    delete_recipe_step,
    get_recipe_detail,
    list_recipes,
    set_publication_status,
    update_recipe,
    update_recipe_ingredient,
    update_recipe_step,
)

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
    response.headers["ETag"] = f'"{created.row_version}"'
    return created


@router.get(
    "/{slug}",
    response_model=RecipeDetailResponse,
    response_model_by_alias=True,
    responses={
        401: {"model": ProblemDetails, "description": "Invalid access token"},
        403: {"model": ProblemDetails, "description": "Not the owner or Admin"},
        404: {"model": ProblemDetails, "description": "Recipe not found"},
    },
)
async def get_recipe_by_slug(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User | None, Depends(get_optional_recipe_viewer)],
) -> RecipeDetailResponse:
    """Return the complete recipe contract, limiting drafts to the owner or Admin."""
    return await get_recipe_detail(session, slug, current_user)


@router.put(
    "/{recipe_id}",
    response_model=RecipeCreateResponse,
    responses={
        403: {"model": ProblemDetails, "description": "Not the owner or Admin"},
        404: {"model": ProblemDetails, "description": "Recipe not found"},
        409: {"model": ProblemDetails, "description": "Version conflict"},
        422: {"model": ProblemDetails, "description": "Invalid recipe data"},
        428: {"model": ProblemDetails, "description": "Missing row version"},
    },
)
async def put_recipe(
    recipe_id: uuid.UUID,
    data: RecipeUpdateRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> RecipeCreateResponse:
    updated = await update_recipe(session, recipe_id, data, current_user, if_match)
    response.headers["ETag"] = f'"{updated.row_version}"'
    return updated


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_recipe(
    recipe_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
) -> Response:
    await delete_recipe(session, recipe_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{recipe_id}/steps",
    response_model=RecipeStepResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_recipe_step(
    recipe_id: uuid.UUID,
    data: RecipeStepCreateRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
) -> RecipeStepResponse:
    step = await create_recipe_step(session, recipe_id, data, current_user)
    response.headers["Location"] = f"/api/v1/recipes/{recipe_id}/steps/{step.id}"
    return step


@router.put("/{recipe_id}/steps/{step_id}", response_model=RecipeStepResponse)
async def put_recipe_step(
    recipe_id: uuid.UUID,
    step_id: uuid.UUID,
    data: RecipeStepUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
) -> RecipeStepResponse:
    return await update_recipe_step(session, recipe_id, step_id, data, current_user)


@router.delete("/{recipe_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_recipe_step(
    recipe_id: uuid.UUID,
    step_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
) -> Response:
    await delete_recipe_step(session, recipe_id, step_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{recipe_id}/ingredients",
    response_model=RecipeIngredientResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_recipe_ingredient(
    recipe_id: uuid.UUID,
    data: RecipeIngredientCreateRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
) -> RecipeIngredientResponse:
    ingredient = await create_recipe_ingredient(session, recipe_id, data, current_user)
    response.headers["Location"] = (
        f"/api/v1/recipes/{recipe_id}/ingredients/{ingredient.id}"
    )
    return ingredient


@router.put(
    "/{recipe_id}/ingredients/{ingredient_id}",
    response_model=RecipeIngredientResponse,
)
async def put_recipe_ingredient(
    recipe_id: uuid.UUID,
    ingredient_id: uuid.UUID,
    data: RecipeIngredientUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
) -> RecipeIngredientResponse:
    return await update_recipe_ingredient(
        session, recipe_id, ingredient_id, data, current_user
    )


@router.delete(
    "/{recipe_id}/ingredients/{ingredient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_recipe_ingredient(
    recipe_id: uuid.UUID,
    ingredient_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
) -> Response:
    await delete_recipe_ingredient(session, recipe_id, ingredient_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{recipe_id}/publish", response_model=RecipeCreateResponse)
async def publish_recipe(
    recipe_id: uuid.UUID,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
) -> RecipeCreateResponse:
    updated = await set_publication_status(session, recipe_id, current_user, publish=True)
    response.headers["ETag"] = f'"{updated.row_version}"'
    return updated


@router.patch("/{recipe_id}/unpublish", response_model=RecipeCreateResponse)
async def unpublish_recipe(
    recipe_id: uuid.UUID,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
) -> RecipeCreateResponse:
    updated = await set_publication_status(session, recipe_id, current_user, publish=False)
    response.headers["ETag"] = f'"{updated.row_version}"'
    return updated
