import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import require_admin
from ..auth.model import User
from ..db import get_session
from .schemas import CategoryCreate, CategoryRead, CategoryUpdate
from .service import create_category, list_categories, update_category

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
async def get_categories(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[CategoryRead]:
    """Return every category, or an empty list when no data exists."""
    return await list_categories(session)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def post_category(
    data: CategoryCreate,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[User, Depends(require_admin)],
) -> CategoryRead:
    """Create a category as Admin and provide its stable public URL."""
    category = await create_category(session, data)
    response.headers["Location"] = f"/api/v1/categories/{category.slug}"
    return category


@router.put("/{category_id}", response_model=CategoryRead)
async def put_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[User, Depends(require_admin)],
) -> CategoryRead:
    """Edit category content; an omitted slug preserves the public URL."""
    return await update_category(session, category_id, data)
