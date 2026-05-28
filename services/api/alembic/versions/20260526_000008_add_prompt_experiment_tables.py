"""Add prompt experiment tables.

Revision ID: 20260526_000008
Revises: 20260525_000007
Create Date: 2026-05-26 00:00:08

Tables added:
  ai_prompt_experiments      — experiment metadata (one per prompt comparison)
  ai_prompt_experiment_runs  — one row per variant run within an experiment
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "20260526_000008"
down_revision: Union[str, None] = "20260525_000007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # ai_prompt_experiments
    # ------------------------------------------------------------------
    op.create_table(
        "ai_prompt_experiments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(100), nullable=True),
        sa.Column("prompt_key", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("goal", sa.String(500), nullable=True),
        sa.Column(
            "baseline_prompt_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_prompt_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_ai_prompt_experiments_tenant_id", "ai_prompt_experiments", ["tenant_id"]
    )
    op.create_index(
        "ix_ai_prompt_experiments_prompt_key", "ai_prompt_experiments", ["prompt_key"]
    )

    # ------------------------------------------------------------------
    # ai_prompt_experiment_runs
    # ------------------------------------------------------------------
    op.create_table(
        "ai_prompt_experiment_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "experiment_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_prompt_experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prompt_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_prompt_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("variant_name", sa.String(100), nullable=False),
        sa.Column("temperature", sa.Numeric(4, 2), nullable=True),
        sa.Column("top_p", sa.Numeric(4, 2), nullable=True),
        sa.Column("top_k", sa.Integer, nullable=True),
        sa.Column("max_tokens", sa.Integer, nullable=True),
        sa.Column("evaluator_score", sa.Integer, nullable=True),
        sa.Column("reviewer_notes", sa.String(1000), nullable=True),
        sa.Column(
            "selected_as_winner", sa.Boolean, nullable=False, server_default="false"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_ai_prompt_experiment_runs_experiment_id",
        "ai_prompt_experiment_runs",
        ["experiment_id"],
    )
    op.create_index(
        "ix_ai_prompt_experiment_runs_prompt_run_id",
        "ai_prompt_experiment_runs",
        ["prompt_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ai_prompt_experiment_runs_prompt_run_id",
        table_name="ai_prompt_experiment_runs",
    )
    op.drop_index(
        "ix_ai_prompt_experiment_runs_experiment_id",
        table_name="ai_prompt_experiment_runs",
    )
    op.drop_table("ai_prompt_experiment_runs")

    op.drop_index(
        "ix_ai_prompt_experiments_prompt_key", table_name="ai_prompt_experiments"
    )
    op.drop_index(
        "ix_ai_prompt_experiments_tenant_id", table_name="ai_prompt_experiments"
    )
    op.drop_table("ai_prompt_experiments")
