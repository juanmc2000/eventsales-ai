"""Add numeric date ambiguity columns to enquiry_date_requests (HOTFIX-001).

Revision ID: 20260603_000013
Revises: 20260602_000012
Create Date: 2026-06-03

Adds five nullable columns to support deterministic numeric date
disambiguation (DD/MM vs MM/DD):

  ambiguity_type        — resolved | resolved_with_confirmation | unresolved_ambiguity
  assumed_date          — date chosen for availability checks
  alternative_date      — the other interpretation (null for unambiguous)
  clarification_required — True when guest confirmation is needed
  clarification_reason  — machine-readable reason code
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260603_000013"
down_revision = "20260602_000012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "enquiry_date_requests",
        sa.Column("ambiguity_type", sa.String(30), nullable=True),
    )
    op.add_column(
        "enquiry_date_requests",
        sa.Column("assumed_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "enquiry_date_requests",
        sa.Column("alternative_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "enquiry_date_requests",
        sa.Column("clarification_required", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "enquiry_date_requests",
        sa.Column("clarification_reason", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("enquiry_date_requests", "clarification_reason")
    op.drop_column("enquiry_date_requests", "clarification_required")
    op.drop_column("enquiry_date_requests", "alternative_date")
    op.drop_column("enquiry_date_requests", "assumed_date")
    op.drop_column("enquiry_date_requests", "ambiguity_type")
