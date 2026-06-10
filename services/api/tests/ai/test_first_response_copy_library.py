"""Tests for RESP-017 — First Response Copy Library.

Validates:
- All expected block keys are registered
- render() interpolates variables correctly
- render() raises KeyError for unknown keys
- render() raises ValueError when required variables are missing
- render_safe() returns None instead of raising
- No block contains forbidden topics (menu, special touches, call scheduling,
  alternative dates)
- required_vars() returns the correct set per block
- all_keys() returns a non-empty list
"""

from __future__ import annotations

import pytest

from app.modules.ai.first_response_copy_library import (
    BLOCK_AVAILABILITY_CHECK_NEXT_STEP,
    BLOCK_AVAILABILITY_CONFIRMED,
    BLOCK_AVAILABILITY_NOT_CHECKED,
    BLOCK_AVAILABILITY_UNAVAILABLE,
    BLOCK_BOOKING_NEXT_STEP,
    BLOCK_CLARIFICATION_NEXT_STEP,
    BLOCK_CONFIRM_AVAILABLE_NEXT_STEP,
    BLOCK_MINIMUM_SPEND,
    BLOCK_SIGNOFF,
    FirstResponseCopyLibrary,
)

ALL_BLOCKS = [
    BLOCK_AVAILABILITY_CONFIRMED,
    BLOCK_AVAILABILITY_NOT_CHECKED,
    BLOCK_AVAILABILITY_UNAVAILABLE,
    BLOCK_MINIMUM_SPEND,
    BLOCK_BOOKING_NEXT_STEP,
    BLOCK_CONFIRM_AVAILABLE_NEXT_STEP,
    BLOCK_AVAILABILITY_CHECK_NEXT_STEP,
    BLOCK_CLARIFICATION_NEXT_STEP,
    BLOCK_SIGNOFF,
]

# Variables required by blocks that need them
_AVAIL_VARS = {"meal_period": "dinner", "event_date": "12th June"}
_SPEND_VARS = {"spend_amount": "£1,500"}
_SIGNOFF_VARS = {"persona_name": "Eleanor"}


# ── Registry ──────────────────────────────────────────────────────────────────


class TestRegistry:
    def test_all_keys_non_empty(self) -> None:
        assert len(FirstResponseCopyLibrary.all_keys()) > 0

    @pytest.mark.parametrize("key", ALL_BLOCKS)
    def test_all_blocks_registered(self, key: str) -> None:
        assert key in FirstResponseCopyLibrary.all_keys()

    def test_unknown_key_raises_key_error_for_required_vars(self) -> None:
        with pytest.raises(KeyError):
            FirstResponseCopyLibrary.required_vars("not_a_real_key")


# ── Variable requirements ─────────────────────────────────────────────────────


class TestRequiredVars:
    def test_availability_confirmed_requires_meal_period_and_date(self) -> None:
        req = FirstResponseCopyLibrary.required_vars(BLOCK_AVAILABILITY_CONFIRMED)
        assert "meal_period" in req
        assert "event_date" in req

    def test_availability_not_checked_requires_meal_period_and_date(self) -> None:
        req = FirstResponseCopyLibrary.required_vars(BLOCK_AVAILABILITY_NOT_CHECKED)
        assert "meal_period" in req
        assert "event_date" in req

    def test_availability_unavailable_requires_meal_period_and_date(self) -> None:
        req = FirstResponseCopyLibrary.required_vars(BLOCK_AVAILABILITY_UNAVAILABLE)
        assert "meal_period" in req
        assert "event_date" in req

    def test_minimum_spend_requires_spend_amount(self) -> None:
        req = FirstResponseCopyLibrary.required_vars(BLOCK_MINIMUM_SPEND)
        assert "spend_amount" in req

    def test_booking_next_step_has_no_required_vars(self) -> None:
        req = FirstResponseCopyLibrary.required_vars(BLOCK_BOOKING_NEXT_STEP)
        assert len(req) == 0

    def test_availability_check_next_step_has_no_required_vars(self) -> None:
        req = FirstResponseCopyLibrary.required_vars(BLOCK_AVAILABILITY_CHECK_NEXT_STEP)
        assert len(req) == 0

    def test_clarification_next_step_has_no_required_vars(self) -> None:
        req = FirstResponseCopyLibrary.required_vars(BLOCK_CLARIFICATION_NEXT_STEP)
        assert len(req) == 0

    def test_signoff_requires_persona_name(self) -> None:
        req = FirstResponseCopyLibrary.required_vars(BLOCK_SIGNOFF)
        assert "persona_name" in req


# ── render() ─────────────────────────────────────────────────────────────────


