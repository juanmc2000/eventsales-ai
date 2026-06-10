"""Tests for the AI draft generation module.

All tests are smoke/unit tests (no DB, no Anthropic API required).
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.modules.ai.schemas import DraftContext, DraftGenerationResult
from app.modules.ai.provider import (
    FallbackProvider,
    AnthropicProvider,
    make_provider,
    _greeting_for_tone,
    _sign_off_for_style,
)
from app.modules.ai.service import _build_subject


# ── DraftContext schema ────────────────────────────────────────────────────────


def test_draft_context_creation() -> None:
    ctx = DraftContext(
        enquiry_id=uuid.uuid4(),
        guest_first_name="Alice",
        guest_last_name="Smith",
        event_type="corporate",
        event_date="2026-08-15",
        party_size=30,
        guest_message="Looking for a private dining experience.",
        restaurant_name="The Grand",
        restaurant_description="A premier London venue.",
        persona_name="Warm Host",
        persona_tone="warm and formal",
        persona_style="concise",
        persona_system_prompt="You are a warm hospitality professional.",
        recommended_minimum_spend=2500.0,
    )
    assert ctx.guest_first_name == "Alice"
    assert ctx.persona_tone == "warm and formal"
    assert ctx.recommended_minimum_spend == 2500.0


def test_draft_generation_result_creation() -> None:
    result = DraftGenerationResult(
        enquiry_id=uuid.uuid4(),
        message_id=uuid.uuid4(),
        subject="Re: Corporate Enquiry — Alice Smith",
        body="Dear Alice, ...",
        persona_name="Warm Host",
        is_fallback=True,
        model="fallback",
    )
    assert result.is_fallback is True
    assert result.model == "fallback"


# ── FallbackProvider ───────────────────────────────────────────────────────────


def _make_context(**overrides) -> DraftContext:
    defaults = dict(
        enquiry_id=uuid.uuid4(),
        guest_first_name="Jane",
        guest_last_name="Doe",
        event_type="birthday",
        event_date="2026-12-25",
        party_size=20,
        guest_message=None,
        restaurant_name="The Garden Room",
        restaurant_description=None,
        persona_name="The Host",
        persona_tone="warm and formal",
        persona_style="concise",
        persona_system_prompt="",
        recommended_minimum_spend=None,
    )
    defaults.update(overrides)
    return DraftContext(**defaults)


def test_fallback_provider_returns_string() -> None:
    provider = FallbackProvider()
    ctx = _make_context()
    result = provider.generate(ctx)
    assert isinstance(result, str)
    assert len(result) > 50


def test_fallback_includes_guest_name() -> None:
    provider = FallbackProvider()
    ctx = _make_context(guest_first_name="Marcus")
    result = provider.generate(ctx)
    assert "Marcus" in result


def test_fallback_includes_restaurant_name() -> None:
    provider = FallbackProvider()
    ctx = _make_context(restaurant_name="Belgravia Hall")
    result = provider.generate(ctx)
    assert "Belgravia Hall" in result


def test_fallback_includes_spend_when_present() -> None:
    provider = FallbackProvider()
    ctx = _make_context(recommended_minimum_spend=1500.0)
    result = provider.generate(ctx)
    assert "1,500" in result


def test_fallback_omits_spend_when_absent() -> None:
    provider = FallbackProvider()
    ctx = _make_context(recommended_minimum_spend=None)
    result = provider.generate(ctx)
    assert "minimum spend" not in result.lower()


def test_fallback_omits_spend_when_zero() -> None:
    provider = FallbackProvider()
    ctx = _make_context(recommended_minimum_spend=0.0)
    result = provider.generate(ctx)
    assert "minimum spend" not in result.lower()


# ── make_provider factory ──────────────────────────────────────────────────────


def test_make_provider_returns_fallback_when_no_key() -> None:
    provider, is_fallback = make_provider("")
    assert is_fallback is True
    assert isinstance(provider, FallbackProvider)


def test_make_provider_returns_anthropic_when_key_present() -> None:
    provider, is_fallback = make_provider("sk-ant-test-key")
    assert is_fallback is False
    assert isinstance(provider, AnthropicProvider)


# ── AnthropicProvider fallback on API error ────────────────────────────────────


def test_anthropic_provider_falls_back_on_api_error() -> None:
    provider = AnthropicProvider(api_key="sk-ant-fake")
    ctx = _make_context()

    with patch("anthropic.Anthropic") as mock_anthropic_cls:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")
        mock_anthropic_cls.return_value = mock_client

        result = provider.generate(ctx)

    # Should fall back to the template provider
    assert isinstance(result, str)
    assert len(result) > 50


def test_anthropic_provider_returns_response_text() -> None:
    provider = AnthropicProvider(api_key="sk-ant-fake")
    ctx = _make_context()

    with patch("anthropic.Anthropic") as mock_anthropic_cls:
        mock_client = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "  Dear Jane, thank you for your enquiry.  "
        mock_client.messages.create.return_value = MagicMock(content=[mock_content])
        mock_anthropic_cls.return_value = mock_client

        result = provider.generate(ctx)

    assert result == "Dear Jane, thank you for your enquiry."


# ── Helper functions ───────────────────────────────────────────────────────────


def test_greeting_warm_tone() -> None:
    assert _greeting_for_tone("warm and formal") == "Dear"


def test_greeting_casual_tone() -> None:
    assert _greeting_for_tone("casual and friendly") == "Hi"


def test_greeting_professional_tone() -> None:
    assert _greeting_for_tone("professional") == "Dear"


def test_sign_off_concise_style() -> None:
    assert _sign_off_for_style("concise") == "Kind regards"


def test_sign_off_detailed_style() -> None:
    assert _sign_off_for_style("warm and detailed") == "With warmest regards"


def test_build_subject_with_event_type() -> None:
    subject = _build_subject("Alice", "Smith", "corporate")
    assert "Corporate" in subject
    assert "Alice Smith" in subject


def test_build_subject_no_event_type() -> None:
    subject = _build_subject("Bob", "Jones", None)
    assert "Event" in subject
    assert "Bob Jones" in subject


# ── DraftGenerationService unit tests (mocked DB) ─────────────────────────────


def test_draft_generation_service_raises_on_missing_enquiry() -> None:
    from app.modules.ai.service import DraftGenerationService

    mock_db = MagicMock()
    service = DraftGenerationService(mock_db)
    service._enquiry_repo.get_by_id = MagicMock(return_value=None)

    with pytest.raises(ValueError, match="not found"):
        service.generate_draft(uuid.uuid4())


def test_draft_generation_service_uses_fallback_when_no_api_key() -> None:
    from app.modules.ai.service import DraftGenerationService

    mock_db = MagicMock()
    service = DraftGenerationService(mock_db)

    enquiry_id = uuid.uuid4()
    mock_enquiry = MagicMock()
    mock_enquiry.id = enquiry_id
    mock_enquiry.restaurant_id = uuid.uuid4()
    mock_enquiry.persona_id = None
    mock_enquiry.first_name = "Claire"
    mock_enquiry.last_name = "Brown"
    mock_enquiry.event_type = "wedding"
    mock_enquiry.event_date = None
    mock_enquiry.party_size = 60
    mock_enquiry.notes = None
    mock_enquiry.metadata_ = {"recommended_minimum_spend": 3000.0}

    mock_restaurant = MagicMock()
    mock_restaurant.name = "The Grand Hall"
    mock_restaurant.description = None

    mock_message = MagicMock()
    mock_message.id = uuid.uuid4()

    service._enquiry_repo.get_by_id = MagicMock(return_value=mock_enquiry)
    service._restaurant_repo.get_by_id = MagicMock(return_value=mock_restaurant)
    service._persona_repo.get_by_id = MagicMock(return_value=None)
    service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=None)
    service._enquiry_repo.add_message = MagicMock(return_value=mock_message)

    with patch("app.modules.ai.service.settings") as mock_settings:
        mock_settings.anthropic_api_key = ""
        result = service.generate_draft(enquiry_id)

    assert result.is_fallback is True
    assert result.model == "fallback"
    assert result.enquiry_id == enquiry_id
    assert "Claire" in result.body
    assert result.subject is not None
    service._enquiry_repo.add_message.assert_called_once()
    # AUTO-004: two commits — one after message persist, one after review_metadata persist
    assert mock_db.commit.call_count == 2


def test_draft_generation_service_stores_outbound_draft_message() -> None:
    from app.modules.ai.service import DraftGenerationService

    mock_db = MagicMock()
    service = DraftGenerationService(mock_db)

    enquiry_id = uuid.uuid4()
    mock_enquiry = MagicMock()
    mock_enquiry.id = enquiry_id
    mock_enquiry.restaurant_id = uuid.uuid4()
    mock_enquiry.persona_id = uuid.uuid4()
    mock_enquiry.first_name = "Tom"
    mock_enquiry.last_name = "Hardy"
    mock_enquiry.event_type = "corporate"
    mock_enquiry.event_date = None
    mock_enquiry.party_size = 40
    mock_enquiry.notes = None
    mock_enquiry.metadata_ = None

    mock_restaurant = MagicMock()
    mock_restaurant.name = "The Venue"
    mock_restaurant.description = None

    mock_persona = MagicMock()
    mock_persona.name = "Refined Host"
    mock_persona.tone = "professional"
    mock_persona.style = "concise"
    mock_persona.system_prompt = ""

    mock_message = MagicMock()
    mock_message.id = uuid.uuid4()

    service._enquiry_repo.get_by_id = MagicMock(return_value=mock_enquiry)
    service._restaurant_repo.get_by_id = MagicMock(return_value=mock_restaurant)
    service._persona_repo.get_by_id = MagicMock(return_value=mock_persona)
    service._enquiry_repo.add_message = MagicMock(return_value=mock_message)

    with patch("app.modules.ai.service.settings") as mock_settings:
        mock_settings.anthropic_api_key = ""
        service.generate_draft(enquiry_id)

    call_kwargs = service._enquiry_repo.add_message.call_args[0][1]
    assert call_kwargs["direction"] == "outbound"
    assert call_kwargs["channel"] == "draft"
    assert call_kwargs["sent_at"] is None
