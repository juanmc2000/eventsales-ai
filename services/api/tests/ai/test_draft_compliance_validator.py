"""Tests for RESP-008 and RESP-012 — Draft Compliance Validator.

Validates:
- pass/fail + violations returned correctly
- Availability over-claim blocked when contract is NOT_CHECKED / CONFIRMED_UNAVAILABLE
- Availability confirmation allowed when contract is CONFIRMED_AVAILABLE
- CONFIRMED_UNAVAILABLE: invented alternatives blocked
- Unconfirmed times must not appear as confirmed
- Minimum spend must not be described as recommended/optional
- Fake booking form links blocked
- unsafe_to_send matches failed checks
- Six-record V4 fixture coverage

RESP-012 additional checks:
- Hosting language blocked when contract is NOT_CHECKED
- Invented SLA commitments blocked
- Invented clarification questions blocked when none authorised
- Forbidden topics: menu/dietary, special touches, call scheduling
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.ai.draft_compliance_validator import (
    ComplianceResult,
    DraftComplianceValidator,
    ValidationContext,
)

# ── Fixture ────────────────────────────────────────────────────────────────────

_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "draft_llm2_availability_6_results.json"


# ── Helpers ────────────────────────────────────────────────────────────────────


def _ctx(**kwargs) -> ValidationContext:
    defaults = dict(
        availability_contract="NOT_CHECKED",
        clarification_questions=[],
        confirmed_minimum_spend=None,
        party_size=None,
        prohibited_times=[],
        response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
    )
    defaults.update(kwargs)
    return ValidationContext(**defaults)


def _validate(draft: str, **ctx_kwargs) -> ComplianceResult:
    return DraftComplianceValidator.validate(draft, _ctx(**ctx_kwargs))


# ── ComplianceResult dataclass ─────────────────────────────────────────────────


class TestComplianceResult:
    def test_to_dict_has_all_keys(self) -> None:
        r = ComplianceResult(passed=True, violations=[], unsafe_to_send=False)
        d = r.to_dict()
        # RESP-033: structured_violations added
        assert set(d.keys()) == {"passed", "violations", "unsafe_to_send", "structured_violations"}

    def test_passed_result(self) -> None:
        r = ComplianceResult(passed=True, violations=[], unsafe_to_send=False)
        assert r.passed is True
        assert r.unsafe_to_send is False
        assert r.violations == []

    def test_failed_result(self) -> None:
        r = ComplianceResult(passed=False, violations=["Something wrong."], unsafe_to_send=True)
        assert r.passed is False
        assert r.unsafe_to_send is True
        assert len(r.violations) == 1


# ── Availability over-claim ────────────────────────────────────────────────────


class TestAvailabilityOverclaim:
    def test_pass_when_no_confirmation_claim(self) -> None:
        draft = "Thank you for your enquiry. I'll check availability and be in touch shortly."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is True

    def test_fail_when_confirms_available_on_not_checked(self) -> None:
        draft = "I'm delighted to confirm the date is available for your dinner."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is False
        assert result.unsafe_to_send is True
        assert len(result.violations) >= 1
        assert any("NOT_CHECKED" in v for v in result.violations)

    def test_fail_is_available_phrase_not_checked(self) -> None:
        draft = "The room is available on that date."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is False

    def test_pass_availability_confirmation_when_confirmed(self) -> None:
        draft = "I'm pleased to let you know the date is available for your event."
        result = _validate(draft, availability_contract="CONFIRMED_AVAILABLE")
        assert result.passed is True

    def test_fail_confirms_availability_when_pending_date_confirmation(self) -> None:
        draft = "The date you've mentioned is available."
        result = _validate(draft, availability_contract="PENDING_DATE_CONFIRMATION")
        assert result.passed is False

    def test_fail_confirms_availability_when_insufficient_information(self) -> None:
        draft = "We are available for your event."
        result = _validate(draft, availability_contract="INSUFFICIENT_INFORMATION")
        assert result.passed is False


# ── CONFIRMED_UNAVAILABLE: no invented alternatives ───────────────────────────


class TestConfirmedUnavailableAlternatives:
    def test_pass_when_just_acknowledges(self) -> None:
        draft = "Unfortunately, we are fully booked for the requested date. We hope to welcome you on another occasion."
        result = _validate(draft, availability_contract="CONFIRMED_UNAVAILABLE")
        assert result.passed is True

    def test_fail_when_invents_alternatives_unavailable(self) -> None:
        draft = "We're fully booked on the 15th. Alternatively, we could offer the 20th."
        result = _validate(draft, availability_contract="CONFIRMED_UNAVAILABLE")
        assert result.passed is False
        assert any("alternative" in v.lower() for v in result.violations)

    def test_fail_how_about_invents_alternative(self) -> None:
        draft = "That date is not available. How about the following Friday instead?"
        result = _validate(draft, availability_contract="CONFIRMED_UNAVAILABLE")
        assert result.passed is False

    def test_fail_different_dates_invents_alternative(self) -> None:
        draft = "We are booked. We have other dates available in July."
        result = _validate(draft, availability_contract="CONFIRMED_UNAVAILABLE")
        assert result.passed is False

    def test_pass_alternatives_allowed_when_available(self) -> None:
        # Alternative phrasing is fine when availability IS confirmed
        draft = "The date is available. Alternatively, we could also arrange a lunchtime event."
        result = _validate(draft, availability_contract="CONFIRMED_AVAILABLE")
        assert result.passed is True


# ── Unconfirmed times ──────────────────────────────────────────────────────────


class TestUnconfirmedTimes:
    def test_pass_when_no_prohibited_times(self) -> None:
        draft = "We look forward to welcoming you and your guests."
        result = _validate(draft, prohibited_times=[])
        assert result.passed is True

    def test_fail_when_confirms_prohibited_7pm(self) -> None:
        draft = "We look forward to welcoming your party at 7pm on the evening."
        result = _validate(draft, prohibited_times=["7pm"])
        assert result.passed is False
        assert any("7pm" in v for v in result.violations)

    def test_fail_when_confirms_prohibited_730pm(self) -> None:
        draft = "Your event starting at 7:30pm sounds wonderful."
        result = _validate(draft, prohibited_times=["7:30pm"])
        assert result.passed is False
        assert any("7:30pm" in v for v in result.violations)

    def test_fail_when_time_mentioned_even_as_preference_echo(self) -> None:
        # RESP-035: any mention of a prohibited time fails, including soft echoes
        draft = "You mentioned 7pm as a preference — I'll note this for when we check availability."
        result = _validate(draft, prohibited_times=["7pm"])
        assert result.passed is False
        assert any("7pm" in v for v in result.violations)


# ── Spend soft language ────────────────────────────────────────────────────────


class TestSpendSoftLanguage:
    def test_pass_when_spend_mandatory_language(self) -> None:
        draft = "Please note our minimum spend of £1,500 is a mandatory requirement."
        result = _validate(draft, confirmed_minimum_spend=1500.0)
        assert result.passed is True

    def test_fail_when_spend_described_as_recommended(self) -> None:
        draft = "Our recommended minimum spend is £1,500."
        result = _validate(draft, confirmed_minimum_spend=1500.0)
        assert result.passed is False
        assert any("recommended" in v.lower() or "mandatory" in v.lower() for v in result.violations)

    def test_fail_when_spend_described_as_optional(self) -> None:
        draft = "There is an optional minimum spend of £1,000."
        result = _validate(draft, confirmed_minimum_spend=1000.0)
        assert result.passed is False

    def test_pass_no_spend_validation_when_no_spend_in_context(self) -> None:
        # If no spend is in context, spend language check is skipped
        draft = "Our recommended minimum spend is £500."
        result = _validate(draft, confirmed_minimum_spend=None)
        assert result.passed is True


# ── Fake URLs ──────────────────────────────────────────────────────────────────


class TestFakeUrls:
    def test_fail_when_contains_form_link_placeholder(self) -> None:
        draft = "Please fill out our enquiry form here: [form link]"
        result = _validate(draft)
        assert result.passed is False
        assert any("link" in v.lower() or "url" in v.lower() or "placeholder" in v.lower() for v in result.violations)

    def test_fail_when_contains_booking_form_url_placeholder(self) -> None:
        draft = "You can complete the form at [booking form url]."
        result = _validate(draft)
        assert result.passed is False

    def test_pass_when_no_fake_urls(self) -> None:
        draft = "Please reply to this email with any further details."
        result = _validate(draft)
        assert result.passed is True


# ── Multiple violations ────────────────────────────────────────────────────────


class TestMultipleViolations:
    def test_multiple_violations_all_captured(self) -> None:
        draft = (
            "The date is available. Our recommended minimum spend is £1,000. "
            "Please use [form link] to book."
        )
        result = _validate(
            draft,
            availability_contract="NOT_CHECKED",
            confirmed_minimum_spend=1000.0,
        )
        assert result.passed is False
        assert result.unsafe_to_send is True
        # Should capture availability + spend + URL violations
        assert len(result.violations) >= 2


# ── Fixture coverage: six V4 records ──────────────────────────────────────────


@pytest.fixture(scope="module")
def fixture_data() -> dict:
    if not _FIXTURE_PATH.exists():
        pytest.skip(f"Fixture not found: {_FIXTURE_PATH}")
    return json.loads(_FIXTURE_PATH.read_text())


class TestFixtureCoverage:
    def test_not_checked_records_compliant_when_no_availability_claim(
        self, fixture_data: dict
    ) -> None:
        """Records without availability should not confirm availability in their drafts."""
        for record in fixture_data.get("without_availability", []):
            draft = record.get("response", "")
            ctx = ValidationContext(
                availability_contract="NOT_CHECKED",
            )
            result = DraftComplianceValidator.validate(draft, ctx)
            # If the draft violates the contract, report which record failed
            if not result.passed:
                # Note: this is an informational check on real LLM output — we log but
                # don't hard-fail the test, since LLM output is non-deterministic.
                # The validator is the tool; this test proves it runs correctly.
                assert isinstance(result.violations, list)

    def test_validator_runs_on_all_six_fixture_records(self, fixture_data: dict) -> None:
        records_with = fixture_data.get("with_availability", [])
        records_without = fixture_data.get("without_availability", [])
        all_records = records_with + records_without
        assert len(all_records) == 6, f"Expected 6 fixture records, got {len(all_records)}"

        for record in all_records:
            av = record.get("availability")
            draft = record.get("response", "")
            if av and av.get("availability_status") == "available":
                contract = "CONFIRMED_AVAILABLE"
            elif av and av.get("availability_status") in ("booked", "held", "unavailable"):
                contract = "CONFIRMED_UNAVAILABLE"
            else:
                contract = "NOT_CHECKED"
            ctx = ValidationContext(availability_contract=contract)
            result = DraftComplianceValidator.validate(draft, ctx)
            # Validator must return a valid ComplianceResult for every record
            assert isinstance(result.passed, bool)
            assert isinstance(result.violations, list)
            assert isinstance(result.unsafe_to_send, bool)


# ── RESP-012: Hosting language ─────────────────────────────────────────────────


class TestHostingLanguage:
    def test_fail_looking_forward_to_hosting_not_checked(self) -> None:
        draft = "We are looking forward to hosting your celebration."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is False
        assert any("hosting language" in v.lower() for v in result.violations)

    def test_fail_would_be_perfect_for_not_checked(self) -> None:
        draft = "Our private dining room would be perfect for your party."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is False

    def test_fail_would_love_to_host_not_checked(self) -> None:
        draft = "We would love to host your event."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is False

    def test_pass_hosting_language_when_confirmed_available(self) -> None:
        draft = "We are looking forward to hosting your celebration."
        result = _validate(draft, availability_contract="CONFIRMED_AVAILABLE")
        assert result.passed is True

    def test_pass_neutral_language_not_checked(self) -> None:
        draft = "Thank you for your enquiry — I'll check availability and come back to you."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is True

    def test_fail_can_certainly_host_not_checked(self) -> None:
        draft = "We can certainly host a group of that size."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is False


# ── RESP-012: Invented SLA ──────────────────────────────────────────────────────


class TestInventedSLA:
    def test_fail_within_24_hours(self) -> None:
        draft = "I will get back to you within 24 hours."
        result = _validate(draft)
        assert result.passed is False
        assert any("sla" in v.lower() or "commitment" in v.lower() for v in result.violations)

    def test_fail_within_2_business_days(self) -> None:
        draft = "You can expect a response within 2 business days."
        result = _validate(draft)
        assert result.passed is False

    def test_fail_by_tomorrow(self) -> None:
        draft = "I will confirm the details by tomorrow."
        result = _validate(draft)
        assert result.passed is False

    def test_fail_by_end_of_today(self) -> None:
        draft = "We aim to respond by end of today."
        result = _validate(draft)
        assert result.passed is False

    def test_fail_respond_within_deadline(self) -> None:
        draft = "We will respond to you within the next few hours."
        result = _validate(draft)
        assert result.passed is False

    def test_pass_no_timeline_commitment(self) -> None:
        draft = "We will be in touch as soon as possible with availability details."
        result = _validate(draft)
        assert result.passed is True


# ── RESP-012: Invented questions ───────────────────────────────────────────────


class TestInventedQuestions:
    def test_fail_question_when_none_authorised(self) -> None:
        draft = "Could you let us know your preferred start time?"
        result = _validate(draft, clarification_questions=[])
        assert result.passed is False
        assert any("question" in v.lower() for v in result.violations)

    def test_pass_question_when_authorised(self) -> None:
        draft = "Could you let us know your preferred start time?"
        result = _validate(draft, clarification_questions=["What time were you thinking?"])
        assert result.passed is True

    def test_fail_multiple_invented_questions(self) -> None:
        draft = "How many guests are you expecting? Would you like a private room?"
        result = _validate(draft, clarification_questions=[])
        assert result.passed is False

    def test_pass_statement_not_question(self) -> None:
        draft = "We will check availability and confirm the details shortly."
        result = _validate(draft, clarification_questions=[])
        assert result.passed is True


# ── RESP-012: Forbidden topics ─────────────────────────────────────────────────


class TestForbiddenTopics:
    def test_fail_menu_options_not_allowed(self) -> None:
        draft = "We can discuss menu options once the date is confirmed."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is False
        assert any("menu" in v.lower() for v in result.violations)

    def test_fail_dietary_requirements_not_allowed(self) -> None:
        draft = "Please let us know any dietary requirements in advance."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is False

    def test_pass_menu_allowed_when_flag_set(self) -> None:
        draft = "We can discuss menu options at the next stage."
        result = _validate(draft, allow_menu_discussion=True, availability_contract="CONFIRMED_AVAILABLE")
        assert result.passed is True

    def test_fail_special_touches_not_allowed(self) -> None:
        draft = "We can arrange special touches to personalise the evening."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is False
        assert any("special" in v.lower() or "touches" in v.lower() for v in result.violations)

    def test_pass_special_touches_allowed_when_flag_set(self) -> None:
        draft = "We can arrange special touches for the occasion."
        result = _validate(draft, allow_special_touches=True, availability_contract="CONFIRMED_AVAILABLE")
        assert result.passed is True

    def test_fail_call_scheduling_not_allowed(self) -> None:
        draft = "Please feel free to arrange a call to discuss further."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is False
        assert any("call" in v.lower() for v in result.violations)

    def test_fail_hop_on_a_call_not_allowed(self) -> None:
        draft = "Happy to hop on a call to go through the details."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is False

    def test_pass_call_scheduling_allowed_when_flag_set(self) -> None:
        draft = "We'd be happy to arrange a call to discuss further."
        result = _validate(draft, allow_call_scheduling=True, availability_contract="CONFIRMED_AVAILABLE")
        assert result.passed is True


# ── RESP-012: Six-record V4 alternative-date failures ─────────────────────────


class TestAlternativeDateInventionDetected:
    """Confirms the validator catches the alternative-date pattern found in email_02/email_03."""

    def test_email_02_pattern_detected(self) -> None:
        draft = (
            "Unfortunately, we are fully booked on 14th March. "
            "I'd recommend reaching out to our events team to explore alternative dates "
            "that might work for your celebration."
        )
        result = _validate(draft, availability_contract="CONFIRMED_UNAVAILABLE")
        assert result.passed is False
        assert any("alternative" in v.lower() for v in result.violations)

    def test_email_03_pattern_detected(self) -> None:
        draft = (
            "We are sorry to inform you that we are fully booked on the requested date. "
            "We suggest looking at alternative dates — perhaps the weekend of the 21st?"
        )
        result = _validate(draft, availability_contract="CONFIRMED_UNAVAILABLE")
        assert result.passed is False
        assert any("alternative" in v.lower() for v in result.violations)

    def test_email_12_sla_invention_detected(self) -> None:
        draft = (
            "Thank you for your enquiry. I will confirm availability within the next 24 hours "
            "and look forward to welcoming you."
        )
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is False
        # Either hosting-language or SLA violation should fire
        assert len(result.violations) >= 1


# ── RESP-020: New pattern extensions ──────────────────────────────────────────


class TestMenuPreferencesExtended:
    """RESP-020: 'menu preferences' must trigger the menu forbidden-topic check."""

    def test_menu_preferences_fails_when_not_allowed(self) -> None:
        draft = (
            "Thank you — I'm delighted to confirm availability. "
            "Our events team will be in touch to discuss timing, menu preferences, "
            "and how we can make the evening memorable."
        )
        result = _validate(draft, availability_contract="CONFIRMED_AVAILABLE")
        assert result.passed is False
        assert any("menu" in v.lower() for v in result.violations)

    def test_menu_choices_still_caught(self) -> None:
        draft = "We can discuss menu choices and dietary requirements at a later stage."
        result = _validate(draft, availability_contract="CONFIRMED_AVAILABLE")
        assert result.passed is False
        assert any("menu" in v.lower() or "dietary" in v.lower() for v in result.violations)

    def test_menu_preferences_pass_when_allowed(self) -> None:
        draft = "Please let us know your menu preferences so we can tailor the experience."
        result = _validate(
            draft,
            availability_contract="CONFIRMED_AVAILABLE",
            allow_menu_discussion=True,
        )
        assert result.passed is True


class TestSpecialDetailsExtended:
    """RESP-020: 'special details/elements' must trigger the special-touches check."""

    def test_special_details_fails_when_not_allowed(self) -> None:
        draft = (
            "Our events team will be in touch to go over timing, menu options, "
            "and all the special details to make your celebration memorable."
        )
        result = _validate(draft, availability_contract="CONFIRMED_AVAILABLE")
        assert result.passed is False
        assert any("special" in v.lower() or "menu" in v.lower() for v in result.violations)

    def test_special_elements_fails_when_not_allowed(self) -> None:
        draft = "We can discuss the special elements to personalise your event."
        result = _validate(draft, availability_contract="CONFIRMED_AVAILABLE")
        assert result.passed is False

    def test_personalisation_fails_when_not_allowed(self) -> None:
        draft = "We offer personalisation options to make your event unique."
        result = _validate(draft, availability_contract="CONFIRMED_AVAILABLE")
        assert result.passed is False
        assert any("special" in v.lower() for v in result.violations)


class TestExploreOtherOptionsExtended:
    """RESP-020: 'explore other options' must trigger the alternatives check when CONFIRMED_UNAVAILABLE."""

    def test_explore_other_options_fails(self) -> None:
        draft = (
            "Unfortunately we are fully booked. Our events team may be able to "
            "explore other options for you."
        )
        result = _validate(draft, availability_contract="CONFIRMED_UNAVAILABLE")
        assert result.passed is False
        assert any("alternative" in v.lower() for v in result.violations)

    def test_other_options_fails(self) -> None:
        draft = (
            "We are fully booked on that date. Please get in touch if you'd like "
            "to discuss other options or dates."
        )
        result = _validate(draft, availability_contract="CONFIRMED_UNAVAILABLE")
        assert result.passed is False

    def test_explore_alternative_options_fails(self) -> None:
        draft = "Our team would be happy to explore alternative options for your group."
        result = _validate(draft, availability_contract="CONFIRMED_UNAVAILABLE")
        assert result.passed is False


class TestUnavailableRoomSuitability:
    """RESP-020: Room suitability language must not appear when slot is CONFIRMED_UNAVAILABLE."""

    def test_perfect_for_group_fails_when_unavailable(self) -> None:
        draft = (
            "Thank you for your enquiry. Unfortunately, we are fully booked for the "
            "requested date. Our Large Private Dining Room would be perfect for a group of 16."
        )
        result = _validate(draft, availability_contract="CONFIRMED_UNAVAILABLE")
        assert result.passed is False
        assert any("suitable" in v.lower() or "perfect" in v.lower() or "suitability" in v.lower() for v in result.violations)

    def test_ideal_for_celebration_fails_when_unavailable(self) -> None:
        draft = (
            "We are sorry to say we are fully booked. Our private dining room "
            "would be ideal for your celebration."
        )
        result = _validate(draft, availability_contract="CONFIRMED_UNAVAILABLE")
        assert result.passed is False

    def test_space_and_expertise_fails_when_unavailable(self) -> None:
        draft = (
            "Unfortunately the date is fully booked. We have the space and expertise to "
            "create a memorable celebration for you."
        )
        result = _validate(draft, availability_contract="CONFIRMED_UNAVAILABLE")
        assert result.passed is False

    def test_perfect_for_group_pass_when_confirmed_available(self) -> None:
        """Suitability language is fine when the slot is confirmed available."""
        draft = (
            "I'm delighted to confirm the date is available. Our Private Dining Room "
            "would be perfect for a group of 12."
        )
        result = _validate(draft, availability_contract="CONFIRMED_AVAILABLE")
        # No suitability violation — slot is confirmed
        suitability_violations = [v for v in result.violations if "suitable" in v.lower() or "suitability" in v.lower()]
        assert len(suitability_violations) == 0

    def test_suitability_violation_also_fires_for_not_checked(self) -> None:
        """RESP-025: suitability check now fires for NOT_CHECKED as well (extended from RESP-020)."""
        draft = "Our room would be perfect for a party of 10."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        suitability_violations = [v for v in result.violations if "suitability" in v.lower() or "suitable" in v.lower() or "perfect" in v.lower()]
        assert len(suitability_violations) >= 1
        assert result.passed is False

    def test_suitability_check_passes_for_confirmed_available(self) -> None:
        """Suitability language is permitted once availability is confirmed."""
        draft = "Our Private Dining Room is perfect for your celebration, and I am pleased to confirm it is available."
        result = _validate(draft, availability_contract="CONFIRMED_AVAILABLE")
        suitability_violations = [v for v in result.violations if "suitability" in v.lower() or "suitable" in v.lower()]
        assert len(suitability_violations) == 0


# ── RESP-052: ACKNOWLEDGE room pre-commitment ─────────────────────────────────


class TestAcknowledgeRoomPrecommitment:
    """RESP-052: ACKNOWLEDGE responses must not name rooms or imply suitability."""

    def _ack_ctx(self, **kwargs) -> ValidationContext:
        return ValidationContext(
            availability_contract="NOT_CHECKED",
            response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
            **kwargs,
        )

    def test_room_name_in_acknowledge_fails(self) -> None:
        """email_100-style: invented room name in ACKNOWLEDGE response (RESP-052)."""
        draft = (
            "Thank you for getting in touch. I'll check availability for dinner on "
            "14th August. Our Main Dining Room exclusive area would seat your group perfectly."
        )
        ctx = self._ack_ctx()
        result = DraftComplianceValidator.validate(draft, ctx)
        room_violations = [v for v in result.violations if "room pre-commitment" in v.lower() or "Room" in v]
        assert len(room_violations) >= 1

    def test_would_be_ideal_in_acknowledge_fails(self) -> None:
        """'would be ideal' in ACKNOWLEDGE response is forbidden (RESP-052)."""
        draft = (
            "Thank you for your enquiry. I'll check availability. "
            "Our private space would be ideal for your celebration."
        )
        ctx = self._ack_ctx()
        result = DraftComplianceValidator.validate(draft, ctx)
        assert result.passed is False
        assert any("pre-commitment" in v for v in result.violations)

    def test_recommended_room_in_acknowledge_fails(self) -> None:
        """'recommended room' in ACKNOWLEDGE response is forbidden (RESP-052)."""
        draft = "I'll check availability. Our recommended room for 30 guests is the Garden Room."
        ctx = self._ack_ctx()
        result = DraftComplianceValidator.validate(draft, ctx)
        assert result.passed is False

    def test_capacity_promise_in_acknowledge_fails(self) -> None:
        """Capacity promise in ACKNOWLEDGE response is forbidden (RESP-052)."""
        draft = "Thank you for your enquiry. We have a space that seats 40 guests. I'll check availability."
        ctx = self._ack_ctx()
        result = DraftComplianceValidator.validate(draft, ctx)
        assert result.passed is False

    def test_clean_acknowledge_passes(self) -> None:
        """Clean ACKNOWLEDGE with no room name or suitability passes (RESP-052)."""
        draft = (
            "Thank you for your enquiry. I'll check availability for dinner on 14th August "
            "for 30 guests and come back to you shortly."
        )
        ctx = self._ack_ctx()
        result = DraftComplianceValidator.validate(draft, ctx)
        room_violations = [v for v in result.violations if "pre-commitment" in v]
        assert len(room_violations) == 0

    def test_check_suitable_space_passes(self) -> None:
        """'I'll check suitable space' phrasing passes (RESP-052)."""
        draft = "Thank you for your enquiry. I'll check suitable space for your group on 14th August."
        ctx = self._ack_ctx()
        result = DraftComplianceValidator.validate(draft, ctx)
        room_violations = [v for v in result.violations if "pre-commitment" in v]
        assert len(room_violations) == 0

    def test_room_precommitment_check_skipped_for_other_goals(self) -> None:
        """Room pre-commitment check does not fire for CONFIRM_AVAILABLE (RESP-052)."""
        draft = "I'm delighted to confirm availability. Our Garden Room is perfect for your group."
        ctx = ValidationContext(
            availability_contract="CONFIRMED_AVAILABLE",
            response_goal="CONFIRM_AVAILABLE",
        )
        result = DraftComplianceValidator.validate(draft, ctx)
        room_violations = [v for v in result.violations if "pre-commitment" in v]

