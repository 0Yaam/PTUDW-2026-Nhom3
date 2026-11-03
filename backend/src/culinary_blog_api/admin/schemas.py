"""Documented response contract for the versioned Admin overview API."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdminUserItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    full_name: str = Field(alias="fullName")
    email: str
    user_name: str = Field(alias="userName")
    role: str
    avatar_url: str | None = Field(default=None, alias="avatarUrl")
    created_at: datetime = Field(alias="createdAt")


class PagedAdminUsersResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[AdminUserItem]
    total_count: int = Field(alias="totalCount")
    page: int
    page_size: int = Field(alias="pageSize")
    total_pages: int = Field(alias="totalPages")
    has_next_page: bool = Field(alias="hasNextPage")
    has_previous_page: bool = Field(alias="hasPreviousPage")
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
