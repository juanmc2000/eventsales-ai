"""Response Preparation Accuracy Runner — Sprint 14 Baseline (TEST-021).

Corrected 100-record response-preparation regression with adjusted scoring that
separates genuine LLM violations from expected fixture violations (runner artefacts).

Runs two fixtures:
  1. first_response_safety_cases_100.json  (100 scenarios across all goals)
  2. unavailable_response_regression.json  (32 RESPOND_UNAVAILABLE scenarios)

Metrics reported:
  - raw_compliance_rate          — validator result / total (all scenarios)
  - adjusted_compliance_rate     — of expected-pass scenarios, how many pass
  - genuine_unsafe_count         — expected pass but actually fails
  - runner_artefact_count        — expected fail and actually fails (intentional violations)
  - auto_send_allowed_rate       — gate allows auto-send
  - date_formatting_defects      — unformatted ISO dates in drafts
  - room_suitability_defects     — room embellishment language in CONFIRM_AVAILABLE
  - wrong_name_defects           — greeting name differs from expected customer name
  - subject_line_defects         — subject line leaked into draft body
  - per_goal_summary             — breakdown by response goal

Produces:
  - Console summary
  - tests/reports/sprint14_baseline_<timestamp>.json — machine-readable report

Run from the services/api/ directory:

    python tests/scripts/run_response_preparation_accuracy_100.py

Exit code 0 if no unexpected compliance failures detected, exit code 1 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow running from services/api/
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.modules.ai.draft_compliance_validator import DraftComplianceValidator, ValidationContext
from app.modules.ai.auto_send_readiness_gate import AutoSendReadinessGate
from app.modules.enquiries.response_context_integrity_gate import ResponseContextIntegrityGate

# ── Paths ─────────────────────────────────────────────────────────────────────

_FIXTURE_100_PATH = (
    Path(__file__).parent.parent / "fixtures" / "first_response_safety_cases_100.json"
)
_FIXTURE_UNAVAIL_PATH = (
    Path(__file__).parent.parent / "fixtures" / "unavailable_response_regression.json"
)
_REPORTS_DIR = Path(__file__).parent.parent / "reports"

# ── Defect detection patterns ─────────────────────────────────────────────────

_ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_SUBJECT_LINE_RE = re.compile(
    r"^(?:Subject|Re|RE|Fwd|FWD)\s*:", re.MULTILINE
)
_ROOM_SUITABILITY_PATTERNS = [
    re.compile(r"\bexcellent\s+fit\b", re.IGNORECASE),
    re.compile(r"\bperfect\s+(?:setting|venue|space|choice|room|for)\b", re.IGNORECASE),
    re.compile(r"\bideal\s+(?:setting|choice|venue|space|room|for)\b", re.IGNORECASE),
    re.compile(r"\bideally\s+suited\b", re.IGNORECASE),
    re.compile(r"\bwell[\s-]+accommodated\b", re.IGNORECASE),
]
_GREETING_RE = re.compile(
    r"^\s*(?:Dear|Hi|Hello)\s+([A-Z][a-z'-]+(?:\s+[A-Z][a-z'-]+)*)",
    re.MULTILINE | re.IGNORECASE,
)

_DETERMINISTIC_GOALS = frozenset({"RESPOND_UNAVAILABLE"})


# ── Defect detectors ─────────────────────────────────────────────────────────


def _has_date_formatting_defect(text: str) -> bool:
    """Return True if an ISO date (YYYY-MM-DD) appears in the draft body."""
    return bool(_ISO_DATE_RE.search(text))


def _has_room_suitability_defect(text: str, response_goal: str) -> bool:
    """Return True if CONFIRM_AVAILABLE draft contains room embellishment language."""
    if response_goal != "CONFIRM_AVAILABLE":
        return False
    return any(p.search(text) for p in _ROOM_SUITABILITY_PATTERNS)


def _has_subject_line_defect(text: str) -> bool:
    """Return True if a subject line leaked into the draft body."""
    return bool(_SUBJECT_LINE_RE.search(text))


def _has_wrong_name_defect(text: str, expected_name: str | None) -> bool:
    """Return True if the greeting name does not match the expected customer name."""
    if not expected_name:
        return False
    match = _GREETING_RE.search(text)
    if not match:
        return False
    greeting = match.group(1).strip().split()[0].lower()
    exp = expected_name.strip().lower()
    return greeting != exp and not greeting.startswith(exp) and not exp.startswith(greeting)


# ── Draft text routing ───────────────────────────────────────────────────────


def _get_draft_text(scenario: dict) -> str:
    """Return production-equivalent draft text.

    RESPOND_UNAVAILABLE → deterministic FirstResponseCopyLibrary text (RESP-023).
    All other goals → fixture draft_text (LLM-generated test draft).
    """
    goal = scenario.get("response_goal", "")
    if goal in _DETERMINISTIC_GOALS:
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
    return scenario.get("draft_text", "")


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
        known_room_names=ctx.get("known_room_names", []),
        # RESP-062: pass expected customer name so the name consistency check fires
        expected_customer_name=ctx.get("guest_first_name"),
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
    if "suitability" in v or "perfect for" in v or "ideal for" in v or "well-suited" in v:
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
    if "section" in v or "label" in v:
        return "section_label"
    if "subject" in v:
        return "subject_line"
    if "room" in v and ("invented" in v or "unknown" in v):
        return "invented_room_name"
    return "other"


# ── Single-fixture evaluator ─────────────────────────────────────────────────


def _evaluate_fixture(
    scenarios: list[dict],
    fixture_label: str,
) -> dict[str, Any]:
    """Evaluate one fixture's scenarios and return structured results."""
    total = len(scenarios)
    expected_pass_count = sum(
        1 for s in scenarios if s.get("expected", {}).get("compliance_passed") is True
    )
    expected_fail_count = total - expected_pass_count

    compliance_passed_count = 0
    genuine_unsafe: list[str] = []  # expected pass, actually fail
    runner_artefacts: list[str] = []  # expected fail, actually fail (intentional)
    unexpected_pass: list[str] = []  # expected fail, actually pass (over-detection fixed)
    auto_send_allowed_count = 0

    date_fmt_defect_ids: list[str] = []
    room_suitability_defect_ids: list[str] = []
    wrong_name_defect_ids: list[str] = []
    subject_line_defect_ids: list[str] = []

    violation_category_counts: dict[str, int] = {}
    per_goal: dict[str, dict[str, int]] = {}

    scenario_results: list[dict] = []

    for sc in scenarios:
        sc_id = sc["id"]
        response_goal = sc.get("response_goal", "")
        expected = sc.get("expected", {})
        exp_compliance = expected.get("compliance_passed")
        exp_auto_send = expected.get("ready_to_send_allowed")

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

        # Core counts
        if compliance.passed:
            compliance_passed_count += 1
        if gate.auto_send_allowed:
            auto_send_allowed_count += 1

        # Classification
        if exp_compliance is True and not compliance.passed:
            genuine_unsafe.append(sc_id)
        elif exp_compliance is False and not compliance.passed:
            runner_artefacts.append(sc_id)
        elif exp_compliance is False and compliance.passed:
            unexpected_pass.append(sc_id)

        # Defect detection (on fixture draft_text for non-deterministic goals)
        if response_goal not in _DETERMINISTIC_GOALS:
            if _has_date_formatting_defect(draft_text):
                date_fmt_defect_ids.append(sc_id)
            if _has_room_suitability_defect(draft_text, response_goal):
                room_suitability_defect_ids.append(sc_id)
            if _has_subject_line_defect(draft_text):
                subject_line_defect_ids.append(sc_id)
            expected_name = sc.get("context", {}).get("guest_first_name")
            if _has_wrong_name_defect(draft_text, expected_name):
                wrong_name_defect_ids.append(sc_id)

        for v in compliance.violations:
            cat = _categorise_violation(v)
            violation_category_counts[cat] = violation_category_counts.get(cat, 0) + 1

        # Per-goal tracking
        if response_goal not in per_goal:
            per_goal[response_goal] = {
                "total": 0,
                "compliance_passed": 0,
                "auto_send_allowed": 0,
                "genuine_unsafe": 0,
                "expected_fail": 0,
            }
        per_goal[response_goal]["total"] += 1
        if compliance.passed:
            per_goal[response_goal]["compliance_passed"] += 1
        if gate.auto_send_allowed:
            per_goal[response_goal]["auto_send_allowed"] += 1
        if exp_compliance is True and not compliance.passed:
            per_goal[response_goal]["genuine_unsafe"] += 1
        if exp_compliance is False:
            per_goal[response_goal]["expected_fail"] += 1

        scenario_results.append({
            "id": sc_id,
            "response_goal": response_goal,
            "category": sc.get("category", ""),
            "compliance_passed": compliance.passed,
            "integrity_passed": integrity.passed,
            "auto_send_allowed": gate.auto_send_allowed,
            "expected_compliance_passed": exp_compliance,
            "expected_auto_send": exp_auto_send,
            "violations": compliance.violations,
            "classification": (
                "genuine_unsafe"
                if sc_id in genuine_unsafe
                else "runner_artefact"
                if sc_id in runner_artefacts
                else "unexpected_pass"
                if sc_id in unexpected_pass
                else "pass"
            ),
            "defects": {
                "date_formatting": sc_id in date_fmt_defect_ids,
                "room_suitability": sc_id in room_suitability_defect_ids,
                "wrong_name": sc_id in wrong_name_defect_ids,
                "subject_line": sc_id in subject_line_defect_ids,
            },
        })

    raw_compliance_rate = compliance_passed_count / total if total else 0
    adjusted_compliance_rate = (
        (expected_pass_count - len(genuine_unsafe)) / expected_pass_count
        if expected_pass_count
        else 1.0
    )
    auto_send_rate = auto_send_allowed_count / total if total else 0

    return {
        "fixture": fixture_label,
        "total": total,
        "expected_pass_count": expected_pass_count,
        "expected_fail_count": expected_fail_count,
        "raw_compliance_passed": compliance_passed_count,
        "raw_compliance_rate": round(raw_compliance_rate * 100, 1),
        "adjusted_compliance_rate": round(adjusted_compliance_rate * 100, 1),
        "genuine_unsafe_count": len(genuine_unsafe),
        "genuine_unsafe_ids": genuine_unsafe,
        "runner_artefact_count": len(runner_artefacts),
        "unexpected_pass_count": len(unexpected_pass),
        "unexpected_pass_ids": unexpected_pass,
        "auto_send_allowed": auto_send_allowed_count,
        "auto_send_rate": round(auto_send_rate * 100, 1),
        "date_formatting_defect_count": len(date_fmt_defect_ids),
        "date_formatting_defect_ids": date_fmt_defect_ids,
        "room_suitability_defect_count": len(room_suitability_defect_ids),
        "room_suitability_defect_ids": room_suitability_defect_ids,
        "wrong_name_defect_count": len(wrong_name_defect_ids),
        "wrong_name_defect_ids": wrong_name_defect_ids,
        "subject_line_defect_count": len(subject_line_defect_ids),
        "subject_line_defect_ids": subject_line_defect_ids,
        "violation_category_counts": violation_category_counts,
        "per_goal_summary": per_goal,
        "scenario_results": scenario_results,
    }


