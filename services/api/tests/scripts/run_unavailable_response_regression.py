"""Unavailable Response Regression Runner (TEST-020).

Standalone script that evaluates all RESPOND_UNAVAILABLE scenarios from the
unavailable response regression fixture using DraftComplianceValidator,
ResponseContextIntegrityGate, and AutoSendReadinessGate. No pytest required —
no LLM calls made.

Production routing:
- All RESPOND_UNAVAILABLE scenarios use FirstResponseCopyLibrary deterministic
  copy blocks (RESP-023), matching production DraftGenerationService behaviour.
- The fixture draft_text field documents the expected response shape but is not
  used during validation.

Run from the services/api/ directory:

    python tests/scripts/run_unavailable_response_regression.py

Outputs:
  - Per-scenario pass/fail with generation path, compliance, integrity, gate status
  - Alternative date analysis (past rejected / future allowed / capacity unsuitable)
  - Compliance pass rate (expected: 100% — deterministic text)
  - Auto-send blocked rate (expected: 100% — goal not auto-sendable)
  - Category breakdown
  - Regression detection (exit code 1 on any mismatch)

Exit code 0 if all expected outcomes matched, exit code 1 otherwise.
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

# ── Paths ────────────────────────────────────────────────────────────────────────

_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "unavailable_response_regression.json"


# ── Deterministic draft builder ──────────────────────────────────────────────────


def _build_deterministic_unavailable_text(scenario: dict) -> str:
    """Build production-equivalent deterministic unavailable draft (RESP-023)."""
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
    signoff = FirstResponseCopyLibrary.render("signoff", {"persona_name": persona_name})
    return f"Dear {guest_name},\n\n{opening}\n\n{signoff}"


# ── Context builders ─────────────────────────────────────────────────────────────


def _context_from_scenario(scenario: dict) -> ValidationContext:
    ctx = scenario.get("context", {})
    return ValidationContext(
        availability_contract=scenario.get("availability_contract", "NOT_CHECKED"),
        clarification_questions=ctx.get("clarification_questions", []),
        confirmed_minimum_spend=ctx.get("confirmed_minimum_spend"),
        party_size=ctx.get("party_size"),
        prohibited_times=ctx.get("prohibited_times", []),
        response_goal=scenario.get("response_goal", ""),
        alternatives_allowed=ctx.get("alternatives_allowed", False),
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


# ── Violation / blocker categorisation ──────────────────────────────────────────


def _categorise_violation(violation: str) -> str:
    v = violation.lower()
    if "contract" in v and "available" in v:
        return "hallucinated_availability"
    if "alternative" in v:
        return "alternative_dates"
    if "suitability" in v or "perfect for" in v or "ideal for" in v:
        return "room_suitability"
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


# ── Runner ───────────────────────────────────────────────────────────────────────


def run() -> None:
    if not _FIXTURE_PATH.exists():
        print(f"[ERROR] Fixture not found: {_FIXTURE_PATH}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(_FIXTURE_PATH.read_text())
    scenarios = data["scenarios"]
    availability_records = data.get("availability_records", [])
    total = len(scenarios)
    meta = data.get("meta", {})

    print(f"\n{'=' * 72}")
    print("UNAVAILABLE RESPONSE REGRESSION RUNNER — TEST-020")
    print(f"{'=' * 72}")
    print(f"Fixture:      {_FIXTURE_PATH.name}")
    print(f"Description:  {meta.get('description', '')[:70]}")
    print(f"Anchor date:  {meta.get('anchor_date', 'unknown')}")
    print(
        f"Records:      {len(availability_records)} availability records  |  {total} scenarios\n"
    )

    compliance_passed_count = 0
    integrity_passed_count = 0
    auto_send_blocked_count = 0
    violation_category_counts: dict[str, int] = {}
    block_reason_counts: dict[str, int] = {}
    compliance_regressions: list[str] = []
    integrity_regressions: list[str] = []
    auto_send_regressions: list[str] = []

    # Category tracking
    category_totals: dict[str, int] = {}
    category_compliance_passed: dict[str, int] = {}

    # Alternative date analysis
    past_alt_rejected_count = 0
    future_alt_offered_count = 0
    capacity_unsuitable_count = 0

    for sc in scenarios:
        sc_id = sc["id"]
        expected = sc["expected"]
        category = sc.get("category", "uncategorised")
        response_goal = sc.get("response_goal", "")

        # Always use deterministic text for RESPOND_UNAVAILABLE
        draft_text = _build_deterministic_unavailable_text(sc)

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
        if not gate.auto_send_allowed:
            auto_send_blocked_count += 1

        # Category tracking
        category_totals[category] = category_totals.get(category, 0) + 1
        if compliance.passed:
            category_compliance_passed[category] = (
                category_compliance_passed.get(category, 0) + 1
            )

        # Alternative date analysis
        ctx_data = sc.get("context", {})
        alt_rejection = ctx_data.get("alt_rejection_reason", "")
        if alt_rejection == "all_alternatives_in_past":
            past_alt_rejected_count += 1
        elif alt_rejection == "capacity_unsuitable":
            capacity_unsuitable_count += 1
        elif ctx_data.get("alternatives_allowed") and ctx_data.get("alternative_dates"):
            future_alt_offered_count += 1

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
        g_status = "BLOCK" if not gate.auto_send_allowed else "ALLOW"
        alts_note = ""
        if ctx_data.get("alternatives_allowed"):
            n_alts = len(ctx_data.get("alternative_dates", []))
            alts_note = f" [alts:{n_alts}]"
        elif alt_rejection:
            alts_note = f" [{alt_rejection[:12]}]"

        print(
            f"  {status_icon} {sc_id:<8}  [deterministic]{alts_note:<20}"
            f"  {category:<32}  C:{c_status}  I:{i_status}  G:{g_status}"
        )

        if not compliance_ok:
            exp_txt = "pass" if exp_compliance else "fail"
            got_txt = "pass" if compliance.passed else "fail"
            print(f"           \u26a0 compliance: expected {exp_txt}, got {got_txt}")
            for v in compliance.violations:
                print(f"               violation: {v[:90]}")
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

    # ── Aggregate ─────────────────────────────────────────────────────────────
    compliance_rate = compliance_passed_count / total * 100
    integrity_rate = integrity_passed_count / total * 100
    blocked_rate = auto_send_blocked_count / total * 100

    print(f"\n{'─' * 72}")
    print("AGGREGATE RESULTS — RESPOND_UNAVAILABLE")
    print(f"{'─' * 72}")
    print(f"  Total scenarios:         {total}")
    print(f"  Compliance pass rate:    {compliance_rate:.1f}%  ({compliance_passed_count}/{total})  [target: 100%]")
    print(f"  Integrity pass rate:     {integrity_rate:.1f}%  ({integrity_passed_count}/{total})")
    print(f"  Auto-send blocked rate:  {blocked_rate:.1f}%  ({auto_send_blocked_count}/{total})  [target: 100%]")

    # ── Alternative date analysis ──────────────────────────────────────────────
    print(f"\n{'─' * 72}")
    print("ALTERNATIVE DATE ANALYSIS")
    print(f"{'─' * 72}")
    print(f"  Past alternatives rejected (not offered):     {past_alt_rejected_count}")
    print(f"  Capacity-unsuitable alternatives (not offered): {capacity_unsuitable_count}")
    print(f"  Future alternatives offered:                  {future_alt_offered_count}")

    # ── Category breakdown ─────────────────────────────────────────────────────
    print(f"\n{'─' * 72}")
    print("CATEGORY BREAKDOWN")
    print(f"{'─' * 72}")
    for cat in sorted(category_totals.keys()):
        n = category_totals[cat]
        c_pass = category_compliance_passed.get(cat, 0)
        print(f"  {cat:<40}  n={n}  compliance={c_pass}/{n}")

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

    # ── Regression summary ─────────────────────────────────────────────────────
    total_regressions = (
        len(compliance_regressions) + len(integrity_regressions) + len(auto_send_regressions)
    )
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

    print(f"{'=' * 72}\n")

    if total_regressions:
        sys.exit(1)


if __name__ == "__main__":
    run()
