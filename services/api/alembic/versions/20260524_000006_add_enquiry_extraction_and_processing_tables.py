"""Add enquiry extraction and processing snapshot tables.

Revision ID: 20260524_000006
Revises: 20260523_000005
Create Date: 2026-05-24 00:00:06

Tables added:
  enquiry_extractions           — structured facts extracted from freeform text via LLM
  enquiry_processing_snapshots  — deterministic processing result (room, pricing, availability)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "20260524_000006"
down_revision: Union[str, None] = "20260523_000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # enquiry_extractions
    # ------------------------------------------------------------------
    op.create_table(
        "enquiry_extractions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=True),
        sa.Column(
            "enquiry_id",
            UUID(as_uuid=True),
            sa.ForeignKey("enquiries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_message_id",
            UUID(as_uuid=True),
            sa.ForeignKey("enquiry_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "prompt_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_prompt_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("extracted_json", JSONB, nullable=True),
        sa.Column("normalized_json", JSONB, nullable=True),
        sa.Column("missing_fields", JSONB, nullable=True),
        sa.Column("confidence_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_enquiry_extractions_tenant_id", "enquiry_extractions", ["tenant_id"]
    )
    op.create_index(
        "ix_enquiry_extractions_enquiry_id", "enquiry_extractions", ["enquiry_id"]
    )
    op.create_index(
        "ix_enquiry_extractions_source_message_id",
        "enquiry_extractions",
        ["source_message_id"],
    )
    op.create_index(
        "ix_enquiry_extractions_prompt_run_id", "enquiry_extractions", ["prompt_run_id"]
    )
    op.create_index(
        "ix_enquiry_extractions_created_at", "enquiry_extractions", ["created_at"]
    )

    # ------------------------------------------------------------------
    # enquiry_processing_snapshots
    # ------------------------------------------------------------------
    op.create_table(
        "enquiry_processing_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=True),
        sa.Column(
            "enquiry_id",
            UUID(as_uuid=True),
            sa.ForeignKey("enquiries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "extraction_id",
            UUID(as_uuid=True),
            sa.ForeignKey("enquiry_extractions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pricing_rule_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pricing_rules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("availability_result_json", JSONB, nullable=True),
        sa.Column("room_suitability_json", JSONB, nullable=True),
        sa.Column("pricing_result_json", JSONB, nullable=True),
        sa.Column("missing_fields_json", JSONB, nullable=True),
        sa.Column("recommended_action", sa.String(30), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_enquiry_processing_snapshots_tenant_id",
        "enquiry_processing_snapshots",
        ["tenant_id"],
    )
    op.create_index(
        "ix_enquiry_processing_snapshots_enquiry_id",
        "enquiry_processing_snapshots",
        ["enquiry_id"],
    )
    op.create_index(
        "ix_enquiry_processing_snapshots_extraction_id",
        "enquiry_processing_snapshots",
        ["extraction_id"],
    )
    op.create_index(
        "ix_enquiry_processing_snapshots_pricing_rule_id",
        "enquiry_processing_snapshots",
        ["pricing_rule_id"],
    )
    op.create_index(
        "ix_enquiry_processing_snapshots_recommended_action",
        "enquiry_processing_snapshots",
        ["recommended_action"],
    )
    op.create_index(
        "ix_enquiry_processing_snapshots_created_at",
        "enquiry_processing_snapshots",
        ["created_at"],
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index(
        "ix_enquiry_processing_snapshots_created_at",
        table_name="enquiry_processing_snapshots",
    )
    op.drop_index(
        "ix_enquiry_processing_snapshots_recommended_action",
        table_name="enquiry_processing_snapshots",
    )
    op.drop_index(
        "ix_enquiry_processing_snapshots_pricing_rule_id",
        table_name="enquiry_processing_snapshots",
    )
    op.drop_index(
        "ix_enquiry_processing_snapshots_extraction_id",
        table_name="enquiry_processing_snapshots",
    )
    op.drop_index(
        "ix_enquiry_processing_snapshots_enquiry_id",
        table_name="enquiry_processing_snapshots",
    )
    op.drop_index(
        "ix_enquiry_processing_snapshots_tenant_id",
        table_name="enquiry_processing_snapshots",
    )
    op.drop_table("enquiry_processing_snapshots")

    op.drop_index("ix_enquiry_extractions_created_at", table_name="enquiry_extractions")
    op.drop_index(
        "ix_enquiry_extractions_prompt_run_id", table_name="enquiry_extractions"
    )
    op.drop_index(
        "ix_enquiry_extractions_source_message_id", table_name="enquiry_extractions"
    )
    op.drop_index(
        "ix_enquiry_extractions_enquiry_id", table_name="enquiry_extractions"
    )
    op.drop_index(
        "ix_enquiry_extractions_tenant_id", table_name="enquiry_extractions"
    )
    op.drop_table("enquiry_extractions")
