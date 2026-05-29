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
