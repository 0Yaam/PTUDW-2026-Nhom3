from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .model import Category
from .schemas import CategoryRead


async def list_categories(session: AsyncSession) -> list[CategoryRead]:
    result = await session.scalars(select(Category).order_by(Category.order_index, Category.name))
    return [CategoryRead.model_validate(category) for category in result.all()]
