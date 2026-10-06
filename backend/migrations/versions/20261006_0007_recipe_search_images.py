"""Index recipe text and persist recipe images.

Revision ID: 20261006_0007
Revises: 20261002_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261006_0007"
down_revision: str | None = "20261002_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.add_column("recipes", sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True))
    op.execute("""
        CREATE FUNCTION update_recipe_search_vector() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('simple', unaccent(coalesce(NEW.title, ''))), 'A') ||
                setweight(to_tsvector('simple', unaccent(coalesce(NEW.description, ''))), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER recipes_search_vector_update
        BEFORE INSERT OR UPDATE OF title, description ON recipes
        FOR EACH ROW EXECUTE FUNCTION update_recipe_search_vector()
    """)
    op.execute("UPDATE recipes SET title = title")
    op.create_index(
        "ix_recipes_search_vector", "recipes", ["search_vector"], postgresql_using="gin"
    )
    op.create_table(
        "recipe_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_url", sa.String(500), nullable=False),
        sa.Column("medium_url", sa.String(500), nullable=True),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("alt_text", sa.String(200), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("order_index >= 0", name="ck_recipe_images_order_nonnegative"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_recipe_images_recipe_id", "recipe_images", ["recipe_id"])
    op.create_index(
        "uq_recipe_images_primary",
        "recipe_images",
        ["recipe_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )


def downgrade() -> None:
    op.drop_index("uq_recipe_images_primary", table_name="recipe_images")
    op.drop_index("ix_recipe_images_recipe_id", table_name="recipe_images")
    op.drop_table("recipe_images")
    op.drop_index("ix_recipes_search_vector", table_name="recipes")
    op.execute("DROP TRIGGER recipes_search_vector_update ON recipes")
    op.execute("DROP FUNCTION update_recipe_search_vector()")
    op.drop_column("recipes", "search_vector")
