import uuid

from pydantic import BaseModel, ConfigDict, field_validator


class CategoryWrite(BaseModel):
    """Fields an Admin may set; slug and IDs always belong to the server."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not 2 <= len(value) <= 50:
            raise ValueError("Name must contain 2 to 50 characters.")
        if "<" in value or ">" in value:
            raise ValueError("Name must not contain HTML.")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if "<" in value or ">" in value:
            raise ValueError("Description must not contain HTML.")
        return value or None


class CategoryCreate(CategoryWrite):
    """Request body for POST /categories."""


class CategoryUpdate(CategoryWrite):
    """Request body for PUT /categories/{id}; omission clears description."""


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    image_url: str | None
    recipe_count: int = 0
