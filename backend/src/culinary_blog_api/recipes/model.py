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
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
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
    status: Mapped[int] = mapped_column(
        SmallInteger(), default=RecipeStatus.DRAFT, index=True
    )
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)
    row_version: Mapped[bytes] = mapped_column(LargeBinary(), default=b"\x00")

    category: Mapped["Category"] = relationship()
    author: Mapped["User"] = relationship()
