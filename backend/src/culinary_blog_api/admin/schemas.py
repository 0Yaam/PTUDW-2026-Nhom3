"""Documented response contract for the versioned Admin overview API."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class RecipeCounts(BaseModel):
    total: int
    draft: int
    published: int
    archived: int


class JobCounts(BaseModel):
    pending: int
    failed: int


class OverviewJobs(BaseModel):
    email: JobCounts
    resize: JobCounts
    cleanup: JobCounts


class RecentRecipe(BaseModel):
    id: UUID
    title: str
    status: Literal["Draft", "Published", "Archived"]
    createdAt: datetime
    author: str


class AdminOverview(BaseModel):
    users: int
    categories: int
    images: int
    recipes: RecipeCounts
    jobs: OverviewJobs
    recentRecipes: list[RecentRecipe]
