"""Add enquiry_date_requests and enquiry_candidate_dates tables.

Revision ID: 20260527_000010
Revises: 20260526_000009
Create Date: 2026-05-27 00:00:10

Tables added:
  enquiry_date_requests    — extracted date intent from a guest enquiry
  enquiry_candidate_dates  — deterministically generated candidate dates
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "20260527_000010"
down_revision: Union[str, None] = "20260526_000009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── enquiry_date_requests ─────────────────────────────────────────────────
    op.create_table(
        "enquiry_date_requests",
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
            sa.ForeignKey("enquiry_extractions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "prompt_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_prompt_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("raw_text", sa.Text, nullable=True),
        sa.Column("date_request_type", sa.String(60), nullable=False, server_default="unknown"),
        sa.Column("anchor_date", sa.Date, nullable=True),
        sa.Column("timezone", sa.String(100), nullable=True),
        sa.Column("extracted_json", JSONB, nullable=True),
        sa.Column("requires_date_clarification", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("clarification_question", sa.Text, nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_enquiry_date_requests_tenant_id",
        "enquiry_date_requests",
        ["tenant_id"],
    )
    op.create_index(
        "ix_enquiry_date_requests_enquiry_id",
        "enquiry_date_requests",
        ["enquiry_id"],
    )
    op.create_index(
        "ix_enquiry_date_requests_extraction_id",
        "enquiry_date_requests",
        ["extraction_id"],
    )
    op.create_index(
        "ix_enquiry_date_requests_prompt_run_id",
        "enquiry_date_requests",
        ["prompt_run_id"],
    )
    op.create_index(
        "ix_enquiry_date_requests_created_at",
        "enquiry_date_requests",
        ["created_at"],
    )

    # ── enquiry_candidate_dates ───────────────────────────────────────────────
    op.create_table(
        "enquiry_candidate_dates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=True),
        sa.Column(
            "enquiry_id",
            UUID(as_uuid=True),
            sa.ForeignKey("enquiries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "date_request_id",
            UUID(as_uuid=True),
            sa.ForeignKey("enquiry_date_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("candidate_date", sa.Date, nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False, server_default="deterministic"),
        sa.Column("availability_status", sa.String(20), nullable=True),
        sa.Column("pricing_checked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("recommended_minimum_spend", sa.Numeric(10, 2), nullable=True),
        sa.Column("ranking_score", sa.Numeric(6, 4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_enquiry_candidate_dates_tenant_id",
        "enquiry_candidate_dates",
        ["tenant_id"],
    )
    op.create_index(
        "ix_enquiry_candidate_dates_enquiry_id",
        "enquiry_candidate_dates",
        ["enquiry_id"],
    )
    op.create_index(
        "ix_enquiry_candidate_dates_date_request_id",
        "enquiry_candidate_dates",
        ["date_request_id"],
    )
    op.create_index(
        "ix_enquiry_candidate_dates_candidate_date",
        "enquiry_candidate_dates",
        ["candidate_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_enquiry_candidate_dates_candidate_date", "enquiry_candidate_dates")
    op.drop_index("ix_enquiry_candidate_dates_date_request_id", "enquiry_candidate_dates")
    op.drop_index("ix_enquiry_candidate_dates_enquiry_id", "enquiry_candidate_dates")
    op.drop_index("ix_enquiry_candidate_dates_tenant_id", "enquiry_candidate_dates")
    op.drop_table("enquiry_candidate_dates")

    op.drop_index("ix_enquiry_date_requests_created_at", "enquiry_date_requests")
    op.drop_index("ix_enquiry_date_requests_prompt_run_id", "enquiry_date_requests")
    op.drop_index("ix_enquiry_date_requests_extraction_id", "enquiry_date_requests")
    op.drop_index("ix_enquiry_date_requests_enquiry_id", "enquiry_date_requests")
    op.drop_index("ix_enquiry_date_requests_tenant_id", "enquiry_date_requests")
    op.drop_table("enquiry_date_requests")
