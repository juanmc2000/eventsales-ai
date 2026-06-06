"""Tests for RESP-007 — Approved Phrase Library.

Validates:
- All response goals have an approved phrase
- Mandatory spend phrase uses mandatory language
- get_phrase_guidance returns non-empty for all known goals
- get_phrase_guidance returns empty for unknown goal
- Phrases appear in the rendered V4 system prompt
- phrase_guidance_line is present in _build_draft_input_payload
- phrase_guidance_line is an optional variable in V4 prompt definition
"""

from __future__ import annotations

import uuid

import pytest

from app.modules.ai.phrase_library import (
    APPROVED_PHRASES,
    PHRASE_CONFIRM_AVAILABLE,
    PHRASE_RESPOND_UNAVAILABLE,
    PHRASE_ACKNOWLEDGE_AND_CHECK,
    PHRASE_REQUEST_DATE_CONFIRMATION,
    PHRASE_REQUEST_MISSING_INFORMATION,
    PHRASE_REQUEST_WEBFORM,
    PHRASE_ESCALATE_TO_HUMAN,
    PHRASE_MINIMUM_SPEND,
    get_phrase_guidance,
)
from app.modules.ai.schemas import DraftContext
from app.modules.ai.service import _build_draft_input_payload, _build_phrase_guidance_line
from app.modules.ai.constants import PROMPT_KEY_DRAFT_RESPONSE
from app.modules.ai.prompt_registry import PromptRegistry
from app.modules.ai.prompt_renderer import PromptRenderer


# ── Helpers ────────────────────────────────────────────────────────────────────


def _base_context(**kwargs) -> DraftContext:
    defaults = dict(
        enquiry_id=uuid.uuid4(),
        guest_first_name="Alice",
        guest_last_name="Smith",
        event_type="dinner",
        event_date=None,
        party_size=None,
        guest_message=None,
        restaurant_name="The Grand",
        restaurant_description=None,
        persona_name="Eleanor",
        persona_tone="warm and formal",
        persona_style="concise",
        persona_system_prompt="You are a hospitality professional.",
        recommended_minimum_spend=None,
    )
    defaults.update(kwargs)
    return DraftContext(**defaults)


# ── APPROVED_PHRASES dict ─────────────────────────────────────────────────────


class TestApprovedPhrasesDict:
    def test_confirm_available_in_dict(self) -> None:
        assert "CONFIRM_AVAILABLE" in APPROVED_PHRASES

    def test_respond_unavailable_in_dict(self) -> None:
        assert "RESPOND_UNAVAILABLE" in APPROVED_PHRASES

    def test_acknowledge_and_check_in_dict(self) -> None:
        assert "ACKNOWLEDGE_AND_CHECK_AVAILABILITY" in APPROVED_PHRASES

    def test_request_date_confirmation_in_dict(self) -> None:
        assert "REQUEST_DATE_CONFIRMATION" in APPROVED_PHRASES

    def test_request_missing_info_in_dict(self) -> None:
        assert "REQUEST_MISSING_INFORMATION" in APPROVED_PHRASES

    def test_request_webform_in_dict(self) -> None:
        assert "REQUEST_WEBFORM" in APPROVED_PHRASES

    def test_escalate_to_human_in_dict(self) -> None:
        assert "ESCALATE_TO_HUMAN" in APPROVED_PHRASES

    def test_minimum_spend_in_dict(self) -> None:
        assert "MINIMUM_SPEND" in APPROVED_PHRASES


# ── Phrase content ─────────────────────────────────────────────────────────────


class TestPhraseContent:
    def test_confirm_available_phrase_sounds_positive(self) -> None:
        assert "available" in PHRASE_CONFIRM_AVAILABLE.lower()

    def test_respond_unavailable_phrase_says_fully_booked(self) -> None:
        assert "fully booked" in PHRASE_RESPOND_UNAVAILABLE.lower()

    def test_acknowledge_phrase_says_check_availability(self) -> None:
        assert "check availability" in PHRASE_ACKNOWLEDGE_AND_CHECK.lower()

    def test_request_date_confirmation_asks_for_exact_date(self) -> None:
        assert "date" in PHRASE_REQUEST_DATE_CONFIRMATION.lower()

    def test_minimum_spend_phrase_uses_mandatory_language(self) -> None:
        phrase = PHRASE_MINIMUM_SPEND
        assert "mandatory" in phrase.lower()
        assert "optional" not in phrase.lower()
        assert "recommended" not in phrase.lower()

    def test_all_response_goal_phrases_are_non_empty(self) -> None:
        for goal, phrase in APPROVED_PHRASES.items():
            assert phrase, f"Phrase for {goal!r} must not be empty"

    def test_no_phrase_contains_placeholder_url(self) -> None:
        for goal, phrase in APPROVED_PHRASES.items():
            assert "[form link]" not in phrase, f"Phrase for {goal!r} contains placeholder URL"
            assert "http" not in phrase, f"Phrase for {goal!r} contains hardcoded URL"