class TestRender:
    def test_availability_confirmed_interpolates_variables(self) -> None:
        result = FirstResponseCopyLibrary.render(BLOCK_AVAILABILITY_CONFIRMED, _AVAIL_VARS)
        assert "dinner" in result
        assert "12th June" in result

    def test_availability_not_checked_interpolates_variables(self) -> None:
        result = FirstResponseCopyLibrary.render(BLOCK_AVAILABILITY_NOT_CHECKED, _AVAIL_VARS)
        assert "dinner" in result
        assert "12th June" in result

    def test_availability_unavailable_interpolates_variables(self) -> None:
        result = FirstResponseCopyLibrary.render(BLOCK_AVAILABILITY_UNAVAILABLE, _AVAIL_VARS)
        assert "dinner" in result
        assert "12th June" in result

    def test_minimum_spend_interpolates_spend_amount(self) -> None:
        result = FirstResponseCopyLibrary.render(BLOCK_MINIMUM_SPEND, _SPEND_VARS)
        assert "£1,500" in result

    def test_minimum_spend_uses_mandatory_framing(self) -> None:
        result = FirstResponseCopyLibrary.render(BLOCK_MINIMUM_SPEND, _SPEND_VARS)
        assert "mandatory" in result.lower()

    def test_booking_next_step_renders_without_variables(self) -> None:
        result = FirstResponseCopyLibrary.render(BLOCK_BOOKING_NEXT_STEP)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_availability_check_next_step_renders_without_variables(self) -> None:
        result = FirstResponseCopyLibrary.render(BLOCK_AVAILABILITY_CHECK_NEXT_STEP)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_clarification_next_step_renders_without_variables(self) -> None:
        result = FirstResponseCopyLibrary.render(BLOCK_CLARIFICATION_NEXT_STEP)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_signoff_interpolates_persona_name(self) -> None:
        result = FirstResponseCopyLibrary.render(BLOCK_SIGNOFF, _SIGNOFF_VARS)
        assert "Eleanor" in result

    def test_unknown_key_raises_key_error(self) -> None:
        with pytest.raises(KeyError):
            FirstResponseCopyLibrary.render("not_a_real_block")

    def test_missing_required_variable_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="meal_period"):
            FirstResponseCopyLibrary.render(BLOCK_AVAILABILITY_CONFIRMED, {"event_date": "12th June"})

    def test_missing_spend_amount_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="spend_amount"):
            FirstResponseCopyLibrary.render(BLOCK_MINIMUM_SPEND, {})

    def test_extra_variables_do_not_break_render(self) -> None:
        vars_ = {**_AVAIL_VARS, "extra_key": "ignored"}
        result = FirstResponseCopyLibrary.render(BLOCK_AVAILABILITY_CONFIRMED, vars_)
        assert "dinner" in result


# ── render_safe() ─────────────────────────────────────────────────────────────


class TestRenderSafe:
    def test_returns_string_on_success(self) -> None:
        result = FirstResponseCopyLibrary.render_safe(BLOCK_AVAILABILITY_CONFIRMED, _AVAIL_VARS)
        assert isinstance(result, str)

    def test_returns_none_for_unknown_key(self) -> None:
        result = FirstResponseCopyLibrary.render_safe("not_a_real_block")
        assert result is None

    def test_returns_none_for_missing_variable(self) -> None:
        result = FirstResponseCopyLibrary.render_safe(BLOCK_AVAILABILITY_CONFIRMED, {})
        assert result is None

    def test_returns_none_with_empty_variables_for_required_block(self) -> None:
        result = FirstResponseCopyLibrary.render_safe(BLOCK_MINIMUM_SPEND)
        assert result is None


# ── Forbidden-topic guardrails ────────────────────────────────────────────────


