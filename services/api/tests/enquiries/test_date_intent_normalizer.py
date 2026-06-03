"""Tests for DateIntentNormalizer (ENQ-002).

All tests are unit-level — no DB or LLM required.
"""

from __future__ import annotations

import pytest

from app.modules.enquiries.date_intent_normalizer import (
    ALL_NORMALIZED_TYPES,
    NORMALIZED_AMBIGUOUS,
    NORMALIZED_EXACT,
    NORMALIZED_RANGE,
    NORMALIZED_RECURRING,
    NORMALIZED_UNKNOWN,
    DateIntentNormalizer,
)


@pytest.fixture()
def normalizer() -> DateIntentNormalizer:
    return DateIntentNormalizer()


class TestNormalise:
    def test_none_returns_unknown(self, normalizer):
        assert normalizer.normalise(None) == NORMALIZED_UNKNOWN

    def test_empty_string_returns_unknown(self, normalizer):
        assert normalizer.normalise("") == NORMALIZED_UNKNOWN

    def test_whitespace_only_returns_unknown(self, normalizer):
        assert normalizer.normalise("   ") == NORMALIZED_UNKNOWN

    def test_unrecognised_returns_unknown(self, normalizer):
        assert normalizer.normalise("some_future_type") == NORMALIZED_UNKNOWN

    # exact
    def test_exact(self, normalizer):
        assert normalizer.normalise("exact") == NORMALIZED_EXACT

    # range subtypes
    @pytest.mark.parametrize("raw", [
        "date_range",
        "multiple_choice",
        "month_flexible",
    ])
    def test_range_subtypes(self, normalizer, raw):
        assert normalizer.normalise(raw) == NORMALIZED_RANGE

    # recurring subtypes
    @pytest.mark.parametrize("raw", [
        "recurring_window",
        "weekday_range_over_relative_period",
        "mixed_relative_dates",
        "relative_period",
    ])
    def test_recurring_subtypes(self, normalizer, raw):
        assert normalizer.normalise(raw) == NORMALIZED_RECURRING

    # ambiguous subtypes
    @pytest.mark.parametrize("raw", [
        "ambiguous_numeric_date",
        "ambiguous",
    ])
    def test_ambiguous_subtypes(self, normalizer, raw):
        assert normalizer.normalise(raw) == NORMALIZED_AMBIGUOUS

    # unknown
    def test_unknown(self, normalizer):
        assert normalizer.normalise("unknown") == NORMALIZED_UNKNOWN

    def test_result_always_in_normalized_set(self, normalizer):
        """Every normalise() result must be a known normalized type."""
        samples = [
            None, "", "exact", "date_range", "multiple_choice",
            "month_flexible", "recurring_window", "weekday_range_over_relative_period",
            "mixed_relative_dates", "relative_period", "ambiguous_numeric_date",
            "ambiguous", "unknown", "something_unknown_xyz",
        ]
        for raw in samples:
            result = normalizer.normalise(raw)
            assert result in ALL_NORMALIZED_TYPES, (
                f"normalise({raw!r}) returned {result!r} which is not in ALL_NORMALIZED_TYPES"
            )

    def test_case_insensitive(self, normalizer):
        """Normalisation is case-insensitive."""
        assert normalizer.normalise("EXACT") == NORMALIZED_EXACT
        assert normalizer.normalise("Date_Range") == NORMALIZED_RANGE

    def test_strip_whitespace(self, normalizer):
        """Leading/trailing whitespace is stripped."""
        assert normalizer.normalise("  exact  ") == NORMALIZED_EXACT
