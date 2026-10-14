"""Track recipe cache generation in the same transaction as recipe writes.

Revision ID: 20261014_0010
Revises: 20261009_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261014_0010"
down_revision: str | Sequence[str] | None = "20261009_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recipe_cache_generation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False),
    )
    op.execute("INSERT INTO recipe_cache_generation (id, version) VALUES (1, 0)")


def downgrade() -> None:
    op.drop_table("recipe_cache_generation")