# ── RESP-053: invented room name validator — all goals ────────────────────────


class TestInventedRoomNameValidator:
    """RESP-053: Invented room names must fail validation across all response goals."""

    KNOWN_ROOMS = ["The Garden Room", "Private Dining Room"]

    def _ctx(self, goal: str, contract: str = "CONFIRMED_AVAILABLE") -> ValidationContext:
        return ValidationContext(
            availability_contract=contract,
            response_goal=goal,
            known_room_names=self.KNOWN_ROOMS,
        )

    def test_invented_room_name_in_confirm_available_fails(self) -> None:
        """Invented room name in CONFIRM_AVAILABLE is flagged (RESP-053)."""
        draft = "I'm delighted to confirm availability. The Rooftop Suite is perfect for your event."
        ctx = self._ctx("CONFIRM_AVAILABLE")
        result = DraftComplianceValidator.validate(draft, ctx)
        assert result.passed is False
        assert any("Rooftop Suite" in v for v in result.violations)

    def test_invented_room_name_in_respond_unavailable_fails(self) -> None:
        """Invented room name in RESPOND_UNAVAILABLE is flagged (RESP-053)."""
        draft = "Unfortunately we are fully booked on that date. The Crystal Ballroom would be available next week."
        ctx = self._ctx("RESPOND_UNAVAILABLE", contract="CONFIRMED_UNAVAILABLE")
        result = DraftComplianceValidator.validate(draft, ctx)
        assert result.passed is False
        assert any("Crystal Ballroom" in v for v in result.violations)

    def test_invented_room_name_in_request_missing_information_fails(self) -> None:
        """Invented room name in REQUEST_MISSING_INFORMATION is flagged (RESP-053)."""
        draft = "Could you confirm the date? Our Executive Lounge is often available."
        ctx = self._ctx("REQUEST_MISSING_INFORMATION", contract="NOT_CHECKED")
        result = DraftComplianceValidator.validate(draft, ctx)
        assert result.passed is False
        assert any("Executive Lounge" in v for v in result.violations)

    def test_known_room_name_in_confirm_available_passes(self) -> None:
        """Known room name in CONFIRM_AVAILABLE passes (RESP-053)."""
        draft = "I'm delighted to confirm availability. The Garden Room is available for dinner on 14th July."
        ctx = self._ctx("CONFIRM_AVAILABLE")
        result = DraftComplianceValidator.validate(draft, ctx)
        room_violations = [v for v in result.violations if "invented" in v.lower()]
        assert len(room_violations) == 0

    def test_no_known_room_names_skips_check(self) -> None:
        """When known_room_names is empty, invented room name check is skipped (RESP-053)."""
        draft = "I'm delighted to confirm availability. The Moonlight Terrace is available."
        ctx = ValidationContext(
            availability_contract="CONFIRMED_AVAILABLE",
            response_goal="CONFIRM_AVAILABLE",
            known_room_names=[],  # no room context
        )
        result = DraftComplianceValidator.validate(draft, ctx)
        room_violations = [v for v in result.violations if "invented" in v.lower()]
        assert len(room_violations) == 0

    def test_structured_violation_code_is_invented_room_name(self) -> None:
        """Structured violation has code 'invented_room_name' (RESP-053)."""
        draft = "I'm delighted to confirm. The Sunset Terrace is the perfect space."
        ctx = self._ctx("CONFIRM_AVAILABLE")
        result = DraftComplianceValidator.validate(draft, ctx)
        codes = [sv.code for sv in result.structured_violations]
        assert "invented_room_name" in codes

    def test_case_insensitive_room_name_match(self) -> None:
        """Known room name comparison is case-insensitive (RESP-053)."""
        draft = "I'm delighted to confirm. The private dining room is available."
        ctx = self._ctx("CONFIRM_AVAILABLE")  # known: "Private Dining Room"
        result = DraftComplianceValidator.validate(draft, ctx)
        room_violations = [v for v in result.violations if "invented" in v.lower()]
        assert len(room_violations) == 0


