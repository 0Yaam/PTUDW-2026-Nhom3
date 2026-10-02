"""Add optional cooking-step duration and image reference.

Revision ID: 20261002_0005
Revises: 20260922_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261002_0005"
down_revision: str | None = "20260922_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("recipe_steps", sa.Column("duration_minutes", sa.Integer(), nullable=True))
    op.add_column("recipe_steps", sa.Column("image_url", sa.String(length=2048), nullable=True))
    op.create_check_constraint(
        "ck_recipe_steps_duration_positive", "recipe_steps", "duration_minutes > 0"
    )


def downgrade() -> None:
    op.drop_constraint("ck_recipe_steps_duration_positive", "recipe_steps", type_="check")
    op.drop_column("recipe_steps", "image_url")
    op.drop_column("recipe_steps", "duration_minutes")