# ── Printer ──────────────────────────────────────────────────────────────────


def _print_fixture_summary(result: dict, verbose: bool = False) -> None:
    label = result["fixture"]
    total = result["total"]
    print(f"\n{'─' * 72}")
    print(f"FIXTURE: {label}  ({total} scenarios)")
    print(f"{'─' * 72}")
    print(
        f"  Raw compliance pass rate:      {result['raw_compliance_rate']:5.1f}%"
        f"  ({result['raw_compliance_passed']}/{total})"
    )
    print(
        f"  Adjusted compliance rate:      {result['adjusted_compliance_rate']:5.1f}%"
        f"  (of {result['expected_pass_count']} expected-pass scenarios)"
    )
    print(
        f"  Genuine unsafe records:        {result['genuine_unsafe_count']}"
        f"  {result['genuine_unsafe_ids']}"
    )
    print(
        f"  Runner artefacts (exp-fail):   {result['runner_artefact_count']}"
    )
    if result["unexpected_pass_count"]:
        print(
            f"  Unexpected passes (fixed):     {result['unexpected_pass_count']}"
            f"  {result['unexpected_pass_ids']}"
        )
    print(
        f"  Auto-send allowed rate:        {result['auto_send_rate']:5.1f}%"
        f"  ({result['auto_send_allowed']}/{total})"
    )

    # Defect counts
    print(f"\n  Defect scan (LLM drafts):")
    print(f"    Date formatting (ISO dates in text):  {result['date_formatting_defect_count']}")
    print(f"    Room suitability (CONFIRM_AVAILABLE): {result['room_suitability_defect_count']}")
    print(f"    Wrong name (greeting mismatch):       {result['wrong_name_defect_count']}")
    print(f"    Subject line leaked:                  {result['subject_line_defect_count']}")

    # Per-goal summary
    print(f"\n  Per-goal summary:")
    for goal, stats in sorted(result["per_goal_summary"].items()):
        n = stats["total"]
        c_pass = stats["compliance_passed"]
        g_allow = stats["auto_send_allowed"]
        g_unsafe = stats["genuine_unsafe"]
        unsafe_note = f"  ⚠ {g_unsafe} genuine unsafe" if g_unsafe else ""
        print(
            f"    {goal:<42}  n={n:2d}  "
            f"compliance={c_pass}/{n}  "
            f"auto-send={g_allow}/{n}{unsafe_note}"
        )

    if result["violation_category_counts"] and verbose:
        print(f"\n  Violation category breakdown:")
        for cat, count in sorted(
            result["violation_category_counts"].items(), key=lambda x: -x[1]
        ):
            bar = "█" * min(count, 30)
            print(f"    {cat:<32}  {count:2d}  {bar}")


