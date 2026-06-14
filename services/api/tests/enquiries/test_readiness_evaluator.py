"""Tests for EnquiryReadinessEvaluator (ENQ-004).

All tests are unit-level — no DB or LLM required.
"""

from __future__ import annotations

import pytest

from app.modules.enquiries.readiness_evaluator import (
    ALL_READINESS_STATUSES,
    STATUS_INSUFFICIENT_INFORMATION,
    STATUS_NEEDS_CLARIFICATION,
    STATUS_READY_FOR_AVAILABILITY,
    STATUS_WEBFORM_REQUIRED,
    EnquiryReadinessEvaluator,
    ReadinessEvaluation,
)


@pytest.fixture()
def evaluator() -> EnquiryReadinessEvaluator:
    return EnquiryReadinessEvaluator()


def _make_extraction(
    *,
    date_request_type: str = "exact",
    requires_clarification: bool = False,
    clarification_question: str | None = None,
    explicit_dates: list | None = None,
    guest_count: int | None = 20,
    occasion: str | None = "birthday",
    meal_period: str | None = "dinner",
    event_time: str | None = None,
    audience_type: str | None = "social",
) -> dict:
    """Build a minimal extraction dict for testing."""
    return {
        "guest_count": guest_count,
        "occasion": occasion,
        "meal_period": meal_period,
        "event_time": event_time,
        "audience_type": audience_type,
        "date_request": {
            "date_request_type": date_request_type,
            "requires_date_clarification": requires_clarification,
            "clarification_question": clarification_question,
            "explicit_dates": explicit_dates or ["2026-08-15"],
        },
    }


# ── None / empty input ────────────────────────────────────────────────────────


class TestNullInput:
    def test_none_returns_insufficient(self, evaluator):
        result = evaluator.evaluate(None)
        assert result.status == STATUS_INSUFFICIENT_INFORMATION

    def test_empty_dict_returns_insufficient(self, evaluator):
        result = evaluator.evaluate({})
        assert result.status == STATUS_INSUFFICIENT_INFORMATION

    def test_non_dict_returns_insufficient(self, evaluator):
        result = evaluator.evaluate("not a dict")  # type: ignore[arg-type]
        assert result.status == STATUS_INSUFFICIENT_INFORMATION

    def test_insufficient_has_all_fields_false(self, evaluator):
        result = evaluator.evaluate(None)
        assert result.date_understood is False
        assert result.guest_count_present is False
        assert result.availability_check_possible is False


# ── READY_FOR_AVAILABILITY ────────────────────────────────────────────────────


class TestReadyForAvailability:
    def test_date_and_guest_count_present(self, evaluator):
        ext = _make_extraction(date_request_type="exact", guest_count=20)
        result = evaluator.evaluate(ext)
        assert result.status == STATUS_READY_FOR_AVAILABILITY

    def test_date_range_type_with_guest_count(self, evaluator):
        ext = _make_extraction(date_request_type="date_range", guest_count=15)
        result = evaluator.evaluate(ext)
        assert result.status == STATUS_READY_FOR_AVAILABILITY

    def test_availability_check_possible_is_true(self, evaluator):
        ext = _make_extraction(date_request_type="exact", guest_count=10)
        result = evaluator.evaluate(ext)
        assert result.availability_check_possible is True
        assert result.date_understood is True
        assert result.guest_count_present is True

    def test_criteria_all_populated(self, evaluator):
        ext = _make_extraction(
            date_request_type="exact",
            guest_count=20,
            occasion="birthday",
            meal_period="dinner",
            audience_type="social",
        )
        result = evaluator.evaluate(ext)
        assert result.status == STATUS_READY_FOR_AVAILABILITY
        assert result.occasion_understood is True
        assert result.meal_period_present is True
        assert result.audience_identified is True


# ── NEEDS_CLARIFICATION ───────────────────────────────────────────────────────