# ── get_phrase_guidance ────────────────────────────────────────────────────────


class TestGetPhraseGuidance:
    def test_returns_non_empty_for_confirm_available(self) -> None:
        result = get_phrase_guidance("CONFIRM_AVAILABLE")
        assert result != ""
        assert "available" in result.lower()

    def test_returns_non_empty_for_respond_unavailable(self) -> None:
        result = get_phrase_guidance("RESPOND_UNAVAILABLE")
        assert result != ""
        assert "booked" in result.lower()

    def test_returns_non_empty_for_acknowledge(self) -> None:
        result = get_phrase_guidance("ACKNOWLEDGE_AND_CHECK_AVAILABILITY")
        assert result != ""

    def test_returns_empty_for_unknown_goal(self) -> None:
        assert get_phrase_guidance("UNKNOWN_GOAL") == ""

    def test_returns_empty_for_empty_string(self) -> None:
        assert get_phrase_guidance("") == ""

    def test_guidance_format_includes_approved_label(self) -> None:
        result = get_phrase_guidance("CONFIRM_AVAILABLE")
        assert "Approved" in result or "approved" in result


# ── _build_phrase_guidance_line ────────────────────────────────────────────────


class TestBuildPhraseGuidanceLine:
    def test_confirm_available_goal_returns_phrase(self) -> None:
        ctx = _base_context(response_goal="CONFIRM_AVAILABLE")
        line = _build_phrase_guidance_line(ctx)
        assert "available" in line.lower()

    def test_respond_unavailable_goal_returns_phrase(self) -> None:
        ctx = _base_context(response_goal="RESPOND_UNAVAILABLE")
        line = _build_phrase_guidance_line(ctx)
        assert "booked" in line.lower()

    def test_acknowledge_goal_returns_phrase(self) -> None:
        ctx = _base_context(response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY")
        line = _build_phrase_guidance_line(ctx)
        assert "check availability" in line.lower()

    def test_none_goal_defaults_to_acknowledge(self) -> None:
        ctx = _base_context(response_goal=None)
        line = _build_phrase_guidance_line(ctx)
        assert "check availability" in line.lower()

    def test_phrase_guidance_line_in_payload(self) -> None:
        ctx = _base_context(response_goal="CONFIRM_AVAILABLE")
        payload = _build_draft_input_payload(ctx)
        assert "phrase_guidance_line" in payload
        assert payload["phrase_guidance_line"] != ""


# ── V4 prompt — phrase_guidance_line optional variable ────────────────────────


class TestV4PhraseGuidanceVariable:
    def test_phrase_guidance_line_is_optional_variable(self) -> None:
        defn = PromptRegistry().get(PROMPT_KEY_DRAFT_RESPONSE)
        assert "phrase_guidance_line" in defn.optional_variables

    def test_approved_phrases_appear_in_rendered_system_prompt(self) -> None:
        """All approved phrases should be represented in the system template."""
        defn = PromptRegistry().get(PROMPT_KEY_DRAFT_RESPONSE)
        renderer = PromptRenderer()
        payload = {
            "persona_system_prompt": "You are Eleanor.",
            "persona_name": "Eleanor",
            "restaurant_name": "The Grand",
            "persona_tone": "warm",
            "persona_style": "concise",
            "response_goal": "CONFIRM_AVAILABLE",
            "guest_first_name": "Alice",
            "guest_last_name": "Smith",
            "phrase_guidance_line": "",
        }
        rendered = renderer.render_system(defn, payload)
        # Each goal's approved phrase is embedded in the system template
        assert "fully booked" in rendered.lower()
        assert "check availability" in rendered.lower()
        assert "delighted" in rendered.lower() or "available" in rendered.lower()

    def test_minimum_spend_mandatory_language_in_system_prompt(self) -> None:
        defn = PromptRegistry().get(PROMPT_KEY_DRAFT_RESPONSE)
        renderer = PromptRenderer()
        payload = {
            "persona_system_prompt": "You are Eleanor.",
            "persona_name": "Eleanor",
            "restaurant_name": "The Grand",
            "persona_tone": "warm",
            "persona_style": "concise",
            "response_goal": "CONFIRM_AVAILABLE",
            "guest_first_name": "Alice",
            "guest_last_name": "Smith",
            "phrase_guidance_line": "",
        }
        rendered = renderer.render_system(defn, payload)
        assert "MANDATORY" in rendered or "mandatory" in rendered
