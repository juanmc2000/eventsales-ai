"""Add review_metadata column to enquiry_messages (AUTO-004).

Revision ID: 20260608_000015
Revises: 20260605_000014
Create Date: 2026-06-08

Persists the draft review lifecycle state on the EnquiryMessage record so
auto-send readiness, validation status, blockers, and generation path are
auditable after draft generation.

Fields stored in the JSON column:
  - review_state:        DraftReviewState status constant
  - validation_status:   "passed" | "failed"
  - validation_blockers: list of compliance violation strings
  - auto_send_allowed:   bool
  - auto_send_blockers:  list of auto-send blocker strings
  - generation_path:     "llm" | "deterministic"

Nullable — pre-AUTO-004 messages and non-draft messages do not have this column.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = "20260608_000015"
down_revision = "20260605_000014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "enquiry_messages",
        sa.Column("review_metadata", JSON, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("enquiry_messages", "review_metadata")
