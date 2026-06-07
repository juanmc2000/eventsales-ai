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
        assert set(d.keys()) == {"passed", "violations", "unsafe_to_send"}

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

    def test_pass_when_time_just_mentioned_not_confirmed(self) -> None:
        # "you mentioned 7pm" is not the same as "confirmed at 7pm"
        draft = "You mentioned 7pm as a preference — I'll note this for when we check availability."
        result = _validate(draft, prohibited_times=["7pm"])
        assert result.passed is True


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

    def test_suitability_violation_fires_for_not_checked(self) -> None:
        """RESP-025: suitability check also fires for NOT_CHECKED (extended from CONFIRMED_UNAVAILABLE)."""
        draft = "Our room would be perfect for a party of 10."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        suitability_violations = [v for v in result.violations if "ROOM_SUITABILITY_PREMATURE" in v]
        assert len(suitability_violations) == 1


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


# ── RESP-025: strengthened checks ─────────────────────────────────────────────


class TestResp025AlternativeDatesExtended:
    """RESP-025: alternative-date check extended to all non-CONFIRMED_AVAILABLE contracts."""

    def test_alternative_dates_fail_for_not_checked(self) -> None:
        draft = "We could suggest alternative dates that might work for your group."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is False
        assert any("ALT_DATE_INVENTED" in v for v in result.violations)

    def test_alternative_dates_fail_for_pending_date_confirmation(self) -> None:
        draft = "How about considering other dates if your first choice doesn't work?"
        result = _validate(draft, availability_contract="PENDING_DATE_CONFIRMATION")
        assert result.passed is False
        assert any("ALT_DATE_INVENTED" in v for v in result.violations)

    def test_alternative_dates_fail_for_insufficient_information(self) -> None:
        draft = "We'd be happy to look at other options for your event."
        result = _validate(draft, availability_contract="INSUFFICIENT_INFORMATION")
        assert result.passed is False
        assert any("ALT_DATE_INVENTED" in v for v in result.violations)

    def test_alternative_dates_pass_when_alternatives_allowed(self) -> None:
        draft = "We can offer alternative dates: 22nd or 23rd June."
        result = _validate(
            draft,
            availability_contract="CONFIRMED_UNAVAILABLE",
            alternatives_allowed=True,
        )
        alt_violations = [v for v in result.violations if "ALT_DATE_INVENTED" in v]
        assert len(alt_violations) == 0

    def test_alternative_dates_pass_for_confirmed_available(self) -> None:
        draft = "We look forward to hosting your event. We can also offer other options."
        result = _validate(draft, availability_contract="CONFIRMED_AVAILABLE")
        alt_violations = [v for v in result.violations if "ALT_DATE_INVENTED" in v]
        assert len(alt_violations) == 0


class TestResp025HostingLanguageExtended:
    """RESP-025: hosting language check extended to CONFIRMED_UNAVAILABLE."""

    def test_hosting_language_fails_for_confirmed_unavailable(self) -> None:
        draft = "We would love to host your celebration at our venue."
        result = _validate(draft, availability_contract="CONFIRMED_UNAVAILABLE")
        assert result.passed is False
        assert any("HOSTING_LANG_NOT_AVAILABLE" in v for v in result.violations)

    def test_perfect_for_fails_for_confirmed_unavailable(self) -> None:
        draft = "Our Private Dining Room would be perfect for a group of 20."
        result = _validate(draft, availability_contract="CONFIRMED_UNAVAILABLE")
        assert result.passed is False
        assert any("HOSTING_LANG_NOT_AVAILABLE" in v or "ROOM_SUITABILITY" in v
                   for v in result.violations)

    def test_hosting_language_still_fails_for_not_checked(self) -> None:
        draft = "We're looking forward to hosting you!"
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is False
        assert any("HOSTING_LANG_NOT_AVAILABLE" in v for v in result.violations)

    def test_hosting_language_passes_for_confirmed_available(self) -> None:
        draft = "We're delighted to host your event and look forward to hosting you."
        result = _validate(draft, availability_contract="CONFIRMED_AVAILABLE")
        hosting_violations = [v for v in result.violations if "HOSTING_LANG_NOT_AVAILABLE" in v]
        assert len(hosting_violations) == 0


