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
    BLOCK_DATE_CONFIRMATION_QUESTION,
    BLOCK_MINIMUM_SPEND,
    BLOCK_SIGNOFF,
    BLOCK_UNAVAILABLE_NO_ALTERNATIVES,
    BLOCK_UNAVAILABLE_ONE_ALTERNATIVE,
    BLOCK_UNAVAILABLE_TWO_ALTERNATIVES,
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


# ── RESP-043: alternative-date copy blocks ────────────────────────────────────


class TestAlternativeDateCopyBlocks:
    """Tests for RESP-043 alternative-date unavailability blocks."""

    def test_no_alternatives_block_renders(self) -> None:
        result = FirstResponseCopyLibrary.render(
            BLOCK_UNAVAILABLE_NO_ALTERNATIVES,
            {"meal_period": "dinner", "requested_date": "15th July"},
        )
        assert "fully booked" in result.lower()
        assert "dinner" in result
        assert "15th July" in result
        # Must not mention alternatives
        assert "alternative" not in result.lower()
        assert "but we do have" not in result.lower()

    def test_one_alternative_block_renders(self) -> None:
        result = FirstResponseCopyLibrary.render(
            BLOCK_UNAVAILABLE_ONE_ALTERNATIVE,
            {
                "meal_period": "dinner",
                "requested_date": "15th July",
                "alternative_date": "14th July",
            },
        )
        assert "fully booked" in result.lower()
        assert "14th July" in result
        assert "15th July" in result

    def test_two_alternatives_block_renders(self) -> None:
        result = FirstResponseCopyLibrary.render(
            BLOCK_UNAVAILABLE_TWO_ALTERNATIVES,
            {
                "meal_period": "dinner",
                "requested_date": "15th July",
                "alternative_date_1": "14th July",
                "alternative_date_2": "16th July",
            },
        )
        assert "fully booked" in result.lower()
        assert "14th July" in result
        assert "16th July" in result
        assert " or " in result

    def test_no_alternatives_missing_var_raises(self) -> None:
        with pytest.raises(ValueError, match="meal_period"):
            FirstResponseCopyLibrary.render(
                BLOCK_UNAVAILABLE_NO_ALTERNATIVES,
                {"requested_date": "15th July"},  # missing meal_period
            )

    def test_one_alternative_missing_alt_raises(self) -> None:
        with pytest.raises(ValueError, match="alternative_date"):
            FirstResponseCopyLibrary.render(
                BLOCK_UNAVAILABLE_ONE_ALTERNATIVE,
                {"meal_period": "dinner", "requested_date": "15th July"},  # missing alternative_date
            )

    def test_two_alternatives_missing_alt2_raises(self) -> None:
        with pytest.raises(ValueError, match="alternative_date_2"):
            FirstResponseCopyLibrary.render(
                BLOCK_UNAVAILABLE_TWO_ALTERNATIVES,
                {
                    "meal_period": "dinner",
                    "requested_date": "15th July",
                    "alternative_date_1": "14th July",
                    # missing alternative_date_2
                },
            )

    def test_all_three_alternative_blocks_are_registered(self) -> None:
        keys = FirstResponseCopyLibrary.all_keys()
        assert BLOCK_UNAVAILABLE_NO_ALTERNATIVES in keys
        assert BLOCK_UNAVAILABLE_ONE_ALTERNATIVE in keys
        assert BLOCK_UNAVAILABLE_TWO_ALTERNATIVES in keys


# ── RESP-051: improved unavailable copy tone ──────────────────────────────────


