"""Add phrase library tables (DATA-020).

Revision ID: 20260609_000015
Revises: 20260605_000014
Create Date: 2026-06-09

Creates three tables for the database-backed phrase library:
  - response_phrase_templates  — catalogue of phrase keys per response goal
  - response_phrase_versions   — versioned phrase text for each template
  - response_phrase_assignments — tenant/restaurant/persona override assignments
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "20260609_000015"
down_revision = "20260605_000014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── response_phrase_templates ──────────────────────────────────────────────
    op.create_table(
        "response_phrase_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, server_default="default"),
        sa.Column("phrase_key", sa.String(100), nullable=False),
        sa.Column("response_goal", sa.String(60), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
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
        "ix_response_phrase_templates_tenant_id",
        "response_phrase_templates",
        ["tenant_id"],
    )
    op.create_index(
        "ix_response_phrase_templates_phrase_key",
        "response_phrase_templates",
        ["phrase_key"],
    )
    op.create_index(
        "ix_response_phrase_templates_response_goal",
        "response_phrase_templates",
        ["response_goal"],
    )

    # ── response_phrase_versions ───────────────────────────────────────────────
    op.create_table(
        "response_phrase_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("response_phrase_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("phrase_text", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("change_notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_response_phrase_versions_template_id",
        "response_phrase_versions",
        ["template_id"],
    )
    op.create_index(
        "ix_response_phrase_versions_status",
        "response_phrase_versions",
        ["status"],
    )

    # ── response_phrase_assignments ────────────────────────────────────────────
    op.create_table(
        "response_phrase_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False, server_default="default"),
        sa.Column(
            "restaurant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "persona_id",
            UUID(as_uuid=True),
            sa.ForeignKey("personas.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("audience_type", sa.String(20), nullable=True),
        sa.Column("phrase_key", sa.String(100), nullable=False),
        sa.Column("phrase_text", sa.Text, nullable=False),
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
        "ix_response_phrase_assignments_tenant_id",
        "response_phrase_assignments",
        ["tenant_id"],
    )
    op.create_index(
        "ix_response_phrase_assignments_restaurant_id",
        "response_phrase_assignments",
        ["restaurant_id"],
    )
    op.create_index(
        "ix_response_phrase_assignments_persona_id",
        "response_phrase_assignments",
        ["persona_id"],
    )
    op.create_index(
        "ix_response_phrase_assignments_phrase_key",
        "response_phrase_assignments",
        ["phrase_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_response_phrase_assignments_phrase_key",
        table_name="response_phrase_assignments",
    )
    op.drop_index(
        "ix_response_phrase_assignments_persona_id",
        table_name="response_phrase_assignments",
    )
    op.drop_index(
        "ix_response_phrase_assignments_restaurant_id",
        table_name="response_phrase_assignments",
    )
    op.drop_index(
        "ix_response_phrase_assignments_tenant_id",
        table_name="response_phrase_assignments",
    )
    op.drop_table("response_phrase_assignments")

    op.drop_index(
        "ix_response_phrase_versions_status",
        table_name="response_phrase_versions",
    )
    op.drop_index(
        "ix_response_phrase_versions_template_id",
        table_name="response_phrase_versions",
    )
    op.drop_table("response_phrase_versions")

    op.drop_index(
        "ix_response_phrase_templates_response_goal",
        table_name="response_phrase_templates",
    )
    op.drop_index(
        "ix_response_phrase_templates_phrase_key",
        table_name="response_phrase_templates",
    )
    op.drop_index(
        "ix_response_phrase_templates_tenant_id",
        table_name="response_phrase_templates",
    )
    op.drop_table("response_phrase_templates")
