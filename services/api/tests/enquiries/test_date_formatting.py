"""Tests for date_formatting module (RESP-057)."""

from __future__ import annotations

import pytest

from app.modules.enquiries.date_formatting import format_event_date, format_event_date_list


class TestFormatEventDate:
    """format_event_date: ISO → natural hospitality format."""

    def test_friday_12_june(self) -> None:
        assert format_event_date("2026-06-12") == "Friday, 12 June 2026"

    def test_saturday_4_july(self) -> None:
        assert format_event_date("2026-07-04") == "Saturday, 4 July 2026"

    def test_no_leading_zero_on_single_digit_day(self) -> None:
        result = format_event_date("2026-06-05")
        assert result.startswith("Friday, 5 ")

    def test_double_digit_day_unchanged(self) -> None:
        result = format_event_date("2026-06-25")
        assert result.startswith("Thursday, 25 ")

    def test_first_of_month(self) -> None:
        result = format_event_date("2026-08-01")
        assert result.startswith("Saturday, 1 ")

    def test_december(self) -> None:
        result = format_event_date("2026-12-25")
        assert "25 December 2026" in result

    def test_january(self) -> None:
        result = format_event_date("2027-01-01")
        assert "1 January 2027" in result

    def test_none_returns_empty_string(self) -> None:
        assert format_event_date(None) == ""  # type: ignore[arg-type]

    def test_empty_string_returns_empty_string(self) -> None:
        assert format_event_date("") == ""

    def test_non_iso_string_passes_through_unchanged(self) -> None:
        """Non-ISO strings (e.g. natural dates, TBC) pass through unchanged."""
        assert format_event_date("the 12th of June") == "the 12th of June"
        assert format_event_date("TBC") == "TBC"
        assert format_event_date("next Saturday") == "next Saturday"

    def test_invalid_iso_date_passes_through(self) -> None:
        """Strings matching YYYY-MM-DD but with invalid values pass through."""
        assert format_event_date("2026-13-01") == "2026-13-01"

    def test_already_formatted_date_passes_through(self) -> None:
        """Already-formatted dates pass through without double-formatting."""
        formatted = "Friday, 12 June 2026"
        assert format_event_date(formatted) == formatted


class TestFormatEventDateList:
    """format_event_date_list: apply formatter to a list of strings."""

    def test_formats_all_iso_dates(self) -> None:
        result = format_event_date_list(["2026-06-12", "2026-06-19"])
        assert result == ["Friday, 12 June 2026", "Friday, 19 June 2026"]

    def test_empty_list_returns_empty_list(self) -> None:
        assert format_event_date_list([]) == []

    def test_none_returns_empty_list(self) -> None:
        assert format_event_date_list(None) == []  # type: ignore[arg-type]

    def test_mixed_list_passes_non_iso_through(self) -> None:
        result = format_event_date_list(["2026-06-12", "TBC"])
        assert result == ["Friday, 12 June 2026", "TBC"]

    def test_single_element_list(self) -> None:
        assert format_event_date_list(["2026-07-04"]) == ["Saturday, 4 July 2026"]
