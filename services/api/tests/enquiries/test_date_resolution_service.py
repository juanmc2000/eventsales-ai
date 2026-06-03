"""Tests for EnquiryDateResolutionService (WORKFLOW-008).

All tests are unit/smoke level — no DB or live LLM required.
DB session is mocked; model persistence is patched.
"""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

import app.db.models  # noqa: F401 — registers all models

from app.modules.enquiries.date_resolution_service import (
    MAX_CANDIDATE_DATES,
    DEFAULT_TIMEZONE,
    SOURCE_TYPE_EXPLICIT,
    SOURCE_TYPE_DETERMINISTIC,
    DateResolutionRequest,
    DateResolutionResult,
    EnquiryDateResolutionService,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_service() -> EnquiryDateResolutionService:
    db = MagicMock()
    return EnquiryDateResolutionService(db=db)


def _resolve(dr_dict: dict, anchor: date | None = None) -> DateResolutionResult:
    service = _make_service()
    request = DateResolutionRequest(
        enquiry_id=uuid.uuid4(),
        date_request_dict=dr_dict,
        anchor_date_override=anchor,
    )
    # Patch persistence so no real DB writes happen
    with (
        patch.object(service, "_persist_date_request", return_value=None),
        patch.object(service, "_persist_candidate_dates"),
    ):
        return service.resolve(request)


# ── DateResolutionRequest / DateResolutionResult schema ───────────────────────


class TestSchemas:
    def test_request_requires_enquiry_id_and_dict(self) -> None:
        req = DateResolutionRequest(
            enquiry_id=uuid.uuid4(),
            date_request_dict={"date_request_type": "exact", "explicit_dates": ["2026-08-15"]},
        )
        assert req.tenant_id is None
        assert req.extraction_id is None
        assert req.anchor_date_override is None

    def test_result_has_all_fields(self) -> None:
        result = DateResolutionResult(
            date_request_id=None,
            date_request_type="exact",
            candidate_dates=[date(2026, 8, 15)],
            requires_date_clarification=False,
        )
        assert result.clarification_question is None
        assert result.error_message is None
        assert result.candidate_dates == [date(2026, 8, 15)]


# ── Exact date expansion ───────────────────────────────────────────────────────


class TestExactExpansion:
    def test_exact_returns_single_explicit_date(self) -> None:
        result = _resolve({
            "date_request_type": "exact",
            "explicit_dates": ["2026-08-15"],
        })
        assert result.candidate_dates == [date(2026, 8, 15)]
        assert result.date_request_type == "exact"

    def test_exact_returns_first_only(self) -> None:
        result = _resolve({
            "date_request_type": "exact",
            "explicit_dates": ["2026-08-15", "2026-08-16"],
        })
        assert result.candidate_dates == [date(2026, 8, 15)]

    def test_exact_falls_back_to_anchor_date_when_no_explicit(self) -> None:
        result = _resolve(
            {"date_request_type": "exact", "explicit_dates": [], "anchor_date": "2026-09-01"},
            anchor=None,
        )
        assert date(2026, 9, 1) in result.candidate_dates

    def test_exact_returns_empty_when_invalid_date(self) -> None:
        result = _resolve({
            "date_request_type": "exact",
            "explicit_dates": ["not-a-date"],
        })
        assert result.candidate_dates == []

    def test_exact_resolves_next_wednesday_from_monday(self) -> None:
        # "next Wednesday" from Monday 2026-06-01 → next calendar week's Wednesday
        result = _resolve(
            {
                "date_request_type": "exact",
                "explicit_dates": [],
                "anchor_date": None,
                "weekdays": ["wednesday"],
                "relative_period": {"direction": "next", "unit": "week", "amount": 1},
            },
            anchor=date(2026, 6, 1),  # Monday
        )
        assert result.candidate_dates == [date(2026, 6, 10)]

    def test_exact_next_wednesday_from_wednesday(self) -> None:
        # "next Wednesday" from Wednesday itself → NEXT week's Wednesday, not today
        result = _resolve(
            {
                "date_request_type": "exact",
                "explicit_dates": [],
                "weekdays": ["wednesday"],
                "relative_period": {"direction": "next", "unit": "week", "amount": 1},
            },
            anchor=date(2026, 6, 3),  # Wednesday
        )
        assert result.candidate_dates == [date(2026, 6, 10)]

    def test_exact_this_wednesday_from_monday(self) -> None:
        # "this Wednesday" from Monday → current week's Wednesday
        result = _resolve(
            {
                "date_request_type": "exact",
                "explicit_dates": [],
                "weekdays": ["wednesday"],
                "relative_period": {"direction": "this", "unit": "week", "amount": 1},
            },
            anchor=date(2026, 6, 1),  # Monday
        )
        assert result.candidate_dates == [date(2026, 6, 3)]


# ── Date range expansion ──────────────────────────────────────────────────────


class TestDateRangeExpansion:
    def test_date_range_includes_start_and_end(self) -> None:
        result = _resolve({
            "date_request_type": "date_range",
            "date_range": {"start_date": "2026-08-01", "end_date": "2026-08-05"},
        })
        assert date(2026, 8, 1) in result.candidate_dates
        assert date(2026, 8, 5) in result.candidate_dates
        assert len(result.candidate_dates) == 5

    def test_date_range_reverses_when_end_before_start(self) -> None:
        result = _resolve({
            "date_request_type": "date_range",
            "date_range": {"start_date": "2026-08-05", "end_date": "2026-08-01"},
        })
        assert date(2026, 8, 1) in result.candidate_dates
        assert date(2026, 8, 5) in result.candidate_dates

    def test_date_range_returns_empty_when_no_start(self) -> None:
        result = _resolve({
            "date_request_type": "date_range",
            "date_range": {"end_date": "2026-08-05"},
        })
        assert result.candidate_dates == []

    def test_date_range_capped_at_max_candidates(self) -> None:
        result = _resolve({
            "date_request_type": "date_range",
            "date_range": {"start_date": "2026-01-01", "end_date": "2027-12-31"},
        })
        assert len(result.candidate_dates) <= MAX_CANDIDATE_DATES


# ── Multiple choice expansion ─────────────────────────────────────────────────


class TestMultipleChoiceExpansion:
    def test_multiple_choice_returns_all_explicit_dates(self) -> None:
        result = _resolve({
            "date_request_type": "multiple_choice",
            "explicit_dates": ["2026-08-01", "2026-09-01", "2026-10-01"],
        })
        assert len(result.candidate_dates) == 3
        assert date(2026, 8, 1) in result.candidate_dates

    def test_multiple_choice_returns_empty_when_none(self) -> None:
        result = _resolve({
            "date_request_type": "multiple_choice",
            "explicit_dates": [],
        })
        assert result.candidate_dates == []


# ── Month flexible expansion ──────────────────────────────────────────────────


class TestMonthFlexibleExpansion:
    def test_month_flexible_generates_all_days_in_month(self) -> None:
        result = _resolve(
            {"date_request_type": "month_flexible", "month": 8, "year": 2026},
            anchor=date(2026, 5, 1),
        )
        assert len(result.candidate_dates) == 31
        assert all(d.month == 8 and d.year == 2026 for d in result.candidate_dates)

    def test_month_flexible_without_year_uses_anchor_year(self) -> None:
        result = _resolve(
            {"date_request_type": "month_flexible", "month": 10},
            anchor=date(2026, 5, 1),
        )
        assert all(d.year == 2026 for d in result.candidate_dates)

    def test_month_flexible_past_month_uses_next_year(self) -> None:
        # month=2 (February) is before anchor month=5, so use next year
        result = _resolve(
            {"date_request_type": "month_flexible", "month": 2},
            anchor=date(2026, 5, 1),
        )
        assert all(d.year == 2027 for d in result.candidate_dates)

    def test_month_flexible_december_has_31_days(self) -> None:
        result = _resolve(
            {"date_request_type": "month_flexible", "month": 12, "year": 2026},
        )
        assert len(result.candidate_dates) == 31

    def test_month_flexible_returns_empty_when_no_month(self) -> None:
        result = _resolve({"date_request_type": "month_flexible"})
        assert result.candidate_dates == []


# ── Weekday range expansion ───────────────────────────────────────────────────


class TestWeekdayRangeExpansion:
    def test_weekday_range_filters_to_target_days(self) -> None:
        result = _resolve(
            {
                "date_request_type": "weekday_range_over_relative_period",
                "weekdays": ["friday", "saturday"],
                "relative_period": {"direction": "next", "unit": "week", "amount": 2},
            },
            anchor=date(2026, 7, 20),  # Monday
        )
        # All dates should be Friday (4) or Saturday (5)
        assert all(d.weekday() in (4, 5) for d in result.candidate_dates)
        assert len(result.candidate_dates) > 0

    def test_weekday_range_returns_empty_when_no_weekdays(self) -> None:
        result = _resolve({
            "date_request_type": "weekday_range_over_relative_period",
            "weekdays": [],
        })
        assert result.candidate_dates == []

    def test_weekday_range_invalid_weekday_name_ignored(self) -> None:
        result = _resolve({
            "date_request_type": "weekday_range_over_relative_period",
            "weekdays": ["notaday"],
            "relative_period": {"direction": "next", "unit": "week", "amount": 1},
        })
        assert result.candidate_dates == []


# ── ENQ-006: weekday_range date_range fallback ────────────────────────────────


class TestWeekdayRangeDateRangeFallback:
    """ENQ-006: resolver uses date_range bounds when relative_period has no direction.

    These tests mirror the 6 LLM output patterns from the 60-record V4 accuracy run
    (anchor 2026-06-03) where relative_period was null/directionless but date_range
    was correctly populated by the LLM.
    """

    def test_any_friday_in_august_uses_date_range_bounds(self) -> None:
        # email_13 pattern: "any Friday in August"
        # LLM: weekdays=['friday'], date_range=2026-08-01..2026-08-31, relative_period=None
        result = _resolve(
            {
                "date_request_type": "weekday_range_over_relative_period",
                "weekdays": ["friday"],
                "relative_period": None,
                "date_range": {"start_date": "2026-08-01", "end_date": "2026-08-31"},
            },
            anchor=date(2026, 6, 3),
        )
        assert result.candidate_dates == [
            date(2026, 8, 7),
            date(2026, 8, 14),
            date(2026, 8, 21),
            date(2026, 8, 28),
        ]

    def test_end_of_july_fri_sat_uses_date_range_bounds(self) -> None:
        # email_23 pattern: "end of July" → weekdays=fri+sat, date_range=2026-07-24..2026-07-31
        # LLM: relative_period={'amount': None, 'unit': None, 'direction': None}
        result = _resolve(
            {
                "date_request_type": "weekday_range_over_relative_period",
                "weekdays": ["friday", "saturday"],
                "relative_period": {"amount": None, "unit": None, "direction": None},
                "date_range": {"start_date": "2026-07-24", "end_date": "2026-07-31"},
            },
            anchor=date(2026, 6, 3),
        )
        assert result.candidate_dates == [
            date(2026, 7, 24),  # Friday
            date(2026, 7, 25),  # Saturday
            date(2026, 7, 31),  # Friday
        ]

    def test_mid_august_weekend_uses_date_range_bounds(self) -> None:
        # email_30 pattern: "mid August" → weekdays=sat+sun, date_range=2026-08-10..2026-08-20
        result = _resolve(
            {
                "date_request_type": "weekday_range_over_relative_period",
                "weekdays": ["saturday", "sunday"],
                "relative_period": {"amount": None, "unit": None, "direction": None},
                "date_range": {"start_date": "2026-08-10", "end_date": "2026-08-20"},
            },
            anchor=date(2026, 6, 3),
        )
        assert result.candidate_dates == [
            date(2026, 8, 15),  # Saturday
            date(2026, 8, 16),  # Sunday
        ]

    def test_weekend_around_july_18_uses_date_range_bounds(self) -> None:
        # email_37 pattern: "the weekend around July 18"
        # LLM: weekdays=sat+sun, date_range=2026-07-17..2026-07-19, relative_period=None
        result = _resolve(
            {
                "date_request_type": "weekday_range_over_relative_period",
                "weekdays": ["saturday", "sunday"],
                "relative_period": None,
                "date_range": {"start_date": "2026-07-17", "end_date": "2026-07-19"},
            },
            anchor=date(2026, 6, 3),
        )
        assert result.candidate_dates == [
            date(2026, 7, 18),  # Saturday
            date(2026, 7, 19),  # Sunday
        ]

    def test_any_friday_in_july_uses_date_range_bounds(self) -> None:
        # email_44 pattern: "any Friday in July"
        result = _resolve(
            {
                "date_request_type": "weekday_range_over_relative_period",
                "weekdays": ["friday"],
                "relative_period": None,
                "date_range": {"start_date": "2026-07-01", "end_date": "2026-07-31"},
            },
            anchor=date(2026, 6, 3),
        )
        assert result.candidate_dates == [
            date(2026, 7, 3),
            date(2026, 7, 10),
            date(2026, 7, 17),
            date(2026, 7, 24),
            date(2026, 7, 31),
        ]

    def test_mon_wed_in_july_uses_date_range_bounds(self) -> None:
        # email_52 pattern: "any Monday to Wednesday in July"
        result = _resolve(
            {
                "date_request_type": "weekday_range_over_relative_period",
                "weekdays": ["monday", "tuesday", "wednesday"],
                "relative_period": None,
                "date_range": {"start_date": "2026-07-01", "end_date": "2026-07-31"},
            },
            anchor=date(2026, 6, 3),
        )
        # July 2026: Mon-Wed occurrences
        expected = [
            date(2026, 7, 1),   # Wednesday
            date(2026, 7, 6),   # Monday
            date(2026, 7, 7),   # Tuesday
            date(2026, 7, 8),   # Wednesday
            date(2026, 7, 13),  # Monday
            date(2026, 7, 14),  # Tuesday
            date(2026, 7, 15),  # Wednesday
            date(2026, 7, 20),  # Monday
            date(2026, 7, 21),  # Tuesday
            date(2026, 7, 22),  # Wednesday
            date(2026, 7, 27),  # Monday
            date(2026, 7, 28),  # Tuesday
            date(2026, 7, 29),  # Wednesday
        ]
        assert result.candidate_dates == expected

    def test_date_range_start_before_anchor_is_clamped(self) -> None:
        # date_range starts in the past; resolver clamps start to anchor_date
        result = _resolve(
            {
                "date_request_type": "weekday_range_over_relative_period",
                "weekdays": ["saturday"],
                "relative_period": None,
                "date_range": {"start_date": "2026-06-01", "end_date": "2026-06-14"},
            },
            anchor=date(2026, 6, 3),
        )
        # Saturdays from anchor(2026-06-03) to 2026-06-14: Jun 6, Jun 13
        assert result.candidate_dates == [date(2026, 6, 6), date(2026, 6, 13)]
        assert date(2026, 6, 1) not in result.candidate_dates  # past date excluded

    def test_date_range_end_before_clamped_start_returns_empty(self) -> None:
        # date_range entirely before anchor_date → empty after clamping
        result = _resolve(
            {
                "date_request_type": "weekday_range_over_relative_period",
                "weekdays": ["friday"],
                "relative_period": None,
                "date_range": {"start_date": "2026-05-01", "end_date": "2026-05-31"},
            },
            anchor=date(2026, 6, 3),
        )
        assert result.candidate_dates == []

    def test_directionless_relative_period_without_date_range_uses_default_window(self) -> None:
        # No date_range provided — ENQ-006 fallback not triggered; single-weekday
        # short-circuit in _expand_recurring fires, resolving via next-calendar-week
        # convention: anchor=Wed Jun 3, "next Friday" = Mon Jun 8 + 4 = Jun 12.
        result = _resolve(
            {
                "date_request_type": "weekday_range_over_relative_period",
                "weekdays": ["friday"],
                "relative_period": {"amount": None, "unit": None, "direction": None},
            },
            anchor=date(2026, 6, 3),
        )
        assert result.candidate_dates == [date(2026, 6, 12)]

    def test_populated_relative_period_direction_is_not_overridden_by_date_range(self) -> None:
        # Existing behaviour: when direction='next' is present, date_range is ignored
        result = _resolve(
            {
                "date_request_type": "weekday_range_over_relative_period",
                "weekdays": ["friday", "saturday"],
                "relative_period": {"direction": "next", "unit": "week", "amount": 2},
                # date_range present but should NOT override the relative_period
                "date_range": {"start_date": "2026-09-01", "end_date": "2026-09-30"},
            },
            anchor=date(2026, 7, 20),  # Monday
        )
        # Fri/Sat in next 2 weeks from 2026-07-21: Jul 24, 25, Jul 31, Aug 1
        assert all(d.weekday() in (4, 5) for d in result.candidate_dates)
        assert date(2026, 9, 4) not in result.candidate_dates  # Sep date not used


# ── Ambiguous numeric date ────────────────────────────────────────────────────


class TestAmbiguousNumericDate:
    def test_ambiguous_sets_requires_clarification(self) -> None:
        result = _resolve({
            "date_request_type": "ambiguous_numeric_date",
            "requires_date_clarification": True,
            "clarification_question": "Did you mean 4 April or 14 April?",
            "ambiguous_dates": [],
        })
        assert result.requires_date_clarification is True

    def test_ambiguous_stores_possible_dates(self) -> None:
        result = _resolve({
            "date_request_type": "ambiguous_numeric_date",
            "ambiguous_dates": [
                {"possible_dates": ["2026-04-04", "2026-04-14"]},
            ],
        })
        assert date(2026, 4, 4) in result.candidate_dates
        assert date(2026, 4, 14) in result.candidate_dates

    def test_ambiguous_deduplicates_candidates(self) -> None:
        result = _resolve({
            "date_request_type": "ambiguous_numeric_date",
            "ambiguous_dates": [
                {"possible_dates": ["2026-04-04", "2026-04-04"]},
            ],
        })
        assert result.candidate_dates.count(date(2026, 4, 4)) == 1


# ── Unknown type ──────────────────────────────────────────────────────────────


class TestRelativePeriodType:
    """The LLM sometimes emits date_request_type='relative_period' (not in schema)."""

    def test_relative_period_single_weekday_resolves_to_next_calendar_week(self) -> None:
        # "next Wednesday" from Monday 2026-06-01 → Wednesday of next calendar week
        result = _resolve(
            {
                "date_request_type": "relative_period",
                "weekdays": ["wednesday"],
                "relative_period": {"direction": "next", "unit": "week", "amount": 1},
            },
            anchor=date(2026, 6, 1),  # Monday
        )
        assert result.candidate_dates == [date(2026, 6, 10)]

    def test_relative_period_multiple_weekdays_uses_range(self) -> None:
        result = _resolve(
            {
                "date_request_type": "relative_period",
                "weekdays": ["friday", "saturday"],
                "relative_period": {"direction": "next", "unit": "week", "amount": 1},
            },
            anchor=date(2026, 6, 1),
        )
        assert all(d.weekday() in (4, 5) for d in result.candidate_dates)
        assert len(result.candidate_dates) > 0


class TestUnknownType:
    def test_unknown_type_returns_empty_candidates(self) -> None:
        result = _resolve({"date_request_type": "unknown"})
        assert result.candidate_dates == []
        assert result.date_request_type == "unknown"

    def test_empty_dict_returns_empty_candidates(self) -> None:
        result = _resolve({})
        assert result.candidate_dates == []


# ── Candidate date cap ────────────────────────────────────────────────────────


class TestCandidateDateCap:
    def test_cap_is_60(self) -> None:
        assert MAX_CANDIDATE_DATES == 60

    def test_multiple_choice_capped_at_max(self) -> None:
        many_dates = [f"2026-{m:02d}-{d:02d}" for m in range(1, 13) for d in range(1, 6)][:70]
        result = _resolve({
            "date_request_type": "multiple_choice",
            "explicit_dates": many_dates,
        })
        assert len(result.candidate_dates) <= MAX_CANDIDATE_DATES


# ── Static helpers ────────────────────────────────────────────────────────────


class TestStaticHelpers:
    def test_parse_date_valid_iso(self) -> None:
        d = EnquiryDateResolutionService._parse_date("2026-08-15")
        assert d == date(2026, 8, 15)

    def test_parse_date_with_timestamp_truncates(self) -> None:
        d = EnquiryDateResolutionService._parse_date("2026-08-15T12:00:00Z")
        assert d == date(2026, 8, 15)

    def test_parse_date_null_string_returns_none(self) -> None:
        assert EnquiryDateResolutionService._parse_date("NULL") is None

    def test_parse_date_none_returns_none(self) -> None:
        assert EnquiryDateResolutionService._parse_date(None) is None

    def test_parse_date_invalid_returns_none(self) -> None:
        assert EnquiryDateResolutionService._parse_date("not-a-date") is None

    def test_parse_weekday_monday(self) -> None:
        assert EnquiryDateResolutionService._parse_weekday("monday") == 0

    def test_parse_weekday_sunday(self) -> None:
        assert EnquiryDateResolutionService._parse_weekday("sunday") == 6

    def test_parse_weekday_case_insensitive(self) -> None:
        assert EnquiryDateResolutionService._parse_weekday("FRIDAY") == 4

    def test_parse_weekday_invalid_returns_none(self) -> None:
        assert EnquiryDateResolutionService._parse_weekday("funday") is None

    def test_resolve_relative_period_next_week(self) -> None:
        start, end = EnquiryDateResolutionService._resolve_relative_period(
            {"direction": "next", "unit": "week", "amount": 1},
            date(2026, 7, 20),
        )
        assert start == date(2026, 7, 21)
        assert end == date(2026, 7, 27)

    def test_resolve_relative_period_last_week(self) -> None:
        start, end = EnquiryDateResolutionService._resolve_relative_period(
            {"direction": "last", "unit": "week", "amount": 1},
            date(2026, 7, 20),
        )
        assert end == date(2026, 7, 19)
        assert (end - start).days == 6

    def test_date_range_list_inclusive(self) -> None:
        dates = EnquiryDateResolutionService._date_range_list(
            date(2026, 8, 1), date(2026, 8, 3)
        )
        assert dates == [date(2026, 8, 1), date(2026, 8, 2), date(2026, 8, 3)]

    def test_date_range_list_capped(self) -> None:
        dates = EnquiryDateResolutionService._date_range_list(
            date(2026, 1, 1), date(2027, 12, 31)
        )
        assert len(dates) == MAX_CANDIDATE_DATES


# ── Default constants ─────────────────────────────────────────────────────────


class TestConstants:
    def test_default_timezone(self) -> None:
        assert DEFAULT_TIMEZONE == "Europe/London"

    def test_source_types(self) -> None:
        assert SOURCE_TYPE_EXPLICIT == "explicit"
        assert SOURCE_TYPE_DETERMINISTIC == "deterministic"


# ── Persistence: models unavailable ──────────────────────────────────────────


class TestPersistenceNoop:
    def test_no_error_when_date_request_model_unavailable(self) -> None:
        service = _make_service()
        request = DateResolutionRequest(
            enquiry_id=uuid.uuid4(),
            date_request_dict={
                "date_request_type": "exact",
                "explicit_dates": ["2026-08-15"],
            },
        )
        with patch(
            "app.modules.enquiries.date_resolution_service._MODELS_AVAILABLE", False
        ):
            result = service.resolve(request)
        # Should still return candidate dates; just no DB row
        assert result.candidate_dates == [date(2026, 8, 15)]
        assert result.date_request_id is None