class TestImprovedUnavailableCopy:
    """RESP-051: warmer tone, invitation to confirm for alternative-date blocks."""

    def test_no_alternatives_contains_empathy_sentence(self) -> None:
        result = FirstResponseCopyLibrary.render(
            BLOCK_UNAVAILABLE_NO_ALTERNATIVES,
            {"meal_period": "dinner", "requested_date": "15th July"},
        )
        # Empathy / warmth sentence present
        assert "thank you" in result.lower()
        # Core unavailability statement
        assert "fully booked" in result.lower()
        # Must NOT suggest alternatives or invite confirmation of a date
        assert "alternative" not in result.lower()
        assert "would that" not in result.lower()
        assert "would either" not in result.lower()
        # Must not mention room names, menus, or pricing
        assert "room" not in result.lower()
        assert "menu" not in result.lower()
        assert "price" not in result.lower()

    def test_one_alternative_invites_guest_to_confirm(self) -> None:
        result = FirstResponseCopyLibrary.render(
            BLOCK_UNAVAILABLE_ONE_ALTERNATIVE,
            {
                "meal_period": "lunch",
                "requested_date": "20th August",
                "alternative_date": "19th August",
            },
        )
        assert "thank you" in result.lower()
        assert "fully booked" in result.lower()
        assert "19th August" in result
        assert "20th August" in result
        # Guest should be invited to confirm
        assert "?" in result
        # Must not mention rooms, menus, or pricing
        assert "room" not in result.lower()
        assert "menu" not in result.lower()

    def test_two_alternatives_invites_guest_to_confirm_either(self) -> None:
        result = FirstResponseCopyLibrary.render(
            BLOCK_UNAVAILABLE_TWO_ALTERNATIVES,
            {
                "meal_period": "dinner",
                "requested_date": "15th July",
                "alternative_date_1": "14th July",
                "alternative_date_2": "16th July",
            },
        )
        assert "thank you" in result.lower()
        assert "fully booked" in result.lower()
        assert "14th July" in result
        assert "16th July" in result
        assert " or " in result
        # Guest should be invited to confirm either date
        assert "?" in result
        # Must not mention rooms, menus, or pricing
        assert "room" not in result.lower()
        assert "menu" not in result.lower()

    def test_no_alternatives_does_not_invent_alternatives(self) -> None:
        result = FirstResponseCopyLibrary.render(
            BLOCK_UNAVAILABLE_NO_ALTERNATIVES,
            {"meal_period": "dinner", "requested_date": "15th July"},
        )
        # Must not mention any date that could be interpreted as an alternative
        assert "but we do have" not in result.lower()
        assert "however" not in result.lower()


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


# ── RESP-057: ISO date auto-formatting in render() ─────────────────────────────


class TestISODateAutoFormatting:
    """RESP-057: render() auto-formats ISO date strings to natural hospitality format."""

    def test_availability_confirmed_iso_date_formatted(self) -> None:
        text = FirstResponseCopyLibrary.render(
            BLOCK_AVAILABILITY_CONFIRMED,
            {"meal_period": "dinner", "event_date": "2026-06-12"},
        )
        assert "2026-06-12" not in text
        assert "Friday, 12 June 2026" in text

    def test_availability_not_checked_iso_date_formatted(self) -> None:
        text = FirstResponseCopyLibrary.render(
            BLOCK_AVAILABILITY_NOT_CHECKED,
            {"meal_period": "lunch", "event_date": "2026-07-04"},
        )
        assert "2026-07-04" not in text
        assert "Saturday, 4 July 2026" in text

    def test_unavailable_no_alternatives_iso_date_formatted(self) -> None:
        text = FirstResponseCopyLibrary.render(
            BLOCK_UNAVAILABLE_NO_ALTERNATIVES,
            {"meal_period": "dinner", "requested_date": "2026-08-15"},
        )
        assert "2026-08-15" not in text
        assert "15 August 2026" in text

    def test_unavailable_one_alternative_all_dates_formatted(self) -> None:
        text = FirstResponseCopyLibrary.render(
            BLOCK_UNAVAILABLE_ONE_ALTERNATIVE,
            {
                "meal_period": "dinner",
                "requested_date": "2026-06-12",
                "alternative_date": "2026-06-19",
            },
        )
        assert "2026-06-12" not in text
        assert "2026-06-19" not in text
        assert "Friday, 12 June 2026" in text
        assert "Friday, 19 June 2026" in text

    def test_unavailable_two_alternatives_all_dates_formatted(self) -> None:
        text = FirstResponseCopyLibrary.render(
            BLOCK_UNAVAILABLE_TWO_ALTERNATIVES,
            {
                "meal_period": "dinner",
                "requested_date": "2026-06-12",
                "alternative_date_1": "2026-06-19",
                "alternative_date_2": "2026-06-26",
            },
        )
        assert "2026-06-12" not in text
        assert "2026-06-19" not in text
        assert "2026-06-26" not in text
        assert "Friday, 12 June 2026" in text
        assert "Friday, 19 June 2026" in text
        assert "Friday, 26 June 2026" in text

    def test_already_formatted_date_passes_through(self) -> None:
        """Pre-formatted dates must not be double-formatted."""
        text = FirstResponseCopyLibrary.render(
            BLOCK_AVAILABILITY_CONFIRMED,
            {"meal_period": "dinner", "event_date": "Friday, 12 June 2026"},
        )
        assert "Friday, 12 June 2026" in text

    def test_non_date_variable_unchanged(self) -> None:
        """Non-date variables must not be altered by the auto-formatter."""
        text = FirstResponseCopyLibrary.render(
            BLOCK_MINIMUM_SPEND,
            {"spend_amount": "£2,500"},
        )
        assert "£2,500" in text

    def test_signoff_persona_name_unchanged(self) -> None:
        text = FirstResponseCopyLibrary.render(
            BLOCK_SIGNOFF,
            {"persona_name": "Sophie"},
        )
        assert "Sophie" in text


