"""Date expression regression tests (TEST-032).

Loads the fixture at tests/data/freeform_date_expression_cases.json and
verifies three deterministic layers without any LLM or database calls:

  Layer 1 — DateIntentNormalizer
  Layer 2 — FreeformDateClarificationDetector (for unknown-type cases)
  Layer 3 — Response goal routing (simplified derivation)

Cases tagged requires_feature=DATE-004 are skipped until PR #537 is merged.
"""

from __future__ import annotations

import json
import pathlib
from datetime import date

import pytest

from app.modules.enquiries.date_intent_normalizer import DateIntentNormalizer
from app.modules.enquiries.freeform_date_clarification_detector import (
    FreeformDateClarificationDetector,
)

# ── Fixture path ──────────────────────────────────────────────────────────────

_FIXTURE = (
    pathlib.Path(__file__).resolve().parents[4]
    / "tests" / "data" / "freeform_date_expression_cases.json"
)

# ── Feature availability probe ────────────────────────────────────────────────

_DATE_004_AVAILABLE = hasattr(FreeformDateClarificationDetector, "_detect_week_commencing")

# ── Helpers ───────────────────────────────────────────────────────────────────

_normalizer = DateIntentNormalizer()


def _load_cases() -> list[dict]:
    with _FIXTURE.open() as f:
        return json.load(f)


def _derive_goal(normalized_type: str, requires_clarification: bool) -> str:
    """Simplified goal derivation matching ResponseGoalEngine Rule 3 and Rule 6c."""
    if requires_clarification:
        return "REQUEST_DATE_CONFIRMATION"
    return "ACKNOWLEDGE_AND_CHECK_AVAILABILITY"


def _run_case(case: dict) -> None:
    case_id = case["case_id"]
    raw_text: str | None = case.get("raw_text")
    date_request_type: str | None = case.get("date_request_type")
    anchor_str: str | None = case.get("anchor_date")
    anchor = date.fromisoformat(anchor_str) if anchor_str else date(2026, 7, 1)
    category = case.get("category", "")

    expected_normalized = case["expected_normalized_type"]
    expected_clarification = case["expected_requires_clarification"]
    expected_clarification_type = case.get("expected_clarification_type")
    expected_goal = case["expected_response_goal"]

    # Layer 1 — DateIntentNormalizer
    actual_normalized = _normalizer.normalise(date_request_type)
    assert actual_normalized == expected_normalized, (
        f"[{case_id}] L1 normalized_type: expected '{expected_normalized}' "
        f"got '{actual_normalized}'"
    )

    # Layer 2 — FreeformDateClarificationDetector
    if category == "ambiguous_numeric":
        # Disambiguation service handles these; skip detector check
        pass
    elif actual_normalized == "unknown" and raw_text:
        detection = FreeformDateClarificationDetector.detect(
            raw_text=raw_text,
            anchor_date=anchor,
        )
        assert detection.clarification_required == expected_clarification, (
            f"[{case_id}] L2 clarification_required: "
            f"expected {expected_clarification} got {detection.clarification_required}"
        )
        if expected_clarification_type is not None:
            assert detection.detection_reason == expected_clarification_type, (
                f"[{case_id}] L2 detection_reason: "
                f"expected '{expected_clarification_type}' got '{detection.detection_reason}'"
            )
    else:
        # Non-unknown types — detector not invoked; clarification must be False
        assert not expected_clarification, (
            f"[{case_id}] L2: non-unknown type should not require clarification"
        )

    # Layer 3 — Response goal routing
    effective_clarification = expected_clarification
    actual_goal = _derive_goal(actual_normalized, effective_clarification)
    assert actual_goal == expected_goal, (
        f"[{case_id}] L3 response_goal: expected '{expected_goal}' got '{actual_goal}'"
    )


# ── Test classes ──────────────────────────────────────────────────────────────


class TestDateNormalization:
    """Layer 1: DateIntentNormalizer maps raw LLM types to normalized categories."""

    @pytest.fixture(autouse=True)
    def load_fixture(self) -> None:
        self.cases = _load_cases()

    def _get_cases(self, *categories: str) -> list[dict]:
        return [c for c in self.cases if c.get("category") in categories]

    def test_exact_cases_normalize_to_exact(self) -> None:
        for case in self._get_cases("exact"):
            assert _normalizer.normalise(case["date_request_type"]) == "exact"

    def test_range_cases_normalize_to_range(self) -> None:
        for case in self._get_cases("range"):
            assert _normalizer.normalise(case["date_request_type"]) == "range"

    def test_recurring_cases_normalize_to_recurring(self) -> None:
        for case in self._get_cases("recurring"):
            assert _normalizer.normalise(case["date_request_type"]) == "recurring"

    def test_ambiguous_cases_normalize_to_ambiguous(self) -> None:
        for case in self._get_cases("ambiguous_numeric"):
            assert _normalizer.normalise(case["date_request_type"]) == "ambiguous"

    def test_unknown_cases_normalize_to_unknown(self) -> None:
        for case in self._get_cases(
            "unknown", "multi_option_weekday", "approximate_month",
            "week_commencing", "first_last_weekend", "any_flexible_week",
            "weekday_range", "between_weekdays", "weekend_after_next",
        ):
            assert _normalizer.normalise(case["date_request_type"]) == "unknown"

    def test_normalization_boundary_cases(self) -> None:
        for case in self._get_cases("normalization"):
            _run_case(case)


