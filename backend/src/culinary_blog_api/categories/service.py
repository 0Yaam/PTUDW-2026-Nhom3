from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..problem import ApiProblem
from .model import Category
from .schemas import CategoryDetail, CategoryRead


async def list_categories(session: AsyncSession) -> list[CategoryRead]:
    result = await session.scalars(select(Category).order_by(Category.order_index, Category.name))
    return [CategoryRead.model_validate(category) for category in result.all()]


async def get_category_by_slug(session: AsyncSession, slug: str) -> CategoryDetail:
    category = await session.scalar(select(Category).where(Category.slug == slug))
    if category is None:
        raise ApiProblem(
            404,
            "CATEGORY_NOT_FOUND",
            "Not Found",
            "No category exists for this slug.",
        )
    # ponytail: recipes stay empty until Issue #4 lands the Recipe model; fill the list here.
    return CategoryDetail.model_validate(category)