# ── RESP-058: Date-confirmation question block ────────────────────────────────


class TestDateConfirmationQuestionBlock:
    """RESP-058: safe date disambiguation block for REQUEST_DATE_CONFIRMATION.

    Must not contain provisional availability language.
    """

    _VARS = {"date_option_1": "7 June", "date_option_2": "6 July"}

    def test_block_is_registered(self) -> None:
        assert BLOCK_DATE_CONFIRMATION_QUESTION in FirstResponseCopyLibrary.all_keys()

    def test_required_vars_includes_both_date_options(self) -> None:
        req = FirstResponseCopyLibrary.required_vars(BLOCK_DATE_CONFIRMATION_QUESTION)
        assert "date_option_1" in req
        assert "date_option_2" in req

    def test_renders_with_date_options(self) -> None:
        text = FirstResponseCopyLibrary.render(BLOCK_DATE_CONFIRMATION_QUESTION, self._VARS)
        assert "7 June" in text
        assert "6 July" in text

    def test_contains_question_mark(self) -> None:
        text = FirstResponseCopyLibrary.render(BLOCK_DATE_CONFIRMATION_QUESTION, self._VARS)
        assert "?" in text

    def test_contains_confirm_language(self) -> None:
        text = FirstResponseCopyLibrary.render(BLOCK_DATE_CONFIRMATION_QUESTION, self._VARS)
        assert "confirm" in text.lower()

    def test_no_provisionally_checked_availability(self) -> None:
        """RESP-058: must not contain provisional availability language."""
        text = FirstResponseCopyLibrary.render(BLOCK_DATE_CONFIRMATION_QUESTION, self._VARS)
        assert "provisionally" not in text.lower()
        assert "checked availability" not in text.lower()
        assert "have checked" not in text.lower()

    def test_says_before_checking_availability(self) -> None:
        """Block must defer availability check explicitly."""
        text = FirstResponseCopyLibrary.render(BLOCK_DATE_CONFIRMATION_QUESTION, self._VARS)
        assert "before checking availability" in text.lower()

    def test_missing_date_option_raises(self) -> None:
        with pytest.raises(ValueError, match="date_option_2"):
            FirstResponseCopyLibrary.render(
                BLOCK_DATE_CONFIRMATION_QUESTION,
                {"date_option_1": "7 June"},
            )

    def test_render_safe_returns_text_with_vars(self) -> None:
        text = FirstResponseCopyLibrary.render_safe(BLOCK_DATE_CONFIRMATION_QUESTION, self._VARS)
        assert text is not None
        assert "7 June" in text

    def test_render_safe_returns_none_missing_var(self) -> None:
        text = FirstResponseCopyLibrary.render_safe(BLOCK_DATE_CONFIRMATION_QUESTION, {})
        assert text is None