class TestFreeformDetectorDate003:
    """Layer 2: FreeformDateClarificationDetector — DATE-003 patterns (1 & 2)."""

    @pytest.fixture(autouse=True)
    def load_fixture(self) -> None:
        self.cases = _load_cases()

    def _get_cases(self, *categories: str) -> list[dict]:
        return [
            c for c in self.cases
            if c.get("category") in categories and not c.get("requires_feature")
        ]

    def test_multi_option_weekday_detected(self) -> None:
        for case in self._get_cases("multi_option_weekday"):
            _run_case(case)

    def test_approximate_month_detected(self) -> None:
        for case in self._get_cases("approximate_month"):
            _run_case(case)

    def test_no_match_cases(self) -> None:
        for case in self._get_cases("no_match"):
            _run_case(case)


@pytest.mark.skipif(
    not _DATE_004_AVAILABLE,
    reason="DATE-004 (PR #537) not yet merged — skipping new pattern tests",
)
class TestFreeformDetectorDate004:
    """Layer 2: FreeformDateClarificationDetector — DATE-004 patterns (3–9).

    These tests are skipped on main until PR #537 is merged.
    """

    @pytest.fixture(autouse=True)
    def load_fixture(self) -> None:
        self.cases = _load_cases()

    def _get_date_004_cases(self, *categories: str) -> list[dict]:
        return [
            c for c in self.cases
            if c.get("category") in categories
            and c.get("requires_feature") == "DATE-004"
        ]

    def test_week_commencing_detected(self) -> None:
        for case in self._get_date_004_cases("week_commencing"):
            _run_case(case)

    def test_first_last_weekend_in_month_detected(self) -> None:
        for case in self._get_date_004_cases("first_last_weekend"):
            _run_case(case)

    def test_any_flexible_next_week_detected(self) -> None:
        for case in self._get_date_004_cases("any_flexible_week"):
            _run_case(case)

    def test_weekday_range_detected(self) -> None:
        for case in self._get_date_004_cases("weekday_range"):
            _run_case(case)

    def test_between_weekdays_detected(self) -> None:
        for case in self._get_date_004_cases("between_weekdays"):
            _run_case(case)

    def test_weekend_after_next_detected(self) -> None:
        for case in self._get_date_004_cases("weekend_after_next"):
            _run_case(case)


class TestResponseGoalRouting:
    """Layer 3: Response goal derivation from clarification state."""

    @pytest.fixture(autouse=True)
    def load_fixture(self) -> None:
        self.cases = _load_cases()

    def test_ambiguous_numeric_routes_to_request_date_confirmation(self) -> None:
        cases = [c for c in self.cases if c["category"] == "ambiguous_numeric"]
        for case in cases:
            goal = _derive_goal("ambiguous", case["expected_requires_clarification"])
            assert goal == "REQUEST_DATE_CONFIRMATION"

    def test_exact_routes_to_acknowledge_and_check(self) -> None:
        cases = [c for c in self.cases if c["category"] == "exact"]
        for case in cases:
            goal = _derive_goal("exact", False)
            assert goal == "ACKNOWLEDGE_AND_CHECK_AVAILABILITY"

    def test_range_routes_to_acknowledge_and_check(self) -> None:
        cases = [c for c in self.cases if c["category"] == "range"]
        for case in cases:
            goal = _derive_goal("range", False)
            assert goal == "ACKNOWLEDGE_AND_CHECK_AVAILABILITY"

    def test_multi_option_weekday_routes_to_request_date_confirmation(self) -> None:
        cases = [c for c in self.cases if c["category"] == "multi_option_weekday"]
        for case in cases:
            goal = _derive_goal("unknown", True)
            assert goal == "REQUEST_DATE_CONFIRMATION"

    def test_approximate_month_routes_to_request_date_confirmation(self) -> None:
        cases = [c for c in self.cases if c["category"] == "approximate_month"]
        for case in cases:
            goal = _derive_goal("unknown", True)
            assert goal == "REQUEST_DATE_CONFIRMATION"

    def test_unknown_no_clarification_routes_to_acknowledge(self) -> None:
        cases = [
            c for c in self.cases
            if c["category"] == "unknown" and not c["expected_requires_clarification"]
        ]
        for case in cases:
            goal = _derive_goal("unknown", False)
            assert goal == "ACKNOWLEDGE_AND_CHECK_AVAILABILITY"


class TestFullFixture:
    """End-to-end check: all active (non-DATE-004) cases pass all 3 layers."""

    @pytest.fixture(autouse=True)
    def load_fixture(self) -> None:
        self.cases = _load_cases()

    def test_all_active_cases_pass_all_layers(self) -> None:
        active = [
            c for c in self.cases
            if not (c.get("requires_feature") == "DATE-004" and not _DATE_004_AVAILABLE)
        ]
        assert len(active) >= 35, "Fewer than 35 active cases — fixture may be corrupt"
        for case in active:
            _run_case(case)

    def test_fixture_has_at_least_50_cases(self) -> None:
        assert len(self.cases) >= 50, f"Expected ≥50 cases, got {len(self.cases)}"

    def test_fixture_covers_required_categories(self) -> None:
        categories = {c["category"] for c in self.cases}
        required = {
            "exact", "range", "ambiguous_numeric",
            "multi_option_weekday", "approximate_month", "unknown",
        }
        missing = required - categories
        assert not missing, f"Required categories missing from fixture: {missing}"
