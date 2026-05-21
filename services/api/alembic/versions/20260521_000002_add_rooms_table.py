"""Add rooms table.

Revision ID: 20260521_000002
Revises: 20260520_000001
Create Date: 2026-05-21 00:00:02

Tables created:
  - rooms
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260521_000002"
down_revision: Union[str, None] = "20260520_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rooms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(100),
            nullable=False,
            server_default="default",
        ),
        sa.Column(
            "restaurant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("room_type", sa.String(100), nullable=True),
        sa.Column("seated_capacity", sa.Integer, nullable=True),
        sa.Column("standing_capacity", sa.Integer, nullable=True),
        sa.Column("min_capacity", sa.Integer, nullable=True),
        sa.Column("max_capacity", sa.Integer, nullable=True),
        sa.Column("layouts", JSON, nullable=True),
        sa.Column("amenities", JSON, nullable=True),
        sa.Column("asset_links", JSON, nullable=True),
        sa.Column("room_hire_fee", sa.Numeric(10, 2), nullable=True),
        sa.Column("minimum_spend_notes", sa.Text, nullable=True),
        sa.Column("suitability_notes", sa.Text, nullable=True),
        sa.Column("booking_url", sa.String(500), nullable=True),
        sa.Column(
            "is_private_dining", sa.Boolean, nullable=False, server_default="false"
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_rooms_tenant_id", "rooms", ["tenant_id"])
    op.create_index("ix_rooms_restaurant_id", "rooms", ["restaurant_id"])
    op.create_index("ix_rooms_slug", "rooms", ["slug"])


def downgrade() -> None:
    op.drop_index("ix_rooms_slug", table_name="rooms")
    op.drop_index("ix_rooms_restaurant_id", table_name="rooms")
    op.drop_index("ix_rooms_tenant_id", table_name="rooms")
    op.drop_table("rooms")
