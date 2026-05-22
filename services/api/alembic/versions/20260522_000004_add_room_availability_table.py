"""Add room_availability table.

Revision ID: 20260522_000004
Revises: 20260522_000003
Create Date: 2026-05-22 00:00:04

Table added:
  room_availability — per-room, per-date, per-meal-period availability status.
  POC-phase: seeded deterministically. Future: live booking system API call.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "20260522_000004"
down_revision: Union[str, None] = "20260522_000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "room_availability",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, server_default="default"),
        sa.Column(
            "room_id",
            UUID(as_uuid=True),
            sa.ForeignKey("rooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("meal_period", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
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
    op.create_index("ix_room_availability_room_id", "room_availability", ["room_id"])
    op.create_index("ix_room_availability_date", "room_availability", ["date"])
    op.create_index("ix_room_availability_tenant_id", "room_availability", ["tenant_id"])
    op.create_unique_constraint(
        "uq_room_availability_slot",
        "room_availability",
        ["room_id", "date", "meal_period"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_room_availability_slot", "room_availability", type_="unique")
    op.drop_index("ix_room_availability_tenant_id", table_name="room_availability")
    op.drop_index("ix_room_availability_date", table_name="room_availability")
    op.drop_index("ix_room_availability_room_id", table_name="room_availability")
    op.drop_table("room_availability")
