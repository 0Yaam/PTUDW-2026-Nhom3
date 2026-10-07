import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Header, Query, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.model import User
from ..db import get_session
from ..storage import FileStorage, S3FileStorage, StorageNotConfigured
from .cache import get_cached, set_cached
from .dependencies import get_optional_recipe_viewer, require_author_or_admin
from .detail import get_recipe_detail
from .features import (
    archive_recipe,
    delete_recipe_image,
    search_recipes,
    set_primary_recipe_image,
    upload_recipe_image,
)
from .problem import ProblemDetails, RecipeProblem
from .schemas import (
    PagedRecipeResponse,
    PagedRecipeSearchResponse,
    RecipeCreateRequest,
    RecipeCreateResponse,
    RecipeDetailResponse,
    RecipeDifficultyFilter,
    RecipeImageResponse,
    RecipeImageUpdateRequest,
    RecipeIngredientCreateRequest,
    RecipeIngredientResponse,
    RecipeIngredientUpdateRequest,
    RecipeListQuery,
    RecipeListSort,
    RecipeSearchQuery,
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
    list_recipes,
    set_publication_status,
    update_recipe,
    update_recipe_ingredient,
    update_recipe_step,
)

router = APIRouter(prefix="/api/v1/recipes", tags=["recipes"])


def get_recipe_storage() -> FileStorage:
    try:
        return S3FileStorage()
    except StorageNotConfigured as error:
        raise RecipeProblem(
            status=503,
            error_code="IMAGE_STORAGE_UNAVAILABLE",
            title="Service Unavailable",
            detail="Image storage is unavailable. Try again later.",
        ) from error


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
    response: Response,
    query: Annotated[RecipeListQuery, Depends(recipe_list_query)],
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User | None, Depends(get_optional_recipe_viewer)],
) -> PagedRecipeResponse:
    """List published recipes publicly, with private rows only for their owner/Admin."""
    cache_key = f"{request.url.path}?{request.url.query}"
    version = None
    if current_user is None:
        version, cached = await get_cached("list", cache_key, PagedRecipeResponse)
        if cached is not None:
            response.headers["X-Recipe-Cache"] = "HIT"
            return cached
    response.headers["X-Recipe-Cache"] = "MISS" if version is not None else "BYPASS"

    result = await list_recipes(session, query, current_user)
    if current_user is None:
        await set_cached("list", cache_key, result, version)
    return result


@router.get(
    "/search",
    response_model=PagedRecipeSearchResponse,
    responses={422: {"model": ProblemDetails, "description": "Invalid search parameters"}},
)
async def get_recipe_search(
    request: Request,
    response: Response,
    q: Annotated[str, Query(min_length=2, max_length=100)],
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User | None, Depends(get_optional_recipe_viewer)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 12,
    category_id: Annotated[uuid.UUID | None, Query(alias="categoryId")] = None,
    difficulty: RecipeDifficultyFilter | None = None,
    max_cook_time: Annotated[int | None, Query(alias="maxCookTime", ge=0)] = None,
    min_servings: Annotated[int | None, Query(alias="minServings", ge=1)] = None,
    sort: RecipeListSort | Literal["relevance"] = "relevance",
) -> PagedRecipeSearchResponse:
    if len(q.strip()) < 2:
        raise RecipeProblem(
            status=422,
            error_code="VALIDATION_ERROR",
            title="Validation Error",
            detail="Search query must have at least 2 characters.",
            errors={"q": ["Enter at least 2 characters."]},
        )
    query = RecipeSearchQuery.model_validate(
        {
            "q": q.strip(),
            "page": page,
            "page_size": page_size,
            "category_id": category_id,
            "difficulty": difficulty,
            "max_cook_time": max_cook_time,
            "min_servings": min_servings,
            "sort": sort,
        }
    )
    cache_key = f"{request.url.path}?{request.url.query}"
    version = None
    if current_user is None:
        version, cached = await get_cached("search", cache_key, PagedRecipeSearchResponse)
        if cached is not None:
            response.headers["X-Recipe-Cache"] = "HIT"
            return cached
    response.headers["X-Recipe-Cache"] = "MISS" if version is not None else "BYPASS"
    result = await search_recipes(session, query)
    if current_user is None:
        await set_cached("search", cache_key, result, version)
    return result


@router.get(
    "/{slug}", response_model=RecipeDetailResponse,
    responses={
        401: {"model": ProblemDetails, "description": "Invalid access token"},
        403: {"model": ProblemDetails, "description": "Private recipe"},
        404: {"model": ProblemDetails, "description": "Recipe not found"},
    },
)
async def get_recipe_by_slug(
    slug: str,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User | None, Depends(get_optional_recipe_viewer)],
) -> RecipeDetailResponse:
    version = None
    if current_user is None:
        version, cached = await get_cached("detail", slug, RecipeDetailResponse)
        if cached is not None:
            response.headers["X-Recipe-Cache"] = "HIT"
            return cached
    response.headers["X-Recipe-Cache"] = "MISS" if version is not None else "BYPASS"
    detail = await get_recipe_detail(session, slug, current_user)
    if current_user is None and detail.status == "Published":
        await set_cached("detail", slug, detail, version)
    return detail


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


@router.patch("/{recipe_id}/archive", response_model=RecipeCreateResponse)
async def patch_recipe_archive(
    recipe_id: uuid.UUID,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
) -> RecipeCreateResponse:
    updated = await archive_recipe(session, recipe_id, current_user)
    response.headers["ETag"] = f'"{updated.row_version}"'
    return updated


@router.post(
    "/{recipe_id}/images",
    response_model=RecipeImageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_recipe_image(
    recipe_id: uuid.UUID,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
    storage: Annotated[FileStorage, Depends(get_recipe_storage)],
    file: Annotated[UploadFile, File()],
) -> RecipeImageResponse:
    image = await upload_recipe_image(session, recipe_id, current_user, file, storage)
    response.headers["Location"] = f"/api/v1/recipes/{recipe_id}/images/{image.id}"
    return image


@router.patch("/{recipe_id}/images/{image_id}", response_model=RecipeImageResponse)
async def patch_recipe_image(
    recipe_id: uuid.UUID,
    image_id: uuid.UUID,
    data: RecipeImageUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
) -> RecipeImageResponse:
    return await set_primary_recipe_image(session, recipe_id, image_id, current_user)


@router.patch(
    "/{recipe_id}/images/{image_id}/primary",
    response_model=RecipeImageResponse,
    include_in_schema=False,
)
async def patch_recipe_image_primary_alias(
    recipe_id: uuid.UUID,
    image_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
) -> RecipeImageResponse:
    """Compatibility alias for the SRS path; issue #43 uses PATCH on the image resource."""
    return await set_primary_recipe_image(session, recipe_id, image_id, current_user)


@router.delete("/{recipe_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_recipe_image(
    recipe_id: uuid.UUID,
    image_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_author_or_admin)],
    storage: Annotated[FileStorage, Depends(get_recipe_storage)],
) -> Response:
    await delete_recipe_image(session, recipe_id, image_id, current_user, storage)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