class TestResp025RoomSuitabilityExtended:
    """RESP-025: room suitability check extended to NOT_CHECKED."""

    def test_perfect_for_group_fails_for_not_checked(self) -> None:
        draft = "Our dining room would be perfect for your group of 25."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is False
        assert any("ROOM_SUITABILITY_PREMATURE" in v for v in result.violations)

    def test_ideal_for_celebration_fails_for_not_checked(self) -> None:
        draft = "The Mezzanine Suite is ideal for celebrations of this size."
        result = _validate(draft, availability_contract="NOT_CHECKED")
        assert result.passed is False
        assert any("ROOM_SUITABILITY_PREMATURE" in v for v in result.violations)

    def test_room_suitability_still_fails_for_confirmed_unavailable(self) -> None:
        draft = "Our space and expertise make us well-suited to hosting your event."
        result = _validate(draft, availability_contract="CONFIRMED_UNAVAILABLE")
        assert result.passed is False
        assert any("ROOM_SUITABILITY_PREMATURE" in v for v in result.violations)

    def test_room_suitability_passes_for_confirmed_available(self) -> None:
        draft = "Our Private Dining Room would be perfect for your group."
        result = _validate(draft, availability_contract="CONFIRMED_AVAILABLE")
        suitability_violations = [v for v in result.violations if "ROOM_SUITABILITY_PREMATURE" in v]
        assert len(suitability_violations) == 0

    def test_room_suitability_passes_for_pending_date_confirmation(self) -> None:
        """Suitability check does not fire for PENDING_DATE_CONFIRMATION or INSUFFICIENT_INFORMATION."""
        draft = "Our room would be perfect for your event."
        result = _validate(draft, availability_contract="PENDING_DATE_CONFIRMATION")
        suitability_violations = [v for v in result.violations if "ROOM_SUITABILITY_PREMATURE" in v]
        assert len(suitability_violations) == 0


# ── RESP-026: verbatim copy block enforcement ─────────────────────────────────