# ── Runner ───────────────────────────────────────────────────────────────────


def run() -> None:
    for path in (_FIXTURE_100_PATH, _FIXTURE_UNAVAIL_PATH):
        if not path.exists():
            print(f"[ERROR] Fixture not found: {path}", file=sys.stderr)
            sys.exit(1)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = _REPORTS_DIR / f"sprint14_baseline_{ts}.json"

    data_100 = json.loads(_FIXTURE_100_PATH.read_text())
    data_unavail = json.loads(_FIXTURE_UNAVAIL_PATH.read_text())

    print(f"\n{'=' * 72}")
    print("RESPONSE PREPARATION ACCURACY — SPRINT 14 BASELINE (TEST-021)")
    print(f"{'=' * 72}")
    print(f"Timestamp:  {ts}")
    print(f"Fixture 1:  {_FIXTURE_100_PATH.name}  ({len(data_100['scenarios'])} scenarios)")
    print(f"Fixture 2:  {_FIXTURE_UNAVAIL_PATH.name}  ({len(data_unavail['scenarios'])} scenarios)")

    result_100 = _evaluate_fixture(data_100["scenarios"], _FIXTURE_100_PATH.name)
    result_unavail = _evaluate_fixture(data_unavail["scenarios"], _FIXTURE_UNAVAIL_PATH.name)

    _print_fixture_summary(result_100, verbose=True)
    _print_fixture_summary(result_unavail, verbose=False)

    # Combined totals
    combined_total = result_100["total"] + result_unavail["total"]
    combined_genuine_unsafe = result_100["genuine_unsafe_count"] + result_unavail["genuine_unsafe_count"]
    combined_auto_send = result_100["auto_send_allowed"] + result_unavail["auto_send_allowed"]
    combined_adj = (
        result_100["adjusted_compliance_rate"] * result_100["expected_pass_count"]
        + result_unavail["adjusted_compliance_rate"] * result_unavail["expected_pass_count"]
    ) / (result_100["expected_pass_count"] + result_unavail["expected_pass_count"])

    print(f"\n{'=' * 72}")
    print("COMBINED SPRINT 14 BASELINE")
    print(f"{'=' * 72}")
    print(f"  Total scenarios:               {combined_total}")
    print(f"  Combined adjusted compliance:  {combined_adj:.1f}%")
    print(f"  Combined genuine unsafe:       {combined_genuine_unsafe}")
    print(f"  Combined auto-send allowed:    {combined_auto_send}/{combined_total}")

    genuine_all = result_100["genuine_unsafe_ids"] + result_unavail["genuine_unsafe_ids"]
    if genuine_all:
        print(f"\n  ⚠  GENUINE UNSAFE RECORDS ({len(genuine_all)}):")
        for sc_id in genuine_all:
            print(f"       {sc_id}")
    else:
        print(f"\n  ✓ No genuine unsafe records detected.")

    # ── Write report ─────────────────────────────────────────────────────────
    report = {
        "meta": {
            "version": "1.0",
            "sprint": "sprint14",
            "timestamp": ts,
            "description": (
                "Sprint 14 baseline response preparation accuracy report (TEST-021). "
                "Corrected scoring separates genuine LLM violations from expected "
                "fixture violations (runner artefacts)."
            ),
        },
        "combined": {
            "total_scenarios": combined_total,
            "combined_adjusted_compliance_rate": round(combined_adj, 1),
            "combined_genuine_unsafe_count": combined_genuine_unsafe,
            "combined_genuine_unsafe_ids": genuine_all,
            "combined_auto_send_allowed": combined_auto_send,
            "combined_auto_send_rate": round(combined_auto_send / combined_total * 100, 1),
        },
        "fixtures": [result_100, result_unavail],
    }

    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  Report written to: {report_path.relative_to(Path(__file__).parent.parent.parent)}")
    print(f"{'=' * 72}\n")

    # Exit code: 1 if there are genuine unsafe records
    if combined_genuine_unsafe > 0:
        sys.exit(1)


if __name__ == "__main__":
    run()
