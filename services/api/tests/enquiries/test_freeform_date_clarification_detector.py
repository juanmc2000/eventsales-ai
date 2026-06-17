"""Tests for FreeformDateClarificationDetector (DATE-003).

Covers:
  - Multi-option weekday detection ("next Friday or Saturday")
  - Approximate month range detection ("mid-July", "early August", "late September")
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
