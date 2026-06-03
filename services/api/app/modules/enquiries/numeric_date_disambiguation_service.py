"""Deterministic numeric date disambiguation service (HOTFIX-001).

Resolves ambiguous numeric date formats (DD/MM vs MM/DD) for hospitality
enquiries.  The platform is UK-focused so DD/MM is the default convention.

All logic is deterministic — no LLM calls are made.

Decision rules (in order):
  Rule 1 — If one value > 12: unambiguous, resolve immediately.
  Rule 2 — If both values ≤ 12: generate both interpretations.
  Rule 3 — British (DD/MM) is the default assumption.
  Rule 5 — If British interpretation is > 180 days away AND American ≤ 90:
            use American, resolved_with_confirmation.
  Rule 6 — Next-year protection: if assumed date falls into the next calendar
            year and today is not Oct/Nov/Dec, set clarification_required.
  Rule 7 — If neither interpretation is clearly more plausible:
            unresolved_ambiguity (British used as fallback assumed date).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

# Horizon thresholds (days from anchor_date)
BRITISH_FAR_DAYS = 180   # British date is "too far" to be the obvious choice
AMERICAN_NEAR_DAYS = 90  # American date is "close enough" to be preferred

# If both interpretations are within this many days of each other, the choice
# is too close to call — return unresolved_ambiguity.
CLOSE_CALL_DAYS = 30

# Resolution status values (stored in enquiry_date_requests.ambiguity_type)
RESOLVED = "resolved"
RESOLVED_WITH_CONFIRMATION = "resolved_with_confirmation"
UNRESOLVED_AMBIGUITY = "unresolved_ambiguity"

_NUMERIC_DATE_RE = re.compile(r"^\s*(\d{1,2})\s*/\s*(\d{1,2})\s*$")

# Month names used in clarification questions
_MONTHS = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


@dataclass
class DisambiguationResult:
    """Result of numeric date disambiguation."""

    ambiguity_type: str
    assumed_date: date | None
    alternative_date: date | None
    clarification_required: bool
    clarification_reason: str | None
    clarification_question: str | None = field(default=None)


class NumericDateDisambiguationService:
    """Disambiguate numeric date strings such as '7/6', '9/1', '25/7'.

    Usage::

        result = NumericDateDisambiguationService.disambiguate(
            value1=9, value2=1, anchor_date=date(2026, 6, 3)
        )
        # result.assumed_date == date(2026, 9, 1) — American chosen by Rule 5
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def from_raw_text(
        cls,
        raw_text: str | None,
        anchor_date: date,
    ) -> DisambiguationResult | None:
        """Parse *raw_text* as "A/B" and run disambiguation.

        Returns None if *raw_text* cannot be parsed as a two-part numeric date.
        """
        if not raw_text:
            return None
        m = _NUMERIC_DATE_RE.match(raw_text.strip())
        if not m:
            return None
        try:
            a = int(m.group(1))
            b = int(m.group(2))
        except ValueError:
            return None
        if not (1 <= a <= 31 and 1 <= b <= 31):
            return None
        return cls.disambiguate(a, b, anchor_date)

    @classmethod
    def disambiguate(
        cls,
        value1: int,
        value2: int,
        anchor_date: date,
    ) -> DisambiguationResult:
        """Apply disambiguation rules to the two parts of a numeric date.

        *value1* / *value2* are the left and right sides of the slash.

        Examples (anchor=2026-06-03):
          disambiguate(25, 7)  → resolved, DD/MM, July 25 2026
          disambiguate(9, 1)   → resolved_with_confirmation, Sep 1 (Rule 5)
          disambiguate(1, 9)   → resolved_with_confirmation, Sep 1 (british default)
          disambiguate(7, 6)   → unresolved_ambiguity, Jun 7 assumed (too close)
        """
        # Rule 1a: value1 > 12 — can only be the day (DD/MM unambiguous)
        if value1 > 12:
            d = cls._nearest_future_date(day=value1, month=value2, anchor=anchor_date)
            if d is None:
                return cls._unresolvable()
            return DisambiguationResult(
                ambiguity_type=RESOLVED,
                assumed_date=d,
                alternative_date=None,
                clarification_required=False,
                clarification_reason=None,
            )

        # Rule 1b: value2 > 12 — can only be the day (must be MM/DD)
        if value2 > 12:
            d = cls._nearest_future_date(day=value2, month=value1, anchor=anchor_date)
            if d is None:
                return cls._unresolvable()
            return DisambiguationResult(
                ambiguity_type=RESOLVED,
                assumed_date=d,
                alternative_date=None,
                clarification_required=False,
                clarification_reason=None,
            )

        # Rule 2: both ≤ 12 — ambiguous
        # Rule 3: British default = DD/MM (day=value1, month=value2)
        british = cls._nearest_future_date(day=value1, month=value2, anchor=anchor_date)
        american = cls._nearest_future_date(day=value2, month=value1, anchor=anchor_date)

        if british is None and american is None:
            return cls._unresolvable()

        if british is None:
            return DisambiguationResult(
                ambiguity_type=RESOLVED_WITH_CONFIRMATION,
                assumed_date=american,
                alternative_date=None,
                clarification_required=True,
                clarification_reason="british_date_invalid",
                clarification_question=cls._question(american, None),
            )

        if american is None:
            return DisambiguationResult(
                ambiguity_type=RESOLVED_WITH_CONFIRMATION,
                assumed_date=british,
                alternative_date=None,
                clarification_required=True,
                clarification_reason="american_date_invalid",
                clarification_question=cls._question(british, None),
            )

        return cls._apply_heuristics(british, american, anchor_date)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    def _apply_heuristics(
        cls,
        british: date,
        american: date,
        anchor: date,
    ) -> DisambiguationResult:
        british_days = (british - anchor).days
        american_days = (american - anchor).days

        # Rule 5: British is far away, American is near — prefer American
        if british_days > BRITISH_FAR_DAYS and american_days <= AMERICAN_NEAR_DAYS:
            return DisambiguationResult(
                ambiguity_type=RESOLVED_WITH_CONFIRMATION,
                assumed_date=american,
                alternative_date=british,
                clarification_required=True,
                clarification_reason="american_nearer_by_horizon_heuristic",
                clarification_question=cls._question(american, british),
            )

        # Default assumed date: British
        assumed, alternative = british, american

        # Rule 6: assumed date is in the next calendar year and today is not
        # Oct/Nov/Dec — year-rollover assumption is risky, flag it
        if assumed.year > anchor.year and anchor.month not in (10, 11, 12):
            return DisambiguationResult(
                ambiguity_type=RESOLVED_WITH_CONFIRMATION,
                assumed_date=assumed,
                alternative_date=alternative,
                clarification_required=True,
                clarification_reason="next_year_assumption",
                clarification_question=cls._question(assumed, alternative),
            )

        # Rule 7: both interpretations are too close in time to prefer one
        if abs(british_days - american_days) <= CLOSE_CALL_DAYS:
            return DisambiguationResult(
                ambiguity_type=UNRESOLVED_AMBIGUITY,
                assumed_date=assumed,  # British fallback
                alternative_date=alternative,
                clarification_required=True,
                clarification_reason="both_interpretations_equally_plausible",
                clarification_question=cls._question(british, american),
            )

        # British is clearly the better choice
        return DisambiguationResult(
            ambiguity_type=RESOLVED_WITH_CONFIRMATION,
            assumed_date=assumed,
            alternative_date=alternative,
            clarification_required=True,
            clarification_reason="british_default",
            clarification_question=cls._question(assumed, alternative),
        )

    @staticmethod
    def _nearest_future_date(day: int, month: int, anchor: date) -> date | None:
        """Return the nearest future (or same-day) date for (day, month).

        If the date in the current year is already past, try next year.
        Returns None if the (day, month) combination is invalid in any year.
        """
        if not (1 <= month <= 12):
            return None
        for year in (anchor.year, anchor.year + 1):
            try:
                d = date(year, month, day)
            except ValueError:
                continue
            if d >= anchor:
                return d
        return None

    @staticmethod
    def _unresolvable() -> DisambiguationResult:
        return DisambiguationResult(
            ambiguity_type=UNRESOLVED_AMBIGUITY,
            assumed_date=None,
            alternative_date=None,
            clarification_required=True,
            clarification_reason="date_values_unresolvable",
        )

    @staticmethod
    def _fmt(d: date) -> str:
        return f"{d.day} {_MONTHS[d.month]} {d.year}"

    @classmethod
    def _question(cls, assumed: date, alternative: date | None) -> str:
        assumed_str = cls._fmt(assumed)
        if alternative is None:
            return f"Could you confirm you meant {assumed_str}?"
        alt_str = cls._fmt(alternative)
        return (
            f"Could you confirm whether you meant {assumed_str} or {alt_str}? "
            f"I've provisionally checked availability for {assumed_str}."
        )
