"""Draft Quality Regression Runner (RESP-015).

Standalone script that evaluates draft quality cases from the fixture file
using DraftComplianceValidator and AutoSendReadinessGate.

Not a pytest test — run directly from the API service root:

    python tests/scripts/run_draft_quality_regression.py

Outputs:
- Pass/fail by record
- Violation summary per record
- Aggregate: compliance pass rate, auto-send rate
- Top failure categories

The six-record availability fixture is included separately.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from the services/api/ directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.modules.ai.draft_compliance_validator import (
    DraftComplianceValidator,
    ValidationContext,
)

try:
    from app.modules.ai.auto_send_readiness_gate import AutoSendReadinessGate
    _GATE_AVAILABLE = True
except ImportError:
    AutoSendReadinessGate = None  # type: ignore[assignment,misc]
    _GATE_AVAILABLE = False

# ── Paths ──────────────────────────────────────────────────────────────────────

_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "draft_quality_cases.json"


# ── Helpers ────────────────────────────────────────────────────────────────────


def _context_from_scenario(scenario: dict) -> ValidationContext:
    ctx_data = scenario.get("context", {})
    return ValidationContext(
        availability_contract=scenario.get("availability_contract", "NOT_CHECKED"),
        clarification_questions=ctx_data.get("clarification_questions", []),
        confirmed_minimum_spend=ctx_data.get("confirmed_minimum_spend"),
        prohibited_times=ctx_data.get("prohibited_times", []),
        response_goal=scenario.get("response_goal", ""),
    )


def _categorise_violation(violation: str) -> str:
    v = violation.lower()
    if "available" in v and "contract" in v:
        return "availability_overclaim"
    if "alternative" in v:
        return "alternative_dates"
    if "spend" in v or "mandatory" in v:
        return "spend_soft_language"
    if "sla" in v or "commitment" in v:
        return "invented_sla"
    if "question" in v:
        return "invented_questions"
    if "hosting" in v:
        return "hosting_language"
    if "link" in v or "url" in v or "placeholder" in v:
        return "fake_url"
    if "time" in v and "confirmed" in v:
        return "unconfirmed_time"
    if "menu" in v or "special" in v or "call" in v:
        return "forbidden_topics"
    return "other"


# ── Runner ─────────────────────────────────────────────────────────────────────


def run() -> None:
    if not _FIXTURE_PATH.exists():
        print(f"[ERROR] Fixture not found: {_FIXTURE_PATH}")
        sys.exit(1)

    data = json.loads(_FIXTURE_PATH.read_text())
    scenarios = data["scenarios"]
    total = len(scenarios)

    print(f"\n{'=' * 65}")
    print("DRAFT QUALITY REGRESSION RUNNER — RESP-015")
    print(f"{'=' * 65}")
    print(f"Fixture: {_FIXTURE_PATH.name}  |  Scenarios: {total}\n")

    compliance_passed_count = 0
    auto_send_allowed_count = 0
    violation_category_counts: dict[str, int] = {}
    unexpected_pass: list[str] = []
    unexpected_fail: list[str] = []

    for sc in scenarios:
        sc_id = sc["id"]
        expected = sc["expected"]
        ctx = _context_from_scenario(sc)
        compliance = DraftComplianceValidator.validate(sc["draft_text"], ctx)
        gate = None
        if _GATE_AVAILABLE:
            gate = AutoSendReadinessGate.evaluate(
                response_goal=sc.get("response_goal", ""),
                draft_compliance_result=compliance,
                date_status=sc.get("date_status", "resolved"),
            )

        # Track counts
        if compliance.passed:
            compliance_passed_count += 1
        if gate and gate.auto_send_allowed:
            auto_send_allowed_count += 1

        # Categorise violations
        for v in compliance.violations:
            cat = _categorise_violation(v)
            violation_category_counts[cat] = violation_category_counts.get(cat, 0) + 1

        # Check against expectations
        exp_compliance = expected.get("compliance_passed")
        exp_auto_send = expected.get("ready_to_send_allowed")

        compliance_match = (exp_compliance is None) or (compliance.passed == exp_compliance)
        auto_send_match = (exp_auto_send is None) or (
            gate is not None and gate.auto_send_allowed == exp_auto_send
        ) or (gate is None and exp_auto_send is None)

        status_parts = []
        if compliance.passed:
            status_parts.append("COMPLIANCE:PASS")
        else:
            status_parts.append("COMPLIANCE:FAIL")
        if gate.auto_send_allowed:
            status_parts.append("GATE:ALLOWED")
        else:
            status_parts.append("GATE:BLOCKED")

        ok = "✓" if (compliance_match and auto_send_match) else "✗"
        print(f"  {ok} {sc_id:<8}  {sc.get('category', ''):<20}  {' | '.join(status_parts)}")
        if not compliance_match:
            exp_txt = "pass" if exp_compliance else "fail"
            got_txt = "pass" if compliance.passed else "fail"
            print(f"           compliance expected {exp_txt}, got {got_txt}")
            if compliance.violations:
                for v in compliance.violations:
                    print(f"             violation: {v}")
            if exp_compliance and not compliance.passed:
                unexpected_fail.append(sc_id)
            elif not exp_compliance and compliance.passed:
                unexpected_pass.append(sc_id)
        if not auto_send_match and gate is not None:
            exp_txt = "allowed" if exp_auto_send else "blocked"
            got_txt = "allowed" if gate.auto_send_allowed else "blocked"
            print(f"           auto-send expected {exp_txt}, got {got_txt}")
            if gate.auto_send_blockers:
                for b in gate.auto_send_blockers:
                    print(f"             blocker: {b}")

    # ── Summary ──────────────────────────────────────────────────────────────
    compliance_rate = compliance_passed_count / total * 100
    auto_send_rate = auto_send_allowed_count / total * 100

    print(f"\n{'─' * 65}")
    print("AGGREGATE RESULTS")
    print(f"{'─' * 65}")
    print(f"  Total scenarios:         {total}")
    print(f"  Compliance pass rate:    {compliance_rate:.1f}%  ({compliance_passed_count}/{total})")
    print(f"  Auto-send allowed rate:  {auto_send_rate:.1f}%  ({auto_send_allowed_count}/{total})")

    if violation_category_counts:
        print(f"\n  Top violation categories:")
        for cat, count in sorted(violation_category_counts.items(), key=lambda x: -x[1]):
            bar = "█" * count
            print(f"    {cat:<28}  {count:2d}  {bar}")

    regressions = len(unexpected_pass) + len(unexpected_fail)
    if regressions:
        print(f"\n  ⚠  REGRESSIONS DETECTED ({regressions}):")
        if unexpected_pass:
            print(f"    Unexpected pass (expected fail): {unexpected_pass}")
        if unexpected_fail:
            print(f"    Unexpected fail (expected pass): {unexpected_fail}")
    else:
        print(f"\n  ✓ All expected outcomes matched.")

    print(f"{'=' * 65}\n")

    if regressions:
        sys.exit(1)


if __name__ == "__main__":
    run()
