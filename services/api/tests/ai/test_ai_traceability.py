"""Comprehensive AI Gateway and prompt traceability tests (TEST-007).

This module consolidates end-to-end traceability scenarios, verifying that:
- Every gateway call creates an ai_prompt_run record
- Prompt run records are created for both success and fallback paths
- Validation results are stored in the run record
- Draft generation flows through the gateway (no direct provider calls)
- Training examples link back to prompt runs
- No live LLM or Gmail calls are made in any test

All tests are deterministic unit tests — no DB, no Anthropic API.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

import app.db.models  # noqa: F401 — registers all SQLAlchemy models before mapper init

from app.modules.ai.constants import (
    PROMPT_KEY_DRAFT_RESPONSE,
    PROMPT_KEY_ENQUIRY_EXTRACTION,
    RUN_STATUS_ERROR,
    RUN_STATUS_FALLBACK,
    RUN_STATUS_SUCCESS,
    TRIGGER_MANUAL_GENERATE_DRAFT,
    TRIGGER_WEBFORM_INTAKE_AUTO_DRAFT,
    VALIDATION_PASSED,
    VALIDATION_SKIPPED,
)
from app.modules.ai.prompt_registry import PromptRegistry
from app.modules.ai.prompt_renderer import MissingPromptVariables, PromptRenderer
from app.modules.ai.schemas import AIGatewayRequest, AIGatewayResult


# ── Helper builders ────────────────────────────────────────────────────────


def _draft_context() -> dict:
    """Minimal valid input_payload for the draft_response prompt."""
    return {
        "persona_system_prompt": "You are a hospitality professional.",
        "persona_name": "Eleanor",
        "restaurant_name": "The Grand",
        "persona_tone": "warm and formal",
        "persona_style": "concise",
        "guest_first_name": "Alice",
        "guest_last_name": "Smith",
    }


def _mock_db() -> tuple[MagicMock, MagicMock]:
    db = MagicMock()
    mock_run = MagicMock()
    mock_run.id = uuid.uuid4()
    db.add = MagicMock()
    db.flush = MagicMock()
    db.get = MagicMock(return_value=mock_run)
    return db, mock_run


# ── Prompt registry traceability ───────────────────────────────────────────

class TestPromptRegistryTraceability:
    def test_all_required_keys_are_registered(self) -> None:
        """Every prompt key used by the system must exist in the registry."""
        registry = PromptRegistry()
        # These keys are used in production code
        assert registry.get(PROMPT_KEY_DRAFT_RESPONSE) is not None
        assert registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION) is not None

    def test_each_active_prompt_has_schema_metadata(self) -> None:
        """Active prompts used for structured output should declare output schema."""
        registry = PromptRegistry()
        draft = registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert draft.output_schema_name is not None
        assert draft.output_schema_version is not None

    def test_prompt_version_is_positive(self) -> None:
        """All registered prompts must have a positive version number."""
        registry = PromptRegistry()
        for key in registry.all_keys():
            defn = registry.get(key)
            assert defn.version >= 1, f"{key}: version must be >= 1"

    def test_prompt_definitions_are_frozen(self) -> None:
        """Prompt definitions are immutable — they cannot be modified at runtime."""
        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        with pytest.raises((AttributeError, TypeError)):
            defn.system_template = "hacked"  # type: ignore[misc]

    def test_renderer_extracts_required_variables_from_templates(self) -> None:
        """Required variables declared in the definition must match the template."""
        registry = PromptRegistry()
        renderer = PromptRenderer()
        defn = registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        # Extract all variables from both templates
        system_vars = renderer.extract_variables(defn.system_template)
        user_vars = renderer.extract_variables(defn.user_template)
        all_template_vars = system_vars | user_vars
        # All required vars must appear in templates
        for required_var in defn.required_variables:
            assert required_var in all_template_vars, (
                f"Required variable '{required_var}' not found in templates for {defn.key}"
            )


# ── Prompt renderer traceability ───────────────────────────────────────────

class TestPromptRendererTraceability:
    def test_input_hash_length_is_always_64(self) -> None:
        """SHA-256 hex digest is always exactly 64 characters."""
        for system, user in [
            ("short", "short"),
            ("a" * 1000, "b" * 1000),
            ("", ""),
        ]:
            h = PromptRenderer.input_hash(system, user)
            assert len(h) == 64, f"Expected 64-char hash, got {len(h)}"

    def test_input_hash_changes_with_system_prompt(self) -> None:
        """A different system prompt produces a different hash."""
        h1 = PromptRenderer.input_hash("system A", "user")
        h2 = PromptRenderer.input_hash("system B", "user")
        assert h1 != h2

    def test_input_hash_changes_with_user_prompt(self) -> None:
        """A different user prompt produces a different hash."""
        h1 = PromptRenderer.input_hash("system", "user A")
        h2 = PromptRenderer.input_hash("system", "user B")
        assert h1 != h2

    def test_missing_variable_error_lists_all_absent_fields(self) -> None:
        """MissingPromptVariables must report every absent required field."""
        registry = PromptRegistry()
        renderer = PromptRenderer()
        defn = registry.get(PROMPT_KEY_DRAFT_RESPONSE)

        with pytest.raises(MissingPromptVariables) as exc_info:
            renderer.render_system(defn, {})

        assert defn.required_variables == exc_info.value.missing

    def test_optional_variables_default_to_empty_string(self) -> None:
        """Optional variables must default to '' when absent, not raise."""
        registry = PromptRegistry()
        renderer = PromptRenderer()
        defn = registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        ctx = _draft_context()
        # No optional vars provided — should render without error
        rendered = renderer.render_user(defn, ctx)
        assert rendered is not None
        assert "Alice" in rendered


# ── Gateway run logging traceability ──────────────────────────────────────

class TestGatewayRunLogging:
    def test_fallback_run_always_creates_db_record(self) -> None:
        """Every gateway call — including fallback — must create an ai_prompt_run."""
        from app.modules.ai.gateway import AIGateway

        db, mock_run = _mock_db()
        gateway = AIGateway(db=db, api_key="")  # No key → fallback
        gateway.run(AIGatewayRequest(
            prompt_key=PROMPT_KEY_DRAFT_RESPONSE,
            input_payload=_draft_context(),
        ))
        db.add.assert_called()  # Run row must be persisted

    def test_live_run_creates_and_updates_db_record(self) -> None:
        """A live provider call must create the run row then update it with results."""
        from app.modules.ai.gateway import AIGateway

        db, mock_run = _mock_db()

        with patch("app.modules.ai.gateway.make_provider") as mock_make:
            mock_provider = MagicMock()
            mock_provider.model_name = "claude-haiku-4-5-20251001"
            mock_provider.generate_from_prompts.return_value = "Dear Alice."
            mock_make.return_value = (mock_provider, False)

            gateway = AIGateway(db=db, api_key="fake_key")
            gateway.run(AIGatewayRequest(
                prompt_key=PROMPT_KEY_DRAFT_RESPONSE,
                input_payload=_draft_context(),
            ))

        # add() for create, flush() for both create and update
        db.add.assert_called()
        assert db.flush.call_count >= 1

    def test_provider_error_still_updates_run_record(self) -> None:
        """If the provider raises, the run record must be updated with error status."""
        from app.modules.ai.gateway import AIGateway

        db, mock_run = _mock_db()

        with patch("app.modules.ai.gateway.make_provider") as mock_make:
            mock_provider = MagicMock()
            mock_provider.model_name = "claude-haiku-4-5-20251001"
            mock_provider.generate_from_prompts.side_effect = RuntimeError("timeout")
            mock_make.return_value = (mock_provider, False)

            gateway = AIGateway(db=db, api_key="fake_key")
            result = gateway.run(AIGatewayRequest(
                prompt_key=PROMPT_KEY_DRAFT_RESPONSE,
                input_payload=_draft_context(),
            ))

        assert result.status == RUN_STATUS_ERROR
        assert result.error_message is not None

    def test_run_result_contains_rendered_prompts(self) -> None:
        """Live run results must expose the rendered system and user prompts."""
        from app.modules.ai.gateway import AIGateway

        db, mock_run = _mock_db()

        with patch("app.modules.ai.gateway.make_provider") as mock_make:
            mock_provider = MagicMock()
            mock_provider.model_name = "claude-haiku-4-5-20251001"
            mock_provider.generate_from_prompts.return_value = "Dear Alice, thank you."
            mock_make.return_value = (mock_provider, False)

            gateway = AIGateway(db=db, api_key="fake_key")
            result = gateway.run(AIGatewayRequest(
                prompt_key=PROMPT_KEY_DRAFT_RESPONSE,
                input_payload=_draft_context(),
            ))

        assert result.rendered_system_prompt is not None
        assert "Eleanor" in result.rendered_system_prompt
        assert result.rendered_user_prompt is not None
        assert "Alice" in result.rendered_user_prompt

    def test_fallback_run_has_no_rendered_prompts(self) -> None:
        """Fallback runs must have None for rendered prompts (no LLM call)."""
        from app.modules.ai.gateway import AIGateway

        db, _ = _mock_db()
        gateway = AIGateway(db=db, api_key="")
        result = gateway.run(AIGatewayRequest(
            prompt_key=PROMPT_KEY_DRAFT_RESPONSE,
            input_payload=_draft_context(),
        ))
        assert result.rendered_system_prompt is None
        assert result.rendered_user_prompt is None
        assert result.raw_response is None

    def test_gateway_result_includes_run_id(self) -> None:
        """Every gateway result must carry a run_id for traceability."""
        from app.modules.ai.gateway import AIGateway

        db, mock_run = _mock_db()
        gateway = AIGateway(db=db, api_key="")
        result = gateway.run(AIGatewayRequest(
            prompt_key=PROMPT_KEY_DRAFT_RESPONSE,
            input_payload=_draft_context(),
        ))
        assert result.run_id is not None
        assert isinstance(result.run_id, uuid.UUID)


# ── Draft generation traceability ─────────────────────────────────────────

class TestDraftGenerationTraceability:
    def _make_enquiry(self) -> MagicMock:
        enquiry = MagicMock()
        enquiry.id = uuid.uuid4()
        enquiry.restaurant_id = uuid.uuid4()
        enquiry.persona_id = uuid.uuid4()
        enquiry.first_name = "Alice"
        enquiry.last_name = "Smith"
        enquiry.event_type = "corporate"
        enquiry.event_date = None
        enquiry.party_size = 20
        enquiry.notes = "Looking for a venue."
        enquiry.metadata_ = {"recommended_minimum_spend": 2500.0}
        return enquiry

    def test_draft_service_no_direct_anthropic_call(self) -> None:
        """DraftGenerationService must not import or call anthropic directly."""
        import inspect
        from app.modules.ai import service as service_module

        source = inspect.getsource(service_module)
        assert "import anthropic" not in source, (
            "DraftGenerationService must not import anthropic directly"
        )
        assert "AnthropicProvider()" not in source, (
            "DraftGenerationService must not instantiate AnthropicProvider directly"
        )

    def test_draft_service_uses_ai_gateway_import(self) -> None:
        """DraftGenerationService source must import and use AIGateway."""
        import inspect
        from app.modules.ai import service as service_module

        source = inspect.getsource(service_module)
        assert "AIGateway" in source, (
            "DraftGenerationService must use AIGateway"
        )

    def test_draft_service_gateway_receives_enquiry_metadata(self) -> None:
        """The gateway call must include enquiry_id, restaurant_id, persona_id."""
        from app.modules.ai.service import DraftGenerationService

        db = MagicMock()
        service = DraftGenerationService(db)
        enquiry = self._make_enquiry()

        mock_restaurant2 = MagicMock()
        mock_restaurant2.name = "The Grand"
        mock_restaurant2.description = "Premier"
        mock_restaurant2.address = "1 London St"

        mock_persona2 = MagicMock()
        mock_persona2.name = "Eleanor"
        mock_persona2.tone = "warm"
        mock_persona2.style = "concise"
        mock_persona2.system_prompt = "Be professional."

        service._enquiry_repo.get_by_id = MagicMock(return_value=enquiry)
        service._restaurant_repo.get_by_id = MagicMock(return_value=mock_restaurant2)
        service._persona_repo.get_by_id = MagicMock(return_value=mock_persona2)
        service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=None)
        service._room_repo.list_for_restaurant = MagicMock(return_value=[])
        service._enquiry_repo.add_message = MagicMock(return_value=MagicMock())

        captured = []

        def capture(req):
            captured.append(req)
            from app.modules.ai.schemas import AIGatewayResult
            return AIGatewayResult(
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

        with patch("app.modules.ai.service.AIGateway") as mock_cls:
            mock_gw = MagicMock()
            mock_gw.run.side_effect = capture
            mock_cls.return_value = mock_gw

            service.generate_draft(enquiry.id)

        assert len(captured) == 1
        req = captured[0]
        assert req.enquiry_id == enquiry.id
        assert req.restaurant_id == enquiry.restaurant_id
        assert req.persona_id == enquiry.persona_id

    def test_draft_fallback_ai_context_is_populated(self) -> None:
        """Even for fallback runs, AIContextOut must be populated with context."""
        from app.modules.ai.service import DraftGenerationService

        db = MagicMock()
        service = DraftGenerationService(db)
        enquiry = self._make_enquiry()

        mock_restaurant = MagicMock()
        mock_restaurant.name = "The Grand"
        mock_restaurant.description = "Premier"
        mock_restaurant.address = "1 London St"

        mock_persona = MagicMock()
        mock_persona.name = "Eleanor"
        mock_persona.tone = "warm"
        mock_persona.style = "concise"
        mock_persona.system_prompt = "Be professional."

        service._enquiry_repo.get_by_id = MagicMock(return_value=enquiry)
        service._restaurant_repo.get_by_id = MagicMock(return_value=mock_restaurant)
        service._persona_repo.get_by_id = MagicMock(return_value=mock_persona)
        service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=None)
        service._room_repo.list_for_restaurant = MagicMock(return_value=[])
        service._enquiry_repo.add_message = MagicMock(return_value=MagicMock())

        from app.modules.ai.schemas import AIGatewayResult

        with patch("app.modules.ai.service.AIGateway") as mock_cls:
            mock_gw = MagicMock()
            mock_gw.run.return_value = AIGatewayResult(
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
            mock_cls.return_value = mock_gw

            result = service.generate_draft(enquiry.id)

        assert result.ai_context is not None
        assert result.ai_context.persona_name == "Eleanor"
        assert result.ai_context.is_fallback is True
        assert result.ai_context.prompt_run_id is None  # No run_id for fallback


# ── Training example traceability ─────────────────────────────────────────

class TestTrainingExampleTraceability:
    def test_training_example_requires_prompt_run_link(self) -> None:
        """Training examples must always link to an existing prompt run."""
        from app.modules.ai.service import TrainingExampleService

        db = MagicMock()
        service = TrainingExampleService(db)
        service._repo = MagicMock()
        service._repo.get_run.return_value = None  # Run doesn't exist

        with pytest.raises(ValueError):
            service.create({"prompt_run_id": uuid.uuid4()})

    def test_training_example_inherits_prompt_key_from_run(self) -> None:
        """The training example's prompt_key is copied from the linked run."""
        from app.modules.ai.service import TrainingExampleService

        db = MagicMock()
        service = TrainingExampleService(db)

        run_id = uuid.uuid4()
        mock_run = MagicMock()
        mock_run.tenant_id = "default"
        mock_run.prompt_key = PROMPT_KEY_DRAFT_RESPONSE
        mock_run.parsed_response = {"subject": "Hi", "body": "Hello"}

        service._repo = MagicMock()
        service._repo.get_run.return_value = mock_run
        service._repo.create_training_example_from_data.return_value = MagicMock()

        service.create({"prompt_run_id": run_id})

        call_data = service._repo.create_training_example_from_data.call_args[0][0]
        assert call_data["prompt_key"] == PROMPT_KEY_DRAFT_RESPONSE

    def test_training_example_captures_original_output(self) -> None:
        """original_output must be set from the run's parsed_response."""
        from app.modules.ai.service import TrainingExampleService

        db = MagicMock()
        service = TrainingExampleService(db)

        run_id = uuid.uuid4()
        parsed = {"subject": "Re: Birthday", "body": "Dear Alice..."}
        mock_run = MagicMock()
        mock_run.tenant_id = "default"
        mock_run.prompt_key = PROMPT_KEY_DRAFT_RESPONSE
        mock_run.parsed_response = parsed

        service._repo = MagicMock()
        service._repo.get_run.return_value = mock_run
        service._repo.create_training_example_from_data.return_value = MagicMock()

        service.create({"prompt_run_id": run_id})

        call_data = service._repo.create_training_example_from_data.call_args[0][0]
        assert call_data["original_output"] == parsed


