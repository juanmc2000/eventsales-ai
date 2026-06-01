"""Extend recommended_action column in enquiry_processing_snapshots to VARCHAR(100).

The original VARCHAR(30) is too short for action codes such as
'send_availability_with_missing_info_question' (44 chars).

Revision ID: 20260601_000011
Revises: 20260527_000010
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa

revision = "20260601_000011"
down_revision = "20260527_000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "enquiry_processing_snapshots",
        "recommended_action",
        existing_type=sa.String(30),
        type_=sa.String(100),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "enquiry_processing_snapshots",
        "recommended_action",
        existing_type=sa.String(100),
        type_=sa.String(30),
        existing_nullable=True,
    )
