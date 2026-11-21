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
from .schemas import AdminOverview, AdminUserItem, PagedAdminUsersResponse

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


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


@router.get(
    "/users",
    response_model=PagedAdminUsersResponse,
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
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=50)] = 10,
    q: Annotated[str | None, Query(max_length=100)] = None,
    role: Annotated[str | None, Query()] = None,
) -> PagedAdminUsersResponse:
    """List users with pagination, search, and role filter for Admin only."""
    filters = []
    if q and q.strip():
        term = f"%{q.strip()}%"
        filters.append(
            or_(
                User.full_name.ilike(term),
                User.email.ilike(term),
                User.user_name.ilike(term),
            )
        )
    if role and role.strip():
        filters.append(User.role == role.strip())

    total_count = await session.scalar(select(func.count(User.id)).where(*filters)) or 0
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    stmt = (
        select(User)
        .where(*filters)
        .order_by(User.created_at.desc(), User.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    users = (await session.scalars(stmt)).all()

    return PagedAdminUsersResponse(
        items=[
            AdminUserItem(
                id=u.id,
                full_name=u.full_name,
                email=u.email,
                user_name=u.user_name,
                role=u.role,
                avatar_url=u.avatar_url,
                created_at=u.created_at,
            )
            for u in users
        ],
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next_page=page < total_pages,
        has_previous_page=page > 1,
    )
