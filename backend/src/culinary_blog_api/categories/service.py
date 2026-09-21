import re
import unicodedata
import uuid

import structlog
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .model import Category
from .problem import CategoryProblem
from .schemas import CategoryCreate, CategoryRead, CategoryUpdate

logger = structlog.get_logger()


def slugify(name: str) -> str:
    """Turn a Vietnamese category name into a stable URL segment."""
    # Unicode decomposition does not convert Vietnamese đ on its own.
    normalized = unicodedata.normalize("NFKD", name.replace("đ", "d").replace("Đ", "D"))
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    if not slug:
        raise CategoryProblem(
            422, "INVALID_CATEGORY", "Validation Error", "Name cannot form a slug."
        )
    return slug


async def _name_exists(
    session: AsyncSession, name: str, *, excluding: uuid.UUID | None = None
) -> bool:
    """Compare names without case, excluding the category being edited."""
    query = select(Category.id).where(func.lower(Category.name) == name.lower())
    if excluding is not None:
        query = query.where(Category.id != excluding)
    return await session.scalar(query) is not None


async def _slug_exists(
    session: AsyncSession, slug: str, *, excluding: uuid.UUID | None = None
) -> bool:
    """Check public URL uniqueness, excluding the category being edited."""
    query = select(Category.id).where(Category.slug == slug)
    if excluding is not None:
        query = query.where(Category.id != excluding)
    return await session.scalar(query) is not None


def _duplicate_name() -> CategoryProblem:
    return CategoryProblem(409, "CATEGORY_NAME_EXISTS", "Conflict", "Category name already exists.")


def _duplicate_slug() -> CategoryProblem:
    return CategoryProblem(409, "CATEGORY_SLUG_EXISTS", "Conflict", "Category slug already exists.")


async def create_category(session: AsyncSession, data: CategoryCreate) -> CategoryRead:
    """Create one category, retrying slug collisions under concurrent requests."""
    if await _name_exists(session, data.name):
        raise _duplicate_name()

    base_slug = slugify(data.name)
    for suffix in range(1, 1001):
        slug = base_slug if suffix == 1 else f"{base_slug}-{suffix}"
        if await session.scalar(select(Category.id).where(Category.slug == slug)) is not None:
            continue
        category = Category(name=data.name, slug=slug, description=data.description)
        session.add(category)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            if await _name_exists(session, data.name):
                raise _duplicate_name() from None
            # A different name can normalize to the same slug. Try the next suffix.
            continue
        logger.info("category_created", category_id=str(category.id), slug=category.slug)
        return CategoryRead.model_validate(category)

    raise CategoryProblem(409, "CATEGORY_SLUG_EXISTS", "Conflict", "No unique slug is available.")


async def update_category(
    session: AsyncSession, category_id: uuid.UUID, data: CategoryUpdate
) -> CategoryRead:
    """Update content and change the public slug only when explicitly supplied."""
    category = await session.get(Category, category_id)
    if category is None:
        raise CategoryProblem(404, "CATEGORY_NOT_FOUND", "Not Found", "Category was not found.")
    if await _name_exists(session, data.name, excluding=category_id):
        raise _duplicate_name()
    if data.slug is not None and await _slug_exists(session, data.slug, excluding=category_id):
        raise _duplicate_slug()

    category.name = data.name
    category.description = data.description
    if data.slug is not None:
        category.slug = data.slug
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        if data.slug is not None and await _slug_exists(session, data.slug, excluding=category_id):
            raise _duplicate_slug() from error
        raise _duplicate_name() from error
    logger.info("category_updated", category_id=str(category.id), slug=category.slug)
    return CategoryRead.model_validate(category)


async def list_categories(session: AsyncSession) -> list[CategoryRead]:
    result = await session.scalars(select(Category).order_by(Category.order_index, Category.name))
    return [CategoryRead.model_validate(category) for category in result.all()]
