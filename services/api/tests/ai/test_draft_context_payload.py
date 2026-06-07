"""Tests for RESP-019 — Remove raw guest message from operational draft prompt context.

Validates:
- guest_message_line no longer contains the full raw message text
- guest_message_line contains structured tone context (audience_type, occasion, tone)
- Operational facts (times, spend, availability) are NOT derived from guest_message_line
- Time tokens (7pm, 7:30pm, 7 or 8pm) are stripped from the tone excerpt
- requested_preferences_line continues to extract time tokens from guest_message
- prohibited_claims_line continues to list forbidden time claims
- When guest_message is None the tone line returns empty string
"""

from __future__ import annotations

import uuid
from dataclasses import replace

import pytest

from app.modules.ai.schemas import DraftContext
from app.modules.ai.service import (
    _build_draft_input_payload,
    _build_guest_tone_line,
    _build_requested_preferences_line,
    _build_prohibited_claims_line,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _base_context(**overrides) -> DraftContext:
    ctx = DraftContext(
        enquiry_id=uuid.uuid4(),
        guest_first_name="Alice",
        guest_last_name="Smith",
        event_type="birthday",
        event_date="2026-06-12",
        party_size=8,
        guest_message=(
            "Hi, do you have availability next Friday for dinner for 8? "
            "It's for my sister's birthday. Around 7ish would be ideal, "
            "but we can be flexible if needed. Thanks, Alice"
        ),
        restaurant_name="The Grand",
        restaurant_description=None,
        persona_name="Eleanor",
        persona_tone="warm and celebratory",
        persona_style="concise",
        persona_system_prompt="You are Eleanor.",
        recommended_minimum_spend=None,
        audience_type="social",
    )
    for k, v in overrides.items():
        ctx = replace(ctx, **{k: v})
    return ctx


# ── Raw message no longer in tone line ────────────────────────────────────────


class TestRawMessageRemoved:
    def test_tone_line_does_not_contain_full_raw_message(self) -> None:
        ctx = _base_context()
        line = _build_guest_tone_line(ctx)
        # The full verbatim message should not appear
        assert "Hi, do you have availability" not in line

    def test_tone_line_does_not_use_old_label(self) -> None:
        ctx = _base_context()
        line = _build_guest_tone_line(ctx)
        assert "Guest message (use for tone and energy only" not in line

    def test_tone_line_contains_structured_label(self) -> None:
        ctx = _base_context()
        line = _build_guest_tone_line(ctx)
        assert "Tone context" in line

    def test_tone_line_returns_empty_when_no_message_or_context(self) -> None:
        ctx = _base_context(
            guest_message=None,
            audience_type=None,
            event_type=None,
            party_size=None,
            persona_tone="",
        )
        assert _build_guest_tone_line(ctx) == ""


# ── Structured tone content ────────────────────────────────────────────────────


class TestStructuredToneContent:
    def test_audience_type_appears_in_tone_line(self) -> None:
        ctx = _base_context(audience_type="corporate")
        line = _build_guest_tone_line(ctx)
        assert "corporate" in line

    def test_occasion_appears_in_tone_line(self) -> None:
        ctx = _base_context(event_type="birthday")
        line = _build_guest_tone_line(ctx)
        assert "birthday" in line

    def test_party_size_appears_in_tone_line(self) -> None:
        ctx = _base_context(party_size=12)
        line = _build_guest_tone_line(ctx)
        assert "12" in line

    def test_persona_tone_appears_in_tone_line(self) -> None:
        ctx = _base_context(persona_tone="warm and celebratory")
        line = _build_guest_tone_line(ctx)
        assert "warm and celebratory" in line

    def test_no_audience_line_when_not_set(self) -> None:
        ctx = _base_context(audience_type=None)
        line = _build_guest_tone_line(ctx)
        assert "Audience type" not in line


# ── Time token stripping ───────────────────────────────────────────────────────


class TestTimeTokenStripping:
    """RESP-019: time tokens must be stripped from the tone excerpt."""

    def test_7pm_stripped_from_excerpt(self) -> None:
        ctx = _base_context(
            guest_message="Hi, around 7pm would be ideal for our dinner. Thanks, Alice"
        )
        line = _build_guest_tone_line(ctx)
        assert "7pm" not in line

    def test_7_30pm_stripped_from_excerpt(self) -> None:
        ctx = _base_context(
            guest_message="We would prefer 7:30pm or thereabouts for the event."
        )
        line = _build_guest_tone_line(ctx)
        assert "7:30pm" not in line
        assert "7:30" not in line

    def test_7_or_8pm_stripped_from_excerpt(self) -> None:
        ctx = _base_context(
            guest_message="Either 7 or 8pm works for us. Looking forward to it."
        )
        line = _build_guest_tone_line(ctx)
        # Specific time reference must not survive into excerpt
        assert "8pm" not in line

    def test_tone_line_contains_no_verbatim_message_text(self) -> None:
        ctx = _base_context(
            guest_message="Around 7pm would be ideal for our group. Thanks."
        )
        line = _build_guest_tone_line(ctx)
        assert "Around 7pm would be ideal" not in line
        assert "Thanks" not in line


# ── Operational fact lines still work ─────────────────────────────────────────


class TestOperationalFactLinesUnaffected:
    """requested_preferences_line and prohibited_claims_line must still extract
    time tokens from guest_message — they are not affected by RESP-019."""

    def test_requested_preferences_extracts_7pm(self) -> None:
        ctx = _base_context(
            guest_message="Around 7pm would be ideal. Thanks."
        )
        line = _build_requested_preferences_line(ctx)
        assert "7" in line

    def test_prohibited_claims_extracts_7pm(self) -> None:
        ctx = _base_context(
            guest_message="Around 7pm would be ideal. Thanks."
        )
        line = _build_prohibited_claims_line(ctx)
        assert "7" in line

    def test_requested_preferences_empty_when_no_times(self) -> None:
        ctx = _base_context(guest_message="Hi, do you have space for a birthday dinner?")
        assert _build_requested_preferences_line(ctx) == ""

    def test_prohibited_claims_empty_when_no_times(self) -> None:
        ctx = _base_context(guest_message="Hi, do you have space for a birthday dinner?")
        assert _build_prohibited_claims_line(ctx) == ""


# ── _build_draft_input_payload integration ────────────────────────────────────


class TestDraftInputPayloadIntegration:
    def test_payload_contains_guest_message_line_key(self) -> None:
        ctx = _base_context()
        payload = _build_draft_input_payload(ctx)
        assert "guest_message_line" in payload

    def test_payload_guest_message_line_does_not_contain_raw_message(self) -> None:
        ctx = _base_context()
        payload = _build_draft_input_payload(ctx)
        # Raw text must not appear verbatim
        assert "Hi, do you have availability next Friday" not in payload["guest_message_line"]

    def test_payload_guest_message_line_is_structured(self) -> None:
        ctx = _base_context()
        payload = _build_draft_input_payload(ctx)
        # Must contain our new structured label
        assert "Tone context" in payload["guest_message_line"]

    def test_payload_requested_preferences_still_present(self) -> None:
        ctx = _base_context(guest_message="I'd prefer 7pm or 7:30pm if possible.")
        payload = _build_draft_input_payload(ctx)
        assert "requested_preferences_line" in payload
        assert payload["requested_preferences_line"] != ""

    def test_payload_prohibited_claims_still_present(self) -> None:
        ctx = _base_context(guest_message="I'd prefer 7pm if possible.")
        payload = _build_draft_input_payload(ctx)
        assert "prohibited_claims_line" in payload
        assert payload["prohibited_claims_line"] != ""


# ── RESP-024: goal-based context pruning ──────────────────────────────────────


class TestGoalBasedContextPruning:
    """RESP-024: payload must vary by response goal — only pass minimum needed."""

    # ── CONFIRM_AVAILABLE ─────────────────────────────────────────────────────

    def test_confirm_available_suppresses_clarification_questions(self) -> None:
        ctx = _base_context(
            response_goal="CONFIRM_AVAILABLE",
            clarification_questions=["What is your preferred start time?"],
        )
        payload = _build_draft_input_payload(ctx)
        assert payload["clarification_questions_line"] == ""

    def test_confirm_available_suppresses_missing_questions(self) -> None:
        ctx = _base_context(
            response_goal="CONFIRM_AVAILABLE",
            missing_questions=["event_date", "party_size"],
        )
        payload = _build_draft_input_payload(ctx)
        assert payload["missing_questions_line"] == ""

    def test_confirm_available_suppresses_requested_preferences(self) -> None:
        ctx = _base_context(
            response_goal="CONFIRM_AVAILABLE",
            guest_message="We'd love 7pm for dinner if possible.",
        )
        payload = _build_draft_input_payload(ctx)
        assert payload["requested_preferences_line"] == ""

    def test_confirm_available_suppresses_prohibited_claims(self) -> None:
        ctx = _base_context(
            response_goal="CONFIRM_AVAILABLE",
            guest_message="Around 7pm would be ideal.",
        )
        payload = _build_draft_input_payload(ctx)
        assert payload["prohibited_claims_line"] == ""

    def test_confirm_available_keeps_room_lines_when_present(self) -> None:
        ctx = _base_context(
            response_goal="CONFIRM_AVAILABLE",
            room_name="Private Dining Room",
            room_seated_capacity=30,
        )
        payload = _build_draft_input_payload(ctx)
        assert payload["room_lines"] != ""
        assert "Private Dining Room" in payload["room_lines"]

    def test_confirm_available_keeps_spend_line(self) -> None:
        ctx = _base_context(
            response_goal="CONFIRM_AVAILABLE",
            recommended_minimum_spend=2500.0,
        )
        payload = _build_draft_input_payload(ctx)
        assert "2,500" in payload["spend_line"]

    # ── ACKNOWLEDGE_AND_CHECK_AVAILABILITY ────────────────────────────────────

    def test_acknowledge_suppresses_room_lines(self) -> None:
        ctx = _base_context(
            response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
            room_name="The Mezzanine",
            room_seated_capacity=40,
            room_suitability_notes="Great for large groups",
        )
        payload = _build_draft_input_payload(ctx)
        assert payload["room_lines"] == ""

    def test_acknowledge_keeps_availability_line(self) -> None:
        ctx = _base_context(
            response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
            availability_status="available",
            availability_date="2026-09-20",
            availability_meal_period="dinner",
        )
        payload = _build_draft_input_payload(ctx)
        assert payload["availability_line"] != ""

    def test_acknowledge_keeps_clarification_questions(self) -> None:
        ctx = _base_context(
            response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
            clarification_questions=["How many guests are attending?"],
        )
        payload = _build_draft_input_payload(ctx)
        assert payload["clarification_questions_line"] != ""

    # ── RESPOND_UNAVAILABLE ───────────────────────────────────────────────────

    def test_respond_unavailable_suppresses_room_lines(self) -> None:
        ctx = _base_context(
            response_goal="RESPOND_UNAVAILABLE",
            room_name="Penthouse Suite",
            room_seated_capacity=80,
        )
        payload = _build_draft_input_payload(ctx)
        assert payload["room_lines"] == ""

    # ── Other goals unaffected ────────────────────────────────────────────────

    def test_request_missing_information_keeps_clarification_questions(self) -> None:
        ctx = _base_context(
            response_goal="REQUEST_MISSING_INFORMATION",
            clarification_questions=["What is the occasion?"],
        )
        payload = _build_draft_input_payload(ctx)
        assert payload["clarification_questions_line"] != ""

    def test_request_missing_information_keeps_requested_preferences(self) -> None:
        ctx = _base_context(
            response_goal="REQUEST_MISSING_INFORMATION",
            guest_message="Would 7pm work for a birthday dinner?",
        )
        payload = _build_draft_input_payload(ctx)
        assert payload["requested_preferences_line"] != ""

    def test_request_missing_information_keeps_room_lines(self) -> None:
        ctx = _base_context(
            response_goal="REQUEST_MISSING_INFORMATION",
            room_name="The Snug",
            room_seated_capacity=12,
        )
        payload = _build_draft_input_payload(ctx)
        assert payload["room_lines"] != ""
