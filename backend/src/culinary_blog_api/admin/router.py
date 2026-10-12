"""Aggregate real operational and content data for the Admin overview."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import require_admin
from ..auth.model import User
from ..categories.model import Category
from ..db import get_session
from ..jobs.model import WelcomeEmailJob
from ..recipes.model import Recipe, RecipeImage, RecipeImageResizeJob, RecipeStatus
from ..storage.model import FileDeletionJob

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/overview")
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
