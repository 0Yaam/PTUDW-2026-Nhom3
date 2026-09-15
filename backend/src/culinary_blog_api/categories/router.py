from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from .schemas import CategoryDetail, CategoryRead
from .service import get_category_by_slug, list_categories

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
async def get_categories(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[CategoryRead]:
    """Return every category, or an empty list when no data exists."""
    return await list_categories(session)


@router.get("/{slug}", response_model=CategoryDetail)
async def get_category(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CategoryDetail:
    """Return one category by its stable slug, with its recipe cards."""
    return await get_category_by_slug(session, slug)
