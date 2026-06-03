"""Tests for DateContextValidator (ENQ-003).

All tests are unit-level — no DB or LLM required.
"""

from __future__ import annotations

import pytest

from app.modules.enquiries.date_context_validator import DateContextValidator


@pytest.fixture()
def validator() -> DateContextValidator:
    return DateContextValidator()


# ── validate() — None / empty input ───────────────────────────────────────────


class TestNullInput:
    def test_none_returns_absent_warning(self, validator):
        warnings = validator.validate(None)
        assert len(warnings) == 1
        assert "absent" in warnings[0]

    def test_empty_dict_returns_absent_warning(self, validator):
        warnings = validator.validate({})
        assert len(warnings) == 1
        assert "absent" in warnings[0]

    def test_non_dict_returns_absent_warning(self, validator):
        warnings = validator.validate("not a dict")  # type: ignore[arg-type]
        assert len(warnings) == 1
        assert "absent" in warnings[0]


# ── validate() — unknown type (no contextual checks) ─────────────────────────


class TestUnknownType:
    def test_unknown_type_no_contextual_warnings(self, validator):
        dr = {"date_request_type": "unknown"}
        warnings = validator.validate(dr)
        assert warnings == []

    def test_exact_type_no_contextual_warnings(self, validator):
        dr = {"date_request_type": "exact", "explicit_dates": ["2026-08-15"]}
        warnings = validator.validate(dr)
        assert warnings == []


# ── validate() — month checks ─────────────────────────────────────────────────


class TestMonthCheck:
    @pytest.mark.parametrize("dr_type", [
        "month_flexible",
        "date_range",
        "weekday_range_over_relative_period",
        "recurring_window",
        "mixed_relative_dates",
    ])
    def test_missing_month_produces_warning(self, validator, dr_type):
        dr = {"date_request_type": dr_type}
        warnings = validator.validate(dr)
        assert any("missing month" in w for w in warnings), (
            f"Expected 'missing month' warning for type {dr_type!r}, got: {warnings}"
        )

    def test_present_month_no_warning(self, validator):
        dr = {"date_request_type": "month_flexible", "month": 8}
        warnings = validator.validate(dr)
        assert not any("missing month" in w for w in warnings)

    def test_null_string_month_produces_warning(self, validator):
        dr = {"date_request_type": "month_flexible", "month": "NULL"}
        warnings = validator.validate(dr)
        assert any("missing month" in w for w in warnings)


# ── validate() — year checks ──────────────────────────────────────────────────


class TestYearCheck:
    def test_month_without_year_produces_warning(self, validator):
        dr = {"date_request_type": "month_flexible", "month": 8}
        warnings = validator.validate(dr)
        assert any("missing year" in w for w in warnings)

    def test_month_with_year_no_year_warning(self, validator):
        dr = {"date_request_type": "month_flexible", "month": 8, "year": 2026}
        warnings = validator.validate(dr)
        assert not any("missing year" in w for w in warnings)

    def test_no_month_no_year_warning(self, validator):
        # When month is absent, year warning is not triggered
        dr = {"date_request_type": "exact"}
        warnings = validator.validate(dr)
        assert not any("missing year" in w for w in warnings)


# ── validate() — date_range bounds checks ────────────────────────────────────


class TestDateRangeBoundsCheck:
    def test_missing_start_and_end_produces_warnings(self, validator):
        dr = {"date_request_type": "date_range", "date_range": {}}
        warnings = validator.validate(dr)
        assert any("start_date" in w for w in warnings)
        assert any("end_date" in w for w in warnings)

    def test_missing_start_only(self, validator):
        dr = {
            "date_request_type": "date_range",
            "date_range": {"end_date": "2026-08-31"},
        }
        warnings = validator.validate(dr)
        assert any("start_date" in w for w in warnings)
        assert not any("end_date" in w for w in warnings)

    def test_both_bounds_present_no_range_warning(self, validator):
        dr = {
            "date_request_type": "date_range",
            "date_range": {"start_date": "2026-08-01", "end_date": "2026-08-31"},
            "month": 8,
            "year": 2026,
        }
        warnings = validator.validate(dr)
        assert not any("start_date" in w for w in warnings)
        assert not any("end_date" in w for w in warnings)

    def test_null_date_range_object_produces_warnings(self, validator):
        dr = {"date_request_type": "date_range", "date_range": None}
        warnings = validator.validate(dr)
        assert any("start_date" in w for w in warnings)


# ── validate() — weekdays checks ──────────────────────────────────────────────


class TestWeekdaysCheck:
    @pytest.mark.parametrize("dr_type", [
        "weekday_range_over_relative_period",
        "recurring_window",
        "relative_period",
    ])
    def test_missing_weekdays_produces_warning(self, validator, dr_type):
        dr = {"date_request_type": dr_type}
        warnings = validator.validate(dr)
        assert any("missing weekdays" in w for w in warnings)

    def test_weekdays_present_no_warning(self, validator):
        dr = {
            "date_request_type": "weekday_range_over_relative_period",
            "weekdays": ["friday", "saturday"],
            "relative_period": {"direction": "next", "unit": "month", "amount": 1},
        }
        warnings = validator.validate(dr)
        assert not any("missing weekdays" in w for w in warnings)

    def test_empty_weekdays_list_produces_warning(self, validator):
        dr = {"date_request_type": "weekday_range_over_relative_period", "weekdays": []}
        warnings = validator.validate(dr)
        assert any("missing weekdays" in w for w in warnings)


# ── validate() — relative_period checks ──────────────────────────────────────


class TestRelativePeriodCheck:
    @pytest.mark.parametrize("dr_type", [
        "weekday_range_over_relative_period",
        "recurring_window",
        "relative_period",
    ])
    def test_missing_relative_period_produces_warning(self, validator, dr_type):
        dr = {"date_request_type": dr_type, "weekdays": ["friday"]}
        warnings = validator.validate(dr)
        assert any("missing relative_period" in w for w in warnings)

    def test_partial_relative_period_produces_warning(self, validator):
        dr = {
            "date_request_type": "weekday_range_over_relative_period",
            "weekdays": ["friday"],
            "relative_period": {"direction": "next"},  # missing unit
        }
        warnings = validator.validate(dr)
        assert any("missing relative_period" in w for w in warnings)

    def test_full_relative_period_no_warning(self, validator):
        dr = {
            "date_request_type": "weekday_range_over_relative_period",
            "weekdays": ["friday"],
            "relative_period": {"direction": "next", "unit": "month", "amount": 1},
        }
        warnings = validator.validate(dr)
        assert not any("missing relative_period" in w for w in warnings)


# ── validate_and_log() ────────────────────────────────────────────────────────


class TestValidateAndLog:
    def test_returns_same_warnings_as_validate(self, validator):
        dr = {"date_request_type": "month_flexible"}
        assert validator.validate_and_log(dr) == validator.validate(dr)

    def test_accepts_enquiry_id_for_context(self, validator):
        import uuid
        dr = {"date_request_type": "month_flexible"}
        warnings = validator.validate_and_log(dr, enquiry_id=uuid.uuid4())
        assert isinstance(warnings, list)

    def test_returns_empty_list_when_no_warnings(self, validator):
        dr = {
            "date_request_type": "exact",
            "explicit_dates": ["2026-08-15"],
        }
        warnings = validator.validate_and_log(dr)
        assert warnings == []
