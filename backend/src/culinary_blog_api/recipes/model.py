import uuid
from datetime import datetime
from decimal import Decimal
from enum import IntEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base

if TYPE_CHECKING:
    from ..auth.model import User
    from ..categories.model import Category


class RecipeStatus(IntEnum):
    DRAFT = 0
    PUBLISHED = 1
    ARCHIVED = 2


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (
        CheckConstraint("prep_time_minutes > 0", name="ck_recipes_prep_time_positive"),
        CheckConstraint("cook_time_minutes >= 0", name="ck_recipes_cook_time_nonnegative"),
        CheckConstraint("servings > 0", name="ck_recipes_servings_positive"),
        CheckConstraint("difficulty BETWEEN 1 AND 4", name="ck_recipes_difficulty"),
        CheckConstraint("status BETWEEN 0 AND 2", name="ck_recipes_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text())
    instructions: Mapped[str] = mapped_column(Text(), default="")
    prep_time_minutes: Mapped[int] = mapped_column(Integer())
    cook_time_minutes: Mapped[int] = mapped_column(Integer())
    servings: Mapped[int] = mapped_column(Integer())
    difficulty: Mapped[int] = mapped_column(SmallInteger(), index=True)
    status: Mapped[int] = mapped_column(SmallInteger(), default=RecipeStatus.DRAFT, index=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    nutrition_calories: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    nutrition_protein: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    nutrition_carbohydrates: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    nutrition_fat: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    nutrition_fiber: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    nutrition_sodium: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
    row_version: Mapped[bytes] = mapped_column(LargeBinary(), default=b"\x00")
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR().with_variant(Text(), "sqlite"), nullable=True
    )
    __mapper_args__ = {
        "version_id_col": row_version,
        "version_id_generator": lambda current: (
            int.from_bytes(current or b"\x00", "big") + 1
        ).to_bytes(8, "big"),
    }

    category: Mapped["Category"] = relationship()
    author: Mapped["User"] = relationship()
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeIngredient.order_index",
    )
    steps: Mapped[list["RecipeStep"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeStep.step_number",
    )
    images: Mapped[list["RecipeImage"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="RecipeImage.order_index"
    )


class RecipeImage(Base):
    __tablename__ = "recipe_images"
    __table_args__ = (
        CheckConstraint("order_index >= 0", name="ck_recipe_images_order_nonnegative"),
        Index(
            "uq_recipe_images_primary",
            "recipe_id",
            unique=True,
            postgresql_where=text("is_primary"),
            sqlite_where=text("is_primary"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), index=True
    )
    original_url: Mapped[str] = mapped_column(String(500))
    medium_url: Mapped[str | None] = mapped_column(String(500))
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    alt_text: Mapped[str | None] = mapped_column(String(200))
    is_primary: Mapped[bool] = mapped_column(Boolean(), default=False)
    order_index: Mapped[int] = mapped_column(Integer(), default=0)

    recipe: Mapped["Recipe"] = relationship(back_populates="images")


class RecipeImageResizeJob(Base):
    """Durable resize request committed with the uploaded image metadata."""

    __tablename__ = "recipe_image_resize_jobs"
    __table_args__ = (
        Index("ix_recipe_image_resize_jobs_due", "status", "next_attempt_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    image_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recipe_images.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[str] = mapped_column(String(16), default="Pending", server_default="Pending")
    attempts: Mapped[int] = mapped_column(Integer(), default=0, server_default="0")
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_error: Mapped[str | None] = mapped_column(String(120))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    __table_args__ = (
        UniqueConstraint("recipe_id", "ingredient_id", name="uq_recipe_ingredient"),
        CheckConstraint("quantity > 0", name="ck_recipe_ingredients_quantity_positive"),
        CheckConstraint("order_index >= 0", name="ck_recipe_ingredients_order_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), index=True
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingredients.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    unit: Mapped[str] = mapped_column(String(30))
    order_index: Mapped[int] = mapped_column(Integer(), default=0)

    recipe: Mapped["Recipe"] = relationship(back_populates="ingredients")
    ingredient: Mapped["Ingredient"] = relationship()


class RecipeStep(Base):
    __tablename__ = "recipe_steps"
    __table_args__ = (
        UniqueConstraint("recipe_id", "step_number", name="uq_recipe_step_number"),
        CheckConstraint("step_number > 0", name="ck_recipe_steps_number_positive"),
        CheckConstraint("duration_minutes > 0", name="ck_recipe_steps_duration_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), index=True
    )
    step_number: Mapped[int] = mapped_column(Integer())
    instruction: Mapped[str] = mapped_column(Text())
    duration_minutes: Mapped[int | None] = mapped_column(Integer())
    image_url: Mapped[str | None] = mapped_column(String(2048))

    recipe: Mapped["Recipe"] = relationship(back_populates="steps")
