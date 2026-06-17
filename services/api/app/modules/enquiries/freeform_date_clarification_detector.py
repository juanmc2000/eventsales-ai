"""Freeform Date Clarification Detector (DATE-003).

Detects freeform date expressions in raw guest text that cannot be resolved to
specific candidate dates without further guest input.  Applied as a fallback
when DateResolutionService produces unknown type and no candidates.

Detected patterns:
  1. Multi-option weekday — "next Friday or Saturday", "Thursday or Friday next week"
     → set clarification_required=True, generate question naming both days
  2. Approximate month range — "mid-July", "early August", "late September"
     → set clarification_required=True, generate question asking for specific date

No LLM calls are made.  All detection is regex-based and deterministic.
"""

from __future__ import annotations

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
