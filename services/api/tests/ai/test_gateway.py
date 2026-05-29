"""Tests for the AI Gateway service (AI-004).

All tests are smoke/unit tests — no DB or Anthropic API required.
The database session is mocked with MagicMock.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.modules.ai.constants import (
    RUN_STATUS_ERROR,
    RUN_STATUS_FALLBACK,
    RUN_STATUS_SUCCESS,
    VALIDATION_SKIPPED,
)
from app.modules.ai.gateway import AIGateway
from app.modules.ai.schemas import AIGatewayRequest, AIGatewayResult


def _mock_run(run_id: uuid.UUID | None = None) -> MagicMock:
    """Return a MagicMock that looks like an AIPromptRun."""
    run = MagicMock()
    run.id = run_id or uuid.uuid4()
    return run


def _mock_db(run_id: uuid.UUID | None = None) -> MagicMock:
    """Return a MagicMock session whose repo.create_run returns a mock run."""
    db = MagicMock()
    mock_run = _mock_run(run_id)
    # The repository does db.add + db.flush + returns the model
    db.add = MagicMock()
    db.flush = MagicMock()
    db.get = MagicMock(return_value=mock_run)
    return db, mock_run


# ── Schema tests ───────────────────────────────────────────────────────────

class TestAIGatewaySchemas:
    def test_gateway_request_creation(self) -> None:
        req = AIGatewayRequest(
            prompt_key="draft_response",
            input_payload={"persona_name": "Eleanor"},
            tenant_id="default",
        )
        assert req.prompt_key == "draft_response"
        assert req.tenant_id == "default"
        assert req.restaurant_id is None

    def test_gateway_result_creation(self) -> None:
        result = AIGatewayResult(
            run_id=uuid.uuid4(),
            prompt_key="draft_response",
            prompt_version=1,
            model_name="fallback",
            model_provider="fallback",
            rendered_system_prompt=None,
            rendered_user_prompt=None,
            raw_response=None,
            is_fallback=True,
            fallback_reason="no_api_key",
            validation_status=VALIDATION_SKIPPED,
            latency_ms=0,
            status=RUN_STATUS_FALLBACK,
        )
        assert result.is_fallback is True
        assert result.raw_response is None


# ── Fallback path ──────────────────────────────────────────────────────────

class TestAIGatewayFallback:
    def test_fallback_run_returns_result(self) -> None:
        db, mock_run = _mock_db()
        gateway = AIGateway(db=db, api_key="")  # No key → fallback
        request = AIGatewayRequest(
            prompt_key="draft_response",
            input_payload={"persona_name": "Eleanor", "restaurant_name": "The Grand",
                           "persona_tone": "warm", "persona_style": "concise",
                           "guest_first_name": "Alice", "guest_last_name": "Smith",
                           "persona_system_prompt": "You are helpful."},
        )
        result = gateway.run(request)
        assert result is not None
        assert result.is_fallback is True
        assert result.status == RUN_STATUS_FALLBACK
        assert result.raw_response is None

    def test_fallback_run_creates_db_record(self) -> None:
        db, mock_run = _mock_db()
        gateway = AIGateway(db=db, api_key="")
        request = AIGatewayRequest(
            prompt_key="draft_response",
            input_payload={"persona_name": "Eleanor", "restaurant_name": "The Grand",
                           "persona_tone": "warm", "persona_style": "concise",
                           "guest_first_name": "Alice", "guest_last_name": "Smith",
                           "persona_system_prompt": "You are helpful."},
        )
        gateway.run(request)
        # The session should have received add() for the run row
        db.add.assert_called()

    def test_fallback_result_has_correct_prompt_key(self) -> None:
        db, _ = _mock_db()
        gateway = AIGateway(db=db, api_key="")
        request = AIGatewayRequest(
            prompt_key="draft_response",
            input_payload={"persona_name": "Eleanor", "restaurant_name": "The Grand",
                           "persona_tone": "warm", "persona_style": "concise",
                           "guest_first_name": "Alice", "guest_last_name": "Smith",
                           "persona_system_prompt": "You are helpful."},
        )
        result = gateway.run(request)
        assert result.prompt_key == "draft_response"
        assert result.prompt_version >= 1

    def test_fallback_validation_status_is_skipped(self) -> None:
        db, _ = _mock_db()
        gateway = AIGateway(db=db, api_key="")
        request = AIGatewayRequest(
            prompt_key="draft_response",
            input_payload={"persona_name": "Eleanor", "restaurant_name": "The Grand",
                           "persona_tone": "warm", "persona_style": "concise",
                           "guest_first_name": "Alice", "guest_last_name": "Smith",
                           "persona_system_prompt": "You are helpful."},
        )
        result = gateway.run(request)
        assert result.validation_status == VALIDATION_SKIPPED


# ── Unknown prompt key ────────────────────────────────────────────────────

class TestAIGatewayErrors:
    def test_unknown_prompt_key_returns_error_result(self) -> None:
        db, _ = _mock_db()
        gateway = AIGateway(db=db, api_key="")
        request = AIGatewayRequest(
            prompt_key="nonexistent_key",
            input_payload={},
        )
        result = gateway.run(request)
        assert result.status == RUN_STATUS_ERROR
        assert result.is_fallback is True
        assert result.error_message is not None

    def test_missing_required_variables_returns_error_result(self) -> None:
        db, _ = _mock_db()
        # Supply an API key so we try to render (and fail)
        with patch("app.modules.ai.gateway.make_provider") as mock_make:
            mock_provider = MagicMock()
            mock_provider.model_name = "claude-haiku-4-5-20251001"
            mock_make.return_value = (mock_provider, False)  # not fallback
            gateway = AIGateway(db=db, api_key="fake_key")

        request = AIGatewayRequest(
            prompt_key="draft_response",
            input_payload={},  # Missing required variables
        )
        result = gateway.run(request)
        assert result.status == RUN_STATUS_ERROR


# ── Live provider path (mocked) ───────────────────────────────────────────

class TestAIGatewayLiveProvider:
    def test_successful_provider_call_returns_result(self) -> None:
        db, mock_run = _mock_db()
        run_id = uuid.uuid4()
        mock_run.id = run_id
        db.get.return_value = mock_run

        with patch("app.modules.ai.gateway.make_provider") as mock_make:
            mock_provider = MagicMock()
            mock_provider.model_name = "claude-haiku-4-5-20251001"
            mock_provider.generate_from_prompts.return_value = "Dear Alice, thank you."
            mock_make.return_value = (mock_provider, False)  # not fallback

            gateway = AIGateway(db=db, api_key="fake_key")

        request = AIGatewayRequest(
            prompt_key="draft_response",
            input_payload={
                "persona_name": "Eleanor",
                "restaurant_name": "The Grand",
                "persona_tone": "warm and formal",
                "persona_style": "concise",
                "guest_first_name": "Alice",
                "guest_last_name": "Smith",
                "persona_system_prompt": "You are a professional.",
            },
        )
        result = gateway.run(request)
        assert result.status == RUN_STATUS_SUCCESS
        assert result.raw_response == "Dear Alice, thank you."
        assert result.is_fallback is False
        assert result.rendered_system_prompt is not None
        assert result.rendered_user_prompt is not None

    def test_provider_exception_returns_error_status(self) -> None:
        db, mock_run = _mock_db()

        with patch("app.modules.ai.gateway.make_provider") as mock_make:
            mock_provider = MagicMock()
            mock_provider.model_name = "claude-haiku-4-5-20251001"
            mock_provider.generate_from_prompts.side_effect = RuntimeError("API down")
            mock_make.return_value = (mock_provider, False)

            gateway = AIGateway(db=db, api_key="fake_key")

        request = AIGatewayRequest(
            prompt_key="draft_response",
            input_payload={
                "persona_name": "Eleanor",
                "restaurant_name": "The Grand",
                "persona_tone": "warm",
                "persona_style": "concise",
                "guest_first_name": "Alice",
                "guest_last_name": "Smith",
                "persona_system_prompt": "You are a professional.",
            },
        )
        result = gateway.run(request)
        assert result.status == RUN_STATUS_ERROR
        assert result.error_message is not None
        assert "API down" in result.error_message

    def test_successful_run_stores_rendered_prompts(self) -> None:
        db, mock_run = _mock_db()

        with patch("app.modules.ai.gateway.make_provider") as mock_make:
            mock_provider = MagicMock()
            mock_provider.model_name = "claude-haiku-4-5-20251001"
            mock_provider.generate_from_prompts.return_value = "Response text."
            mock_make.return_value = (mock_provider, False)

            gateway = AIGateway(db=db, api_key="fake_key")

        request = AIGatewayRequest(
            prompt_key="draft_response",
            input_payload={
                "persona_name": "Eleanor",
                "restaurant_name": "The Grand",
                "persona_tone": "warm",
                "persona_style": "concise",
                "guest_first_name": "Alice",
                "guest_last_name": "Smith",
                "persona_system_prompt": "You are a professional.",
            },
        )
        result = gateway.run(request)
        # Rendered prompts are stored in result
        assert result.rendered_system_prompt is not None
        assert "Eleanor" in result.rendered_system_prompt
        assert result.rendered_user_prompt is not None
        assert "Alice" in result.rendered_user_prompt

    def test_latency_is_recorded(self) -> None:
        db, mock_run = _mock_db()

        with patch("app.modules.ai.gateway.make_provider") as mock_make:
            mock_provider = MagicMock()
            mock_provider.model_name = "claude-haiku-4-5-20251001"
            mock_provider.generate_from_prompts.return_value = "OK"
            mock_make.return_value = (mock_provider, False)

            gateway = AIGateway(db=db, api_key="fake_key")

        request = AIGatewayRequest(
            prompt_key="draft_response",
            input_payload={
                "persona_name": "Eleanor",
                "restaurant_name": "The Grand",
                "persona_tone": "warm",
                "persona_style": "concise",
                "guest_first_name": "Alice",
                "guest_last_name": "Smith",
                "persona_system_prompt": "You are a professional.",
            },
        )
        result = gateway.run(request)
        assert isinstance(result.latency_ms, int)
        assert result.latency_ms >= 0


# ── LLM parameter persistence ────────────────────────────────────────────

class TestAIGatewayParameterPersistence:
    """Verify that LLM generation parameters from the prompt definition are
    stored in the run record and forwarded to the provider."""

    _DRAFT_PAYLOAD = {
        "persona_name": "Eleanor",
        "restaurant_name": "The Grand",
        "persona_tone": "warm",
        "persona_style": "concise",
        "guest_first_name": "Alice",
        "guest_last_name": "Smith",
        "persona_system_prompt": "You are a professional.",
    }

    def test_run_record_includes_temperature_from_definition(self) -> None:
        """Gateway stores temperature from prompt definition in the run row."""
        db, mock_run = _mock_db()

        with patch("app.modules.ai.gateway.make_provider") as mock_make:
            mock_provider = MagicMock()
            mock_provider.model_name = "claude-haiku-4-5-20251001"
            mock_provider.generate_from_prompts.return_value = "OK"
            mock_make.return_value = (mock_provider, False)
            gateway = AIGateway(db=db, api_key="fake_key")

        gateway.run(AIGatewayRequest(
            prompt_key="draft_response",
            input_payload=self._DRAFT_PAYLOAD,
        ))

        # Inspect the object added to the session
        added = db.add.call_args[0][0]
        assert hasattr(added, "temperature")
        assert added.temperature is not None
        assert float(added.temperature) >= 0.0

    def test_run_record_includes_max_tokens_from_definition(self) -> None:
        """Gateway stores max_tokens from prompt definition in the run row."""
        db, mock_run = _mock_db()

        with patch("app.modules.ai.gateway.make_provider") as mock_make:
            mock_provider = MagicMock()
            mock_provider.model_name = "claude-haiku-4-5-20251001"
            mock_provider.generate_from_prompts.return_value = "OK"
            mock_make.return_value = (mock_provider, False)
            gateway = AIGateway(db=db, api_key="fake_key")

        gateway.run(AIGatewayRequest(
            prompt_key="draft_response",
            input_payload=self._DRAFT_PAYLOAD,
        ))

        added = db.add.call_args[0][0]
        assert hasattr(added, "max_tokens")
        assert added.max_tokens is not None
        assert added.max_tokens > 0

    def test_run_record_includes_prompt_name_and_goal(self) -> None:
        """Gateway stores prompt name and goal in the run row."""
        db, mock_run = _mock_db()

        with patch("app.modules.ai.gateway.make_provider") as mock_make:
            mock_provider = MagicMock()
            mock_provider.model_name = "claude-haiku-4-5-20251001"
            mock_provider.generate_from_prompts.return_value = "OK"
            mock_make.return_value = (mock_provider, False)
            gateway = AIGateway(db=db, api_key="fake_key")

        gateway.run(AIGatewayRequest(
            prompt_key="draft_response",
            input_payload=self._DRAFT_PAYLOAD,
        ))

        added = db.add.call_args[0][0]
        assert hasattr(added, "prompt_name")
        assert hasattr(added, "prompt_goal")
        assert added.prompt_name is not None
        assert added.prompt_goal is not None

    def test_provider_called_with_runtime_params(self) -> None:
        """Provider.generate_from_prompts receives max_tokens and temperature."""
        db, mock_run = _mock_db()

        with patch("app.modules.ai.gateway.make_provider") as mock_make:
            mock_provider = MagicMock()
            mock_provider.model_name = "claude-haiku-4-5-20251001"
            mock_provider.generate_from_prompts.return_value = "OK"
            mock_make.return_value = (mock_provider, False)
            gateway = AIGateway(db=db, api_key="fake_key")

        gateway.run(AIGatewayRequest(
            prompt_key="draft_response",
            input_payload=self._DRAFT_PAYLOAD,
        ))

        call_kwargs = mock_provider.generate_from_prompts.call_args.kwargs
        assert "max_tokens" in call_kwargs
        assert "temperature" in call_kwargs
        assert call_kwargs["max_tokens"] > 0
        assert 0.0 <= call_kwargs["temperature"] <= 2.0

    def test_fallback_run_still_stores_llm_params(self) -> None:
        """Fallback runs log the configured parameters even though no LLM is called."""
        db, mock_run = _mock_db()
        gateway = AIGateway(db=db, api_key="")  # fallback

        gateway.run(AIGatewayRequest(
            prompt_key="draft_response",
            input_payload=self._DRAFT_PAYLOAD,
        ))

        added = db.add.call_args[0][0]
        assert added.temperature is not None
        assert added.max_tokens is not None

    def test_extraction_prompt_uses_low_temperature(self) -> None:
        """Enquiry extraction prompt (V3) uses a very low temperature for deterministic output."""
        db, mock_run = _mock_db()
        gateway = AIGateway(db=db, api_key="")  # fallback — just check run_data

        gateway.run(AIGatewayRequest(
            prompt_key="enquiry_extraction",
            input_payload={"restaurant_name": "The Grand", "freeform_text": "Birthday for 20"},
        ))

        added = db.add.call_args[0][0]
        # V3 prompt uses temperature=0.05; assert <= 0.1 to allow future tuning
        assert float(added.temperature) <= 0.1
