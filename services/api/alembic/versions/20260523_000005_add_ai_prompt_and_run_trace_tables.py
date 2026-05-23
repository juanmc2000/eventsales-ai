"""Add AI prompt versioning and run trace tables.

Revision ID: 20260523_000005
Revises: 20260522_000004
Create Date: 2026-05-23 00:00:05

Tables added:
  ai_prompt_templates     — logical prompt definitions (tenant-aware)
  ai_prompt_versions      — immutable versioned prompt snapshots
  tenant_prompt_configs   — per-tenant active version selection
  ai_prompt_runs          — full trace log of every LLM call
  ai_training_examples    — curated examples for future evaluation / fine-tuning
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "20260523_000005"
down_revision: Union[str, None] = "20260522_000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # ai_prompt_templates
    # ------------------------------------------------------------------
    op.create_table(
        "ai_prompt_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=True),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("is_system_default", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
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
    op.create_index("ix_ai_prompt_templates_tenant_id", "ai_prompt_templates", ["tenant_id"])
    op.create_index("ix_ai_prompt_templates_key", "ai_prompt_templates", ["key"])

    # ------------------------------------------------------------------
    # ai_prompt_versions
    # ------------------------------------------------------------------
    op.create_table(
        "ai_prompt_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "prompt_template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_prompt_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("system_prompt", sa.Text, nullable=False),
        sa.Column("user_prompt_template", sa.Text, nullable=False),
        sa.Column("output_schema_name", sa.String(100), nullable=True),
        sa.Column("output_schema_version", sa.String(20), nullable=True),
        sa.Column("model_provider", sa.String(50), nullable=True),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("temperature", sa.String(10), nullable=True),
        sa.Column("max_tokens", sa.Integer, nullable=True),
        sa.Column("change_notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_ai_prompt_versions_prompt_template_id",
        "ai_prompt_versions",
        ["prompt_template_id"],
    )

    # ------------------------------------------------------------------
    # tenant_prompt_configs
    # ------------------------------------------------------------------
    op.create_table(
        "tenant_prompt_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("prompt_key", sa.String(100), nullable=False),
        sa.Column(
            "active_prompt_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_prompt_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "restaurant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("restaurants.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "persona_id",
            UUID(as_uuid=True),
            sa.ForeignKey("personas.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
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
    op.create_index("ix_tenant_prompt_configs_tenant_id", "tenant_prompt_configs", ["tenant_id"])
    op.create_index(
        "ix_tenant_prompt_configs_restaurant_id", "tenant_prompt_configs", ["restaurant_id"]
    )
    op.create_index(
        "ix_tenant_prompt_configs_persona_id", "tenant_prompt_configs", ["persona_id"]
    )

    # ------------------------------------------------------------------
    # ai_prompt_runs
    # ------------------------------------------------------------------
    op.create_table(
        "ai_prompt_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=True),
        sa.Column(
            "restaurant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("restaurants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "enquiry_id",
            UUID(as_uuid=True),
            sa.ForeignKey("enquiries.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "persona_id",
            UUID(as_uuid=True),
            sa.ForeignKey("personas.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("trigger_type", sa.String(50), nullable=True),
        sa.Column("trigger_source", sa.String(50), nullable=True),
        sa.Column("triggered_by_user_id", sa.String(255), nullable=True),
        sa.Column(
            "prompt_template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_prompt_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "prompt_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_prompt_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("prompt_key", sa.String(100), nullable=True),
        sa.Column("prompt_version", sa.Integer, nullable=True),
        sa.Column("model_provider", sa.String(50), nullable=True),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("rendered_system_prompt", sa.Text, nullable=True),
        sa.Column("rendered_user_prompt", sa.Text, nullable=True),
        sa.Column("input_payload", JSONB, nullable=True),
        sa.Column("input_hash", sa.String(64), nullable=True),
        sa.Column("raw_response", sa.Text, nullable=True),
        sa.Column("parsed_response", JSONB, nullable=True),
        sa.Column("validation_status", sa.String(20), nullable=True),
        sa.Column("validation_errors", JSONB, nullable=True),
        sa.Column("fallback_used", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("fallback_reason", sa.String(255), nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("token_input_count", sa.Integer, nullable=True),
        sa.Column("token_output_count", sa.Integer, nullable=True),
        sa.Column("estimated_cost", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="success"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_ai_prompt_runs_tenant_id", "ai_prompt_runs", ["tenant_id"])
    op.create_index("ix_ai_prompt_runs_restaurant_id", "ai_prompt_runs", ["restaurant_id"])
    op.create_index("ix_ai_prompt_runs_enquiry_id", "ai_prompt_runs", ["enquiry_id"])
    op.create_index(
        "ix_ai_prompt_runs_prompt_template_id", "ai_prompt_runs", ["prompt_template_id"]
    )
    op.create_index(
        "ix_ai_prompt_runs_prompt_version_id", "ai_prompt_runs", ["prompt_version_id"]
    )
    op.create_index("ix_ai_prompt_runs_prompt_key", "ai_prompt_runs", ["prompt_key"])
    op.create_index("ix_ai_prompt_runs_input_hash", "ai_prompt_runs", ["input_hash"])
    op.create_index("ix_ai_prompt_runs_created_at", "ai_prompt_runs", ["created_at"])

    # ------------------------------------------------------------------
    # ai_training_examples
    # ------------------------------------------------------------------
    op.create_table(
        "ai_training_examples",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "prompt_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_prompt_runs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("tenant_id", sa.String(100), nullable=True),
        sa.Column("prompt_key", sa.String(100), nullable=True),
        sa.Column("original_output", JSONB, nullable=True),
        sa.Column("corrected_output", JSONB, nullable=True),
        sa.Column("correction_reason", sa.Text, nullable=True),
        sa.Column("reviewed_by_user_id", sa.String(255), nullable=True),
        sa.Column("quality_rating", sa.Integer, nullable=True),
        sa.Column(
            "approved_for_training", sa.Boolean, nullable=False, server_default="false"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_ai_training_examples_prompt_run_id", "ai_training_examples", ["prompt_run_id"]
    )
    op.create_index(
        "ix_ai_training_examples_tenant_id", "ai_training_examples", ["tenant_id"]
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index("ix_ai_training_examples_tenant_id", table_name="ai_training_examples")
    op.drop_index("ix_ai_training_examples_prompt_run_id", table_name="ai_training_examples")
    op.drop_table("ai_training_examples")

    op.drop_index("ix_ai_prompt_runs_created_at", table_name="ai_prompt_runs")
    op.drop_index("ix_ai_prompt_runs_input_hash", table_name="ai_prompt_runs")
    op.drop_index("ix_ai_prompt_runs_prompt_key", table_name="ai_prompt_runs")
    op.drop_index("ix_ai_prompt_runs_prompt_version_id", table_name="ai_prompt_runs")
    op.drop_index("ix_ai_prompt_runs_prompt_template_id", table_name="ai_prompt_runs")
    op.drop_index("ix_ai_prompt_runs_enquiry_id", table_name="ai_prompt_runs")
    op.drop_index("ix_ai_prompt_runs_restaurant_id", table_name="ai_prompt_runs")
    op.drop_index("ix_ai_prompt_runs_tenant_id", table_name="ai_prompt_runs")
    op.drop_table("ai_prompt_runs")

    op.drop_index("ix_tenant_prompt_configs_persona_id", table_name="tenant_prompt_configs")
    op.drop_index(
        "ix_tenant_prompt_configs_restaurant_id", table_name="tenant_prompt_configs"
    )
    op.drop_index("ix_tenant_prompt_configs_tenant_id", table_name="tenant_prompt_configs")
    op.drop_table("tenant_prompt_configs")

    op.drop_index(
        "ix_ai_prompt_versions_prompt_template_id", table_name="ai_prompt_versions"
    )
    op.drop_table("ai_prompt_versions")

    op.drop_index("ix_ai_prompt_templates_key", table_name="ai_prompt_templates")
    op.drop_index("ix_ai_prompt_templates_tenant_id", table_name="ai_prompt_templates")
    op.drop_table("ai_prompt_templates")
