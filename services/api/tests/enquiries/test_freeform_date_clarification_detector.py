"""Tests for FreeformDateClarificationDetector (DATE-003 / DATE-004).

Covers:
  - Multi-option weekday detection ("next Friday or Saturday")
  - Approximate month range detection ("mid-July", "early August", "late September")
  - Week commencing ("week commencing 13 July", "w/c 13th July")
  - First/last weekend in month ("first weekend in August")
  - Any flexible next/this week ("any weekday next week")
  - Weekday range ("Friday to Sunday", "Thursday through Saturday")
  - Between weekdays ("between Thursday and Saturday")
  - Weekend after next ("the weekend after next")
  - No-match cases (normal expressions that don't need extra clarification)
"""

from __future__ import annotations

from datetime import date

import pytest

from app.modules.enquiries.freeform_date_clarification_detector import (
    FreeformDateClarificationDetector,
)


# Anchor: Tuesday 1 July 2026 (weekday=1)
_ANCHOR = date(2026, 7, 1)


# ── Multi-option weekday ──────────────────────────────────────────────────────


class TestMultiOptionWeekday:
    """Pattern 1: 'next Friday or Saturday' style expressions."""

    def test_next_friday_or_saturday_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "next Friday or Saturday", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.clarification_required is True
        assert result.detection_reason == "multi_option_weekday"

    def test_next_friday_or_saturday_question_names_both_days(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "next Friday or Saturday", anchor_date=_ANCHOR
        )
        # Next week from 2026-07-01 (Tue): Mon 2026-07-06, Fri=2026-07-10, Sat=2026-07-11
        assert "Friday" in result.clarification_question
        assert "Saturday" in result.clarification_question
        assert "?" in result.clarification_question

    def test_next_friday_or_saturday_candidate_dates_are_correct(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "next Friday or Saturday", anchor_date=_ANCHOR
        )
        # Next week from 2026-07-01: Fri=2026-07-10, Sat=2026-07-11
        assert "2026-07-10" in result.candidate_dates
        assert "2026-07-11" in result.candidate_dates

    def test_thursday_or_friday_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "Thursday or Friday next week", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.clarification_required is True
        assert "Thursday" in result.clarification_question
        assert "Friday" in result.clarification_question

    def test_saturday_or_sunday_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "Could we book Saturday or Sunday?", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.clarification_required is True
        assert "Saturday" in result.clarification_question
        assert "Sunday" in result.clarification_question

    def test_single_weekday_not_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "next Friday", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is False

    def test_exact_date_not_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "12 July 2026", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is False


# ── Approximate month range ───────────────────────────────────────────────────


class TestApproximateMonthRange:
    """Pattern 2: 'mid-July', 'early August', 'late September' style expressions."""

    def test_mid_july_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "mid-July", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.clarification_required is True
        assert result.detection_reason == "approximate_month_range"

    def test_mid_july_question_mentions_month_and_year(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "mid-July", anchor_date=_ANCHOR
        )
        assert "July" in result.clarification_question
        assert "2026" in result.clarification_question
        assert "?" in result.clarification_question

    def test_early_august_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "early August", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert "August" in result.clarification_question

    def test_late_september_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "late September", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert "September" in result.clarification_question

    def test_mid_july_no_candidate_dates(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "mid-July", anchor_date=_ANCHOR
        )
        # Approximate month expressions don't produce specific candidate dates
        assert result.candidate_dates == []

    def test_end_of_month_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "end of August", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.clarification_required is True

    def test_mid_july_year_wraps_when_month_past(self) -> None:
        # Anchor in August — mid-July should wrap to next year
        anchor_aug = date(2026, 8, 15)
        result = FreeformDateClarificationDetector.detect(
            "mid-July", anchor_date=anchor_aug
        )
        assert result.pattern_detected is True
        assert "2027" in result.clarification_question


# ── No-match cases ────────────────────────────────────────────────────────────


