"""Add restaurant and room policy FAQ tables (DATA-021).

Revision ID: 20260609_000016
Revises: 20260609_000015
Create Date: 2026-06-09

Stores restaurant-specific and room-specific policy answers for deterministic
customer question answering (PolicyQuestionResolver, RESP-045).

Supported answer_policy values:
  allowed | not_allowed | approval_required | information_only | unknown
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "20260609_000016"
down_revision = "20260609_000015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── restaurant_policy_faqs ─────────────────────────────────────────────────
    op.create_table(
        "restaurant_policy_faqs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, server_default="default"),
        sa.Column(
            "restaurant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question_key", sa.String(100), nullable=False),
        sa.Column("answer_policy", sa.String(30), nullable=False),
        sa.Column("answer_text", sa.Text, nullable=True),
        sa.Column(
            "requires_human_review",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_restaurant_policy_faqs_tenant_id",
        "restaurant_policy_faqs",
        ["tenant_id"],
    )
    op.create_index(
        "ix_restaurant_policy_faqs_restaurant_id",
        "restaurant_policy_faqs",
        ["restaurant_id"],
    )
    op.create_index(
        "ix_restaurant_policy_faqs_question_key",
        "restaurant_policy_faqs",
        ["question_key"],
    )

    # ── room_policy_faqs ───────────────────────────────────────────────────────
    op.create_table(
        "room_policy_faqs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, server_default="default"),
        sa.Column(
            "restaurant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "room_id",
            UUID(as_uuid=True),
            sa.ForeignKey("rooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question_key", sa.String(100), nullable=False),
        sa.Column("answer_policy", sa.String(30), nullable=False),
        sa.Column("answer_text", sa.Text, nullable=True),
        sa.Column(
            "requires_human_review",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_room_policy_faqs_tenant_id",
        "room_policy_faqs",
        ["tenant_id"],
    )
    op.create_index(
        "ix_room_policy_faqs_restaurant_id",
        "room_policy_faqs",
        ["restaurant_id"],
    )
    op.create_index(
        "ix_room_policy_faqs_room_id",
        "room_policy_faqs",
        ["room_id"],
    )
    op.create_index(
        "ix_room_policy_faqs_question_key",
        "room_policy_faqs",
        ["question_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_room_policy_faqs_question_key", table_name="room_policy_faqs")
    op.drop_index("ix_room_policy_faqs_room_id", table_name="room_policy_faqs")
    op.drop_index("ix_room_policy_faqs_restaurant_id", table_name="room_policy_faqs")
    op.drop_index("ix_room_policy_faqs_tenant_id", table_name="room_policy_faqs")
    op.drop_table("room_policy_faqs")

    op.drop_index(
        "ix_restaurant_policy_faqs_question_key",
        table_name="restaurant_policy_faqs",
    )
    op.drop_index(
        "ix_restaurant_policy_faqs_restaurant_id",
        table_name="restaurant_policy_faqs",
    )
    op.drop_index(
        "ix_restaurant_policy_faqs_tenant_id",
        table_name="restaurant_policy_faqs",
    )
    op.drop_table("restaurant_policy_faqs")
