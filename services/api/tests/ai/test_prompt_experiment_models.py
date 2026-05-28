"""Model and schema tests for prompt experiment tables (DATA-017).

Verifies that:
- AIPromptExperiment and AIPromptExperimentRun classes import cleanly
- Both tables appear in Base.metadata
- Required columns exist on each model
- Pydantic schemas can be instantiated
"""

import uuid
from datetime import datetime, timezone


def test_experiment_model_classes_importable() -> None:
    """AIPromptExperiment and AIPromptExperimentRun can be imported."""
    from app.modules.ai.models import (  # noqa: F401
        AIPromptExperiment,
        AIPromptExperimentRun,
    )


def test_experiment_tables_in_metadata() -> None:
    """Both experiment tables are registered in Base.metadata."""
    import app.db.models  # noqa: F401

    from app.db.base import Base

    expected = {"ai_prompt_experiments", "ai_prompt_experiment_runs"}
    actual = set(Base.metadata.tables.keys())
    missing = expected - actual
    assert not missing, f"Missing experiment tables: {missing}"


def test_prompt_experiment_columns() -> None:
    """AIPromptExperiment has all required columns."""
    from app.modules.ai.models import AIPromptExperiment

    cols = {c.name for c in AIPromptExperiment.__table__.columns}
    assert "id" in cols
    assert "tenant_id" in cols
    assert "prompt_key" in cols
    assert "name" in cols
    assert "goal" in cols
    assert "baseline_prompt_version_id" in cols
    assert "status" in cols
    assert "notes" in cols
    assert "created_at" in cols


def test_prompt_experiment_run_columns() -> None:
    """AIPromptExperimentRun has all required columns."""
    from app.modules.ai.models import AIPromptExperimentRun

    cols = {c.name for c in AIPromptExperimentRun.__table__.columns}
    assert "id" in cols
    assert "experiment_id" in cols
    assert "prompt_run_id" in cols
    assert "variant_name" in cols
    assert "temperature" in cols
    assert "top_p" in cols
    assert "top_k" in cols
    assert "max_tokens" in cols
    assert "evaluator_score" in cols
    assert "reviewer_notes" in cols
    assert "selected_as_winner" in cols
    assert "created_at" in cols


def test_experiment_run_links_to_experiment() -> None:
    """AIPromptExperimentRun.experiment_id has a FK to ai_prompt_experiments."""
    from app.modules.ai.models import AIPromptExperimentRun

    fk_targets = {
        fk.column.table.name
        for fk in AIPromptExperimentRun.__table__.foreign_keys
    }
    assert "ai_prompt_experiments" in fk_targets


def test_experiment_run_links_to_prompt_run() -> None:
    """AIPromptExperimentRun.prompt_run_id has a FK to ai_prompt_runs."""
    from app.modules.ai.models import AIPromptExperimentRun

    fk_targets = {
        fk.column.table.name
        for fk in AIPromptExperimentRun.__table__.foreign_keys
    }
    assert "ai_prompt_runs" in fk_targets


def test_experiment_baseline_fk_is_nullable() -> None:
    """baseline_prompt_version_id is nullable (baseline is optional)."""
    from app.modules.ai.models import AIPromptExperiment

    col = AIPromptExperiment.__table__.c["baseline_prompt_version_id"]
    assert col.nullable is True


def test_selected_as_winner_defaults_false() -> None:
    """selected_as_winner is non-nullable and has a Python-side default of False."""
    from app.modules.ai.models import AIPromptExperimentRun

    col = AIPromptExperimentRun.__table__.c["selected_as_winner"]
    assert col.nullable is False


# ── Schema tests ─────────────────────────────────────────────────────────────


def test_prompt_experiment_out_schema() -> None:
    """PromptExperimentOut can be constructed from attribute dict."""
    from app.modules.ai.schemas import PromptExperimentOut

    now = datetime.now(timezone.utc)
    exp = PromptExperimentOut(
        id=uuid.uuid4(),
        tenant_id=None,
        prompt_key="draft_response",
        name="Temperature Comparison",
        goal="Compare 0.3 vs 0.7 temperature on draft quality.",
        baseline_prompt_version_id=None,
        status="active",
        notes=None,
        created_at=now,
    )
    assert exp.prompt_key == "draft_response"
    assert exp.status == "active"


def test_prompt_experiment_run_out_schema() -> None:
    """PromptExperimentRunOut can be constructed with all fields."""
    from app.modules.ai.schemas import PromptExperimentRunOut

    now = datetime.now(timezone.utc)
    run = PromptExperimentRunOut(
        id=uuid.uuid4(),
        experiment_id=uuid.uuid4(),
        prompt_run_id=uuid.uuid4(),
        variant_name="temperature_0.3",
        temperature=0.3,
        top_p=None,
        top_k=None,
        max_tokens=800,
        evaluator_score=4,
        reviewer_notes="Good tone, slight verbosity.",
        selected_as_winner=False,
        created_at=now,
    )
    assert run.variant_name == "temperature_0.3"
    assert run.evaluator_score == 4
    assert run.selected_as_winner is False


def test_prompt_experiment_create_schema() -> None:
    """PromptExperimentCreate validates required fields."""
    from app.modules.ai.schemas import PromptExperimentCreate

    exp = PromptExperimentCreate(
        prompt_key="draft_response",
        name="My Experiment",
    )
    assert exp.prompt_key == "draft_response"
    assert exp.goal is None
    assert exp.baseline_prompt_version_id is None