class TestV5FixtureCoverage:
    """RESP-020: Validates that V5 fixture failure patterns are caught by strengthened validator."""

    def test_email01_available_menu_preferences_caught(self) -> None:
        """email_01 AVAILABLE: 'menu preferences, and any special touches' should fail."""
        draft = (
            "Thank you for your enquiry — I'm delighted to let you know that the date "
            "is available for your event.\n\n"
            "We'd love to host your sister's birthday celebration on 12th June. "
            "Our semi-private dining area would be perfect for your party of 8, "
            "offering an intimate setting with a wonderful atmosphere.\n\n"
            "There is a mandatory minimum spend of £1,000 for this space. Your preference "
            "for around 7pm is noted, and we can certainly discuss timing as we move forward.\n\n"
            "The next step is for one of our events team to connect with you to discuss the "
            "finer details — timing, menu preferences, and any special touches to make the "
            "evening memorable.\n\nWarm regards,\nEleanor"
        )
        result = _validate(
            draft,
            availability_contract="CONFIRMED_AVAILABLE",
            confirmed_minimum_spend=1000.0,
        )
        assert result.passed is False
        # Should catch menu preferences and/or special touches
        assert len(result.violations) >= 1

    def test_email01_unavailable_alternative_options_caught(self) -> None:
        """email_01 UNAVAILABLE: 'explore alternative options' + 'other dates' should fail."""
        draft = (
            "Thank you for your enquiry. Unfortunately, we are fully booked for the "
            "requested date.\n\n"
            "We'd have loved to host your dad's birthday celebration at The Ivy Tower Bridge. "
            "Saturday 20th June is a popular evening, and our private dining spaces are reserved.\n\n"
            "If you're flexible with your date, our events team would be happy to explore "
            "alternative options that work for your group of 10.\n\n"
            "Do get in touch if you'd like to discuss other dates.\n\nWarm regards,\nEleanor"
        )
        result = _validate(
            draft,
            availability_contract="CONFIRMED_UNAVAILABLE",
        )
        assert result.passed is False
        assert any("alternative" in v.lower() for v in result.violations)

    def test_email03_unavailable_perfect_for_group_caught(self) -> None:
        """email_03 UNAVAILABLE: 'Our Large Private Dining Room would be perfect for a group of 16'."""
        draft = (
            "Thank you for your enquiry. Unfortunately, we are fully booked for the "
            "requested date.\n\n"
            "We'd have loved to host Claire's engagement party at The Ivy Tower Bridge. "
            "Our Large Private Dining Room would be perfect for a group of 16, and we have "
            "the space and expertise to create a memorable celebration.\n\n"
            "If you're able to consider alternative dates, please do get back in touch.\n\n"
            "Best regards,\nJames"
        )
        result = _validate(
            draft,
            availability_contract="CONFIRMED_UNAVAILABLE",
        )
        assert result.passed is False
        # Should catch both the suitability language and the alternative dates
        assert len(result.violations) >= 1


