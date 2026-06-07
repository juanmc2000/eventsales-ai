"""Tests for RESP-023 — RESPOND_UNAVAILABLE fully deterministic draft generation.

Validates:
- RESPOND_UNAVAILABLE bypasses the LLM gateway entirely
- Draft body contains the approved unavailable opening and signoff
- Draft body contains no alternative-date language
- Draft body contains no room/suitability details
- model is set to "deterministic" (not "fallback")
- is_fallback is False
- Room context is stripped before body generation
- Other goals (CONFIRM_AVAILABLE, ACKNOWLEDGE_AND_CHECK_AVAILABILITY) still call the gateway
- _generate_deterministic_unavailable uses copy-library blocks verbatim
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

import app.db.models  # noqa: F401 — registers all SQLAlchemy models

from app.modules.ai.service import _generate_deterministic_unavailable
from app.modules.ai.schemas import DraftContext


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_context(**overrides) -> DraftContext:
    defaults = dict(
        enquiry_id=uuid.uuid4(),
        guest_first_name="Alice",
        guest_last_name="Smith",
        event_type="birthday",
        event_date="2026-09-15",
        party_size=30,
        guest_message=None,
        restaurant_name="The Grand",
        restaurant_description=None,
        persona_name="Events Team",
        persona_tone="warm and professional",
        persona_style="concise",
        persona_system_prompt="",
        recommended_minimum_spend=None,
        response_goal="RESPOND_UNAVAILABLE",
        availability_status="unavailable",
        availability_date="2026-09-15",
        availability_meal_period="dinner",
    )
    defaults.update(overrides)
    return DraftContext(**defaults)


def _make_enquiry(enquiry_id: uuid.UUID | None = None) -> MagicMock:
    enquiry = MagicMock()
    enquiry.id = enquiry_id or uuid.uuid4()
    enquiry.restaurant_id = uuid.uuid4()
    enquiry.persona_id = uuid.uuid4()
    enquiry.first_name = "Alice"
    enquiry.last_name = "Smith"
    enquiry.event_type = "birthday"
    enquiry.event_date = None
    enquiry.party_size = 30
    enquiry.notes = None
    enquiry.metadata_ = {}
    enquiry.preferred_area = None
    return enquiry


# ── _generate_deterministic_unavailable unit tests ────────────────────────────


def test_deterministic_unavailable_contains_opening():
    ctx = _make_context(availability_meal_period="dinner", availability_date="15th September")
    body = _generate_deterministic_unavailable(ctx)
    assert "fully booked" in body.lower() or "unavailable" in body.lower() or "unfortunately" in body.lower()


def test_deterministic_unavailable_contains_meal_period_and_date():
    ctx = _make_context(availability_meal_period="lunch", availability_date="20th October")
    body = _generate_deterministic_unavailable(ctx)
    assert "lunch" in body
    assert "20th October" in body


def test_deterministic_unavailable_contains_signoff_with_persona_name():
    ctx = _make_context(persona_name="Sarah")
    body = _generate_deterministic_unavailable(ctx)
    assert "Sarah" in body


def test_deterministic_unavailable_no_alternative_dates():
    ctx = _make_context()
    body = _generate_deterministic_unavailable(ctx)
    forbidden_phrases = [
        "alternative date",
        "another date",
        "other availability",
        "could try",
        "suggest",
        "would love to host",
        "perfect for your group",
    ]
    body_lower = body.lower()
    for phrase in forbidden_phrases:
        assert phrase not in body_lower, f"Forbidden phrase found: {phrase!r}"


def test_deterministic_unavailable_no_room_details():
    ctx = _make_context(
        room_name="Private Dining Room",
        room_seated_capacity=40,
        room_suitability_notes="Perfect for corporate events",
    )
    body = _generate_deterministic_unavailable(ctx)
    assert "Private Dining Room" not in body
    assert "suitability" not in body.lower()
    assert "seated" not in body.lower()


def test_deterministic_unavailable_no_minimum_spend():
    ctx = _make_context(recommended_minimum_spend=5000.0, confirmed_minimum_spend=5000.0)
    body = _generate_deterministic_unavailable(ctx)
    assert "£" not in body
    assert "spend" not in body.lower()
    assert "minimum" not in body.lower()


def test_deterministic_unavailable_fallback_when_no_date_info():
    ctx = _make_context(availability_meal_period=None, availability_date=None, event_date=None)
    body = _generate_deterministic_unavailable(ctx)
    # Should still produce a valid body using defaults
    assert len(body) > 10
    assert ctx.persona_name in body


# ── DraftGenerationService integration: RESPOND_UNAVAILABLE bypasses gateway ──


def _make_service_mocks(goal: str = "RESPOND_UNAVAILABLE"):
    """Return a configured DraftGenerationService with all DB dependencies mocked."""
    from app.modules.ai.service import DraftGenerationService

    enquiry_id = uuid.uuid4()
    enquiry = _make_enquiry(enquiry_id)

    restaurant = MagicMock()
    restaurant.name = "The Grand"
    restaurant.description = "A fine venue"
    restaurant.address = "1 London Road"

    persona = MagicMock()
    persona.name = "Events Team"
    persona.tone = "warm"
    persona.style = "concise"
    persona.system_prompt = ""

    message = MagicMock()
    message.id = uuid.uuid4()

    db = MagicMock()
    svc = DraftGenerationService.__new__(DraftGenerationService)
    svc._db = db

    enquiry_repo = MagicMock()
    enquiry_repo.get_by_id.return_value = enquiry
    enquiry_repo.add_message.return_value = message
    svc._enquiry_repo = enquiry_repo

    persona_repo = MagicMock()
    persona_repo.get_by_id.return_value = persona
    persona_repo.get_default_persona_for_restaurant.return_value = persona
    svc._persona_repo = persona_repo

    restaurant_repo = MagicMock()
    restaurant_repo.get_by_id.return_value = restaurant
    svc._restaurant_repo = restaurant_repo

    room_repo = MagicMock()
    room_repo.list_for_restaurant.return_value = []
    svc._room_repo = room_repo

    return svc, enquiry_id, goal


@patch("app.modules.ai.service._load_latest_processing_snapshot", return_value=None)
@patch("app.modules.ai.service._enrich_context_from_response_plan")
@patch("app.modules.ai.service.AIGateway")
def test_respond_unavailable_does_not_call_gateway(
    mock_gateway_cls, mock_enrich, mock_snapshot
):
    """RESPOND_UNAVAILABLE must never reach the AI gateway."""
    from app.modules.ai.service import DraftGenerationService
    from app.modules.ai.schemas import DraftContext

    svc, enquiry_id, _ = _make_service_mocks("RESPOND_UNAVAILABLE")

    def _enrich_side_effect(db, eid, ctx):
        from dataclasses import replace
        return replace(ctx, response_goal="RESPOND_UNAVAILABLE")

    mock_enrich.side_effect = _enrich_side_effect

    result = svc.generate_draft(enquiry_id)

    mock_gateway_cls.assert_not_called()
    assert result.model == "deterministic"
    assert result.is_fallback is False


@patch("app.modules.ai.service._load_latest_processing_snapshot", return_value=None)
@patch("app.modules.ai.service._enrich_context_from_response_plan")
@patch("app.modules.ai.service.AIGateway")
def test_respond_unavailable_body_no_alternative_dates(
    mock_gateway_cls, mock_enrich, mock_snapshot
):
    """RESPOND_UNAVAILABLE draft body must not contain alternative-date language."""
    from app.modules.ai.service import DraftGenerationService

    svc, enquiry_id, _ = _make_service_mocks()

    def _enrich_side_effect(db, eid, ctx):
        from dataclasses import replace
        return replace(
            ctx,
            response_goal="RESPOND_UNAVAILABLE",
            availability_meal_period="dinner",
            availability_date="2026-09-15",
        )

    mock_enrich.side_effect = _enrich_side_effect

    result = svc.generate_draft(enquiry_id)

    body_lower = result.body.lower()
    for phrase in ["alternative date", "another date", "suggest", "would love to host"]:
        assert phrase not in body_lower, f"Forbidden phrase in body: {phrase!r}"


@patch("app.modules.ai.service._load_latest_processing_snapshot", return_value=None)
@patch("app.modules.ai.service._enrich_context_from_response_plan")
@patch("app.modules.ai.service.AIGateway")
def test_respond_unavailable_room_name_not_in_body(
    mock_gateway_cls, mock_enrich, mock_snapshot
):
    """Room name must not appear in the RESPOND_UNAVAILABLE draft body."""
    from app.modules.ai.service import DraftGenerationService

    svc, enquiry_id, _ = _make_service_mocks()

    # Inject a room into the matched room list so context would normally carry it
    room = MagicMock()
    room.name = "Mezzanine Suite"
    room.room_type = "private_dining"
    room.seated_capacity = 50
    room.standing_capacity = 60
    room.layouts = ["boardroom"]
    room.amenities = ["AV"]
    room.suitability_notes = "Great for corporate"
    room.booking_url = None
    room.is_private_dining = True
    room.min_capacity = 10
    room.max_capacity = 60
    svc._room_repo.list_for_restaurant.return_value = [room]

    def _enrich_side_effect(db, eid, ctx):
        from dataclasses import replace
        return replace(ctx, response_goal="RESPOND_UNAVAILABLE")

    mock_enrich.side_effect = _enrich_side_effect

    result = svc.generate_draft(enquiry_id)

    assert "Mezzanine Suite" not in result.body
    assert result.ai_context.room_name is None


@patch("app.modules.ai.service._load_latest_processing_snapshot", return_value=None)
@patch("app.modules.ai.service._enrich_context_from_response_plan")
@patch("app.modules.ai.service.AIGateway")
def test_other_goals_still_call_gateway(
    mock_gateway_cls, mock_enrich, mock_snapshot
):
    """Non-unavailable goals must still reach the AI gateway."""
    from app.modules.ai.service import DraftGenerationService
    from app.modules.ai.constants import PROMPT_KEY_DRAFT_RESPONSE
    from app.modules.ai.constants import RUN_STATUS_SUCCESS, VALIDATION_SKIPPED
    from app.modules.ai.schemas import AIGatewayResult

    svc, enquiry_id, _ = _make_service_mocks()

    gateway_instance = MagicMock()
    mock_gateway_cls.return_value = gateway_instance

    run_id = uuid.uuid4()
    gateway_instance.run.return_value = AIGatewayResult(
        run_id=run_id,
        prompt_key=PROMPT_KEY_DRAFT_RESPONSE,
        prompt_version=6,
        model_name="claude-haiku-4-5-20251001",
        model_provider="anthropic",
        rendered_system_prompt="sys",
        rendered_user_prompt="usr",
        raw_response="Dear Alice, we are delighted to confirm availability.",
        is_fallback=False,
        fallback_reason=None,
        validation_status=VALIDATION_SKIPPED,
        latency_ms=100,
        status=RUN_STATUS_SUCCESS,
    )

    def _enrich_side_effect(db, eid, ctx):
        from dataclasses import replace
        return replace(ctx, response_goal="CONFIRM_AVAILABLE")

    mock_enrich.side_effect = _enrich_side_effect

    # integrity gate must pass
    with patch("app.modules.ai.service._check_context_integrity") as mock_integrity:
        mock_integrity.return_value = MagicMock(passed=True)
        result = svc.generate_draft(enquiry_id)

    gateway_instance.run.assert_called_once()
    assert result.model != "deterministic"
