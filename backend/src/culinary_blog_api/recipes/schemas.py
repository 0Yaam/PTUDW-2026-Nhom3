import uuid
from datetime import datetime
from decimal import Decimal
from enum import IntEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecipeDifficulty(IntEnum):
    EASY = 1
    MEDIUM = 2
    HARD = 3
    EXPERT = 4


class NutritionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calories: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    protein: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    carbohydrates: Decimal | None = Field(
        default=None, ge=0, max_digits=8, decimal_places=2
    )
    fat: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    fiber: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    sodium: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)


class RecipeCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    category_id: uuid.UUID = Field(alias="categoryId")
    prep_time_minutes: int = Field(alias="prepTimeMinutes", gt=0)
    cook_time_minutes: int = Field(alias="cookTimeMinutes", ge=0)
    servings: int = Field(gt=0)
    difficulty: RecipeDifficulty
    instructions: str = ""
    nutrition: NutritionInput | None = None

    @field_validator("title", "description", "instructions", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class NutritionResponse(BaseModel):
    calories: float | None = None
    protein: float | None = None
    carbohydrates: float | None = None
    fat: float | None = None
    fiber: float | None = None
    sodium: float | None = None


class RecipeCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    title: str
    slug: str
    description: str
    instructions: str
    category_id: uuid.UUID = Field(alias="categoryId")
    author_id: uuid.UUID = Field(alias="authorId")
    prep_time_minutes: int = Field(alias="prepTimeMinutes")
    cook_time_minutes: int = Field(alias="cookTimeMinutes")
    servings: int
    difficulty: RecipeDifficulty
    status: Literal["Draft"]
    nutrition: NutritionResponse | None = None
    created_at: datetime = Field(alias="createdAt")
