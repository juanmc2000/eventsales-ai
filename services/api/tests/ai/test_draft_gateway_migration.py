"""Tests verifying the DraftGenerationService uses AIGateway (AI-006).

All tests are smoke/unit — no DB, no Anthropic API required.
The DB session and repositories are mocked.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.modules.ai.constants import (
    PROMPT_KEY_DRAFT_RESPONSE,
    RUN_STATUS_FALLBACK,
    RUN_STATUS_SUCCESS,
    TRIGGER_MANUAL_GENERATE_DRAFT,
    TRIGGER_WEBFORM_INTAKE_AUTO_DRAFT,
    VALIDATION_SKIPPED,
)
from app.modules.ai.schemas import AIGatewayResult, AIContextOut


def _make_gateway_result(
    is_fallback: bool = False,
    raw_response: str | None = "Dear Alice, thank you.",
    model_name: str = "claude-haiku-4-5-20251001",
    run_id: uuid.UUID | None = None,
) -> AIGatewayResult:
    return AIGatewayResult(
        run_id=run_id or uuid.uuid4(),
        prompt_key=PROMPT_KEY_DRAFT_RESPONSE,
        prompt_version=1,
        model_name="fallback" if is_fallback else model_name,
        model_provider="fallback" if is_fallback else "anthropic",
        rendered_system_prompt=None if is_fallback else "System prompt text",
        rendered_user_prompt=None if is_fallback else "User prompt text",
        raw_response=None if is_fallback else raw_response,
        is_fallback=is_fallback,
        fallback_reason="no_api_key" if is_fallback else None,
        validation_status=VALIDATION_SKIPPED,
        latency_ms=0 if is_fallback else 150,
        status=RUN_STATUS_FALLBACK if is_fallback else RUN_STATUS_SUCCESS,
    )


def _make_mock_enquiry(enquiry_id: uuid.UUID | None = None) -> MagicMock:
    enquiry = MagicMock()
    enquiry.id = enquiry_id or uuid.uuid4()
    enquiry.restaurant_id = uuid.uuid4()
    enquiry.persona_id = uuid.uuid4()
    enquiry.first_name = "Alice"
    enquiry.last_name = "Smith"
    enquiry.event_type = "corporate"
    enquiry.event_date = None
    enquiry.party_size = 20
    enquiry.notes = "Looking for a private dining experience."
    enquiry.metadata_ = {"recommended_minimum_spend": 2500.0}
    return enquiry


def _make_mock_persona() -> MagicMock:
    persona = MagicMock()
    persona.name = "Eleanor"
    persona.tone = "warm and formal"
    persona.style = "concise"
    persona.system_prompt = "You are a hospitality professional."
    return persona


def _make_mock_restaurant() -> MagicMock:
    restaurant = MagicMock()
    restaurant.name = "The Grand"
    restaurant.description = "Premier London venue"
    restaurant.address = "1 Grand Street, London"
    return restaurant


def _make_mock_message(message_id: uuid.UUID | None = None) -> MagicMock:
    msg = MagicMock()
    msg.id = message_id or uuid.uuid4()
    return msg


# ── Service wiring to gateway ──────────────────────────────────────────────

class TestDraftGenerationUsesGateway:
    def test_calls_ai_gateway_run(self) -> None:
        """DraftGenerationService must call AIGateway.run(), not provider directly."""
        from app.modules.ai.service import DraftGenerationService

        db = MagicMock()
        service = DraftGenerationService(db)

        enquiry = _make_mock_enquiry()
        service._enquiry_repo.get_by_id = MagicMock(return_value=enquiry)
        service._restaurant_repo.get_by_id = MagicMock(return_value=_make_mock_restaurant())
        service._persona_repo.get_by_id = MagicMock(return_value=_make_mock_persona())
        service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=_make_mock_persona())
        service._room_repo.list_for_restaurant = MagicMock(return_value=[])
        service._enquiry_repo.add_message = MagicMock(return_value=_make_mock_message())

        with patch("app.modules.ai.service.AIGateway") as mock_gateway_cls:
            mock_gateway = MagicMock()
            mock_gateway.run.return_value = _make_gateway_result()
            mock_gateway_cls.return_value = mock_gateway

            service.generate_draft(enquiry.id)

            mock_gateway.run.assert_called_once()

    def test_gateway_called_with_correct_prompt_key(self) -> None:
        from app.modules.ai.service import DraftGenerationService
        from app.modules.ai.schemas import AIGatewayRequest

        db = MagicMock()
        service = DraftGenerationService(db)
        enquiry = _make_mock_enquiry()

        service._enquiry_repo.get_by_id = MagicMock(return_value=enquiry)
        service._restaurant_repo.get_by_id = MagicMock(return_value=_make_mock_restaurant())
        service._persona_repo.get_by_id = MagicMock(return_value=_make_mock_persona())
        service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=_make_mock_persona())
        service._room_repo.list_for_restaurant = MagicMock(return_value=[])
        service._enquiry_repo.add_message = MagicMock(return_value=_make_mock_message())

        captured_request = []

        def capture_run(request: AIGatewayRequest) -> AIGatewayResult:
            captured_request.append(request)
            return _make_gateway_result()

        with patch("app.modules.ai.service.AIGateway") as mock_gateway_cls:
            mock_gateway = MagicMock()
            mock_gateway.run.side_effect = capture_run
            mock_gateway_cls.return_value = mock_gateway

            service.generate_draft(enquiry.id)

        assert len(captured_request) == 1
        assert captured_request[0].prompt_key == PROMPT_KEY_DRAFT_RESPONSE

    def test_gateway_receives_enquiry_id(self) -> None:
        from app.modules.ai.service import DraftGenerationService
        from app.modules.ai.schemas import AIGatewayRequest

        db = MagicMock()
        service = DraftGenerationService(db)
        enquiry_id = uuid.uuid4()
        enquiry = _make_mock_enquiry(enquiry_id)

        service._enquiry_repo.get_by_id = MagicMock(return_value=enquiry)
        service._restaurant_repo.get_by_id = MagicMock(return_value=_make_mock_restaurant())
        service._persona_repo.get_by_id = MagicMock(return_value=_make_mock_persona())
        service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=_make_mock_persona())
        service._room_repo.list_for_restaurant = MagicMock(return_value=[])
        service._enquiry_repo.add_message = MagicMock(return_value=_make_mock_message())

        captured = []

        def capture(request: AIGatewayRequest) -> AIGatewayResult:
            captured.append(request)
            return _make_gateway_result()

        with patch("app.modules.ai.service.AIGateway") as mock_cls:
            mock_gw = MagicMock()
            mock_gw.run.side_effect = capture
            mock_cls.return_value = mock_gw

            service.generate_draft(enquiry_id)

        assert captured[0].enquiry_id == enquiry_id
        assert captured[0].restaurant_id == enquiry.restaurant_id

    def test_gateway_called_with_trigger_type(self) -> None:
        from app.modules.ai.service import DraftGenerationService

        db = MagicMock()
        service = DraftGenerationService(db)
        enquiry = _make_mock_enquiry()

        service._enquiry_repo.get_by_id = MagicMock(return_value=enquiry)
        service._restaurant_repo.get_by_id = MagicMock(return_value=_make_mock_restaurant())
        service._persona_repo.get_by_id = MagicMock(return_value=_make_mock_persona())
        service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=_make_mock_persona())
        service._room_repo.list_for_restaurant = MagicMock(return_value=[])
        service._enquiry_repo.add_message = MagicMock(return_value=_make_mock_message())

        captured = []

        def capture(request):
            captured.append(request)
            return _make_gateway_result()

        with patch("app.modules.ai.service.AIGateway") as mock_cls:
            mock_gw = MagicMock()
            mock_gw.run.side_effect = capture
            mock_cls.return_value = mock_gw

            service.generate_draft(enquiry.id, trigger_type=TRIGGER_WEBFORM_INTAKE_AUTO_DRAFT)

        assert captured[0].trigger_type == TRIGGER_WEBFORM_INTAKE_AUTO_DRAFT


# ── Fallback path ──────────────────────────────────────────────────────────

class TestDraftGenerationFallback:
    def test_fallback_result_still_produces_body(self) -> None:
        from app.modules.ai.service import DraftGenerationService

        db = MagicMock()
        service = DraftGenerationService(db)
        enquiry = _make_mock_enquiry()

        service._enquiry_repo.get_by_id = MagicMock(return_value=enquiry)
        service._restaurant_repo.get_by_id = MagicMock(return_value=_make_mock_restaurant())
        service._persona_repo.get_by_id = MagicMock(return_value=_make_mock_persona())
        service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=_make_mock_persona())
        service._room_repo.list_for_restaurant = MagicMock(return_value=[])
        msg = _make_mock_message()
        service._enquiry_repo.add_message = MagicMock(return_value=msg)

        with patch("app.modules.ai.service.AIGateway") as mock_cls:
            mock_gw = MagicMock()
            mock_gw.run.return_value = _make_gateway_result(is_fallback=True)
            mock_cls.return_value = mock_gw

            result = service.generate_draft(enquiry.id)

        assert result.is_fallback is True
        assert result.body  # fallback body is non-empty
        assert "Alice" in result.body or "The Grand" in result.body or "Thank you" in result.body

    def test_fallback_ai_context_has_no_run_id(self) -> None:
        from app.modules.ai.service import DraftGenerationService

        db = MagicMock()
        service = DraftGenerationService(db)
        enquiry = _make_mock_enquiry()

        service._enquiry_repo.get_by_id = MagicMock(return_value=enquiry)
        service._restaurant_repo.get_by_id = MagicMock(return_value=_make_mock_restaurant())
        service._persona_repo.get_by_id = MagicMock(return_value=_make_mock_persona())
        service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=_make_mock_persona())
        service._room_repo.list_for_restaurant = MagicMock(return_value=[])
        service._enquiry_repo.add_message = MagicMock(return_value=_make_mock_message())

        with patch("app.modules.ai.service.AIGateway") as mock_cls:
            mock_gw = MagicMock()
            mock_gw.run.return_value = _make_gateway_result(is_fallback=True)
            mock_cls.return_value = mock_gw

            result = service.generate_draft(enquiry.id)

        assert result.ai_context.prompt_run_id is None


# ── Live provider path ─────────────────────────────────────────────────────

class TestDraftGenerationLivePath:
    def test_live_path_result_body_matches_gateway_response(self) -> None:
        from app.modules.ai.service import DraftGenerationService

        db = MagicMock()
        service = DraftGenerationService(db)
        enquiry = _make_mock_enquiry()

        service._enquiry_repo.get_by_id = MagicMock(return_value=enquiry)
        service._restaurant_repo.get_by_id = MagicMock(return_value=_make_mock_restaurant())
        service._persona_repo.get_by_id = MagicMock(return_value=_make_mock_persona())
        service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=_make_mock_persona())
        service._room_repo.list_for_restaurant = MagicMock(return_value=[])
        service._enquiry_repo.add_message = MagicMock(return_value=_make_mock_message())

        expected_body = "Dear Alice, we are thrilled to host your event."
        run_id = uuid.uuid4()

        with patch("app.modules.ai.service.AIGateway") as mock_cls:
            mock_gw = MagicMock()
            mock_gw.run.return_value = _make_gateway_result(
                raw_response=expected_body, run_id=run_id
            )
            mock_cls.return_value = mock_gw

            result = service.generate_draft(enquiry.id)

        assert result.body == expected_body
        assert result.is_fallback is False
        assert result.ai_context.prompt_run_id == run_id

    def test_live_path_ai_context_has_rendered_prompts(self) -> None:
        from app.modules.ai.service import DraftGenerationService

        db = MagicMock()
        service = DraftGenerationService(db)
        enquiry = _make_mock_enquiry()

        service._enquiry_repo.get_by_id = MagicMock(return_value=enquiry)
        service._restaurant_repo.get_by_id = MagicMock(return_value=_make_mock_restaurant())
        service._persona_repo.get_by_id = MagicMock(return_value=_make_mock_persona())
        service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=_make_mock_persona())
        service._room_repo.list_for_restaurant = MagicMock(return_value=[])
        service._enquiry_repo.add_message = MagicMock(return_value=_make_mock_message())

        with patch("app.modules.ai.service.AIGateway") as mock_cls:
            mock_gw = MagicMock()
            mock_gw.run.return_value = _make_gateway_result()
            mock_cls.return_value = mock_gw

            result = service.generate_draft(enquiry.id)

        assert result.ai_context.system_prompt == "System prompt text"
        assert result.ai_context.user_message == "User prompt text"


# ── Input payload building ─────────────────────────────────────────────────

class TestBuildDraftInputPayload:
    def test_required_variables_present(self) -> None:
        from app.modules.ai.service import _build_draft_input_payload
        from app.modules.ai.schemas import DraftContext

        ctx = DraftContext(
            enquiry_id=uuid.uuid4(),
            guest_first_name="Alice",
            guest_last_name="Smith",
            event_type="corporate",
            event_date="2026-08-15",
            party_size=20,
            guest_message="Looking for a venue.",
            restaurant_name="The Grand",
            restaurant_description="Premier venue",
            persona_name="Eleanor",
            persona_tone="warm",
            persona_style="concise",
            persona_system_prompt="You are professional.",
            recommended_minimum_spend=2500.0,
        )
        payload = _build_draft_input_payload(ctx)
        assert payload["persona_name"] == "Eleanor"
        assert payload["guest_first_name"] == "Alice"
        assert payload["restaurant_name"] == "The Grand"

    def test_optional_lines_present_when_data_available(self) -> None:
        from app.modules.ai.service import _build_draft_input_payload
        from app.modules.ai.schemas import DraftContext

        ctx = DraftContext(
            enquiry_id=uuid.uuid4(),
            guest_first_name="Alice",
            guest_last_name="Smith",
            event_type="corporate",
            event_date="2026-08-15",
            party_size=20,
            guest_message="Looking for a venue.",
            restaurant_name="The Grand",
            restaurant_description=None,
            persona_name="Eleanor",
            persona_tone="warm",
            persona_style="concise",
            persona_system_prompt="",
            recommended_minimum_spend=2500.0,
        )
        payload = _build_draft_input_payload(ctx)
        assert "Corporate" in payload["event_type_line"]
        assert "2026-08-15" in payload["event_date_line"]
        assert "20" in payload["party_size_line"]
        assert "2,500" in payload["spend_line"]
        assert "Looking for a venue" in payload["guest_message_line"]

    def test_optional_lines_empty_when_data_absent(self) -> None:
        from app.modules.ai.service import _build_draft_input_payload
        from app.modules.ai.schemas import DraftContext

        ctx = DraftContext(
            enquiry_id=uuid.uuid4(),
            guest_first_name="Alice",
            guest_last_name="Smith",
            event_type=None,
            event_date=None,
            party_size=None,
            guest_message=None,
            restaurant_name="The Grand",
            restaurant_description=None,
            persona_name="Eleanor",
            persona_tone="warm",
            persona_style="concise",
            persona_system_prompt="",
            recommended_minimum_spend=None,
        )
        payload = _build_draft_input_payload(ctx)
        assert payload["event_type_line"] == ""
        assert payload["event_date_line"] == ""
        assert payload["party_size_line"] == ""
        assert payload["spend_line"] == ""
        assert payload["guest_message_line"] == ""
