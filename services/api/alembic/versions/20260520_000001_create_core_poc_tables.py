"""Create core POC tables.

Revision ID: 20260520_000001
Revises:
Create Date: 2026-05-20 00:00:01

Tables created:
  - restaurants
  - personas
  - restaurant_personas
  - pricing_rules
  - enquiries
  - enquiry_messages
  - email_events
  - calendar_events
  - demand_events
  - insight_snapshots
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260520_000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── restaurants ──────────────────────────────────────────────────────────
    op.create_table(
        "restaurants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, server_default="default"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("settings", JSON, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
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
    op.create_index("ix_restaurants_slug", "restaurants", ["slug"], unique=True)
    op.create_index("ix_restaurants_tenant_id", "restaurants", ["tenant_id"])

    # ── personas ─────────────────────────────────────────────────────────────
    op.create_table(
        "personas",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("tone", sa.String(100), nullable=False, server_default="professional"),
        sa.Column("style", sa.String(100), nullable=False, server_default="concise"),
        sa.Column("system_prompt", sa.Text, nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
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
    op.create_index("ix_personas_slug", "personas", ["slug"], unique=True)

    # ── restaurant_personas ───────────────────────────────────────────────────
    op.create_table(
        "restaurant_personas",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "restaurant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "persona_id",
            UUID(as_uuid=True),
            sa.ForeignKey("personas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_restaurant_personas_restaurant_id",
        "restaurant_personas",
        ["restaurant_id"],
    )
    op.create_index(
        "ix_restaurant_personas_persona_id",
        "restaurant_personas",
        ["persona_id"],
    )

    # ── pricing_rules ─────────────────────────────────────────────────────────
    op.create_table(
        "pricing_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "restaurant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("day_of_week", sa.Integer, nullable=True),
        sa.Column("meal_period", sa.String(20), nullable=False, server_default="all"),
        sa.Column("minimum_spend", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("minimum_covers", sa.Integer, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
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
    op.create_index(
        "ix_pricing_rules_restaurant_id", "pricing_rules", ["restaurant_id"]
    )

    # ── enquiries ─────────────────────────────────────────────────────────────
    op.create_table(
        "enquiries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "restaurant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("restaurants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "persona_id",
            UUID(as_uuid=True),
            sa.ForeignKey("personas.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reference", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="new"),
        sa.Column("source", sa.String(30), nullable=False, server_default="webform"),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("party_size", sa.Integer, nullable=True),
        sa.Column("event_date", sa.Date, nullable=True),
        sa.Column("event_type", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("metadata", JSON, nullable=True),
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
    op.create_index("ix_enquiries_reference", "enquiries", ["reference"], unique=True)
    op.create_index("ix_enquiries_restaurant_id", "enquiries", ["restaurant_id"])
    op.create_index("ix_enquiries_persona_id", "enquiries", ["persona_id"])
    op.create_index("ix_enquiries_status", "enquiries", ["status"])
    op.create_index("ix_enquiries_email", "enquiries", ["email"])
    op.create_index("ix_enquiries_event_date", "enquiries", ["event_date"])

    # ── enquiry_messages ──────────────────────────────────────────────────────
    op.create_table(
        "enquiry_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "enquiry_id",
            UUID(as_uuid=True),
            sa.ForeignKey("enquiries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_enquiry_messages_enquiry_id", "enquiry_messages", ["enquiry_id"]
    )

    # ── email_events ──────────────────────────────────────────────────────────
    op.create_table(
        "email_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "enquiry_id",
            UUID(as_uuid=True),
            sa.ForeignKey("enquiries.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("from_address", sa.String(255), nullable=False),
        sa.Column("to_address", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("message_id", sa.String(500), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("metadata", JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_email_events_enquiry_id", "email_events", ["enquiry_id"])
    op.create_index("ix_email_events_direction", "email_events", ["direction"])
    op.create_index("ix_email_events_status", "email_events", ["status"])
    op.create_index("ix_email_events_message_id", "email_events", ["message_id"])

    # ── calendar_events ───────────────────────────────────────────────────────
    op.create_table(
        "calendar_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "restaurant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("restaurants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "enquiry_id",
            UUID(as_uuid=True),
            sa.ForeignKey("enquiries.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("event_date", sa.Date, nullable=False),
        sa.Column("meal_period", sa.String(20), nullable=False),
        sa.Column("party_size", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="tentative"),
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
    op.create_index(
        "ix_calendar_events_restaurant_id", "calendar_events", ["restaurant_id"]
    )
    op.create_index("ix_calendar_events_event_date", "calendar_events", ["event_date"])
    op.create_index("ix_calendar_events_enquiry_id", "calendar_events", ["enquiry_id"])

    # ── demand_events ─────────────────────────────────────────────────────────
    op.create_table(
        "demand_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "restaurant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_date", sa.Date, nullable=False),
        sa.Column("meal_period", sa.String(20), nullable=False, server_default="all"),
        sa.Column("demand_level", sa.String(20), nullable=False),
        sa.Column("demand_score", sa.Float, nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="seeded"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_demand_events_restaurant_id", "demand_events", ["restaurant_id"])
    op.create_index("ix_demand_events_event_date", "demand_events", ["event_date"])
    op.create_index("ix_demand_events_demand_level", "demand_events", ["demand_level"])

    # ── insight_snapshots ─────────────────────────────────────────────────────
    op.create_table(
        "insight_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "restaurant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("snapshot_type", sa.String(20), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("data", JSON, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_insight_snapshots_restaurant_id", "insight_snapshots", ["restaurant_id"]
    )
    op.create_index(
        "ix_insight_snapshots_snapshot_type", "insight_snapshots", ["snapshot_type"]
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("insight_snapshots")
    op.drop_table("demand_events")
    op.drop_table("calendar_events")
    op.drop_table("email_events")
    op.drop_table("enquiry_messages")
    op.drop_table("enquiries")
    op.drop_table("pricing_rules")
    op.drop_table("restaurant_personas")
    op.drop_table("personas")
    op.drop_table("restaurants")