class TestNeedsClarification:
    def test_ambiguous_date_flag(self, evaluator):
        ext = _make_extraction(requires_clarification=True)
        result = evaluator.evaluate(ext)
        assert result.status == STATUS_NEEDS_CLARIFICATION
        assert result.date_clarification_required is True

    def test_date_understood_but_no_guest_count(self, evaluator):
        ext = _make_extraction(date_request_type="exact", guest_count=None)
        result = evaluator.evaluate(ext)
        assert result.status == STATUS_NEEDS_CLARIFICATION

    def test_guest_count_present_but_no_date(self, evaluator):
        ext = _make_extraction(date_request_type="unknown", guest_count=20)
        result = evaluator.evaluate(ext)
        assert result.status == STATUS_NEEDS_CLARIFICATION

    def test_ambiguous_overrides_guest_count(self, evaluator):
        # Even with guest count, clarification required → NEEDS_CLARIFICATION
        ext = _make_extraction(
            date_request_type="ambiguous_numeric_date",
            requires_clarification=True,
            guest_count=10,
        )
        result = evaluator.evaluate(ext)
        assert result.status == STATUS_NEEDS_CLARIFICATION

    def test_missing_for_availability_contains_guest_count(self, evaluator):
        ext = _make_extraction(date_request_type="exact", guest_count=None)
        result = evaluator.evaluate(ext)
        assert "guest_count" in result.missing_for_availability

    def test_missing_for_availability_contains_date(self, evaluator):
        ext = _make_extraction(date_request_type="unknown", guest_count=20)
        result = evaluator.evaluate(ext)
        assert "date" in result.missing_for_availability


# ── WEBFORM_REQUIRED ──────────────────────────────────────────────────────────


class TestWebformRequired:
    def test_no_date_no_guest_count_but_some_context(self, evaluator):
        ext = {
            "guest_count": None,
            "occasion": "birthday",
            "meal_period": "dinner",
            "audience_type": "social",
            "date_request": {
                "date_request_type": "unknown",
                "requires_date_clarification": False,
            },
        }
        result = evaluator.evaluate(ext)
        assert result.status == STATUS_WEBFORM_REQUIRED

    def test_webform_has_date_and_guest_count_false(self, evaluator):
        ext = {
            "guest_count": None,
            "occasion": "anniversary",
            "meal_period": None,
            "audience_type": None,
            "date_request": {"date_request_type": "unknown"},
        }
        result = evaluator.evaluate(ext)
        assert result.status in (STATUS_WEBFORM_REQUIRED, STATUS_INSUFFICIENT_INFORMATION)


# ── INSUFFICIENT_INFORMATION ──────────────────────────────────────────────────


class TestInsufficientInformation:
    def test_no_useful_data(self, evaluator):
        ext = {
            "guest_count": None,
            "occasion": None,
            "meal_period": None,
            "audience_type": None,
            "date_request": {"date_request_type": "unknown"},
        }
        result = evaluator.evaluate(ext)
        assert result.status == STATUS_INSUFFICIENT_INFORMATION

    def test_all_null_string_values(self, evaluator):
        ext = {
            "guest_count": None,
            "occasion": "NULL",
            "meal_period": "NULL",
            "audience_type": "NULL",
            "date_request": {"date_request_type": "unknown"},
        }
        result = evaluator.evaluate(ext)
        assert result.status == STATUS_INSUFFICIENT_INFORMATION


# ── to_dict() / serialisation ────────────────────────────────────────────────


class TestToDictSerialisation:
    def test_to_dict_contains_all_fields(self, evaluator):
        ext = _make_extraction()
        evaluation = evaluator.evaluate(ext)
        d = evaluation.to_dict()
        assert "status" in d
        assert "date_understood" in d
        assert "guest_count_present" in d
        assert "occasion_understood" in d
        assert "meal_period_present" in d
        assert "audience_identified" in d
        assert "date_clarification_required" in d
        assert "availability_check_possible" in d
        assert "missing_for_availability" in d
        assert "notes" in d

    def test_status_always_in_known_set(self, evaluator):
        samples = [
            None,
            {},
            _make_extraction(),
            _make_extraction(guest_count=None),
            _make_extraction(date_request_type="unknown"),
            _make_extraction(requires_clarification=True),
        ]
        for ext in samples:
            result = evaluator.evaluate(ext)
            assert result.status in ALL_READINESS_STATUSES, (
                f"evaluate({ext!r}).status = {result.status!r} not in ALL_READINESS_STATUSES"
            )

    def test_to_dict_values_are_serialisable(self, evaluator):
        ext = _make_extraction()
        d = evaluator.evaluate(ext).to_dict()
        import json
        # Should not raise
        json.dumps(d)