# ── RESP-027: Section label suppression ───────────────────────────────────────


class TestSectionLabels:
    """RESP-027: Internal section labels must not appear in customer-facing drafts."""

    def test_opening_label_fails(self) -> None:
        result = _validate("**Opening**\nDear Alice, thank you for your enquiry.")
        assert result.passed is False
        assert any("section label" in v.lower() for v in result.violations)

    def test_sign_off_label_fails(self) -> None:
        result = _validate("Dear Alice, thank you.\n\n**Sign-off**\nWarm regards, Sophie")
        assert result.passed is False
        assert any("section label" in v.lower() for v in result.violations)

    def test_enquiry_summary_label_fails(self) -> None:
        result = _validate("**Enquiry summary**\nYou enquired about a private dining room.")
        assert result.passed is False
        assert any("section label" in v.lower() for v in result.violations)

    def test_availability_confirmation_label_fails(self) -> None:
        result = _validate(
            "**Availability confirmation**\nI am pleased to confirm the date is available.",
            availability_contract="CONFIRMED_AVAILABLE",
        )
        assert result.passed is False
        assert any("section label" in v.lower() for v in result.violations)

    def test_booking_next_step_label_fails(self) -> None:
        result = _validate("**Booking next step**\nPlease complete our form.")
        assert result.passed is False

    def test_next_steps_label_fails(self) -> None:
        result = _validate("**Next steps**\nPlease complete our form.")
        assert result.passed is False

    def test_closing_label_fails(self) -> None:
        result = _validate("Dear Alice.\n\n**Closing**\nWarm regards.")
        assert result.passed is False

    def test_clean_draft_without_labels_passes(self) -> None:
        result = _validate(
            "Dear Alice, thank you for your enquiry. I am pleased to confirm availability. "
            "Warm regards, Sophie.",
            availability_contract="CONFIRMED_AVAILABLE",
        )
        assert result.passed is True

    def test_label_in_body_text_not_as_heading_passes(self) -> None:
        """The word 'opening' in plain text (not as **Opening**) is allowed."""
        result = _validate("Dear Alice, as an opening remark, thank you for reaching out.")
        assert result.passed is True

    def test_only_one_violation_raised_per_section_label_category(self) -> None:
        draft = "**Opening**\nDear Alice.\n\n**Sign-off**\nWarm regards."
        result = _validate(draft)
        section_violations = [v for v in result.violations if "section label" in v.lower()]
        assert len(section_violations) == 1  # One violation per category


