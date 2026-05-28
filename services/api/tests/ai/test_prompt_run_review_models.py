"""Model and schema tests for prompt run quality review (DATA-018).

Verifies that:
- AIPromptRunReview imports cleanly
- The table appears in Base.metadata
- All required columns exist
- FK to ai_prompt_runs is present and correct
- Pydantic schemas can be instantiated
"""

import uuid
from datetime import datetime, timezone


def test_review_model_importable() -> None:
    """AIPromptRunReview can be imported."""
    from app.modules.ai.models import AIPromptRunReview  # noqa: F401


def test_review_table_in_metadata() -> None:
    """ai_prompt_run_reviews table is registered in Base.metadata."""
    import app.db.models  # noqa: F401

    from app.db.base import Base

    assert "ai_prompt_run_reviews" in Base.metadata.tables


def test_review_columns() -> None:
    """AIPromptRunReview has all required columns."""
    from app.modules.ai.models import AIPromptRunReview

    cols = {c.name for c in AIPromptRunReview.__table__.columns}
    assert "id" in cols
    assert "prompt_run_id" in cols
    assert "tenant_id" in cols
    assert "reviewer_user_id" in cols
    assert "accuracy_score" in cols
    assert "tone_fit_score" in cols
    assert "persona_fit_score" in cols
    assert "commercial_quality_score" in cols
    assert "completeness_score" in cols
    assert "hallucination_risk_score" in cols
    assert "ready_to_send" in cols
    assert "reviewer_notes" in cols
    assert "created_at" in cols
    assert "updated_at" in cols


def test_review_links_to_prompt_run() -> None:
    """AIPromptRunReview.prompt_run_id has a FK to ai_prompt_runs."""
    from app.modules.ai.models import AIPromptRunReview

    fk_targets = {
        fk.column.table.name
        for fk in AIPromptRunReview.__table__.foreign_keys
    }
    assert "ai_prompt_runs" in fk_targets


def test_score_columns_are_nullable() -> None:
    """All score columns are nullable — reviewers may score partial dimensions."""
    from app.modules.ai.models import AIPromptRunReview

    nullable_score_cols = [
        "accuracy_score", "tone_fit_score", "persona_fit_score",
        "commercial_quality_score", "completeness_score", "hallucination_risk_score",
    ]
    for col_name in nullable_score_cols:
        col = AIPromptRunReview.__table__.c[col_name]
        assert col.nullable is True, f"{col_name} should be nullable"


def test_ready_to_send_is_nullable() -> None:
    """ready_to_send is nullable — not set until reviewer makes judgment."""
    from app.modules.ai.models import AIPromptRunReview

    col = AIPromptRunReview.__table__.c["ready_to_send"]
    assert col.nullable is True


def test_no_ml_scoring_fields() -> None:
    """Review model has no automated/ML scoring fields (POC guardrail)."""
    from app.modules.ai.models import AIPromptRunReview

    cols = {c.name for c in AIPromptRunReview.__table__.columns}
    assert "ml_score" not in cols
    assert "auto_score" not in cols
    assert "predicted_quality" not in cols


# ── Schema tests ─────────────────────────────────────────────────────────────


def test_prompt_run_review_out_schema() -> None:
    """PromptRunReviewOut can be constructed with all fields."""
    from app.modules.ai.schemas import PromptRunReviewOut

    now = datetime.now(timezone.utc)
    review = PromptRunReviewOut(
        id=uuid.uuid4(),
        prompt_run_id=uuid.uuid4(),
        tenant_id=None,
        reviewer_user_id="admin",
        accuracy_score=4.5,
        tone_fit_score=4.0,
        persona_fit_score=5.0,
        commercial_quality_score=3.5,
        completeness_score=4.0,
        hallucination_risk_score=0.5,
        ready_to_send=True,
        reviewer_notes="Good response, minor tone improvement suggested.",
        created_at=now,
        updated_at=now,
    )
    assert review.accuracy_score == 4.5
    assert review.ready_to_send is True


def test_prompt_run_review_create_schema() -> None:
    """PromptRunReviewCreate validates required prompt_run_id."""
    from app.modules.ai.schemas import PromptRunReviewCreate

    review = PromptRunReviewCreate(
        prompt_run_id=uuid.uuid4(),
        accuracy_score=3.0,
        ready_to_send=False,
    )
    assert review.accuracy_score == 3.0
    assert review.tone_fit_score is None
    assert review.ready_to_send is False


def test_prompt_run_review_create_all_nullable() -> None:
    """PromptRunReviewCreate accepts only prompt_run_id — all scores optional."""
    from app.modules.ai.schemas import PromptRunReviewCreate

    review = PromptRunReviewCreate(prompt_run_id=uuid.uuid4())
    assert review.accuracy_score is None
    assert review.ready_to_send is None


def test_prompt_run_review_update_schema() -> None:
    """PromptRunReviewUpdate can be created with partial updates."""
    from app.modules.ai.schemas import PromptRunReviewUpdate

    update = PromptRunReviewUpdate(ready_to_send=True, reviewer_notes="Updated review.")
    assert update.ready_to_send is True
    assert update.accuracy_score is None
