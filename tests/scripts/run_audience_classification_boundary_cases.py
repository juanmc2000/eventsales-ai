#!/usr/bin/env python3
"""Audience-boundary classification runner (TEST-031).

Runs all 40 boundary cases through CustomerTypeResolver deterministically
(no LLM calls) and reports accuracy, confusion matrix, and per-case failures.

Usage (from project root, with venv active):
    python tests/scripts/run_audience_classification_boundary_cases.py

Exit codes:
    0 — all cases passed
    1 — one or more cases failed
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_TESTS_DIR = _SCRIPT_DIR.parent
_REPO_ROOT = _TESTS_DIR.parent
_API_ROOT = _REPO_ROOT / "services" / "api"
_FIXTURE_PATH = _TESTS_DIR / "data" / "audience_classification_boundary_cases.json"

if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from app.modules.enquiries.customer_type_resolver import CustomerTypeResolver
from app.modules.enquiries.sender_domain_classification_service import (
    SenderDomainClassificationService,
)


def _run_case(rec: dict) -> dict:
    sender_email = rec["sender_email"]
    extraction = rec.get("extraction_audience_type", "unknown")
    text = rec.get("enquiry_text", "")
    expected_type = rec["expected_audience_type"]
    expected_rule = rec.get("expected_rule_id", "")

    domain = SenderDomainClassificationService.classify(sender_email)
    result = CustomerTypeResolver.resolve(extraction, domain, text)

    type_match = result.resolved_type == expected_type
    # rule_id check: only evaluate if resolver exposes rule_id (RESP-082)
    rule_match = True
    rule_mismatch_detail = ""
    if expected_rule and hasattr(result, "rule_id") and result.rule_id:
        rule_match = result.rule_id == expected_rule
        if not rule_match:
            rule_mismatch_detail = f"expected rule={expected_rule}, actual rule={result.rule_id}"

    passed = type_match and rule_match
    reason = getattr(result, "reason", None) or (result.evidence[0] if result.evidence else "")

    return {
        "case_id": rec["case_id"],
        "category": rec["category"],
        "passed": passed,
        "expected_type": expected_type,
        "actual_type": result.resolved_type,
        "type_match": type_match,
        "expected_rule": expected_rule,
        "actual_rule": getattr(result, "rule_id", ""),
        "rule_match": rule_match,
        "rule_mismatch_detail": rule_mismatch_detail,
        "confidence": result.confidence,
        "resolution_method": result.resolution_method,
        "reason": reason,
        "description": rec.get("description", ""),
        "notes": rec.get("notes", ""),
    }


def _confusion_matrix(results: list[dict]) -> dict[str, dict[str, int]]:
    types = ["social", "corporate", "agency", "unknown"]
    matrix: dict[str, dict[str, int]] = {t: {t2: 0 for t2 in types} for t in types}
    for r in results:
        exp = r["expected_type"]
        act = r["actual_type"]
        if exp in matrix and act in types:
            matrix[exp][act] += 1
    return matrix


def main() -> None:
    if not _FIXTURE_PATH.exists():
        print(f"ERROR: Fixture not found at {_FIXTURE_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(_FIXTURE_PATH) as f:
        data = json.load(f)

    records = data["records"]
    total = len(records)
    print(f"Audience Classification Boundary Cases (TEST-031)")
    print(f"Fixture: {_FIXTURE_PATH.name}  |  Total: {total}")
    print("-" * 70)

    case_results: list[dict] = []
    for rec in records:
        cr = _run_case(rec)
        status = "PASS" if cr["passed"] else "FAIL"
        print(f"  {cr['case_id']:<15} [{cr['expected_type']:>10} → {cr['actual_type']:>10}]  {status}")
        if not cr["passed"]:
            if not cr["type_match"]:
                print(f"    TYPE MISMATCH: expected={cr['expected_type']} actual={cr['actual_type']}")
            if not cr["rule_match"] and cr["rule_mismatch_detail"]:
                print(f"    RULE MISMATCH: {cr['rule_mismatch_detail']}")
            print(f"    reason: {cr['reason']}")
        case_results.append(cr)

    passed = [r for r in case_results if r["passed"]]
    failed = [r for r in case_results if not r["passed"]]
    type_failed = [r for r in case_results if not r["type_match"]]

    sep = "=" * 70
    print(f"\n{sep}")
    print(f"RESULTS — {len(passed)}/{total} passed")
    print(sep)

    # Per-category breakdown
    by_category: dict[str, list[dict]] = {}
    for r in case_results:
        cat = r["category"]
        by_category.setdefault(cat, []).append(r)
    print(f"\nPer-category breakdown:")
    for cat, cases in sorted(by_category.items()):
        n_pass = sum(1 for c in cases if c["passed"])
        print(f"  {cat:<40}: {n_pass}/{len(cases)}")

    # Per-audience-type breakdown
    by_expected: dict[str, list[dict]] = {}
    for r in case_results:
        by_expected.setdefault(r["expected_type"], []).append(r)
    print(f"\nPer-expected-audience breakdown:")
    for aud_type in ("social", "corporate", "agency", "unknown"):
        cases = by_expected.get(aud_type, [])
        if not cases:
            continue
        n_pass = sum(1 for c in cases if c["passed"])
        print(f"  {aud_type:<12}: {n_pass}/{len(cases)}")

    # Confusion matrix
    matrix = _confusion_matrix(case_results)
    print(f"\nConfusion matrix (expected → actual):")
    types = ["social", "corporate", "agency", "unknown"]
    header = f"  {'expected':>10}  " + "  ".join(f"{t:>10}" for t in types)
    print(header)
    for exp_type in types:
        row = matrix.get(exp_type, {t: 0 for t in types})
        if sum(row.values()) == 0:
            continue
        row_str = "  ".join(f"{row.get(t, 0):>10}" for t in types)
        print(f"  {exp_type:>10}  {row_str}")

    # Failure table
    if type_failed:
        print(f"\nType misclassification failures ({len(type_failed)}):")
        for r in type_failed:
            print(f"  {r['case_id']:<15} expected={r['expected_type']:<12} "
                  f"actual={r['actual_type']:<12} method={r['resolution_method']}")
            print(f"    {r['description']}")

    # Overall verdict
    print(f"\n{'PASSED' if not failed else 'FAILED'}: {len(passed)}/{total} cases correct.")
    if failed:
        print(f"  {len(type_failed)} type misclassification(s), "
              f"{sum(1 for r in failed if not r['rule_match'])} rule mismatch(es)")

    print(sep)
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
