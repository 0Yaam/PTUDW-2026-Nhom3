import uuid
from datetime import datetime
from decimal import Decimal
from enum import IntEnum, StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecipeDifficulty(IntEnum):
    EASY = 1
    MEDIUM = 2
    HARD = 3
    EXPERT = 4


class RecipeDifficultyFilter(StrEnum):
    """Query-string values documented by FR-RCP-001/FR-SRCH-002."""

    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"
    EXPERT = "Expert"

    @property
    def value_for_database(self) -> RecipeDifficulty:
        return RecipeDifficulty[self.name]


RecipeListSort = Literal[
    "-createdAt",
    "createdAt",
    "title",
    "-title",
    "cookTime",
    "-cookTime",
]


class RecipeListQuery(BaseModel):
    """Validated query parameters for the public recipe collection."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=12, ge=1, le=50)
    category_id: uuid.UUID | None = None
    difficulty: RecipeDifficultyFilter | None = None
    max_cook_time: int | None = Field(default=None, ge=0)
    min_servings: int | None = Field(default=None, ge=1)
    sort: RecipeListSort = "-createdAt"


class RecipeSearchQuery(RecipeListQuery):
    q: str = Field(min_length=2, max_length=100)
    sort: RecipeListSort | Literal["relevance"] = "relevance"

    @field_validator("q")
    @classmethod
    def trim_query(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Search query must have at least 2 characters.")
        return value


class NutritionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calories: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    protein: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    carbohydrates: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
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


class RecipeUpdateRequest(RecipeCreateRequest):
    """Full recipe replacement; rowVersion is an alternative to If-Match."""

    row_version: str | None = Field(default=None, alias="rowVersion")


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
    status: Literal["Draft", "Published", "Archived"]
    nutrition: NutritionResponse | None = None
    created_at: datetime = Field(alias="createdAt")
    row_version: str = Field(alias="rowVersion")


class RecipeStepCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    instruction: str = Field(min_length=1, max_length=2000)
    duration_minutes: int | None = Field(default=None, alias="durationMinutes", gt=0)
    image_url: str | None = Field(default=None, alias="imageUrl", max_length=2048)

    @field_validator("instruction", "image_url", mode="before")
    @classmethod
    def trim_step_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class RecipeStepUpdateRequest(RecipeStepCreateRequest):
    step_number: int | None = Field(default=None, alias="stepNumber", gt=0)


class RecipeStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    recipe_id: uuid.UUID = Field(alias="recipeId")
    step_number: int = Field(alias="stepNumber")
    instruction: str
    duration_minutes: int | None = Field(alias="durationMinutes")
    image_url: str | None = Field(alias="imageUrl")


class RecipeCategorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    name: str
    slug: str


class RecipeAuthorSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    full_name: str = Field(alias="fullName")
    user_name: str = Field(alias="userName")
    avatar_url: str | None = Field(alias="avatarUrl")


class RecipeIngredientCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    ingredient_name: str = Field(alias="ingredientName", min_length=1, max_length=120)
    quantity: Decimal = Field(gt=0, max_digits=8, decimal_places=2)
    unit: str = Field(min_length=1, max_length=30)

    @field_validator("ingredient_name", "unit", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class RecipeIngredientUpdateRequest(RecipeIngredientCreateRequest):
    order_index: int | None = Field(default=None, alias="orderIndex", ge=0)


class RecipeIngredientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    recipe_id: uuid.UUID = Field(alias="recipeId")
    ingredient_id: uuid.UUID = Field(alias="ingredientId")
    name: str
    quantity: float
    unit: str
    order_index: int = Field(alias="orderIndex")


class RecipeSummaryResponse(BaseModel):
    """The list-card shape returned by ``GET /api/v1/recipes``."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID
    title: str
    slug: str
    description: str
    category: RecipeCategorySummary
    prep_time_minutes: int = Field(alias="prepTimeMinutes")
    cook_time_minutes: int = Field(alias="cookTimeMinutes")
    servings: int
    difficulty: RecipeDifficulty
    status: Literal["Draft", "Published", "Archived"]
    created_at: datetime = Field(alias="createdAt")


class PagedRecipeResponse(BaseModel):
    """Offset-pagination metadata specified by FR-RCP-001."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[RecipeSummaryResponse]
    total_count: int = Field(alias="totalCount")
    page: int
    page_size: int = Field(alias="pageSize")
    total_pages: int = Field(alias="totalPages")
    has_next_page: bool = Field(alias="hasNextPage")
    has_previous_page: bool = Field(alias="hasPreviousPage")


class RecipeSearchSummaryResponse(RecipeSummaryResponse):
    relevance_score: float = Field(alias="relevanceScore")


class PagedRecipeSearchResponse(PagedRecipeResponse):
    items: list[RecipeSearchSummaryResponse]


class RecipeImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    recipe_id: uuid.UUID = Field(alias="recipeId")
    original_url: str = Field(alias="originalUrl")
    medium_url: str | None = Field(alias="mediumUrl")
    thumbnail_url: str | None = Field(alias="thumbnailUrl")
    alt_text: str | None = Field(alias="altText")
    is_primary: bool = Field(alias="isPrimary")
    order_index: int = Field(alias="orderIndex")


class RecipeImageUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    is_primary: Literal[True] = Field(alias="isPrimary")


class RecipeIngredientDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID
    ingredient_id: uuid.UUID = Field(alias="ingredientId")
    name: str
    quantity: float
    unit: str
    order_index: int = Field(alias="orderIndex")


class RecipeDetailResponse(RecipeCreateResponse):
    category: RecipeCategorySummary
    author: RecipeAuthorSummary
    ingredients: list[RecipeIngredientDetail]
    steps: list[RecipeStepResponse]
    images: list[RecipeImageResponse]
    published_at: datetime | None = Field(alias="publishedAt")