# ── RESP-066: meal period inference from event_time ───────────────────────────


class TestMealPeriodTimeInference:
    """RESP-066: meal_period_present should be True when event_time is available.

    When the LLM extracts event_time (HH:MM) but returns meal_period = "unknown",
    the meal period can be deterministically inferred (before 15:00 → lunch;
    15:00+ → dinner).  Marking meal_period_present = True prevents unnecessary
    guest-facing clarification questions like "breakfast, lunch or dinner?".
    """

    def test_event_time_afternoon_infers_meal_period_present(self, evaluator):
        # "around 4ish" → event_time="16:00", meal_period="unknown"
        ext = _make_extraction(meal_period="unknown", event_time="16:00")
        result = evaluator.evaluate(ext)
        assert result.meal_period_present is True

    def test_event_time_morning_infers_meal_period_present(self, evaluator):
        # "at 10am" → event_time="10:00", meal_period="unknown"
        ext = _make_extraction(meal_period="unknown", event_time="10:00")
        result = evaluator.evaluate(ext)
        assert result.meal_period_present is True

    def test_event_time_noon_infers_meal_period_present(self, evaluator):
        ext = _make_extraction(meal_period="unknown", event_time="12:00")
        result = evaluator.evaluate(ext)
        assert result.meal_period_present is True

    def test_event_time_overrides_null_meal_period(self, evaluator):
        ext = _make_extraction(meal_period=None, event_time="19:30")
        result = evaluator.evaluate(ext)
        assert result.meal_period_present is True

    def test_event_time_overrides_missing_meal_period(self, evaluator):
        ext = {
            "guest_count": 10,
            "occasion": "birthday",
            "event_time": "20:00",
            "audience_type": "social",
            "date_request": {"date_request_type": "exact"},
        }
        result = evaluator.evaluate(ext)
        assert result.meal_period_present is True

    def test_no_event_time_unknown_meal_period_is_absent(self, evaluator):
        # Neither meal_period nor event_time → meal_period_present False
        ext = _make_extraction(meal_period="unknown", event_time=None)
        result = evaluator.evaluate(ext)
        assert result.meal_period_present is False

    def test_no_event_time_null_meal_period_is_absent(self, evaluator):
        ext = _make_extraction(meal_period=None, event_time=None)
        result = evaluator.evaluate(ext)
        assert result.meal_period_present is False

    def test_explicit_meal_period_still_works(self, evaluator):
        # Explicit meal_period takes precedence — event_time not needed
        ext = _make_extraction(meal_period="dinner", event_time=None)
        result = evaluator.evaluate(ext)
        assert result.meal_period_present is True

    def test_unparseable_event_time_does_not_infer(self, evaluator):
        # event_time that cannot be split into an integer hour → no inference
        ext = _make_extraction(meal_period="unknown", event_time="afternoon")
        result = evaluator.evaluate(ext)
        assert result.meal_period_present is False

    def test_email_48_scenario_no_meal_period_question(self, evaluator):
        # Exact scenario: work team meal, 4ish → no clarification needed for meal period
        ext = {
            "guest_count": 11,
            "occasion": "work team meal",
            "meal_period": "unknown",
            "event_time": "16:00",
            "audience_type": "social",
            "date_request": {
                "date_request_type": "exact",
                "requires_date_clarification": False,
                "explicit_dates": ["2026-06-10"],
            },
        }
        result = evaluator.evaluate(ext)
        assert result.meal_period_present is True
        assert result.status == STATUS_READY_FOR_AVAILABILITY
