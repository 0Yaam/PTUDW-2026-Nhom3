import uuid

from pydantic import BaseModel, ConfigDict, field_validator


class CategoryWrite(BaseModel):
    """Shared category fields an Admin may set."""

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
    """Update fields; an omitted slug preserves the existing public URL."""

    slug: str | None = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not 2 <= len(value) <= 100:
            raise ValueError("Slug must contain 2 to 100 characters.")
        if not value.isascii() or value != value.lower():
            raise ValueError("Slug must use lowercase ASCII letters, numbers, and hyphens.")
        if value.startswith("-") or value.endswith("-") or "--" in value:
            raise ValueError("Slug must not start, end, or repeat a hyphen.")
        if not all(character.isalnum() or character == "-" for character in value):
            raise ValueError("Slug must use lowercase ASCII letters, numbers, and hyphens.")
        return value


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    image_url: str | None
    recipe_count: int = 0
