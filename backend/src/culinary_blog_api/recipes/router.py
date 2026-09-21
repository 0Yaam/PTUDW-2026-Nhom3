from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.model import User
from ..db import get_session
from .dependencies import require_author_or_admin
from .problem import ProblemDetails
from .schemas import RecipeCreateRequest, RecipeCreateResponse
from .service import create_recipe

router = APIRouter(prefix="/api/v1/recipes", tags=["recipes"])


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
