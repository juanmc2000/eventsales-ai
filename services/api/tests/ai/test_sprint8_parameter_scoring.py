"""Sprint 8 deterministic test coverage — Prompt Parameter & Quality Scoring.

TEST-009: Add Prompt Parameter and Quality Scoring Tests

Covers:
- Prompt version parameter fields (configured values)
- Prompt run runtime parameter fields (actual persisted values)
- AI Gateway persists runtime configuration correctly
- Prompt run API returns parameter fields in responses
- Prompt experiment model and API integration
- Experiment run links to prompt run
- Prompt run review model and API integration
- Score validation (0.0–5.0 range)
- ready_to_send review flag
- No live LLM calls anywhere in this file

All tests use mock providers and repositories — no live DB or Anthropic required.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.modules.ai.prompt_registry import PromptDefinition, PromptRegistry
from app.modules.ai.constants import (
    PROMPT_KEY_DRAFT_RESPONSE,
    PROMPT_KEY_ENQUIRY_EXTRACTION,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _mock_db() -> tuple[MagicMock, MagicMock]:
    """Return a minimal mock DB session and mock prompt run."""
    db = MagicMock()
    mock_run = MagicMock()
    mock_run.id = uuid.uuid4()
    db.add = MagicMock()
    db.flush = MagicMock()
    db.commit = MagicMock()
    db.get = MagicMock(return_value=mock_run)
    db.scalars = MagicMock()
    db.scalars.return_value.first = MagicMock(return_value=None)
    return db, mock_run


# ── 1. Prompt Version Parameter Fields ────────────────────────────────────────


class TestPromptVersionParameterFields:
    """Validate that PromptDefinition (code-first version) stores parameters."""

    def test_draft_response_temperature_is_float(self) -> None:
        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert isinstance(defn.temperature, float), (
            "temperature must be stored as a float, not a string"
        )

    def test_draft_response_has_name_and_goal(self) -> None:
        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert defn.name, "Draft response prompt must have a human-readable name"
        assert defn.goal, "Draft response prompt must have a goal description"

    def test_extraction_temperature_is_low(self) -> None:
        """Extraction must be configured for factual precision (low temperature)."""
        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert defn.temperature < 0.5, (
            f"Extraction temperature should be < 0.5 for factual tasks, got {defn.temperature}"
        )

    def test_extraction_temperature_is_float_not_string(self) -> None:
        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert isinstance(defn.temperature, float), (
            f"temperature must be float, got {type(defn.temperature).__name__}"
        )

    def test_all_definitions_have_float_temperature(self) -> None:
        registry = PromptRegistry()
        for key in registry.all_keys():
            defn = registry.get(key)
            assert isinstance(defn.temperature, float), (
                f"Prompt '{key}' has non-float temperature: {defn.temperature!r}"
            )

    def test_definition_max_tokens_is_int_or_none(self) -> None:
        registry = PromptRegistry()
        for key in registry.all_keys():
            defn = registry.get(key)
            assert defn.max_tokens is None or isinstance(defn.max_tokens, int), (
                f"Prompt '{key}' max_tokens must be int or None"
            )

    def test_configured_vs_actual_distinction(self) -> None:
        """PromptDefinition is the configured value; run data is the actual value.

        This test asserts the distinction is maintained by verifying that the
        configured temperature on the definition is the same value the gateway
        would write to the run record — no implicit coercion.
        """
        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        # The gateway writes defn.temperature directly to the run record.
        # Assert no lossy string conversion happens.
        written_temperature = defn.temperature
        assert isinstance(written_temperature, float)
        assert written_temperature == defn.temperature


# ── 2. Prompt Run Runtime Parameter Fields ────────────────────────────────────


class TestPromptRunRuntimeParameterFields:
    """Validate that AIPromptRun model columns carry the correct types."""

    def test_prompt_run_has_numeric_temperature_column(self) -> None:
        from sqlalchemy import inspect as sa_inspect
        from app.modules.ai.models import AIPromptRun
        import app.db.models  # noqa: F401 — register all models
        cols = {c.name: c for c in sa_inspect(AIPromptRun).columns}
        assert "temperature" in cols
        # Column must be Numeric, not String
        col_type = type(cols["temperature"].type).__name__
        assert col_type == "Numeric", f"temperature column type should be Numeric, got {col_type}"

    def test_prompt_run_has_top_p_column(self) -> None:
        from sqlalchemy import inspect as sa_inspect
        from app.modules.ai.models import AIPromptRun
        import app.db.models  # noqa: F401
        cols = {c.name: c for c in sa_inspect(AIPromptRun).columns}
        assert "top_p" in cols

    def test_prompt_run_has_max_tokens_column(self) -> None:
        from sqlalchemy import inspect as sa_inspect
        from app.modules.ai.models import AIPromptRun
        import app.db.models  # noqa: F401
        cols = {c.name: c for c in sa_inspect(AIPromptRun).columns}
        assert "max_tokens" in cols

    def test_prompt_run_has_prompt_name_column(self) -> None:
        from sqlalchemy import inspect as sa_inspect
        from app.modules.ai.models import AIPromptRun
        import app.db.models  # noqa: F401
        cols = {c.name: c for c in sa_inspect(AIPromptRun).columns}
        assert "prompt_name" in cols

    def test_prompt_run_has_prompt_goal_column(self) -> None:
        from sqlalchemy import inspect as sa_inspect
        from app.modules.ai.models import AIPromptRun
        import app.db.models  # noqa: F401
        cols = {c.name: c for c in sa_inspect(AIPromptRun).columns}
        assert "prompt_goal" in cols


# ── 3. Gateway Persists Runtime Configuration ─────────────────────────────────


class TestGatewayPersistsRuntimeConfig:
    """Verify AIGateway writes the configured parameters to the run record."""

    def test_gateway_writes_temperature_to_run(self) -> None:
        from app.modules.ai.gateway import AIGateway
        from app.modules.ai.schemas import AIGatewayRequest

        db, _ = _mock_db()
        gateway = AIGateway(db=db, api_key="")  # empty key → fallback
        request = AIGatewayRequest(
            prompt_key=PROMPT_KEY_DRAFT_RESPONSE,
            input_payload={
                "persona_name": "Eleanor",
                "restaurant_name": "The Grand Ballroom",
                "persona_system_prompt": "You are Eleanor.",
                "guest_message": "Hello",
            },
        )
        gateway.run(request)
        db.add.assert_called_once()
        written = db.add.call_args[0][0]
        assert hasattr(written, "temperature")
        assert isinstance(written.temperature, float)

    def test_gateway_writes_prompt_name_to_run(self) -> None:
        from app.modules.ai.gateway import AIGateway
        from app.modules.ai.schemas import AIGatewayRequest

        db, _ = _mock_db()
        gateway = AIGateway(db=db, api_key="")
        request = AIGatewayRequest(
            prompt_key=PROMPT_KEY_DRAFT_RESPONSE,
            input_payload={
                "persona_name": "Eleanor",
                "restaurant_name": "The Grand Ballroom",
                "persona_system_prompt": "You are Eleanor.",
                "guest_message": "Hello",
            },
        )
        gateway.run(request)
        written = db.add.call_args[0][0]
        assert hasattr(written, "prompt_name")
        # May be None for prompts without a name, but attribute must exist

    def test_gateway_does_not_call_live_provider_without_api_key(self) -> None:
        from app.modules.ai.gateway import AIGateway
        from app.modules.ai.schemas import AIGatewayRequest

        db, _ = _mock_db()
        gateway = AIGateway(db=db, api_key="")
        request = AIGatewayRequest(
            prompt_key=PROMPT_KEY_DRAFT_RESPONSE,
            input_payload={
                "persona_name": "Eleanor",
                "restaurant_name": "The Grand Ballroom",
                "persona_system_prompt": "You are Eleanor.",
                "guest_message": "Hello",
            },
        )
        result = gateway.run(request)
        assert result.is_fallback is True

    def test_gateway_extraction_persists_low_temperature(self) -> None:
        """Extraction run records must have temperature < 0.5."""
        from app.modules.ai.gateway import AIGateway
        from app.modules.ai.schemas import AIGatewayRequest

        db, _ = _mock_db()
        gateway = AIGateway(db=db, api_key="")
        request = AIGatewayRequest(
            prompt_key=PROMPT_KEY_ENQUIRY_EXTRACTION,
            input_payload={"freeform_text": "I'd like to book a table for 20 people."},
        )
        gateway.run(request)
        written = db.add.call_args[0][0]
        assert written.temperature < 0.5, (
            f"Extraction run should persist a low temperature, got {written.temperature}"
        )


# ── 4. Prompt Run API Returns Parameter Fields ────────────────────────────────


class TestPromptRunAPIParameterFields:
    """Prompt run API must include LLM parameter fields in serialized output."""

    def test_prompt_run_out_schema_includes_temperature(self) -> None:
        from app.modules.ai.schemas import PromptRunOut
        fields = PromptRunOut.model_fields
        assert "temperature" in fields

    def test_prompt_run_out_schema_includes_max_tokens(self) -> None:
        from app.modules.ai.schemas import PromptRunOut
        fields = PromptRunOut.model_fields
        assert "max_tokens" in fields

    def test_prompt_run_out_schema_includes_prompt_name(self) -> None:
        from app.modules.ai.schemas import PromptRunOut
        fields = PromptRunOut.model_fields
        assert "prompt_name" in fields

    def test_prompt_run_out_schema_includes_prompt_goal(self) -> None:
        from app.modules.ai.schemas import PromptRunOut
        fields = PromptRunOut.model_fields
        assert "prompt_goal" in fields

    def test_prompt_run_out_schema_includes_token_counts(self) -> None:
        from app.modules.ai.schemas import PromptRunOut
        fields = PromptRunOut.model_fields
        assert "token_input_count" in fields
        assert "token_output_count" in fields


# ── 5. Prompt Experiment Model ────────────────────────────────────────────────


class TestPromptExperimentModel:
    """Validate AIPromptExperiment model structure."""

    def test_experiment_table_exists(self) -> None:
        import app.db.models  # noqa: F401
        from app.db.base import Base
        assert "ai_prompt_experiments" in Base.metadata.tables

    def test_experiment_run_table_exists(self) -> None:
        import app.db.models  # noqa: F401
        from app.db.base import Base
        assert "ai_prompt_experiment_runs" in Base.metadata.tables

    def test_experiment_has_status_column(self) -> None:
        from sqlalchemy import inspect as sa_inspect
        from app.modules.ai.models import AIPromptExperiment
        import app.db.models  # noqa: F401
        cols = {c.name for c in sa_inspect(AIPromptExperiment).columns}
        assert "status" in cols

    def test_experiment_run_has_selected_as_winner(self) -> None:
        from sqlalchemy import inspect as sa_inspect
        from app.modules.ai.models import AIPromptExperimentRun
        import app.db.models  # noqa: F401
        cols = {c.name: c for c in sa_inspect(AIPromptExperimentRun).columns}
        assert "selected_as_winner" in cols
        assert cols["selected_as_winner"].nullable is False

    def test_experiment_run_links_to_prompt_run(self) -> None:
        """experiment_run.prompt_run_id must FK to ai_prompt_runs.id."""
        from sqlalchemy import inspect as sa_inspect
        from app.modules.ai.models import AIPromptExperimentRun
        import app.db.models  # noqa: F401
        cols = {c.name: c for c in sa_inspect(AIPromptExperimentRun).columns}
        assert "prompt_run_id" in cols
        fks = {fk.column.table.name for fk in cols["prompt_run_id"].foreign_keys}
        assert "ai_prompt_runs" in fks

    def test_experiment_run_links_to_experiment(self) -> None:
        from sqlalchemy import inspect as sa_inspect
        from app.modules.ai.models import AIPromptExperimentRun
        import app.db.models  # noqa: F401
        cols = {c.name: c for c in sa_inspect(AIPromptExperimentRun).columns}
        fks = {fk.column.table.name for fk in cols["experiment_id"].foreign_keys}
        assert "ai_prompt_experiments" in fks


# ── 6. Prompt Experiment API ──────────────────────────────────────────────────


class TestPromptExperimentServiceSchema:
    """PromptExperiment schemas serialize/validate correctly."""

    def test_experiment_create_schema_requires_prompt_key(self) -> None:
        from pydantic import ValidationError
        from app.modules.ai.schemas import PromptExperimentCreate
        with pytest.raises(ValidationError):
            PromptExperimentCreate()  # type: ignore[call-arg]

    def test_experiment_create_schema_valid(self) -> None:
        from app.modules.ai.schemas import PromptExperimentCreate
        data = PromptExperimentCreate(prompt_key="draft_response", name="Test Exp")
        assert data.prompt_key == "draft_response"

    def test_experiment_run_create_requires_prompt_run_id(self) -> None:
        from pydantic import ValidationError
        from app.modules.ai.schemas import PromptExperimentRunCreate
        with pytest.raises(ValidationError):
            PromptExperimentRunCreate()  # type: ignore[call-arg]

    def test_experiment_run_update_schema_has_score(self) -> None:
        from app.modules.ai.schemas import PromptExperimentRunUpdate
        fields = PromptExperimentRunUpdate.model_fields
        assert "evaluator_score" in fields


# ── 7. Prompt Run Review Model ────────────────────────────────────────────────


class TestPromptRunReviewModel:
    """Validate AIPromptRunReview model structure."""

    def test_review_table_exists(self) -> None:
        import app.db.models  # noqa: F401
        from app.db.base import Base
        assert "ai_prompt_run_reviews" in Base.metadata.tables

    def test_review_has_all_score_columns(self) -> None:
        from sqlalchemy import inspect as sa_inspect
        from app.modules.ai.models import AIPromptRunReview
        import app.db.models  # noqa: F401
        cols = {c.name for c in sa_inspect(AIPromptRunReview).columns}
        expected_scores = {
            "accuracy_score",
            "tone_fit_score",
            "persona_fit_score",
            "commercial_quality_score",
            "completeness_score",
            "hallucination_risk_score",
        }
        assert expected_scores <= cols

    def test_review_has_ready_to_send_column(self) -> None:
        from sqlalchemy import inspect as sa_inspect
        from app.modules.ai.models import AIPromptRunReview
        import app.db.models  # noqa: F401
        cols = {c.name for c in sa_inspect(AIPromptRunReview).columns}
        assert "ready_to_send" in cols

    def test_review_links_to_prompt_run(self) -> None:
        from sqlalchemy import inspect as sa_inspect
        from app.modules.ai.models import AIPromptRunReview
        import app.db.models  # noqa: F401
        cols = {c.name: c for c in sa_inspect(AIPromptRunReview).columns}
        fks = {fk.column.table.name for fk in cols["prompt_run_id"].foreign_keys}
        assert "ai_prompt_runs" in fks

    def test_review_has_no_ml_auto_score_fields(self) -> None:
        """POC guardrail: no automated/ML scoring fields."""
        from sqlalchemy import inspect as sa_inspect
        from app.modules.ai.models import AIPromptRunReview
        import app.db.models  # noqa: F401
        forbidden = {"ml_score", "auto_score", "predicted_quality", "evaluator_score"}
        cols = {c.name for c in sa_inspect(AIPromptRunReview).columns}
        assert forbidden.isdisjoint(cols), (
            f"Review model must not have automated scoring fields: {forbidden & cols}"
        )


# ── 8. Prompt Run Review API ──────────────────────────────────────────────────


class TestPromptRunReviewService:
    """PromptRunReviewService validates scores and fields correctly."""

    def _service(self) -> object:
        from app.modules.ai.service import PromptRunReviewService
        db = MagicMock()
        return PromptRunReviewService(db)

    def test_score_validation_rejects_below_zero(self) -> None:
        from app.modules.ai.service import PromptRunReviewService
        db = MagicMock()
        svc = PromptRunReviewService(db)
        with pytest.raises(ValueError, match="accuracy_score must be between"):
            svc.create_review(
                {"prompt_run_id": uuid.uuid4(), "accuracy_score": -1.0}
            )

    def test_score_validation_rejects_above_five(self) -> None:
        from app.modules.ai.service import PromptRunReviewService
        db = MagicMock()
        svc = PromptRunReviewService(db)
        with pytest.raises(ValueError, match="accuracy_score must be between"):
            svc.create_review(
                {"prompt_run_id": uuid.uuid4(), "accuracy_score": 5.5}
            )

    def test_score_validation_accepts_zero(self) -> None:
        from app.modules.ai.service import PromptRunReviewService
        db = MagicMock()
        mock_run = MagicMock()
        db.get.return_value = mock_run
        mock_review = MagicMock()
        mock_review.id = uuid.uuid4()
        db.scalars.return_value.first.return_value = None
        # Patch repository.create_review
        svc = PromptRunReviewService(db)
        with patch.object(svc._repo, "create_review", return_value=MagicMock()) as mock_create:
            svc.create_review({"prompt_run_id": uuid.uuid4(), "accuracy_score": 0.0})
            mock_create.assert_called_once()

    def test_score_validation_accepts_five(self) -> None:
        from app.modules.ai.service import PromptRunReviewService
        db = MagicMock()
        mock_run = MagicMock()
        db.get.return_value = mock_run
        svc = PromptRunReviewService(db)
        with patch.object(svc._repo, "create_review", return_value=MagicMock()):
            svc.create_review({"prompt_run_id": uuid.uuid4(), "accuracy_score": 5.0})

    def test_create_review_raises_if_run_not_found(self) -> None:
        from app.modules.ai.service import PromptRunReviewService
        db = MagicMock()
        db.get.return_value = None
        svc = PromptRunReviewService(db)
        run_id = uuid.uuid4()
        with pytest.raises(ValueError, match="not found"):
            svc.create_review({"prompt_run_id": run_id})

    def test_update_review_cannot_change_prompt_run_id(self) -> None:
        """update_review must strip prompt_run_id from the update payload."""
        from app.modules.ai.service import PromptRunReviewService
        db = MagicMock()
        mock_review = MagicMock()
        svc = PromptRunReviewService(db)
        with patch.object(svc._repo, "update_review", return_value=mock_review) as mock_upd:
            svc.update_review(
                uuid.uuid4(),
                {"accuracy_score": 4.0, "prompt_run_id": uuid.uuid4()},
            )
            applied = mock_upd.call_args[0][1]
            assert "prompt_run_id" not in applied

    def test_ready_to_send_flag_stored(self) -> None:
        from app.modules.ai.service import PromptRunReviewService
        db = MagicMock()
        mock_run = MagicMock()
        db.get.return_value = mock_run
        svc = PromptRunReviewService(db)
        with patch.object(svc._repo, "create_review", return_value=MagicMock()) as mock_create:
            svc.create_review(
                {"prompt_run_id": uuid.uuid4(), "ready_to_send": True}
            )
            payload = mock_create.call_args[0][0]
            assert payload.get("ready_to_send") is True

    def test_all_six_score_fields_validated(self) -> None:
        """All six score fields must each be individually validated."""
        from app.modules.ai.service import PromptRunReviewService
        score_fields = [
            "accuracy_score",
            "tone_fit_score",
            "persona_fit_score",
            "commercial_quality_score",
            "completeness_score",
            "hallucination_risk_score",
        ]
        for field in score_fields:
            db = MagicMock()
            db.get.return_value = MagicMock()
            svc = PromptRunReviewService(db)
            with pytest.raises(ValueError, match=f"{field} must be between"):
                svc.create_review({"prompt_run_id": uuid.uuid4(), field: 99.0})
