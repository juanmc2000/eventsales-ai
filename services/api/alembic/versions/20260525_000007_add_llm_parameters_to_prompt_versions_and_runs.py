"""Add LLM parameter fields to prompt versions and prompt runs.

Revision ID: 20260525_000007
Revises: 20260524_000006
Create Date: 2026-05-25 00:00:07

Changes:
  ai_prompt_versions  — add prompt_key, prompt_name, goal, top_p, top_k;
                        change temperature from String(10) to NUMERIC(4,2)
  ai_prompt_runs      — add temperature, top_p, top_k, max_tokens,
                        prompt_name, prompt_goal
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260525_000007"
down_revision: Union[str, None] = "20260524_000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # ai_prompt_versions: add prompt_key, prompt_name, goal, top_p, top_k
    # Also migrate temperature from String(10) -> NUMERIC(4,2)
    # ------------------------------------------------------------------
    op.add_column(
        "ai_prompt_versions",
        sa.Column("prompt_key", sa.String(100), nullable=True),
    )
    op.add_column(
        "ai_prompt_versions",
        sa.Column("prompt_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "ai_prompt_versions",
        sa.Column("goal", sa.Text, nullable=True),
    )
    op.add_column(
        "ai_prompt_versions",
        sa.Column("top_p", sa.Numeric(4, 2), nullable=True),
    )
    op.add_column(
        "ai_prompt_versions",
        sa.Column("top_k", sa.Integer, nullable=True),
    )
    # Migrate temperature column from String(10) to NUMERIC(4,2)
    op.alter_column(
        "ai_prompt_versions",
        "temperature",
        type_=sa.Numeric(4, 2),
        existing_type=sa.String(10),
        existing_nullable=True,
        postgresql_using="temperature::numeric",
    )
    op.create_index(
        "ix_ai_prompt_versions_prompt_key", "ai_prompt_versions", ["prompt_key"]
    )

    # ------------------------------------------------------------------
    # ai_prompt_runs: add runtime LLM parameters + prompt_name, prompt_goal
    # ------------------------------------------------------------------
    op.add_column(
        "ai_prompt_runs",
        sa.Column("prompt_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "ai_prompt_runs",
        sa.Column("prompt_goal", sa.Text, nullable=True),
    )
    op.add_column(
        "ai_prompt_runs",
        sa.Column("temperature", sa.Numeric(4, 2), nullable=True),
    )
    op.add_column(
        "ai_prompt_runs",
        sa.Column("top_p", sa.Numeric(4, 2), nullable=True),
    )
    op.add_column(
        "ai_prompt_runs",
        sa.Column("top_k", sa.Integer, nullable=True),
    )
    op.add_column(
        "ai_prompt_runs",
        sa.Column("max_tokens", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    # ------------------------------------------------------------------
    # ai_prompt_runs: remove added columns
    # ------------------------------------------------------------------
    op.drop_column("ai_prompt_runs", "max_tokens")
    op.drop_column("ai_prompt_runs", "top_k")
    op.drop_column("ai_prompt_runs", "top_p")
    op.drop_column("ai_prompt_runs", "temperature")
    op.drop_column("ai_prompt_runs", "prompt_goal")
    op.drop_column("ai_prompt_runs", "prompt_name")

    # ------------------------------------------------------------------
    # ai_prompt_versions: remove added columns + revert temperature type
    # ------------------------------------------------------------------
    op.drop_index("ix_ai_prompt_versions_prompt_key", table_name="ai_prompt_versions")
    op.alter_column(
        "ai_prompt_versions",
        "temperature",
        type_=sa.String(10),
        existing_type=sa.Numeric(4, 2),
        existing_nullable=True,
        postgresql_using="temperature::text",
    )
    op.drop_column("ai_prompt_versions", "top_k")
    op.drop_column("ai_prompt_versions", "top_p")
    op.drop_column("ai_prompt_versions", "goal")
    op.drop_column("ai_prompt_versions", "prompt_name")
    op.drop_column("ai_prompt_versions", "prompt_key")