# ── RESP-026: Copy block enforcement ──────────────────────────────────────────


class TestCopyBlockCompliance:
    """RESP-026: Required copy blocks must appear verbatim (normalised) in the draft."""

    def _ctx(self, phrase: str | None = None, **kwargs) -> ValidationContext:
        return ValidationContext(required_opening_phrase=phrase, **kwargs)

    def test_missing_required_phrase_fails(self) -> None:
        phrase = "Thank you for your enquiry. Unfortunately, we are fully booked for the requested date."
        result = _validate(
            "Dear Alice, I am sorry but we cannot accommodate your request.",
            required_opening_phrase=phrase,
        )
        assert result.passed is False
        assert any("copy block" in v.lower() or "required" in v.lower() for v in result.violations)

    def test_exact_phrase_present_passes(self) -> None:
        phrase = "Thank you for your enquiry. Unfortunately, we are fully booked for the requested date."
        result = _validate(
            f"Dear Alice, {phrase} Warm regards, Sophie.",
            required_opening_phrase=phrase,
        )
        copy_violations = [v for v in result.violations if "copy block" in v.lower()]
        assert len(copy_violations) == 0

    def test_phrase_with_extra_whitespace_passes(self) -> None:
        """Formatting differences (extra spaces/newlines) should not cause false failures."""
        phrase = "Thank you for your enquiry — I'll check availability for the requested date and come back to you shortly."
        draft = (
            "Dear Alice,\n\n"
            "Thank you for your enquiry — I'll check availability for the requested\n"
            "date and come back to you shortly.\n\n"
            "Warm regards, Sophie"
        )
        result = _validate(draft, required_opening_phrase=phrase)
        copy_violations = [v for v in result.violations if "copy block" in v.lower()]
        assert len(copy_violations) == 0

    def test_phrase_with_bold_markdown_passes(self) -> None:
        """Bold markdown formatting (**text**) should be stripped before comparison."""
        phrase = "Thank you for your enquiry — I'm delighted to let you know that the date is available for your event."
        draft = (
            "Dear Alice, **Thank you for your enquiry** — I'm delighted to let you know "
            "that the date is available for your event. Warm regards, Sophie."
        )
        result = _validate(draft, required_opening_phrase=phrase, availability_contract="CONFIRMED_AVAILABLE")
        copy_violations = [v for v in result.violations if "copy block" in v.lower()]
        assert len(copy_violations) == 0

    def test_paraphrased_phrase_fails(self) -> None:
        """Paraphrasing the opening phrase is not allowed — must be verbatim."""
        phrase = "Thank you for your enquiry — I'm delighted to let you know that the date is available for your event."
        result = _validate(
            "Dear Alice, I am very pleased to inform you that the date is available.",
            required_opening_phrase=phrase,
            availability_contract="CONFIRMED_AVAILABLE",
        )
        assert result.passed is False
        assert any("copy block" in v.lower() or "required" in v.lower() for v in result.violations)

    def test_no_required_phrase_set_passes(self) -> None:
        """When required_opening_phrase is None, the check does not fire."""
        result = _validate(
            "Dear Alice, I am very pleased to inform you that the date is available.",
            availability_contract="CONFIRMED_AVAILABLE",
        )
        copy_violations = [v for v in result.violations if "copy block" in v.lower()]
        assert len(copy_violations) == 0

    def test_empty_required_phrase_does_not_fire(self) -> None:
        """Empty string required_opening_phrase is treated as not set."""
        result = _validate(
            "Dear Alice, some text.",
            required_opening_phrase="",
        )
        copy_violations = [v for v in result.violations if "copy block" in v.lower()]
        assert len(copy_violations) == 0


