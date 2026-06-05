"""Add enquiry_response_plans table (ORCH-006).

Revision ID: 20260605_000014
Revises: 20260603_000013
Create Date: 2026-06-05

Stores the assembled response plan produced by ResponsePreparationBuilder.
One row per response-preparation run; ORCH-007 queries the latest row per
enquiry via GET /enquiries/{id}/response-preparation/latest.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

# revision identifiers, used by Alembic.
revision = "20260605_000014"
down_revision = "20260603_000013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enquiry_response_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=True),
        sa.Column(
            "enquiry_id",
            UUID(as_uuid=True),
            sa.ForeignKey("enquiries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("enquiry_processing_snapshots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("response_goal", sa.String(60), nullable=False),
        sa.Column("response_priority", sa.String(20), nullable=False),
        sa.Column("can_generate_draft", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("goal_reason", sa.Text, nullable=True),
        sa.Column("blocking_fields", JSON, nullable=True),
        sa.Column("known_facts", JSON, nullable=True),
        sa.Column("missing_information", JSON, nullable=True),
        sa.Column("clarification_questions", JSON, nullable=True),
        sa.Column("date_context", JSON, nullable=True),
        sa.Column("availability_context", JSON, nullable=True),
        sa.Column("customer_type_context", JSON, nullable=True),
        sa.Column("persona_context", JSON, nullable=True),
        sa.Column("draft_instructions", JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_enquiry_response_plans_enquiry_id", "enquiry_response_plans", ["enquiry_id"])
    op.create_index("ix_enquiry_response_plans_tenant_id", "enquiry_response_plans", ["tenant_id"])
    op.create_index("ix_enquiry_response_plans_response_goal", "enquiry_response_plans", ["response_goal"])
    op.create_index("ix_enquiry_response_plans_created_at", "enquiry_response_plans", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_enquiry_response_plans_created_at", table_name="enquiry_response_plans")
    op.drop_index("ix_enquiry_response_plans_response_goal", table_name="enquiry_response_plans")
    op.drop_index("ix_enquiry_response_plans_tenant_id", table_name="enquiry_response_plans")
    op.drop_index("ix_enquiry_response_plans_enquiry_id", table_name="enquiry_response_plans")
    op.drop_table("enquiry_response_plans")
