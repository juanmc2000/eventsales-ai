"""Add date_request_type_normalized to enquiry_date_requests (ENQ-002).

Revision ID: 20260602_000012
Revises: 20260601_000011
Create Date: 2026-06-02

Adds a nullable column to store the simplified 5-category normalised
date intent type alongside the existing raw LLM classification.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260602_000012"
down_revision = "20260601_000011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "enquiry_date_requests",
        sa.Column(
            "date_request_type_normalized",
            sa.String(20),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_enquiry_date_requests_date_request_type_normalized",
        "enquiry_date_requests",
        ["date_request_type_normalized"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_enquiry_date_requests_date_request_type_normalized",
        table_name="enquiry_date_requests",
    )
    op.drop_column("enquiry_date_requests", "date_request_type_normalized")
