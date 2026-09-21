"""Create the base recipes table."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260920_0003"
down_revision: str | Sequence[str] | None = "20260916_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recipes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False, server_default=""),
        sa.Column("prep_time_minutes", sa.Integer(), nullable=False),
        sa.Column("cook_time_minutes", sa.Integer(), nullable=False),
        sa.Column("servings", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nutrition_calories", sa.Numeric(8, 2), nullable=True),
        sa.Column("nutrition_protein", sa.Numeric(8, 2), nullable=True),
        sa.Column("nutrition_carbohydrates", sa.Numeric(8, 2), nullable=True),
        sa.Column("nutrition_fat", sa.Numeric(8, 2), nullable=True),
        sa.Column("nutrition_fiber", sa.Numeric(8, 2), nullable=True),
        sa.Column("nutrition_sodium", sa.Numeric(8, 2), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "row_version",
            sa.LargeBinary(),
            nullable=False,
            server_default=sa.text("'\\x00'::bytea"),
        ),
        sa.CheckConstraint(
            "prep_time_minutes > 0", name="ck_recipes_prep_time_positive"
        ),
        sa.CheckConstraint(
            "cook_time_minutes >= 0", name="ck_recipes_cook_time_nonnegative"
        ),
        sa.CheckConstraint("servings > 0", name="ck_recipes_servings_positive"),
        sa.CheckConstraint("difficulty BETWEEN 1 AND 4", name="ck_recipes_difficulty"),
        sa.CheckConstraint("status BETWEEN 0 AND 2", name="ck_recipes_status"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recipes_slug", "recipes", ["slug"], unique=True)
    op.create_index("ix_recipes_category_id", "recipes", ["category_id"])
    op.create_index("ix_recipes_author_id", "recipes", ["author_id"])
    op.create_index("ix_recipes_difficulty", "recipes", ["difficulty"])
    op.create_index("ix_recipes_status", "recipes", ["status"])
    op.create_index("ix_recipes_published_at", "recipes", ["published_at"])
    op.create_index("ix_recipes_is_deleted", "recipes", ["is_deleted"])


def downgrade() -> None:
    op.drop_table("recipes")
