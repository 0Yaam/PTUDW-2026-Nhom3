import uuid

from pydantic import BaseModel, ConfigDict


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    image_url: str | None
    recipe_count: int = 0


class RecipeSummary(BaseModel):
    """Recipe card contract agreed with Issue #4. Fields stay optional until the model lands."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    image_url: str | None = None
    cook_time_minutes: int | None = None
    difficulty: str | None = None


class CategoryDetail(CategoryRead):
    recipes: list[RecipeSummary] = []
