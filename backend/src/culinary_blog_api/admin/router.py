"""Aggregate real operational and content data for the Admin overview."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import require_admin
from ..auth.model import User
from ..categories.model import Category
from ..db import get_session
from ..jobs.model import WelcomeEmailJob
from ..recipes.model import Recipe, RecipeImage, RecipeImageResizeJob, RecipeStatus
from ..recipes.problem import ProblemDetails
from ..storage.model import FileDeletionJob
from .schemas import AdminOverview, AdminUserPage

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get(
    "/users",
    response_model=AdminUserPage,
    response_model_by_alias=True,
    responses={
        401: {"model": ProblemDetails, "description": "Bearer token is missing or invalid"},
        403: {"model": ProblemDetails, "description": "Admin role is required"},
    },
)
async def list_admin_users(
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[User, Depends(require_admin)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 20,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    role: Annotated[str | None, Query(pattern="^(Admin|Author)$")] = None,
) -> AdminUserPage:
    """Return a paged, secret-free directory of Admin and Author accounts."""
    filters = [User.role.in_(("Admin", "Author"))]
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        filters.append(
            or_(
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                User.user_name.ilike(pattern),
            )
        )
    if role:
        filters.append(User.role == role)
    total = await session.scalar(select(func.count(User.id)).where(*filters)) or 0
    rows = await session.scalars(
        select(User)
        .where(*filters)
        .order_by(User.created_at.desc(), User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    total_pages = max(1, (total + page_size - 1) // page_size)
    return AdminUserPage(
        items=list(rows), totalCount=total, page=page, pageSize=page_size,
        totalPages=total_pages, hasNextPage=page < total_pages, hasPreviousPage=page > 1,
    )


@router.get(
    "/overview",
    response_model=AdminOverview,
    responses={
        401: {"model": ProblemDetails, "description": "Bearer token is missing or invalid"},
        403: {"model": ProblemDetails, "description": "Admin role is required"},
    },
)
async def get_overview(
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[User, Depends(require_admin)],
) -> dict:
    """Return a bounded snapshot; all aggregates run in SQL, without per-row queries."""
    user_count = await session.scalar(select(func.count(User.id))) or 0
    category_count = await session.scalar(select(func.count(Category.id))) or 0
    image_count = await session.scalar(select(func.count(RecipeImage.id))) or 0
    recipe_rows = await session.execute(
        select(Recipe.status, func.count(Recipe.id))
        .where(Recipe.is_deleted.is_(False))
        .group_by(Recipe.status)
    )
    recipe_counts = dict(recipe_rows.all())
    job_counts = {}
    for label, model in (
        ("email", WelcomeEmailJob),
        ("resize", RecipeImageResizeJob),
        ("cleanup", FileDeletionJob),
    ):
        rows = await session.execute(
            select(model.status, func.count(model.id)).group_by(model.status)
        )
        counts = dict(rows.all())
        job_counts[label] = {
            "pending": counts.get("Pending", 0) + counts.get("Processing", 0),
            "failed": counts.get("Failed", 0),
        }
    recent = await session.execute(
        select(Recipe.id, Recipe.title, Recipe.status, Recipe.created_at, User.full_name)
        .join(User, Recipe.author_id == User.id)
        .where(Recipe.is_deleted.is_(False))
        .order_by(Recipe.created_at.desc(), Recipe.id.desc())
        .limit(5)
    )
    return {
        "users": user_count,
        "categories": category_count,
        "images": image_count,
        "recipes": {
            "total": sum(recipe_counts.values()),
            "draft": recipe_counts.get(RecipeStatus.DRAFT, 0),
            "published": recipe_counts.get(RecipeStatus.PUBLISHED, 0),
            "archived": recipe_counts.get(RecipeStatus.ARCHIVED, 0),
        },
        "jobs": job_counts,
        "recentRecipes": [
            {
                "id": str(recipe_id),
                "title": title,
                "status": RecipeStatus(status).name.title(),
                "createdAt": created_at.isoformat(),
                "author": author,
            }
            for recipe_id, title, status, created_at, author in recent
        ],
    }