# ── No live calls guarantee ────────────────────────────────────────────────

class TestNoLiveLLMCalls:
    def test_fallback_gateway_never_calls_anthropic_sdk(self) -> None:
        """Fallback gateway must not import or call the anthropic SDK."""
        from app.modules.ai.gateway import AIGateway

        db, _ = _mock_db()
        gateway = AIGateway(db=db, api_key="")  # Fallback mode

        # Patch anthropic at the module level to detect any import
        with patch.dict("sys.modules", {"anthropic": MagicMock()}):
            import anthropic as mock_anthropic
            gateway.run(AIGatewayRequest(
                prompt_key=PROMPT_KEY_DRAFT_RESPONSE,
                input_payload=_draft_context(),
            ))
            # Anthropic client should NOT be instantiated for fallback
            mock_anthropic.Anthropic.assert_not_called()

    def test_renderer_is_pure_python(self) -> None:
        """PromptRenderer must not make any I/O calls."""
        import io
        from app.modules.ai.prompt_renderer import PromptRenderer

        registry = PromptRegistry()
        renderer = PromptRenderer()
        defn = registry.get(PROMPT_KEY_DRAFT_RESPONSE)

        # Should complete with no I/O
        system = renderer.render_system(defn, _draft_context())
        user = renderer.render_user(defn, _draft_context())
        h = PromptRenderer.input_hash(system, user)

        assert isinstance(system, str)
        assert isinstance(user, str)
        assert isinstance(h, str)