class TestNoMatchCases:
    """Expressions that should not trigger clarification detection."""

    def test_empty_string_no_match(self) -> None:
        result = FreeformDateClarificationDetector.detect("", anchor_date=_ANCHOR)
        assert result.pattern_detected is False

    def test_none_raw_text_no_match(self) -> None:
        result = FreeformDateClarificationDetector.detect(None, anchor_date=_ANCHOR)
        assert result.pattern_detected is False

    def test_specific_date_no_match(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "15 July 2026", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is False

    def test_any_weekend_this_month_no_match(self) -> None:
        # Already handled by recurring_window path in DateResolutionService
        result = FreeformDateClarificationDetector.detect(
            "any weekend this month", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is False


# ── Pattern 3: Week commencing ────────────────────────────────────────────────


class TestWeekCommencing:
    """Pattern 3: 'week commencing 13 July', 'w/c 13th July' expressions."""

    def test_week_commencing_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "week commencing 13 July", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.clarification_required is True
        assert result.detection_reason == "week_commencing"

    def test_wc_short_form_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "w/c 13th July", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.detection_reason == "week_commencing"

    def test_week_commencing_produces_five_candidates(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "week commencing 13 July", anchor_date=_ANCHOR
        )
        assert len(result.candidate_dates) == 5
        assert result.candidate_dates[0] == "2026-07-13"
        assert result.candidate_dates[4] == "2026-07-17"

    def test_week_commencing_question_contains_month(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "week commencing 13 July", anchor_date=_ANCHOR
        )
        assert "July" in result.clarification_question
        assert "13" in result.clarification_question

    def test_wc_no_slash_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "wc 7 August", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.detection_reason == "week_commencing"


# ── Pattern 4 & 5: First/last weekend in month ───────────────────────────────


class TestFirstLastWeekendInMonth:
    """Patterns 4 & 5: 'first weekend in August', 'last weekend in August'."""

    def test_first_weekend_in_august_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "first weekend in August", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.clarification_required is True
        assert result.detection_reason == "first_weekend_in_month"

    def test_last_weekend_in_august_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "last weekend in August", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.detection_reason == "last_weekend_in_month"

    def test_first_weekend_produces_two_candidates(self) -> None:
        # August 2026: first Saturday = 1 Aug
        result = FreeformDateClarificationDetector.detect(
            "first weekend in August", anchor_date=_ANCHOR
        )
        assert len(result.candidate_dates) == 2
        assert result.candidate_dates[0] == "2026-08-01"
        assert result.candidate_dates[1] == "2026-08-02"

    def test_first_weekend_question_mentions_both_days(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "first weekend in August", anchor_date=_ANCHOR
        )
        assert "Saturday" in result.clarification_question
        assert "Sunday" in result.clarification_question

    def test_last_weekend_in_august_produces_two_candidates(self) -> None:
        # August 2026: last Saturday = 29 Aug
        result = FreeformDateClarificationDetector.detect(
            "last weekend in August", anchor_date=_ANCHOR
        )
        assert len(result.candidate_dates) == 2
        assert result.candidate_dates[0] == "2026-08-29"
        assert result.candidate_dates[1] == "2026-08-30"


# ── Pattern 6: Any flexible time next/this week ───────────────────────────────


class TestAnyFlexibleNextWeek:
    """Pattern 6: 'any weekday next week', 'any evening next week'."""

    def test_any_weekday_next_week_detected(self) -> None:
        # Anchor: Tuesday 1 July 2026 → next week Mon 6 Jul
        result = FreeformDateClarificationDetector.detect(
            "any weekday next week", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.clarification_required is True
        assert result.detection_reason == "any_flexible_next_week"

    def test_any_evening_next_week_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "any evening next week", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.detection_reason == "any_flexible_next_week"

    def test_any_morning_this_week_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "any morning this week", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.detection_reason == "any_flexible_next_week"

    def test_any_weekday_next_week_produces_five_candidates(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "any weekday next week", anchor_date=_ANCHOR
        )
        # Next week from Tue 1 Jul: Mon 6 Jul – Fri 10 Jul
        assert len(result.candidate_dates) == 5
        assert result.candidate_dates[0] == "2026-07-06"
        assert result.candidate_dates[4] == "2026-07-10"

    def test_any_flexible_next_week_question_lists_days(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "any weekday next week", anchor_date=_ANCHOR
        )
        assert "Monday" in result.clarification_question
        assert "Friday" in result.clarification_question


# ── Pattern 7: Weekday range (to / through) ───────────────────────────────────


class TestWeekdayRangeTo:
    """Pattern 7: 'Friday to Sunday', 'Thursday through Saturday'."""

    def test_friday_to_sunday_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "Friday to Sunday", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.clarification_required is True
        assert result.detection_reason == "weekday_range"

    def test_thursday_through_saturday_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "Thursday through Saturday", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.detection_reason == "weekday_range"

    def test_friday_to_sunday_produces_three_candidates(self) -> None:
        # Anchor: Tue 1 Jul → next Friday = 3 Jul, Sat = 4 Jul, Sun = 5 Jul
        result = FreeformDateClarificationDetector.detect(
            "Friday to Sunday", anchor_date=_ANCHOR
        )
        assert len(result.candidate_dates) == 3
        assert result.candidate_dates[0] == "2026-07-03"
        assert result.candidate_dates[1] == "2026-07-04"
        assert result.candidate_dates[2] == "2026-07-05"

    def test_weekday_range_question_lists_all_days(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "Friday to Sunday", anchor_date=_ANCHOR
        )
        assert "Friday" in result.clarification_question
        assert "Sunday" in result.clarification_question


# ── Pattern 8: Between weekdays ───────────────────────────────────────────────


class TestBetweenWeekdays:
    """Pattern 8: 'between Thursday and Saturday'."""

    def test_between_thursday_and_saturday_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "between Thursday and Saturday", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.clarification_required is True
        assert result.detection_reason == "between_weekdays"

    def test_between_weekdays_produces_candidates(self) -> None:
        # Anchor: Tue 1 Jul → next Thu = 2 Jul, Fri = 3 Jul, Sat = 4 Jul
        result = FreeformDateClarificationDetector.detect(
            "between Thursday and Saturday", anchor_date=_ANCHOR
        )
        assert len(result.candidate_dates) == 3
        assert result.candidate_dates[0] == "2026-07-02"
        assert result.candidate_dates[2] == "2026-07-04"

    def test_between_weekdays_question_lists_days(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "between Thursday and Saturday", anchor_date=_ANCHOR
        )
        assert "Thursday" in result.clarification_question
        assert "Saturday" in result.clarification_question


# ── Pattern 9: Weekend after next ────────────────────────────────────────────


class TestWeekendAfterNext:
    """Pattern 9: 'the weekend after next', 'weekend after next'."""

    def test_weekend_after_next_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "the weekend after next", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.clarification_required is True
        assert result.detection_reason == "weekend_after_next"

    def test_weekend_after_next_no_the_detected(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "weekend after next", anchor_date=_ANCHOR
        )
        assert result.pattern_detected is True
        assert result.detection_reason == "weekend_after_next"

    def test_weekend_after_next_produces_two_candidates(self) -> None:
        # Anchor: Tue 1 Jul → next Sat = 4 Jul → wan Sat = 11 Jul, Sun = 12 Jul
        result = FreeformDateClarificationDetector.detect(
            "the weekend after next", anchor_date=_ANCHOR
        )
        assert len(result.candidate_dates) == 2
        assert result.candidate_dates[0] == "2026-07-11"
        assert result.candidate_dates[1] == "2026-07-12"

    def test_weekend_after_next_question_names_both_days(self) -> None:
        result = FreeformDateClarificationDetector.detect(
            "the weekend after next", anchor_date=_ANCHOR
        )
        assert "Saturday" in result.clarification_question
        assert "Sunday" in result.clarification_question