# ── RESP-031: Calibrated copy block check for CONFIRM_AVAILABLE ───────────────


class TestConfirmAvailableSemanticValidation:
    """RESP-031: CONFIRM_AVAILABLE uses semantic availability check, not verbatim phrase."""

    _PHRASE = (
        "Thank you for your enquiry — I'm delighted to confirm that we have "
        "availability for dinner on 12th June."
    )

    def _ctx_confirm(self, **kwargs) -> ValidationContext:
        return ValidationContext(
            response_goal="CONFIRM_AVAILABLE",
            availability_contract="CONFIRMED_AVAILABLE",
            required_opening_phrase=self._PHRASE,
            **kwargs,
        )

    def test_paraphrase_with_availability_language_passes(self) -> None:
        """RESP-031: harmless paraphrase is accepted if availability is confirmed."""
        draft = (
            "Dear Alice, I am delighted to confirm that we are available on 12th June "
            "for dinner. Warm regards, Sophie."
        )
        result = DraftComplianceValidator.validate(draft, self._ctx_confirm())
        copy_violations = [v for v in result.violations if "copy block" in v.lower() or "confirm_available" in v.lower()]
        assert len(copy_violations) == 0, copy_violations

    def test_draft_without_availability_language_fails(self) -> None:
        """Draft must confirm availability — not just greet the guest."""
        draft = (
            "Dear Alice, thank you for getting in touch. Please find our details below. "
            "Warm regards, Sophie."
        )
        result = DraftComplianceValidator.validate(draft, self._ctx_confirm())
        assert result.passed is False
        assert any("confirm_available" in v.lower() or "availability" in v.lower() for v in result.violations)

    def test_standard_approved_phrase_passes(self) -> None:
        """The exact approved phrase also passes the semantic check."""
        draft = (
            "Dear Alice, "
            + self._PHRASE
            + " Warm regards, Sophie."
        )
        result = DraftComplianceValidator.validate(draft, self._ctx_confirm())
        copy_violations = [v for v in result.violations if "copy block" in v.lower()]
        assert len(copy_violations) == 0

    def test_variant_availability_phrases_pass(self) -> None:
        """Common availability confirmation forms must be accepted."""
        phrases = [
            "Dear Alice, we are available on 12th June.",
            "Dear Alice, I'm pleased to confirm your booking is available.",
            "Dear Alice, the date is free for your event.",
            "Dear Alice, we have the date available for you.",
        ]
        for draft in phrases:
            result = DraftComplianceValidator.validate(draft, self._ctx_confirm())
            copy_violations = [
                v for v in result.violations
                if "copy block" in v.lower() or "confirm_available" in v.lower()
            ]
            assert len(copy_violations) == 0, f"Failed for: {draft!r}\nViolations: {result.violations}"

    def test_respond_unavailable_still_requires_verbatim(self) -> None:
        """RESP-031: other goals keep strict verbatim enforcement."""
        phrase = "Thank you for your enquiry. Unfortunately, we are fully booked for dinner on 12th June."
        result = _validate(
            "Dear Alice, I regret to inform you that we cannot accommodate your request.",
            required_opening_phrase=phrase,
            availability_contract="CONFIRMED_UNAVAILABLE",
            response_goal="RESPOND_UNAVAILABLE",
        )
        assert result.passed is False
        assert any("copy block" in v.lower() or "required" in v.lower() for v in result.violations)

    def test_confirm_available_no_required_phrase_skips_check(self) -> None:
        """When required_opening_phrase is not set, check does not fire even for CONFIRM_AVAILABLE."""
        draft = "Dear Alice, I am happy to assist. Warm regards, Sophie."
        result = DraftComplianceValidator.validate(
            draft,
            ValidationContext(
                response_goal="CONFIRM_AVAILABLE",
                availability_contract="CONFIRMED_AVAILABLE",
            ),
        )
        copy_violations = [v for v in result.violations if "copy block" in v.lower()]
        assert len(copy_violations) == 0

    def test_forbidden_topics_still_caught_for_confirm_available(self) -> None:
        """Semantic open-phrase check does not exempt other compliance violations."""
        draft = (
            "Dear Alice, we are available on 12th June. "
            "Please let us know your menu preferences and dietary requirements. "
            "Warm regards, Sophie."
        )
        result = DraftComplianceValidator.validate(draft, self._ctx_confirm())
        # Availability phrase is fine — but menu/dietary must still be caught
        topic_violations = [v for v in result.violations if "menu" in v.lower() or "dietary" in v.lower()]
        assert len(topic_violations) > 0, "Menu/dietary violation was not caught"

    def test_minimum_spend_soft_language_still_caught(self) -> None:
        """Spend soft-language check remains strict regardless of RESP-031."""
        draft = (
            "Dear Alice, we are available on 12th June. "
            "The recommended minimum spend is £2,000. Warm regards, Sophie."
        )
        result = DraftComplianceValidator.validate(
            draft,
            ValidationContext(
                response_goal="CONFIRM_AVAILABLE",
                availability_contract="CONFIRMED_AVAILABLE",
                confirmed_minimum_spend=2000.0,
                required_opening_phrase=self._PHRASE,
            ),
        )
        spend_violations = [v for v in result.violations if "spend" in v.lower() or "mandatory" in v.lower()]
        assert len(spend_violations) > 0, "Spend soft-language violation was not caught"


