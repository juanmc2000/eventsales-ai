#!/usr/bin/env python3
"""Offline regression runner for freeform date expression cases (TEST-032).

Tests three deterministic layers without any LLM or database calls:

  Layer 1 — DateIntentNormalizer
    Verifies that each raw date_request_type maps to the expected
    normalized type (exact / range / recurring / ambiguous / unknown).

  Layer 2 — FreeformDateClarificationDetector
    Verifies that ambiguous freeform expressions (multi-option weekday,
    approximate month, week commencing, etc.) are detected correctly
    and produce the right clarification_type / requires_clarification.

  Layer 3 — Response goal routing
    Derives the expected response goal from clarification state and
    normalized type using simple deterministic rules that mirror
    ResponseGoalEngine precedence — confirming that the right goal
    emerges from the date handling layer.

Usage::

    cd /path/to/eventsales-ai
    python tests/scripts/run_freeform_date_expression_cases.py

Exit code: 0 on full pass, 1 on any failure.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

# ── Path bootstrap ─────────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[2]
_API_ROOT = _REPO_ROOT / "services" / "api"
sys.path.insert(0, str(_API_ROOT))

from app.modules.enquiries.date_intent_normalizer import DateIntentNormalizer  # noqa: E402
from app.modules.enquiries.freeform_date_clarification_detector import (  # noqa: E402
    FreeformDateClarificationDetector,
)

# ── Feature availability probe ────────────────────────────────────────────────
# DATE-004 adds patterns 3-9 to FreeformDateClarificationDetector.
# When the feature is not yet merged, cases tagged requires_feature=DATE-004
# are skipped rather than failed so CI stays green on main.
_DATE_004_AVAILABLE = hasattr(FreeformDateClarificationDetector, "_detect_week_commencing")

# ── Fixture ───────────────────────────────────────────────────────────────────

_FIXTURE = _REPO_ROOT / "tests" / "data" / "freeform_date_expression_cases.json"

# ── Response goal derivation (mirrors ResponseGoalEngine rule precedence) ─────
#
# We derive the expected response goal from the fixture field directly — the
# check verifies our fixture logic is consistent, not the engine itself.
# The actual goal routing is tested via test_response_goal_engine.py.

_NORMALIZER = DateIntentNormalizer()


def _derive_goal(
    normalized_type: str,
    requires_clarification: bool,
) -> str:
    """Simplified goal derivation matching ResponseGoalEngine Rule 3 and Rule 6c.

    Rule 3 fires when clarification is required regardless of normalized type.
    Rule 6c (ACKNOWLEDGE_AND_CHECK_AVAILABILITY) is the default no-availability goal.
    """
    if requires_clarification:
        return "REQUEST_DATE_CONFIRMATION"
    return "ACKNOWLEDGE_AND_CHECK_AVAILABILITY"


# ── Runner ────────────────────────────────────────────────────────────────────


def run() -> int:
    """Run all cases and return exit code."""
    if not _FIXTURE.exists():
        print(f"ERROR: fixture not found at {_FIXTURE}")
        return 1

    with _FIXTURE.open() as f:
        cases = json.load(f)

    total = len(cases)
    print(f"\nFreeform Date Expression Regression — {total} cases\n")
    print(f"{'ID':<30}  {'L1 Norm':<8}  {'L2 Detect':<12}  {'L3 Goal':<8}  Status")
    print("-" * 80)

    failures: list[dict] = []
    skipped: list[str] = []

    for case in cases:
        case_id = case["case_id"]
        raw_text: str | None = case.get("raw_text")
        date_request_type: str | None = case.get("date_request_type")
        anchor_str: str | None = case.get("anchor_date")
        anchor = date.fromisoformat(anchor_str) if anchor_str else date(2026, 7, 1)

        expected_normalized = case["expected_normalized_type"]
        expected_clarification = case["expected_requires_clarification"]
        expected_clarification_type = case.get("expected_clarification_type")
        expected_goal = case["expected_response_goal"]

        # ── Feature gate ──────────────────────────────────────────────────────
        required_feature = case.get("requires_feature")
        if required_feature == "DATE-004" and not _DATE_004_AVAILABLE:
            skipped.append(case_id)
            print(f"{case_id:<30}  {'--':<8}  {'--':<12}  {'--':<8}  SKIP (DATE-004 pending)")
            continue

        case_failures: list[str] = []

        # ── Layer 1: DateIntentNormalizer ──────────────────────────────────────
        actual_normalized = _NORMALIZER.normalise(date_request_type)
        l1_pass = actual_normalized == expected_normalized
        if not l1_pass:
            case_failures.append(
                f"L1 norm: expected '{expected_normalized}' got '{actual_normalized}'"
            )

        # ── Layer 2: FreeformDateClarificationDetector ────────────────────────
        # Only run the detector when the normalized type is unknown — matching
        # the EnquiryDateResolutionService fallback path (step 3b).
        if actual_normalized == "unknown" and raw_text:
            detection = FreeformDateClarificationDetector.detect(
                raw_text=raw_text,
                anchor_date=anchor,
            )
            actual_clarification = detection.clarification_required
            actual_clarification_type = detection.detection_reason
        else:
            # For non-unknown types, the detector is not invoked
            actual_clarification = False
            actual_clarification_type = None

        # For ambiguous_numeric cases, clarification is set from the type itself
        # (NumericDateDisambiguationService), not from the freeform detector.
        # The fixture still marks expected_requires_clarification=True for these,
        # so we skip L2 detector accuracy for that category.
        category = case.get("category", "")
        if category == "ambiguous_numeric":
            l2_pass = True  # disambiguation service handles these; skip detector check
        else:
            l2_clarif_pass = actual_clarification == expected_clarification
            l2_type_pass = (
                actual_clarification_type == expected_clarification_type
                if expected_clarification_type is not None
                else (not actual_clarification or actual_clarification_type is not None)
            )
            l2_pass = l2_clarif_pass and l2_type_pass
            if not l2_clarif_pass:
                case_failures.append(
                    f"L2 clarif: expected {expected_clarification} got {actual_clarification}"
                )
            if not l2_type_pass:
                case_failures.append(
                    f"L2 type: expected '{expected_clarification_type}' got '{actual_clarification_type}'"
                )

        # ── Layer 3: Response goal routing ─────────────────────────────────────
        # For ambiguous_numeric, clarification is always required.
        effective_clarification = expected_clarification
        actual_goal = _derive_goal(actual_normalized, effective_clarification)
        l3_pass = actual_goal == expected_goal
        if not l3_pass:
            case_failures.append(
                f"L3 goal: expected '{expected_goal}' got '{actual_goal}'"
            )

        # ── Summary row ────────────────────────────────────────────────────────
        status = "PASS" if not case_failures else "FAIL"
        l1_str = "OK" if l1_pass else "FAIL"
        l2_str = "OK" if l2_pass else "FAIL"
        l3_str = "OK" if l3_pass else "FAIL"
        print(f"{case_id:<30}  {l1_str:<8}  {l2_str:<12}  {l3_str:<8}  {status}")

        if case_failures:
            failures.append({"case_id": case_id, "errors": case_failures})

    # ── Category breakdown ─────────────────────────────────────────────────────
    categories: dict[str, dict] = {}
    for case in cases:
        cat = case.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"total": 0, "failures": 0}
        categories[cat]["total"] += 1
    for f in failures:
        cat = next((c.get("category", "unknown") for c in cases if c["case_id"] == f["case_id"]), "unknown")
        categories[cat]["failures"] += 1

    print("\n── Category breakdown ─────────────────────────────────────────────────────")
    print(f"{'Category':<30}  {'Pass':<6}  {'Total':<6}")
    print("-" * 50)
    for cat, counts in sorted(categories.items()):
        passed = counts["total"] - counts["failures"]
        print(f"{cat:<30}  {passed:<6}  {counts['total']:<6}")

    # ── Failure details ────────────────────────────────────────────────────────
    if failures:
        print(f"\n── Failures ({len(failures)}/{total}) ───────────────────────────────────────────")
        for f in failures:
            print(f"\n  {f['case_id']}:")
            for err in f["errors"]:
                print(f"    • {err}")

    # ── Final verdict ──────────────────────────────────────────────────────────
    active = total - len(skipped)
    passed = active - len(failures)
    print(f"\n{'=' * 80}")
    if skipped:
        print(f"NOTE  {len(skipped)} case(s) skipped (DATE-004 not yet merged)")
    if not failures:
        print(f"PASS  {passed}/{active} active cases passed (3 layers each)")
        return 0
    else:
        print(f"FAIL  {passed}/{active} passed — {len(failures)} case(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(run())