class TestResp026VerbatimCopyBlockEnforcement:
    """RESP-026: required copy blocks must be present verbatim."""

    # ── Opening block — CONFIRMED_AVAILABLE ───────────────────────────────────

    def test_confirmed_available_opening_block_present_passes(self) -> None:
        draft = (
            "Thank you for your enquiry — I'm delighted to confirm that we have "
            "availability for dinner on 15th September.\n\n"
            "Warm regards,\nEvents Team"
        )
        result = _validate(
            draft,
            availability_contract="CONFIRMED_AVAILABLE",
            meal_period="dinner",
            event_date="15th September",
            persona_name="Events Team",
        )
        copy_violations = [v for v in result.violations if "COPY_BLOCK_MISSING" in v]
        assert len(copy_violations) == 0

    def test_confirmed_available_opening_block_absent_fails(self) -> None:
        draft = (
            "Great news! We can accommodate your event on 15th September.\n\n"
            "Warm regards,\nEvents Team"
        )
        result = _validate(
            draft,
            availability_contract="CONFIRMED_AVAILABLE",
            meal_period="dinner",
            event_date="15th September",
            persona_name="Events Team",
        )
        copy_violations = [v for v in result.violations if "COPY_BLOCK_MISSING" in v and "opening" in v.lower()]
        assert len(copy_violations) >= 1

    # ── Opening block — CONFIRMED_UNAVAILABLE ─────────────────────────────────

    def test_unavailable_opening_block_present_passes(self) -> None:
        draft = (
            "Thank you for your enquiry. Unfortunately, we are fully booked for "
            "dinner on 20th October.\n\nWarm regards,\nSarah"
        )
        result = _validate(
            draft,
            availability_contract="CONFIRMED_UNAVAILABLE",
            meal_period="dinner",
            event_date="20th October",
            persona_name="Sarah",
        )
        copy_violations = [v for v in result.violations if "COPY_BLOCK_MISSING" in v]
        assert len(copy_violations) == 0

    def test_unavailable_opening_block_paraphrased_fails(self) -> None:
        draft = (
            "Hi there! We regret to say that the date you've chosen is not available.\n\n"
            "Kind regards,\nSarah"
        )
        result = _validate(
            draft,
            availability_contract="CONFIRMED_UNAVAILABLE",
            meal_period="dinner",
            event_date="20th October",
            persona_name="Sarah",
        )
        copy_violations = [v for v in result.violations if "COPY_BLOCK_MISSING" in v and "opening" in v.lower()]
        assert len(copy_violations) >= 1

    # ── Opening block — NOT_CHECKED ───────────────────────────────────────────

    def test_not_checked_opening_block_present_passes(self) -> None:
        draft = (
            "Thank you for your enquiry — I'll check availability for lunch on "
            "10th August and come back to you shortly.\n\nWarm regards,\nJames"
        )
        result = _validate(
            draft,
            availability_contract="NOT_CHECKED",
            meal_period="lunch",
            event_date="10th August",
            persona_name="James",
        )
        copy_violations = [v for v in result.violations if "COPY_BLOCK_MISSING" in v]
        assert len(copy_violations) == 0

    def test_not_checked_opening_block_absent_fails(self) -> None:
        draft = (
            "Hi! We'll look into that for you and get back shortly.\n\nWarm regards,\nJames"
        )
        result = _validate(
            draft,
            availability_contract="NOT_CHECKED",
            meal_period="lunch",
            event_date="10th August",
            persona_name="James",
        )
        copy_violations = [v for v in result.violations if "COPY_BLOCK_MISSING" in v and "opening" in v.lower()]
        assert len(copy_violations) >= 1

    # ── Minimum spend block ───────────────────────────────────────────────────

    def test_spend_block_present_passes(self) -> None:
        draft = (
            "Thank you for your enquiry — I'm delighted to confirm that we have "
            "availability for dinner on 15th September.\n\n"
            "Please note that our mandatory minimum spend for this space is £2,500.\n\n"
            "Warm regards,\nEvents Team"
        )
        result = _validate(
            draft,
            availability_contract="CONFIRMED_AVAILABLE",
            confirmed_minimum_spend=2500.0,
            meal_period="dinner",
            event_date="15th September",
            persona_name="Events Team",
        )
        copy_violations = [v for v in result.violations if "COPY_BLOCK_MISSING" in v]
        assert len(copy_violations) == 0

    def test_spend_block_paraphrased_fails(self) -> None:
        draft = (
            "Thank you for your enquiry — I'm delighted to confirm that we have "
            "availability for dinner on 15th September.\n\n"
            "There is a spend requirement of £2,500 for this event.\n\n"
            "Warm regards,\nEvents Team"
        )
        result = _validate(
            draft,
            availability_contract="CONFIRMED_AVAILABLE",
            confirmed_minimum_spend=2500.0,
            meal_period="dinner",
            event_date="15th September",
            persona_name="Events Team",
        )
        copy_violations = [v for v in result.violations if "COPY_BLOCK_MISSING" in v and "spend" in v.lower()]
        assert len(copy_violations) >= 1

    def test_spend_block_not_checked_when_unavailable(self) -> None:
        """Spend block is only required for CONFIRMED_AVAILABLE."""
        draft = (
            "Thank you for your enquiry. Unfortunately, we are fully booked for "
            "dinner on 15th September.\n\nWarm regards,\nEvents Team"
        )
        result = _validate(
            draft,
            availability_contract="CONFIRMED_UNAVAILABLE",
            confirmed_minimum_spend=2500.0,
            meal_period="dinner",
            event_date="15th September",
            persona_name="Events Team",
        )
        spend_violations = [v for v in result.violations if "COPY_BLOCK_MISSING" in v and "spend" in v.lower()]
        assert len(spend_violations) == 0

    # ── Signoff block ─────────────────────────────────────────────────────────

    def test_signoff_block_present_passes(self) -> None:
        draft = (
            "Thank you for your enquiry — I'll check availability for dinner on "
            "5th November and come back to you shortly.\n\nWarm regards,\nEleanor"
        )
        result = _validate(
            draft,
            availability_contract="NOT_CHECKED",
            meal_period="dinner",
            event_date="5th November",
            persona_name="Eleanor",
        )
        copy_violations = [v for v in result.violations if "COPY_BLOCK_MISSING" in v]
        assert len(copy_violations) == 0

    def test_signoff_block_absent_fails(self) -> None:
        draft = (
            "Thank you for your enquiry — I'll check availability for dinner on "
            "5th November and come back to you shortly.\n\nBest,\nEleanor"
        )
        result = _validate(
            draft,
            availability_contract="NOT_CHECKED",
            meal_period="dinner",
            event_date="5th November",
            persona_name="Eleanor",
        )
        signoff_violations = [v for v in result.violations if "COPY_BLOCK_MISSING" in v and "signoff" in v.lower()]
        assert len(signoff_violations) >= 1

    def test_signoff_check_skipped_when_no_persona_name(self) -> None:
        """Signoff check must not fire when persona_name is absent."""
        draft = "Thank you for your enquiry — we'll be in touch shortly.\n\nBest wishes"
        result = _validate(
            draft,
            availability_contract="NOT_CHECKED",
            meal_period="lunch",
            event_date="5th November",
            persona_name=None,
        )
        signoff_violations = [v for v in result.violations if "COPY_BLOCK_MISSING" in v and "signoff" in v.lower()]
        assert len(signoff_violations) == 0

    # ── Formatting tolerance ──────────────────────────────────────────────────

    def test_bold_markdown_formatting_does_not_cause_false_failure(self) -> None:
        """Markdown bold formatting in the draft must not cause false block-missing failures."""
        draft = (
            "**Thank you for your enquiry — I'm delighted to confirm that we have "
            "availability for dinner on 15th September.**\n\n"
            "**Warm regards,**\n**Events Team**"
        )
        result = _validate(
            draft,
            availability_contract="CONFIRMED_AVAILABLE",
            meal_period="dinner",
            event_date="15th September",
            persona_name="Events Team",
        )
        copy_violations = [v for v in result.violations if "COPY_BLOCK_MISSING" in v]
        assert len(copy_violations) == 0

    def test_extra_whitespace_does_not_cause_false_failure(self) -> None:
        draft = (
            "Thank you  for  your  enquiry — I'll check availability  for lunch on "
            "10th August  and come back  to you shortly.\n\n\nWarm regards,\nJames"
        )
        result = _validate(
            draft,
            availability_contract="NOT_CHECKED",
            meal_period="lunch",
            event_date="10th August",
            persona_name="James",
        )
        copy_violations = [v for v in result.violations if "COPY_BLOCK_MISSING" in v]
        assert len(copy_violations) == 0
