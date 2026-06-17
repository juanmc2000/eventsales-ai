"""Freeform Date Clarification Detector (DATE-003 / DATE-004).

Detects freeform date expressions in raw guest text that cannot be resolved to
specific candidate dates without further guest input.  Applied as a fallback
when DateResolutionService produces unknown type and no candidates.

Detected patterns:
  1. Multi-option weekday    — "next Friday or Saturday", "Thursday or Friday next week"
     → clarification_required=True, question names both days
  2. Approximate month range — "mid-July", "early August", "late September"
     → clarification_required=True, question asks for specific date
  3. Week commencing         — "week commencing 13 July", "w/c 13 July"
     → clarification_required=True, question asks for specific day in that week
  4. First/last weekend      — "first weekend in August", "last weekend in August"
     → clarification_required=True, question asks Saturday or Sunday
  5. Any flexible next week  — "any weekday next week", "any evening next week"
     → clarification_required=True, question asks for preferred day
  6. Weekday range (to/through) — "Friday to Sunday", "Thursday through Saturday"
     → clarification_required=True, question lists all days in range
  7. Between weekdays        — "between Thursday and Saturday"
     → clarification_required=True, question lists all days in range
  8. Weekend after next      — "the weekend after next"
     → clarification_required=True, question names both days of that weekend

No LLM calls are made.  All detection is regex-based and deterministic.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date, timedelta


# ── Constants ────────────────────────────────────────────────────────────────

_WEEKDAY_NAMES = (
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
)

_WEEKDAY_PATTERN = re.compile(
    r"\b(" + "|".join(_WEEKDAY_NAMES) + r")\b",
    re.IGNORECASE,
)

_MULTI_WEEKDAY_OR_PATTERN = re.compile(
    r"\b(?:next\s+|this\s+)?"
    r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"\s+or\s+"
    r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)

_APPROXIMATE_MONTH_PATTERN = re.compile(
    r"\b(early|mid(?:-|\s)?|late|end\s+of)\s*"
    r"(january|february|march|april|may|june|july|august|september|october|november|december)\b",
    re.IGNORECASE,
)

# DATE-004: new patterns ────────────────────────────────────────────────────────

# Pattern 3: "week commencing 13 July", "wc 13 July", "w/c 13th July"
_WEEK_COMMENCING_PATTERN = re.compile(
    r"\b(?:week\s+commencing|w/?c)\s+"
    r"(\d{1,2})(?:st|nd|rd|th)?\s+"
    r"(january|february|march|april|may|june|july|august|september|october|november|december)\b",
    re.IGNORECASE,
)

# Pattern 4 & 5: "first weekend in August", "last weekend in August"
_WEEKEND_IN_MONTH_PATTERN = re.compile(
    r"\b(first|last)\s+weekend\s+in\s+"
    r"(january|february|march|april|may|june|july|august|september|october|november|december)\b",
    re.IGNORECASE,
)

# Pattern 6: "any weekday next week", "any evening next week", "any morning this week"
_ANY_FLEXIBLE_NEXT_WEEK_PATTERN = re.compile(
    r"\bany\s+(?:weekday|evening|day|morning|afternoon|night)\s+(?:next|this)\s+week\b",
    re.IGNORECASE,
)

# Pattern 7: "Friday to Sunday", "Thursday through Saturday"
_WEEKDAY_RANGE_TO_PATTERN = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"\s+(?:to|through)\s+"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)

# Pattern 8: "between Thursday and Saturday"
_BETWEEN_WEEKDAYS_PATTERN = re.compile(
    r"\bbetween\s+"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"\s+and\s+"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)

# Pattern 9: "the weekend after next", "weekend after next"
_WEEKEND_AFTER_NEXT_PATTERN = re.compile(
    r"\b(?:the\s+)?weekend\s+after\s+next\b",
    re.IGNORECASE,
)

_MONTH_NAME_TO_NUMBER: dict[str, int] = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

_WEEKDAY_PYTHON: dict[str, int] = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


# ── Output ────────────────────────────────────────────────────────────────────


@dataclass
class ClarificationDetectionResult:
    """Result of FreeformDateClarificationDetector.detect().

    Attributes:
        pattern_detected:       True when a known ambiguous pattern was found.
        clarification_required: True when the guest must clarify before proceeding.
        clarification_question: Human-readable question to include in the response.
        detection_reason:       Machine-readable reason code.
        candidate_dates:        Specific dates extracted from the pattern, if any.
    """

    pattern_detected: bool = False
    clarification_required: bool = False
    clarification_question: str | None = None
    detection_reason: str | None = None
    candidate_dates: list[str] = field(default_factory=list)


# ── Detector ─────────────────────────────────────────────────────────────────


class FreeformDateClarificationDetector:
    """Detects freeform date expressions that require guest clarification.

    Usage::

        from datetime import date
        result = FreeformDateClarificationDetector.detect(
            raw_text="next Friday or Saturday",
            anchor_date=date(2026, 7, 1),
        )
        # result.pattern_detected → True
        # result.clarification_question → "Could you confirm whether you mean Friday, 3 July or Saturday, 4 July?"
    """

    @classmethod
    def detect(
        cls,
        raw_text: str | None,
        anchor_date: date | None = None,
    ) -> ClarificationDetectionResult:
        """Run all detection patterns against raw_text.

        Patterns are tested in priority order; the first match wins.

        Args:
            raw_text:    The raw date phrase as extracted from the guest message.
            anchor_date: Reference date for resolving relative weekday expressions.
                         Defaults to today when None.

        Returns:
            ClarificationDetectionResult — pattern_detected=False when no match.
        """
        if not raw_text or not raw_text.strip():
            return ClarificationDetectionResult()

        anchor = anchor_date or date.today()

        # Pattern 1: multi-option weekday ("next Friday or Saturday")
        result = cls._detect_multi_weekday(raw_text, anchor)
        if result.pattern_detected:
            return result

        # Pattern 2: approximate month range ("mid-July", "early August")
        result = cls._detect_approximate_month(raw_text, anchor)
        if result.pattern_detected:
            return result

        # DATE-004: new patterns ─────────────────────────────────────────────

        # Pattern 3: week commencing ("week commencing 13 July", "w/c 13 July")
        result = cls._detect_week_commencing(raw_text, anchor)
        if result.pattern_detected:
            return result

        # Pattern 4 & 5: first/last weekend in month
        result = cls._detect_weekend_in_month(raw_text, anchor)
        if result.pattern_detected:
            return result

        # Pattern 6: any flexible time next/this week
        result = cls._detect_any_flexible_next_week(raw_text, anchor)
        if result.pattern_detected:
            return result

        # Pattern 7: weekday range ("Friday to Sunday", "Thursday through Saturday")
        result = cls._detect_weekday_range(raw_text, anchor)
        if result.pattern_detected:
            return result

        # Pattern 8: between weekdays ("between Thursday and Saturday")
        result = cls._detect_between_weekdays(raw_text, anchor)
        if result.pattern_detected:
            return result

        # Pattern 9: weekend after next
        result = cls._detect_weekend_after_next(raw_text, anchor)
        if result.pattern_detected:
            return result

        return ClarificationDetectionResult()

    # ── Pattern 1: Multi-option weekday ──────────────────────────────────────

    @classmethod
    def _detect_multi_weekday(
        cls,
        raw_text: str,
        anchor: date,
    ) -> ClarificationDetectionResult:
        """Detect 'next Friday or Saturday' style expressions."""
        match = _MULTI_WEEKDAY_OR_PATTERN.search(raw_text)
        if not match:
            return ClarificationDetectionResult()

        # Extract the two weekday names from the match
        weekdays_found = _WEEKDAY_PATTERN.findall(match.group())
        if len(weekdays_found) < 2:
            return ClarificationDetectionResult()

        day1_name = weekdays_found[0].lower()
        day2_name = weekdays_found[1].lower()

        day1_num = _WEEKDAY_PYTHON.get(day1_name)
        day2_num = _WEEKDAY_PYTHON.get(day2_name)

        if day1_num is None or day2_num is None:
            return ClarificationDetectionResult()

        # Determine the reference window: "next week" if "next" appears in the text
        use_next_week = bool(re.search(r"\bnext\b", raw_text, re.IGNORECASE))

        day1_date = cls._resolve_weekday(day1_num, anchor, use_next_week)
        day2_date = cls._resolve_weekday(day2_num, anchor, use_next_week)

        candidates = []
        if day1_date:
            candidates.append(day1_date.isoformat())
        if day2_date:
            candidates.append(day2_date.isoformat())

        # Build clarification question
        parts = []
        if day1_date:
            parts.append(f"{day1_date.strftime('%A, %-d %B')}")
        if day2_date:
            parts.append(f"{day2_date.strftime('%A, %-d %B')}")

        if len(parts) == 2:
            question = f"Could you confirm whether you mean {parts[0]} or {parts[1]}?"
        elif len(parts) == 1:
            question = f"Could you confirm you mean {parts[0]}?"
        else:
            question = "Could you confirm the specific date you have in mind?"

        return ClarificationDetectionResult(
            pattern_detected=True,
            clarification_required=True,
            clarification_question=question,
            detection_reason="multi_option_weekday",
            candidate_dates=candidates,
        )

    @staticmethod
    def _resolve_weekday(weekday_num: int, anchor: date, use_next_week: bool) -> date | None:
        """Resolve a weekday number to the nearest future occurrence.

        When use_next_week=True, resolves to the next calendar week (Mon–Sun).
        Otherwise resolves to the first occurrence of that weekday >= anchor.
        """
        if use_next_week:
            # Next calendar week: start from Monday of next week
            days_to_next_monday = 7 - anchor.weekday()
            monday_next = anchor + timedelta(days=days_to_next_monday)
            return monday_next + timedelta(days=weekday_num)
        else:
            # First occurrence of weekday_num on or after anchor
            days_ahead = (weekday_num - anchor.weekday()) % 7
            return anchor + timedelta(days=days_ahead)

    # ── Pattern 2: Approximate month range ───────────────────────────────────

    @classmethod
    def _detect_approximate_month(
        cls,
        raw_text: str,
        anchor: date,
    ) -> ClarificationDetectionResult:
        """Detect 'mid-July', 'early August', 'late September' style expressions."""
        match = _APPROXIMATE_MONTH_PATTERN.search(raw_text)
        if not match:
            return ClarificationDetectionResult()

        qualifier = match.group(1).lower().replace("-", "").replace(" ", "")  # early/mid/late/endof
        month_name = match.group(2).lower()
        month_num = _MONTH_NAME_TO_NUMBER.get(month_name)

        if month_num is None:
            return ClarificationDetectionResult()

        # Determine year
        year = anchor.year
        if month_num < anchor.month:
            year += 1

        # Build month-aware question
        month_display = month_name.capitalize()
        if qualifier in ("mid", "midmid"):
            qualifier_text = f"mid-{month_display}"
        elif qualifier == "early":
            qualifier_text = f"early {month_display}"
        elif qualifier in ("late", "endof"):
            qualifier_text = f"late {month_display}"
        else:
            qualifier_text = month_display

        question = (
            f"Could you let me know the specific date you have in mind for {qualifier_text} {year}?"
        )

        return ClarificationDetectionResult(
            pattern_detected=True,
            clarification_required=True,
            clarification_question=question,
            detection_reason="approximate_month_range",
            candidate_dates=[],
        )

    # ── Pattern 3: Week commencing ────────────────────────────────────────────

    @classmethod
    def _detect_week_commencing(
        cls,
        raw_text: str,
        anchor: date,
    ) -> ClarificationDetectionResult:
        """Detect 'week commencing 13 July', 'w/c 13th July' expressions."""
        match = _WEEK_COMMENCING_PATTERN.search(raw_text)
        if not match:
            return ClarificationDetectionResult()

        day = int(match.group(1))
        month_name = match.group(2).lower()
        month_num = _MONTH_NAME_TO_NUMBER.get(month_name)
        if month_num is None:
            return ClarificationDetectionResult()

        year = anchor.year
        if month_num < anchor.month or (month_num == anchor.month and day < anchor.day):
            year += 1

        try:
            wc_monday = date(year, month_num, day)
        except ValueError:
            return ClarificationDetectionResult()

        # Generate candidate dates Mon–Fri of that week
        candidates = [
            (wc_monday + timedelta(days=i)).isoformat() for i in range(5)
        ]

        month_display = month_name.capitalize()
        question = (
            f"Could you let me know which day of the week commencing "
            f"{day} {month_display} {year} works best for you?"
        )

        return ClarificationDetectionResult(
            pattern_detected=True,
            clarification_required=True,
            clarification_question=question,
            detection_reason="week_commencing",
            candidate_dates=candidates,
        )

    # ── Pattern 4 & 5: First/last weekend in month ────────────────────────────

    @classmethod
    def _detect_weekend_in_month(
        cls,
        raw_text: str,
        anchor: date,
    ) -> ClarificationDetectionResult:
        """Detect 'first weekend in August', 'last weekend in August'."""
        match = _WEEKEND_IN_MONTH_PATTERN.search(raw_text)
        if not match:
            return ClarificationDetectionResult()

        ordinal = match.group(1).lower()   # "first" or "last"
        month_name = match.group(2).lower()
        month_num = _MONTH_NAME_TO_NUMBER.get(month_name)
        if month_num is None:
            return ClarificationDetectionResult()

        year = anchor.year
        if month_num < anchor.month:
            year += 1

        # Find first Saturday of the month
        first_day = date(year, month_num, 1)
        days_to_saturday = (5 - first_day.weekday()) % 7
        first_saturday = first_day + timedelta(days=days_to_saturday)
        first_sunday = first_saturday + timedelta(days=1)

        if ordinal == "first":
            sat = first_saturday
            sun = first_sunday
            reason = "first_weekend_in_month"
        else:
            # Last weekend: find last Saturday of month
            last_day_num = calendar.monthrange(year, month_num)[1]
            last_day = date(year, month_num, last_day_num)
            days_back = (last_day.weekday() - 5) % 7
            sat = last_day - timedelta(days=days_back)
            sun = sat + timedelta(days=1)
            reason = "last_weekend_in_month"

        candidates = [sat.isoformat(), sun.isoformat()]

        question = (
            f"Could you confirm whether you mean Saturday "
            f"{sat.strftime('%-d %B')} or Sunday {sun.strftime('%-d %B')} {year}?"
        )

        return ClarificationDetectionResult(
            pattern_detected=True,
            clarification_required=True,
            clarification_question=question,
            detection_reason=reason,
            candidate_dates=candidates,
        )

    # ── Pattern 6: Any flexible time next/this week ───────────────────────────

    @classmethod
    def _detect_any_flexible_next_week(
        cls,
        raw_text: str,
        anchor: date,
    ) -> ClarificationDetectionResult:
        """Detect 'any weekday next week', 'any evening this week' expressions."""
        match = _ANY_FLEXIBLE_NEXT_WEEK_PATTERN.search(raw_text)
        if not match:
            return ClarificationDetectionResult()

        use_next_week = bool(re.search(r"\bnext\b", raw_text, re.IGNORECASE))

        if use_next_week:
            days_to_monday = 7 - anchor.weekday()
            monday = anchor + timedelta(days=days_to_monday)
            week_label = "next week"
        else:
            # "this week" — Mon of current week
            monday = anchor - timedelta(days=anchor.weekday())
            week_label = "this week"

        # Mon–Fri candidates
        candidates = [
            (monday + timedelta(days=i)).isoformat() for i in range(5)
        ]
        day_names = [
            (monday + timedelta(days=i)).strftime("%A, %-d %B")
            for i in range(5)
        ]
        days_str = ", ".join(day_names[:-1]) + f", or {day_names[-1]}"

        question = (
            f"Could you let me know which day {week_label} suits you — "
            f"{days_str}?"
        )

        return ClarificationDetectionResult(
            pattern_detected=True,
            clarification_required=True,
            clarification_question=question,
            detection_reason="any_flexible_next_week",
            candidate_dates=candidates,
        )

    # ── Pattern 7: Weekday range (to / through) ───────────────────────────────

    @classmethod
    def _detect_weekday_range(
        cls,
        raw_text: str,
        anchor: date,
    ) -> ClarificationDetectionResult:
        """Detect 'Friday to Sunday', 'Thursday through Saturday' expressions."""
        match = _WEEKDAY_RANGE_TO_PATTERN.search(raw_text)
        if not match:
            return ClarificationDetectionResult()

        start_name = match.group(1).lower()
        end_name = match.group(2).lower()

        start_num = _WEEKDAY_PYTHON.get(start_name)
        end_num = _WEEKDAY_PYTHON.get(end_name)
        if start_num is None or end_num is None:
            return ClarificationDetectionResult()

        return cls._build_weekday_range_result(
            start_name, start_num, end_name, end_num, anchor,
            detection_reason="weekday_range",
        )

    # ── Pattern 8: Between weekdays ───────────────────────────────────────────

    @classmethod
    def _detect_between_weekdays(
        cls,
        raw_text: str,
        anchor: date,
    ) -> ClarificationDetectionResult:
        """Detect 'between Thursday and Saturday' expressions."""
        match = _BETWEEN_WEEKDAYS_PATTERN.search(raw_text)
        if not match:
            return ClarificationDetectionResult()

        start_name = match.group(1).lower()
        end_name = match.group(2).lower()

        start_num = _WEEKDAY_PYTHON.get(start_name)
        end_num = _WEEKDAY_PYTHON.get(end_name)
        if start_num is None or end_num is None:
            return ClarificationDetectionResult()

        return cls._build_weekday_range_result(
            start_name, start_num, end_name, end_num, anchor,
            detection_reason="between_weekdays",
        )

    @classmethod
    def _build_weekday_range_result(
        cls,
        start_name: str,
        start_num: int,
        end_name: str,
        end_num: int,
        anchor: date,
        detection_reason: str,
    ) -> ClarificationDetectionResult:
        """Shared helper: resolve a weekday range to candidate dates and question."""
        start_date = cls._resolve_weekday(start_num, anchor, use_next_week=False)
        if start_date is None:
            return ClarificationDetectionResult()

        # Build the range — handle wrap-around (e.g. Friday=4 to Sunday=6 is fine;
        # Friday=4 to Monday=0 wraps: +3 days mod 7 = 3)
        if end_num >= start_num:
            day_count = end_num - start_num + 1
        else:
            day_count = (7 - start_num) + end_num + 1

        candidates = []
        parts = []
        for i in range(day_count):
            d = start_date + timedelta(days=i)
            candidates.append(d.isoformat())
            parts.append(d.strftime("%A, %-d %B"))

        if len(parts) == 1:
            question = f"Could you confirm you mean {parts[0]}?"
        elif len(parts) == 2:
            question = f"Could you confirm whether you mean {parts[0]} or {parts[1]}?"
        else:
            question = (
                "Could you let me know which specific date you have in mind — "
                + ", ".join(parts[:-1])
                + f", or {parts[-1]}?"
            )

        return ClarificationDetectionResult(
            pattern_detected=True,
            clarification_required=True,
            clarification_question=question,
            detection_reason=detection_reason,
            candidate_dates=candidates,
        )

    # ── Pattern 9: Weekend after next ─────────────────────────────────────────

    @classmethod
    def _detect_weekend_after_next(
        cls,
        raw_text: str,
        anchor: date,
    ) -> ClarificationDetectionResult:
        """Detect 'the weekend after next', 'weekend after next' expressions."""
        if not _WEEKEND_AFTER_NEXT_PATTERN.search(raw_text):
            return ClarificationDetectionResult()

        # Next weekend: next Saturday from anchor
        days_to_next_sat = (5 - anchor.weekday()) % 7
        if days_to_next_sat == 0:
            days_to_next_sat = 7
        next_saturday = anchor + timedelta(days=days_to_next_sat)

        # Weekend after next: one week further
        wan_saturday = next_saturday + timedelta(weeks=1)
        wan_sunday = wan_saturday + timedelta(days=1)

        candidates = [wan_saturday.isoformat(), wan_sunday.isoformat()]
        question = (
            f"Could you confirm whether you mean Saturday "
            f"{wan_saturday.strftime('%-d %B')} or Sunday "
            f"{wan_sunday.strftime('%-d %B')}?"
        )

        return ClarificationDetectionResult(
            pattern_detected=True,
            clarification_required=True,
            clarification_question=question,
            detection_reason="weekend_after_next",
            candidate_dates=candidates,
        )
