"""Add ai_prompt_run_reviews table for quality scoring.

Revision ID: 20260526_000009
Revises: 20260526_000008
Create Date: 2026-05-26 00:00:09

Tables added:
  ai_prompt_run_reviews  — structured quality review of a prompt run output
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "20260526_000009"
down_revision: Union[str, None] = "20260526_000008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_prompt_run_reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "prompt_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_prompt_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.String(100), nullable=True),
        sa.Column("reviewer_user_id", sa.String(255), nullable=True),
        # Quality scores — nullable; reviewer may score only relevant dimensions
        sa.Column("accuracy_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("tone_fit_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("persona_fit_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("commercial_quality_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("completeness_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("hallucination_risk_score", sa.Numeric(4, 2), nullable=True),
        # Reviewer judgment — NOT an automated send trigger
        sa.Column("ready_to_send", sa.Boolean, nullable=True),
        sa.Column("reviewer_notes", sa.String(2000), nullable=True),
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
        "ix_ai_prompt_run_reviews_prompt_run_id",
        "ai_prompt_run_reviews",
        ["prompt_run_id"],
    )
    op.create_index(
        "ix_ai_prompt_run_reviews_tenant_id",
        "ai_prompt_run_reviews",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_prompt_run_reviews_tenant_id", table_name="ai_prompt_run_reviews")
    op.drop_index(
        "ix_ai_prompt_run_reviews_prompt_run_id", table_name="ai_prompt_run_reviews"
    )
    op.drop_table("ai_prompt_run_reviews")
