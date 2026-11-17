import re
import unicodedata
import uuid

import structlog
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..recipes.model import Recipe, RecipeStatus
from .model import Category
from .problem import CategoryProblem
from .schemas import (
    CategoryCreate,
    CategoryDetail,
    CategoryRead,
    CategoryUpdate,
    RecipeCard,
)

logger = structlog.get_logger()


def slugify(name: str) -> str:
    """Turn a Vietnamese category name into a stable URL segment."""
    # Chuẩn hóa Unicode không tự chuyển ký tự tiếng Việt đ.
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
    """Tạo lỗi dùng chung cho trường hợp tên danh mục bị trùng."""
    return CategoryProblem(409, "CATEGORY_NAME_EXISTS", "Conflict", "Category name already exists.")


def _duplicate_slug() -> CategoryProblem:
    """Tạo lỗi dùng chung cho trường hợp slug công khai bị trùng."""
    return CategoryProblem(409, "CATEGORY_SLUG_EXISTS", "Conflict", "Category slug already exists.")


def _category_in_use(recipe_count: int) -> CategoryProblem:
    """Tạo lỗi ngăn xóa danh mục khi vẫn còn công thức tham chiếu."""
    noun = "recipe" if recipe_count == 1 else "recipes"
    return CategoryProblem(
        409,
        "CATEGORY_IN_USE",
        "Conflict",
        f"Category contains {recipe_count} {noun}. Reassign them before deleting it.",
    )


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
            # Tên khác nhau có thể chuẩn hóa thành cùng slug, nên thử hậu tố tiếp theo.
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
    item = CategoryRead.model_validate(category)
    item.recipe_count = await session.scalar(
        select(func.count(Recipe.id)).where(Recipe.category_id == category_id)
    ) or 0
    return item


async def list_categories(session: AsyncSession) -> list[CategoryRead]:
    """Lấy danh sách danh mục kèm số công thức bằng một truy vấn group duy nhất."""
    result = await session.execute(
        select(Category, func.count(Recipe.id).label("recipe_count"))
        .outerjoin(Recipe, Recipe.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.order_index, Category.name)
    )
    categories: list[CategoryRead] = []
    for category, recipe_count in result.all():
        item = CategoryRead.model_validate(category)
        item.recipe_count = recipe_count
        categories.append(item)
    return categories


async def delete_category(session: AsyncSession, category_id: uuid.UUID) -> None:
    """Delete one category only when no recipe of any status references it."""
    category = await session.get(Category, category_id)
    if category is None:
        raise CategoryProblem(404, "CATEGORY_NOT_FOUND", "Not Found", "Category was not found.")

    recipe_count = await session.scalar(
        select(func.count(Recipe.id)).where(Recipe.category_id == category_id)
    )
    if recipe_count:
        raise _category_in_use(recipe_count)

    await session.delete(category)
    try:
        await session.commit()
    except IntegrityError:
        # Một công thức có thể được gán sau lúc đếm. Giữ danh mục và chuyển
        # ràng buộc database thành lỗi đúng theo hợp đồng API.
        await session.rollback()
        current_count = await session.scalar(
            select(func.count(Recipe.id)).where(Recipe.category_id == category_id)
        )
        raise _category_in_use(current_count or 1) from None
    logger.info("category_deleted", category_id=str(category_id), slug=category.slug)


async def get_category_by_slug(session: AsyncSession, slug: str) -> CategoryDetail:
    """Read one category by its stable public slug, with its published recipes."""
    category = await session.scalar(select(Category).where(Category.slug == slug))
    if category is None:
        raise CategoryProblem(
            404, "CATEGORY_NOT_FOUND", "Not Found", "Category was not found."
        )

    # Người đọc chỉ thấy công thức đã đăng; bản nháp chỉ thuộc về tác giả.
    recipes = await session.scalars(
        select(Recipe)
        .where(
            Recipe.category_id == category.id,
            Recipe.status == RecipeStatus.PUBLISHED,
            Recipe.is_deleted.is_(False),
        )
        .order_by(Recipe.published_at.desc(), Recipe.title)
    )
    cards = [RecipeCard.model_validate(recipe) for recipe in recipes.all()]
    detail = CategoryDetail.model_validate(category)
    detail.recipes = cards
    detail.recipe_count = len(cards)
    return detail