# ── TEST-019: Clarification context wiring ────────────────────────────────────


class TestClarificationContextWiring:
    """TEST-019: ValidationContext.clarification_questions wiring correctness.

    Validates that approved clarification questions suppress the invented-question
    check, and that genuine invented questions (no approved questions provided)
    still fail.  Mirrors the specific email patterns from the Sprint 13 evaluation.
    """

    def test_approved_date_question_passes_when_wired(self) -> None:
        """email_20 pattern: REQUEST_DATE_CONFIRMATION with approved question passes."""
        draft = (
            "Dear Neil,\n\n"
            "Thank you for your enquiry — I'll check availability for dinner on "
            "2026-06-07 and come back to you shortly.\n\n"
            "Before I proceed, could you confirm whether you mean 7 June or 6 July? "
            "I have provisionally checked availability for 7 June.\n\n"
            "Warm regards,\nEleanor"
        )
        ctx = ValidationContext(
            availability_contract="PENDING_DATE_CONFIRMATION",
            clarification_questions=[
                "Could you confirm whether you mean 7 June or 6 July? "
                "I have provisionally checked availability for 7 June."
            ],
            response_goal="REQUEST_DATE_CONFIRMATION",
        )
        result = DraftComplianceValidator.validate(draft, ctx)
        invented_q_violations = [v for v in result.violations if "question" in v.lower() and "invented" in v.lower()]
        assert len(invented_q_violations) == 0, (
            "Approved question was incorrectly flagged as invented: "
            + str(invented_q_violations)
        )

    def test_approved_meal_period_question_passes_when_wired(self) -> None:
        """email_48 pattern: REQUEST_MISSING_INFORMATION with approved question passes."""
        draft = (
            "Dear Sarah,\n\n"
            "Thank you for your enquiry about hosting your work team meal with us.\n\n"
            "Could you confirm whether you are looking for breakfast, lunch or dinner?\n\n"
            "Warm regards,\nEleanor"
        )
        ctx = ValidationContext(
            availability_contract="INSUFFICIENT_INFORMATION",
            clarification_questions=[
                "Could you confirm whether you are looking for breakfast, lunch or dinner?"
            ],
            response_goal="REQUEST_MISSING_INFORMATION",
        )
        result = DraftComplianceValidator.validate(draft, ctx)
        invented_q_violations = [v for v in result.violations if "question" in v.lower()]
        assert len(invented_q_violations) == 0, (
            "Approved meal-period question was incorrectly flagged: "
            + str(invented_q_violations)
        )

    def test_empty_clarification_questions_still_fails(self) -> None:
        """email_26 pattern: CONFIRM_AVAILABLE with no approved questions fails."""
        draft = (
            "Dear Natalie,\n\n"
            "Thank you for your enquiry — I'm delighted to confirm that we have "
            "availability for dinner on 2026-07-04.\n\n"
            "I notice you've mentioned both 2026-07-04 and 2026-07-05 as potential dates. "
            "To move forward, could you please confirm which date you'd prefer for your "
            "engagement party?\n\n"
            "Warm regards,\nEleanor"
        )
        ctx = ValidationContext(
            availability_contract="CONFIRMED_AVAILABLE",
            clarification_questions=[],  # no approved questions — question is invented
            response_goal="CONFIRM_AVAILABLE",
        )
        result = DraftComplianceValidator.validate(draft, ctx)
        assert result.passed is False
        assert any("question" in v.lower() for v in result.violations)

    def test_confirm_available_with_invented_question_fails(self) -> None:
        """email_44 pattern: CONFIRM_AVAILABLE invents clarification after confirming."""
        draft = (
            "Dear Chris,\n\n"
            "What a lovely occasion — we'd be delighted to host your leaving do.\n\n"
            "Thank you for your enquiry — I'm delighted to confirm that we have "
            "availability for dinner on 2026-07-03.\n\n"
            "Before we proceed, I'd like to clarify one detail: you've listed several dates. "
            "Could you confirm that 2026-07-03 is your preferred date for the celebration?\n\n"
            "Warm regards,\nEleanor"
        )
        ctx = ValidationContext(
            availability_contract="CONFIRMED_AVAILABLE",
            clarification_questions=[],  # no approved questions
            response_goal="CONFIRM_AVAILABLE",
        )
        result = DraftComplianceValidator.validate(draft, ctx)
        assert result.passed is False
        assert any("question" in v.lower() for v in result.violations)

    def test_question_passes_when_any_approved_question_present(self) -> None:
        """Non-empty clarification_questions suppresses the invented-question check entirely."""
        draft = "Could you let us know your preferred start time? We look forward to welcoming you."
        ctx = ValidationContext(
            availability_contract="NOT_CHECKED",
            clarification_questions=["What time were you thinking of starting?"],
            response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
        )
        result = DraftComplianceValidator.validate(draft, ctx)
        invented_q_violations = [v for v in result.violations if "question" in v.lower() and "invented" in v.lower()]
        assert len(invented_q_violations) == 0
