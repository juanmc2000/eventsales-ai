"""Human Review Calibration Sheet Export (EVAL-001).

Generates a CSV from the 100-record safety regression fixture with
pre-populated validator results and blank human-review columns.

Reviewers fill in `human_ready_to_send` (TRUE/FALSE) and `reviewer_notes`,
then run compare_human_review.py to calibrate validator strictness.

Run from the services/api/ directory:

    python tests/scripts/export_human_review_calibration.py [--fixture PATH] [--output PATH]

Outputs:
  tests/data/human_review_calibration_<timestamp>.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
import json

# Allow running from services/api/
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.modules.ai.draft_compliance_validator import DraftComplianceValidator, ValidationContext
from app.modules.ai.auto_send_readiness_gate import AutoSendReadinessGate
from app.modules.enquiries.response_context_integrity_gate import ResponseContextIntegrityGate

# ── Paths ───────────────────────────────────────────────────────────────────────

_DEFAULT_FIXTURE = Path(__file__).parent.parent / "fixtures" / "first_response_safety_cases_100.json"
_OUTPUT_DIR = Path(__file__).parent.parent / "data"

# ── CSV columns ─────────────────────────────────────────────────────────────────

_FIELDNAMES = [
    "record_id",
    "category",
    "customer_type",
    "response_goal",
    "availability_contract",
    "date_status",
    "draft_response",
    "validator_result",
    "validator_violations",
    "integrity_result",
    "integrity_violations",
    "auto_send_result",
    "auto_send_blockers",
    # Human-review fields — filled in by reviewer
    "human_ready_to_send",
    "reviewer_notes",
]

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


def _run(fixture_path: Path, output_path: Path) -> None:
    if not fixture_path.exists():
        print(f"[ERROR] Fixture not found: {fixture_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(fixture_path.read_text())
    scenarios = data["scenarios"]
    total = len(scenarios)

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    for sc in scenarios:
        ctx = _context_from_scenario(sc)
        compliance = DraftComplianceValidator.validate(sc["draft_text"], ctx)

        integrity = ResponseContextIntegrityGate.check(
            context_restaurant_name=sc.get("context_restaurant_name", ""),
            context_room_name=sc.get("context_room_name"),
            availability_restaurant_name=sc.get("availability_restaurant_name"),
            availability_room_name=sc.get("availability_room_name"),
        )

        gate = AutoSendReadinessGate.evaluate(
            response_goal=sc.get("response_goal", ""),
            draft_compliance_result=compliance,
            date_status=sc.get("date_status", "resolved"),
            integrity_result=integrity,
        )

        rows.append({
            "record_id": sc["id"],
            "category": sc.get("category", ""),
            "customer_type": sc.get("customer_type", ""),
            "response_goal": sc.get("response_goal", ""),
            "availability_contract": sc.get("availability_contract", ""),
            "date_status": sc.get("date_status", ""),
            "draft_response": sc["draft_text"],
            "validator_result": "PASS" if compliance.passed else "FAIL",
            "validator_violations": " | ".join(compliance.violations),
            "integrity_result": "PASS" if integrity.passed else "FAIL",
            "integrity_violations": " | ".join(integrity.violations),
            "auto_send_result": "ALLOW" if gate.auto_send_allowed else "BLOCK",
            "auto_send_blockers": " | ".join(gate.auto_send_blockers),
            # Human-review columns — left blank for reviewer to fill
            "human_ready_to_send": "",
            "reviewer_notes": "",
        })

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Exported {total} rows to: {output_path}")
    print(f"\nNext steps:")
    print(f"  1. Open the CSV in a spreadsheet tool")
    print(f"  2. For each row, set 'human_ready_to_send' to TRUE or FALSE")
    print(f"  3. Add 'reviewer_notes' for any disagreements with the validator")
    print(f"  4. Save and run: python tests/scripts/compare_human_review.py --input <path>")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export human review calibration CSV")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=_DEFAULT_FIXTURE,
        help="Path to the scenario fixture JSON (default: first_response_safety_cases_100.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path (default: tests/data/human_review_calibration_<timestamp>.csv)",
    )
    args = parser.parse_args()

    if args.output is None:
        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        args.output = _OUTPUT_DIR / f"human_review_calibration_{ts}.csv"

    _run(fixture_path=args.fixture, output_path=args.output)


if __name__ == "__main__":
    main()
