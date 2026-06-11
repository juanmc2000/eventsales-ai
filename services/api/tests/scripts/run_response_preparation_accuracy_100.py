"""Response Preparation Compliance Accuracy Runner — 100 Records (TEST-019).

Re-evaluates Sprint 13 compliance results with corrected ValidationContext
that passes clarification_questions parsed from clarification_questions_line.

Prior runner wiring bug: ValidationContext was created without
clarification_questions, causing the compliance validator to treat every
question in the draft as invented — producing 14 false-positive violations.

This runner corrects the wiring and separates:
  - Genuine LLM failures (questions appear where none were approved)
  - Runner artefacts (false positives now resolved)

Run from the services/api/ directory:

    python tests/scripts/run_response_preparation_accuracy_100.py

Inputs (root-level tests/data/):
  - response_prep_100_results.json  (pre-generated drafts + clarification context)

Outputs:
  - Per-record corrected compliance result
  - Genuine failures vs resolved false positives clearly separated
  - Adjusted compliance pass rate
  - JSON export written to tests/data/

Exit code 0 if adjusted compliance rate >= 90%.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Path resolution ────────────────────────────────────────────────────────────

_SCRIPT_DIR = Path(__file__).resolve().parent       # services/api/tests/scripts/
_API_TESTS_DIR = _SCRIPT_DIR.parent                  # services/api/tests/
_API_ROOT = _API_TESTS_DIR.parent                    # services/api/
_SVC_ROOT = _API_ROOT.parent                         # services/
_REPO_ROOT = _SVC_ROOT.parent                        # project root

_RESULTS_PATH = _REPO_ROOT / "tests" / "data" / "response_prep_100_results.json"
_OUTPUT_DIR = _REPO_ROOT / "tests" / "data"

if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

# ── Imports ────────────────────────────────────────────────────────────────────

from app.modules.ai.draft_compliance_validator import DraftComplianceValidator, ValidationContext  # noqa: E402

# ── Helpers ────────────────────────────────────────────────────────────────────

# Maps availability_status from results JSON to ValidationContext availability_contract
_AVAILABILITY_CONTRACT_MAP: dict[str, str] = {
    "AVAILABLE": "CONFIRMED_AVAILABLE",
    "UNAVAILABLE": "CONFIRMED_UNAVAILABLE",
    "PENDING_DATE_CONFIRMATION": "PENDING_DATE_CONFIRMATION",
    "INSUFFICIENT_INFORMATION": "INSUFFICIENT_INFORMATION",
    "NOT_CHECKED": "NOT_CHECKED",
}


def _parse_clarification_questions(line: str) -> list[str]:
    """Parse individual questions from a clarification_questions_line string.

    The line format is:
        Clarification questions:
        - Question one here.
        - Question two here.

    Returns a list of question strings (stripped).
    If the line is empty or has no bullet items, returns [].
    """
    if not line or not line.strip():
        return []
    questions: list[str] = []
    for raw in line.splitlines():
        stripped = raw.strip()
        if stripped.startswith("- "):
            questions.append(stripped[2:].strip())
    return questions


def _availability_contract(record: dict) -> str:
    """Map availability_status in the results record to a ValidationContext contract string."""
    status = record.get("availability_status", "NOT_CHECKED")
    return _AVAILABILITY_CONTRACT_MAP.get(status, "NOT_CHECKED")


def _build_context(record: dict) -> ValidationContext:
    """Build a corrected ValidationContext with clarification_questions wired in."""
    clarification_questions_line = record.get("clarification_questions_line", "")
    questions = _parse_clarification_questions(clarification_questions_line)
    return ValidationContext(
        availability_contract=_availability_contract(record),
        clarification_questions=questions,
        response_goal=record.get("response_goal", ""),
    )


def _categorise_result(
    old_passed: bool,
    new_passed: bool,
    clarification_questions_line: str,
) -> str:
    """Classify outcome into one of four categories."""
    if old_passed and new_passed:
        return "pass"
    if not old_passed and new_passed:
        return "false_positive_resolved"
    if not old_passed and not new_passed:
        # Both fail — but was the old failure caused by missing questions?
        if clarification_questions_line and clarification_questions_line.strip():
            return "genuine_failure_with_other_violations"
        return "genuine_failure"
    # old passed, new fails — unexpected; indicates a regression
    return "new_failure"


# ── Runner ─────────────────────────────────────────────────────────────────────


def run() -> None:
    if not _RESULTS_PATH.exists():
        print(f"[ERROR] Results file not found: {_RESULTS_PATH}", file=sys.stderr)
        print("Run the Sprint response preparation runner first to generate this file.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(_RESULTS_PATH.read_text())
    records = data.get("results", [])
    total = len(records)

    if total == 0:
        print("[ERROR] Results file contains no records.", file=sys.stderr)
        sys.exit(1)

    source_file = data.get("fixture", "unknown")
    run_id = data.get("run_id", "unknown")

    print(f"\n{'=' * 70}")
    print("RESPONSE PREPARATION COMPLIANCE ACCURACY — TEST-019 (corrected wiring)")
    print(f"{'=' * 70}")
    print(f"Source results: {Path(source_file).name if source_file != 'unknown' else 'unknown'}")
    print(f"Source run ID:  {run_id}")
    print(f"Records:        {total}\n")
    print("Wiring fix: clarification_questions_line → ValidationContext.clarification_questions\n")

    pass_count = 0
    false_positive_resolved_count = 0
    genuine_failure_count = 0
    new_failure_count = 0

    genuine_failures: list[str] = []
    false_positives_resolved: list[str] = []
    new_failures: list[str] = []

    scenario_results: list[dict] = []

    for rec in records:
        record_id = rec.get("record_id", "unknown")
        draft_text = rec.get("response", "")
        old_compliance = rec.get("compliance", {})
        old_passed = old_compliance.get("passed", True)
        old_violations = old_compliance.get("violations", [])
        clarification_questions_line = rec.get("clarification_questions_line", "")
        response_goal = rec.get("response_goal", "")

        # Re-validate with corrected context
        ctx = _build_context(rec)
        new_result = DraftComplianceValidator.validate(draft_text, ctx)
        new_passed = new_result.passed
        new_violations = list(new_result.violations)

        category = _categorise_result(old_passed, new_passed, clarification_questions_line)

        # Count
        if category == "pass":
            pass_count += 1
        elif category == "false_positive_resolved":
            false_positive_resolved_count += 1
            false_positives_resolved.append(record_id)
        elif category in ("genuine_failure", "genuine_failure_with_other_violations"):
            genuine_failure_count += 1
            genuine_failures.append(record_id)
        elif category == "new_failure":
            new_failure_count += 1
            new_failures.append(record_id)

        # Per-record output
        old_icon = "\u2713" if old_passed else "\u2717"
        new_icon = "\u2713" if new_passed else "\u2717"
        delta = ""
        if not old_passed and new_passed:
            delta = "  \u2192 FALSE POSITIVE RESOLVED"
        elif not old_passed and not new_passed:
            delta = "  \u2192 GENUINE FAILURE"
        elif not old_passed or not new_passed:
            delta = "  \u2192 CHANGED"

        print(
            f"  {record_id:<12}  {response_goal:<36}  "
            f"old:{old_icon}  new:{new_icon}{delta}"
        )

        if not new_passed:
            for v in new_violations:
                print(f"             violation: {v[:88]}")

        scenario_results.append({
            "record_id": record_id,
            "response_goal": response_goal,
            "availability_status": rec.get("availability_status", "NOT_CHECKED"),
            "clarification_questions_line": clarification_questions_line,
            "clarification_questions_parsed": _parse_clarification_questions(clarification_questions_line),
            "old_compliance_passed": old_passed,
            "old_violations": old_violations,
            "new_compliance_passed": new_passed,
            "new_violations": new_violations,
            "category": category,
        })

    # ── Aggregate ─────────────────────────────────────────────────────────────
    old_pass_count = sum(1 for r in scenario_results if r["old_compliance_passed"])
    adjusted_pass_count = pass_count + false_positive_resolved_count
    old_rate = old_pass_count / total * 100
    adjusted_rate = adjusted_pass_count / total * 100

    print(f"\n{'─' * 70}")
    print("AGGREGATE")
    print(f"{'─' * 70}")
    print(f"  Total records:                {total}")
    print(f"  Old compliance pass rate:     {old_rate:.1f}%  ({old_pass_count}/{total})")
    print(f"  Adjusted compliance pass rate:{adjusted_rate:.1f}%  ({adjusted_pass_count}/{total})")
    print(f"")
    print(f"  False positives resolved:     {false_positive_resolved_count}")
    print(f"    {false_positives_resolved}")
    print(f"")
    print(f"  Genuine failures remaining:   {genuine_failure_count}")
    print(f"    {genuine_failures}")

    if new_failures:
        print(f"\n  \u26a0 UNEXPECTED NEW FAILURES ({new_failure_count}):")
        print(f"    {new_failures}")

    # Acceptance criteria
    print(f"\n{'─' * 70}")
    print("ACCEPTANCE CRITERIA")
    print(f"{'─' * 70}")

    # Check specific false positives are resolved.
    # These 14 records had invented-question violations caused by runner wiring.
    # After the fix, they must not contain any "question" violation — some may
    # still fail for other genuine reasons (e.g. availability overclaim).
    fp_ids = {
        "email_20", "email_48", "email_55", "email_61", "email_64",
        "email_66", "email_68", "email_71", "email_72", "email_75",
        "email_79", "email_87", "email_93", "email_97",
    }
    genuine_set = set(genuine_failures)

    # Build a lookup of new violations by record_id
    new_violations_by_id: dict[str, list[str]] = {
        s["record_id"]: s["new_violations"] for s in scenario_results
    }

    # For each fp_id, verify the "invented question" violation is gone
    fp_question_violations_remaining: list[str] = [
        rid for rid in fp_ids
        if any("question" in v.lower() for v in new_violations_by_id.get(rid, []))
    ]
    fp_question_violations_cleared = len(fp_question_violations_remaining) == 0

    no_new_failures = new_failure_count == 0
    adjusted_rate_ok = adjusted_rate >= 90.0

    criteria = [
        (
            "Approved-question violations cleared from all 14 false-positive records",
            fp_question_violations_cleared,
        ),
        ("email_26 genuine invented question still fails", "email_26" in genuine_set),
        ("email_44 genuine invented question still fails", "email_44" in genuine_set),
        ("No unexpected new failures introduced", no_new_failures),
        ("Adjusted compliance rate >= 90%", adjusted_rate_ok),
    ]

    if not fp_question_violations_cleared:
        print(f"\n  Records still showing question violations: {fp_question_violations_remaining}")

    all_pass = True
    for label, passed in criteria:
        icon = "\u2713" if passed else "\u2717"
        print(f"  [{icon}]  {label}")
        if not passed:
            all_pass = False

    # ── Export ─────────────────────────────────────────────────────────────────
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = _OUTPUT_DIR / f"response_prep_100_corrected_results_{ts}.json"
    export = {
        "run_at": ts,
        "source_run_id": run_id,
        "source_fixture": source_file,
        "total_records": total,
        "old_compliance_pass_rate": round(old_rate, 1),
        "adjusted_compliance_pass_rate": round(adjusted_rate, 1),
        "false_positives_resolved": false_positives_resolved,
        "genuine_failures": genuine_failures,
        "new_failures": new_failures,
        "scenarios": scenario_results,
    }
    output_path.write_text(json.dumps(export, indent=2))
    print(f"\n  Results exported to: {output_path.relative_to(_REPO_ROOT)}")
    print(f"{'=' * 70}\n")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    run()