class TestForbiddenTopicGuardrails:
    """No copy block must contain menu, special-touches, call-scheduling,
    or alternative-date language."""

    FORBIDDEN_PATTERNS = [
        "menu",
        "dietary",
        "special touch",
        "decoration",
        "call us",
        "give us a call",
        "phone us",
        "schedule a call",
        "alternative date",
        "other date",
        "different date",
    ]

    def _render_all(self) -> list[str]:
        rendered = []
        vars_map = {
            BLOCK_AVAILABILITY_CONFIRMED: _AVAIL_VARS,
            BLOCK_AVAILABILITY_NOT_CHECKED: _AVAIL_VARS,
            BLOCK_AVAILABILITY_UNAVAILABLE: _AVAIL_VARS,
            BLOCK_MINIMUM_SPEND: _SPEND_VARS,
            BLOCK_BOOKING_NEXT_STEP: {},
            BLOCK_AVAILABILITY_CHECK_NEXT_STEP: {},
            BLOCK_CLARIFICATION_NEXT_STEP: {},
            BLOCK_SIGNOFF: _SIGNOFF_VARS,
        }
        for key in ALL_BLOCKS:
            text = FirstResponseCopyLibrary.render(key, vars_map.get(key, {}))
            rendered.append(text)
        return rendered

    @pytest.mark.parametrize("pattern", FORBIDDEN_PATTERNS)
    def test_no_block_contains_forbidden_pattern(self, pattern: str) -> None:
        for text in self._render_all():
            assert pattern not in text.lower(), (
                f"Forbidden pattern {pattern!r} found in copy block: {text!r}"
            )

    def test_availability_confirmed_does_not_claim_hosting(self) -> None:
        result = FirstResponseCopyLibrary.render(BLOCK_AVAILABILITY_CONFIRMED, _AVAIL_VARS)
        assert "looking forward to hosting" not in result.lower()
        assert "would be perfect" not in result.lower()

    def test_unavailable_does_not_suggest_alternatives(self) -> None:
        result = FirstResponseCopyLibrary.render(BLOCK_AVAILABILITY_UNAVAILABLE, _AVAIL_VARS)
        assert "alternative" not in result.lower()
        assert "other date" not in result.lower()
        assert "flexible" not in result.lower()


# ── RESP-030: CONFIRM_AVAILABLE next-step block ───────────────────────────────


class TestConfirmAvailableNextStepBlock:
    """RESP-030: constrained next-step block for CONFIRM_AVAILABLE."""

    def test_block_is_registered(self) -> None:
        assert BLOCK_CONFIRM_AVAILABLE_NEXT_STEP in FirstResponseCopyLibrary.all_keys()

    def test_no_required_vars(self) -> None:
        """Block renders with no variables required."""
        text = FirstResponseCopyLibrary.render(BLOCK_CONFIRM_AVAILABLE_NEXT_STEP)
        assert isinstance(text, str)
        assert len(text) > 10

    def test_required_vars_is_empty_set(self) -> None:
        assert FirstResponseCopyLibrary.required_vars(BLOCK_CONFIRM_AVAILABLE_NEXT_STEP) == frozenset()

    def test_contains_proceed_language(self) -> None:
        text = FirstResponseCopyLibrary.render(BLOCK_CONFIRM_AVAILABLE_NEXT_STEP)
        assert "proceed" in text.lower()

    def test_contains_events_team_language(self) -> None:
        text = FirstResponseCopyLibrary.render(BLOCK_CONFIRM_AVAILABLE_NEXT_STEP)
        assert "events team" in text.lower()

    def test_contains_finalise_booking_language(self) -> None:
        text = FirstResponseCopyLibrary.render(BLOCK_CONFIRM_AVAILABLE_NEXT_STEP)
        assert "booking" in text.lower()

    def test_no_menu_language(self) -> None:
        text = FirstResponseCopyLibrary.render(BLOCK_CONFIRM_AVAILABLE_NEXT_STEP)
        for phrase in ("menu", "dietary", "food options"):
            assert phrase not in text.lower(), f"Forbidden phrase {phrase!r} in block"

    def test_no_timing_language(self) -> None:
        text = FirstResponseCopyLibrary.render(BLOCK_CONFIRM_AVAILABLE_NEXT_STEP)
        for phrase in ("preferred timing", "time of day", "start time"):
            assert phrase not in text.lower(), f"Forbidden phrase {phrase!r} in block"

    def test_no_special_requests_language(self) -> None:
        text = FirstResponseCopyLibrary.render(BLOCK_CONFIRM_AVAILABLE_NEXT_STEP)
        for phrase in ("special request", "special arrangement", "decoration"):
            assert phrase not in text.lower(), f"Forbidden phrase {phrase!r} in block"

    def test_no_call_scheduling_language(self) -> None:
        text = FirstResponseCopyLibrary.render(BLOCK_CONFIRM_AVAILABLE_NEXT_STEP)
        for phrase in ("arrange a call", "schedule a call", "give us a call"):
            assert phrase not in text.lower(), f"Forbidden phrase {phrase!r} in block"

    def test_no_additional_details_invitation(self) -> None:
        """Must not invite 'additional details' which leads LLM to ask follow-up questions."""
        text = FirstResponseCopyLibrary.render(BLOCK_CONFIRM_AVAILABLE_NEXT_STEP)
        assert "additional details" not in text.lower()

    def test_render_safe_returns_text(self) -> None:
        text = FirstResponseCopyLibrary.render_safe(BLOCK_CONFIRM_AVAILABLE_NEXT_STEP)
        assert text is not None
        assert len(text) > 10
