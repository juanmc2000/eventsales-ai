"""First Response Safety Regression Runner (TEST-011, updated RESP-032).

Standalone script that evaluates all 25 first-response safety scenarios
using DraftComplianceValidator, ResponseContextIntegrityGate, and
AutoSendReadinessGate. No pytest required — no LLM calls made.

RESP-032: Production-equivalent routing
- RESPOND_UNAVAILABLE scenarios use the deterministic unavailable builder
  (FirstResponseCopyLibrary) rather than the LLM-generated draft_text.
  This matches production behaviour where RESPOND_UNAVAILABLE bypasses LLM.
- Each result includes generation_path: "llm" | "deterministic"
- Report separates CONFIRM_AVAILABLE pass rate, RESPOND_UNAVAILABLE
  deterministic pass rate, validator failure rate, and auto-send rate.

Run from the services/api/ directory:

    python tests/scripts/run_first_response_safety_regression.py

Outputs:
  - Per-scenario pass/fail with generation_path, violation/blocker detail
  - Compliance pass rate
  - Integrity pass rate
  - Auto-send eligibility rate
  - Per-goal summary (CONFIRM_AVAILABLE, RESPOND_UNAVAILABLE, others)
  - Violation breakdown by category
  - Auto-send block reason breakdown
  - Ready-to-send rate

Exit code 1 if any expected outcomes are not matched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from services/api/
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.modules.ai.draft_compliance_validator import DraftComplianceValidator, ValidationContext
from app.modules.ai.auto_send_readiness_gate import AutoSendReadinessGate
from app.modules.enquiries.response_context_integrity_gate import ResponseContextIntegrityGate

# ── Paths ───────────────────────────────────────────────────────────────────────

_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "first_response_safety_cases.json"

# ── Deterministic unavailable draft text constants ────────────────────────────

_DETERMINISTIC_GOALS = frozenset({"RESPOND_UNAVAILABLE"})


def _get_generation_path(response_goal: str) -> str:
    """Return 'deterministic' for goals that bypass the LLM, 'llm' for all others."""
    return "deterministic" if response_goal in _DETERMINISTIC_GOALS else "llm"


def _build_deterministic_unavailable_text(scenario: dict) -> str:
    """RESP-032: Build deterministic unavailable draft using FirstResponseCopyLibrary.

    Matches what DraftGenerationService._generate_deterministic_unavailable_draft()
    produces in production — approved copy blocks only, no LLM.
    """
    from app.modules.ai.first_response_copy_library import FirstResponseCopyLibrary

    ctx = scenario.get("context", {})
    meal_period = ctx.get("meal_period") or "dinner"
    event_date = ctx.get("event_date") or "the requested date"
    guest_name = ctx.get("guest_first_name") or "there"
    persona_name = ctx.get("persona_name") or "Events Team"

    opening = FirstResponseCopyLibrary.render(
        "availability_unavailable",
        {"meal_period": meal_period, "event_date": event_date},
    )
    signoff = FirstResponseCopyLibrary.render(
        "signoff",
        {"persona_name": persona_name},
    )
    return f"Dear {guest_name},\n\n{opening}\n\n{signoff}"


def _get_draft_text(scenario: dict) -> str:
    """RESP-032: Return the draft text to evaluate.

    For RESPOND_UNAVAILABLE, return the production-equivalent deterministic text.
    For all other goals, use the fixture draft_text (LLM-generated test draft).
    """
    goal = scenario.get("response_goal", "")
    if goal == "RESPOND_UNAVAILABLE":
        return _build_deterministic_unavailable_text(scenario)
    return scenario.get("draft_text", "")


# ── Helpers ─────────────────────────────────────────────────────────────────────


def _context_from_scenario(scenario: dict) -> ValidationContext:
    ctx = scenario.get("context", {})
    return ValidationContext(
        availability_contract=scenario.get("availability_contract", "NOT_CHECKED"),
        clarification_questions=ctx.get("clarification_questions", []),
        confirmed_minimum_spend=ctx.get("confirmed_minimum_spend"),
        party_size=ctx.get("party_size"),
        prohibited_times=ctx.get("prohibited_times", []),
        response_goal=scenario.get("response_goal", ""),
        allow_menu_discussion=ctx.get("allow_menu_discussion", False),
        allow_special_touches=ctx.get("allow_special_touches", False),
        allow_call_scheduling=ctx.get("allow_call_scheduling", False),
    )


def _integrity_from_scenario(scenario: dict):
    return ResponseContextIntegrityGate.check(
        context_restaurant_name=scenario.get("context_restaurant_name", ""),
        context_room_name=scenario.get("context_room_name"),
        availability_restaurant_name=scenario.get("availability_restaurant_name"),
        availability_room_name=scenario.get("availability_room_name"),
    )


def _categorise_violation(violation: str) -> str:
    v = violation.lower()
    if "contract" in v and "available" in v:
        return "hallucinated_availability"
    if "alternative" in v:
        return "alternative_dates"
    if "suitability" in v or "perfect for" in v or "ideal for" in v:
        return "room_suitability_unavailable"
    if "spend" in v or "mandatory" in v:
        return "spend_soft_language"
    if "link" in v or "url" in v or "placeholder" in v:
        return "fake_url"
    if "time" in v and "confirmed" in v:
        return "unconfirmed_time"
    if "hosting" in v:
        return "hosting_language"
    if "within" in v or "hours" in v or "commitment" in v:
        return "invented_sla"
    if "question" in v:
        return "invented_questions"
    if "menu" in v or "dietary" in v or "special touch" in v:
        return "forbidden_topics"
    return "other"


def _categorise_blocker(blocker: str) -> str:
    b = blocker.lower()
    if "compliance" in b:
        return "compliance_failure"
    if "auto-send allowed set" in b or ("goal" in b and "not" in b):
        return "goal_not_auto_sendable"
    if "date" in b or "resolved" in b:
        return "date_status"
    if "escalate" in b or "human" in b:
        return "escalation"
    if "integrity" in b:
        return "integrity_failure"
    return "other"


# ── Runner ──────────────────────────────────────────────────────────────────────


def run() -> None:
    if not _FIXTURE_PATH.exists():
        print(f"[ERROR] Fixture not found: {_FIXTURE_PATH}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(_FIXTURE_PATH.read_text())
    scenarios = data["scenarios"]
    availability_records = data.get("availability_records", [])
    total = len(scenarios)

    print(f"\n{'=' * 68}")
    print("FIRST RESPONSE SAFETY REGRESSION RUNNER — TEST-011 / RESP-032")
    print(f"{'=' * 68}")
    print(f"Fixture:  {_FIXTURE_PATH.name}")
    print(f"Records:  {len(availability_records)} availability records  |  {total} scenarios\n")

    compliance_passed_count = 0
    integrity_passed_count = 0
    auto_send_allowed_count = 0
    violation_category_counts: dict[str, int] = {}
    block_reason_counts: dict[str, int] = {}
    compliance_regressions: list[str] = []
    integrity_regressions: list[str] = []
    auto_send_regressions: list[str] = []

    # RESP-032: per-goal tracking
    per_goal_totals: dict[str, int] = {}
    per_goal_compliance_passed: dict[str, int] = {}
    per_goal_auto_send_allowed: dict[str, int] = {}
    per_goal_deterministic: dict[str, int] = {}

    for sc in scenarios:
        sc_id = sc["id"]
        expected = sc["expected"]
        category = sc.get("category", "")
        response_goal = sc.get("response_goal", "")
        generation_path = _get_generation_path(response_goal)

        # RESP-032: use production-equivalent draft text
        draft_text = _get_draft_text(sc)

        ctx = _context_from_scenario(sc)
        compliance = DraftComplianceValidator.validate(draft_text, ctx)
        integrity = _integrity_from_scenario(sc)
        gate = AutoSendReadinessGate.evaluate(
            response_goal=response_goal,
            draft_compliance_result=compliance,
            date_status=sc.get("date_status", "resolved"),
            integrity_result=integrity,
        )

        # Counts
        if compliance.passed:
            compliance_passed_count += 1
        if integrity.passed:
            integrity_passed_count += 1
        if gate.auto_send_allowed:
            auto_send_allowed_count += 1

        # RESP-032: per-goal aggregation
        per_goal_totals[response_goal] = per_goal_totals.get(response_goal, 0) + 1
        if compliance.passed:
            per_goal_compliance_passed[response_goal] = per_goal_compliance_passed.get(response_goal, 0) + 1
        if gate.auto_send_allowed:
            per_goal_auto_send_allowed[response_goal] = per_goal_auto_send_allowed.get(response_goal, 0) + 1
        if generation_path == "deterministic":
            per_goal_deterministic[response_goal] = per_goal_deterministic.get(response_goal, 0) + 1

        for v in compliance.violations:
            cat = _categorise_violation(v)
            violation_category_counts[cat] = violation_category_counts.get(cat, 0) + 1

        for b in gate.auto_send_blockers:
            reason = _categorise_blocker(b)
            block_reason_counts[reason] = block_reason_counts.get(reason, 0) + 1

        # Expected vs actual
        exp_compliance = expected.get("compliance_passed")
        exp_integrity = expected.get("integrity_passed", True)
        exp_auto_send = expected.get("ready_to_send_allowed")

        compliance_ok = (exp_compliance is None) or (compliance.passed == exp_compliance)
        integrity_ok = integrity.passed == exp_integrity
        auto_send_ok = (exp_auto_send is None) or (gate.auto_send_allowed == exp_auto_send)

        all_ok = compliance_ok and integrity_ok and auto_send_ok
        status_icon = "\u2713" if all_ok else "\u2717"

        c_status = "PASS" if compliance.passed else "FAIL"
        i_status = "PASS" if integrity.passed else "FAIL"
        g_status = "ALLOW" if gate.auto_send_allowed else "BLOCK"
        path_label = f"[{generation_path}]"

        print(f"  {status_icon} {sc_id:<8}  {path_label:<15}  {category:<28}  C:{c_status}  I:{i_status}  G:{g_status}")

        if not compliance_ok:
            exp_txt = "pass" if exp_compliance else "fail"
            got_txt = "pass" if compliance.passed else "fail"
            print(f"           \u26a0 compliance: expected {exp_txt}, got {got_txt}")
            for v in compliance.violations:
                print(f"               violation: {v[:90]}")
            if exp_compliance and not compliance.passed:
                compliance_regressions.append(sc_id)
            elif not exp_compliance and compliance.passed:
                compliance_regressions.append(sc_id)

        if not integrity_ok:
            exp_txt = "pass" if exp_integrity else "fail"
            got_txt = "pass" if integrity.passed else "fail"
            print(f"           \u26a0 integrity: expected {exp_txt}, got {got_txt}")
            for v in integrity.violations:
                print(f"               violation: {v[:90]}")
            integrity_regressions.append(sc_id)

        if not auto_send_ok:
            exp_txt = "allowed" if exp_auto_send else "blocked"
            got_txt = "allowed" if gate.auto_send_allowed else "blocked"
            print(f"           \u26a0 auto-send: expected {exp_txt}, got {got_txt}")
            for b in gate.auto_send_blockers:
                print(f"               blocker: {b[:90]}")
            auto_send_regressions.append(sc_id)

    # ── Aggregate ────────────────────────────────────────────────────────────
    compliance_rate = compliance_passed_count / total * 100
    integrity_rate = integrity_passed_count / total * 100
    auto_send_rate = auto_send_allowed_count / total * 100

    print(f"\n{'─' * 68}")
    print("AGGREGATE RESULTS")
    print(f"{'─' * 68}")
    print(f"  Total scenarios:        {total}")
    print(f"  Compliance pass rate:   {compliance_rate:.1f}%  ({compliance_passed_count}/{total})")
    print(f"  Integrity pass rate:    {integrity_rate:.1f}%  ({integrity_passed_count}/{total})")
    print(f"  Auto-send allowed rate: {auto_send_rate:.1f}%  ({auto_send_allowed_count}/{total})")
    print(f"  Ready-to-send rate:     {auto_send_rate:.1f}%  (same as auto-send allowed)")

    # ── RESP-032: Per-goal summary ────────────────────────────────────────────
    print(f"\n{'─' * 68}")
    print("PER-GOAL SUMMARY  (RESP-032)")
    print(f"{'─' * 68}")
    for goal in sorted(per_goal_totals.keys()):
        n = per_goal_totals[goal]
        c_pass = per_goal_compliance_passed.get(goal, 0)
        g_allow = per_goal_auto_send_allowed.get(goal, 0)
        det = per_goal_deterministic.get(goal, 0)
        path_note = f" [deterministic x{det}]" if det > 0 else " [llm]"
        print(
            f"  {goal:<40}  n={n}  "
            f"compliance={c_pass}/{n}  "
            f"auto-send={g_allow}/{n}"
            f"{path_note}"
        )

    if violation_category_counts:
        print(f"\n  Compliance violation breakdown:")
        for cat, count in sorted(violation_category_counts.items(), key=lambda x: -x[1]):
            bar = "\u2588" * count
            print(f"    {cat:<32}  {count:2d}  {bar}")

    if block_reason_counts:
        print(f"\n  Auto-send block reason breakdown:")
        for reason, count in sorted(block_reason_counts.items(), key=lambda x: -x[1]):
            bar = "\u2588" * count
            print(f"    {reason:<32}  {count:2d}  {bar}")

    total_regressions = len(compliance_regressions) + len(integrity_regressions) + len(auto_send_regressions)
    if total_regressions:
        print(f"\n  \u26a0  REGRESSIONS DETECTED ({total_regressions}):")
        if compliance_regressions:
            print(f"    Compliance mismatches:  {compliance_regressions}")
        if integrity_regressions:
            print(f"    Integrity mismatches:   {integrity_regressions}")
        if auto_send_regressions:
            print(f"    Auto-send mismatches:   {auto_send_regressions}")
    else:
        print(f"\n  \u2713 All expected outcomes matched.")

    print(f"{'=' * 68}\n")

    if total_regressions:
        sys.exit(1)


if __name__ == "__main__":
    run()
