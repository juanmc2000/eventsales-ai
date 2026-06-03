"""Date Intent Normalizer (ENQ-002).

Reduces the high-granularity date_request_type classification produced by the
LLM into a simplified 5-category model used by downstream deterministic
processing.

Simplified categories:
- exact      — a single, specific date
- range      — a window of possible dates (date_range, multiple_choice, month_flexible)
- recurring  — a repeating pattern over a period (recurring_window, weekday_range, mixed)
- ambiguous  — numerically ambiguous (e.g. 03/04 could be March 4 or April 3)
- unknown    — no usable date information

No LLM calls are made.  The mapping is deterministic and auditable.
"""

from __future__ import annotations

# ── Normalized type constants ──────────────────────────────────────────────────

NORMALIZED_EXACT = "exact"
NORMALIZED_RANGE = "range"
NORMALIZED_RECURRING = "recurring"
NORMALIZED_AMBIGUOUS = "ambiguous"
NORMALIZED_UNKNOWN = "unknown"

ALL_NORMALIZED_TYPES = {
    NORMALIZED_EXACT,
    NORMALIZED_RANGE,
    NORMALIZED_RECURRING,
    NORMALIZED_AMBIGUOUS,
    NORMALIZED_UNKNOWN,
}

# ── Legacy → normalized mapping ───────────────────────────────────────────────
# Maps raw LLM date_request_type values to the simplified normalized type.
# Any type not in this dict falls through to NORMALIZED_UNKNOWN.

_MAPPING: dict[str, str] = {
    # Exact
    "exact": NORMALIZED_EXACT,
    # Range subtypes
    "date_range": NORMALIZED_RANGE,
    "multiple_choice": NORMALIZED_RANGE,
    "month_flexible": NORMALIZED_RANGE,
    # Recurring subtypes
    "recurring_window": NORMALIZED_RECURRING,
    "weekday_range_over_relative_period": NORMALIZED_RECURRING,
    "mixed_relative_dates": NORMALIZED_RECURRING,
    "relative_period": NORMALIZED_RECURRING,  # LLM off-schema fallback (db88876)
    # Ambiguous
    "ambiguous_numeric_date": NORMALIZED_AMBIGUOUS,
    "ambiguous": NORMALIZED_AMBIGUOUS,
    # Unknown
    "unknown": NORMALIZED_UNKNOWN,
}


# ── Normalizer ─────────────────────────────────────────────────────────────────


class DateIntentNormalizer:
    """Normalise a raw LLM date_request_type to a simplified category.

    Usage::

        normalizer = DateIntentNormalizer()
        normalized = normalizer.normalise("month_flexible")
        # → "range"
    """

    def normalise(self, raw_type: str | None) -> str:
        """Return the normalized date intent category.

        Returns ``"unknown"`` for None, empty, or unrecognised input.

        Args:
            raw_type: The date_request_type string as returned by the LLM.

        Returns:
            A normalized type string from ``ALL_NORMALIZED_TYPES``.
        """
        if not raw_type or not raw_type.strip():
            return NORMALIZED_UNKNOWN

        return _MAPPING.get(raw_type.strip().lower(), NORMALIZED_UNKNOWN)
