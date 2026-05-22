"""Add audience column to restaurant_personas.

Revision ID: 20260522_000003
Revises: 20260521_000002
Create Date: 2026-05-22 00:00:03

Columns added:
  - restaurant_personas.audience (VARCHAR(20), nullable)

Values: "social" | "corporate" | "agency" | NULL (default fallback).
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260522_000003"
down_revision: Union[str, None] = "20260521_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "restaurant_personas",
        sa.Column("audience", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("restaurant_personas", "audience")
