"""Human Review Calibration Comparator (EVAL-001).

Re-imports a filled calibration CSV and compares human reviewer decisions
against validator/auto-send gate results to measure agreement and identify
cases where the validator is too strict or too permissive.

Run from the services/api/ directory:

    python tests/scripts/compare_human_review.py --input <path_to_filled_csv>

Outputs:
  - Agreement rate (human vs auto_send_result)
  - False-positive rate (validator blocked but human says ready)
  - False-negative rate (validator allowed but human says not ready)
  - Ranked disagreement categories
  - JSON report saved to tests/data/

The comparison uses `human_ready_to_send` (TRUE/FALSE) vs `auto_send_result`
(ALLOW/BLOCK) as the primary agreement axis.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────────────────────

_OUTPUT_DIR = Path(__file__).parent.parent / "data"


# ── Helpers ─────────────────────────────────────────────────────────────────────


def _parse_human_flag(value: str) -> bool | None:
    """Parse human_ready_to_send cell to bool. Returns None if blank or unknown."""
    v = value.strip().upper()
    if v in ("TRUE", "YES", "1", "Y"):
        return True
    if v in ("FALSE", "NO", "0", "N"):
        return False
    return None


def _auto_send_bool(value: str) -> bool:
    return value.strip().upper() == "ALLOW"


# ── Runner ──────────────────────────────────────────────────────────────────────


def run(input_path: Path, output_path: Path | None) -> None:
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with input_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("[ERROR] CSV is empty", file=sys.stderr)
        sys.exit(1)

    required_cols = {"record_id", "auto_send_result", "human_ready_to_send"}
    missing = required_cols - set(rows[0].keys())
    if missing:
        print(f"[ERROR] CSV missing columns: {missing}", file=sys.stderr)
        sys.exit(1)

    total = len(rows)
    reviewed = 0
    agree = 0
    false_positives: list[dict] = []   # validator BLOCK, human says ALLOW
    false_negatives: list[dict] = []   # validator ALLOW, human says BLOCK
    skipped: list[str] = []
    category_disagreements: dict[str, int] = {}

    for row in rows:
        human = _parse_human_flag(row.get("human_ready_to_send", ""))
        if human is None:
            skipped.append(row["record_id"])
            continue

        reviewed += 1
        auto = _auto_send_bool(row.get("auto_send_result", ""))
        category = row.get("category", "unknown")

        if human == auto:
            agree += 1
        else:
            # Disagreement
            category_disagreements[category] = category_disagreements.get(category, 0) + 1
            entry = {
                "record_id": row["record_id"],
                "category": category,
                "response_goal": row.get("response_goal", ""),
                "validator_result": row.get("validator_result", ""),
                "validator_violations": row.get("validator_violations", ""),
                "auto_send_result": row.get("auto_send_result", ""),
                "human_ready_to_send": row.get("human_ready_to_send", ""),
                "reviewer_notes": row.get("reviewer_notes", ""),
            }
            if not auto and human:
                false_positives.append(entry)   # validator too strict
            else:
                false_negatives.append(entry)   # validator too permissive

    # ── Print report ─────────────────────────────────────────────────────────
    print(f"\n{'=' * 68}")
    print("HUMAN REVIEW CALIBRATION REPORT — EVAL-001")
    print(f"{'=' * 68}")
    print(f"Input:             {input_path.name}")
    print(f"Total rows:        {total}")
    print(f"Reviewed:          {reviewed}  (skipped: {len(skipped)} blank)")
    print(f"{'─' * 68}")

    if reviewed == 0:
        print("\n[WARN] No reviewed rows found. Fill in 'human_ready_to_send' column and re-run.")
        print(f"{'=' * 68}\n")
        return

    agree_rate = agree / reviewed * 100
    fp_rate = len(false_positives) / reviewed * 100
    fn_rate = len(false_negatives) / reviewed * 100
    disagree_total = len(false_positives) + len(false_negatives)

    print(f"Agreement rate:    {agree_rate:.1f}%  ({agree}/{reviewed})")
    print(f"Disagreements:     {disagree_total}  ({disagree_total / reviewed * 100:.1f}%)")
    print(f"  False-positives: {len(false_positives)}  (validator too strict — human would send)")
    print(f"  False-negatives: {len(false_negatives)}  (validator too permissive — human would not send)")

    if category_disagreements:
        print(f"\nDisagreement categories (ranked):")
        for cat, count in sorted(category_disagreements.items(), key=lambda x: -x[1]):
            bar = "\u2588" * count
            print(f"  {cat:<34}  {count:2d}  {bar}")

    if false_positives:
        print(f"\nFalse-positives (validator blocked, human says ready):")
        for fp in false_positives:
            print(f"  {fp['record_id']:<10}  [{fp['category']}]  goal={fp['response_goal']}")
            if fp["validator_violations"]:
                for v in fp["validator_violations"].split(" | "):
                    print(f"    violation: {v[:80]}")
            if fp["reviewer_notes"]:
                print(f"    notes: {fp['reviewer_notes'][:80]}")

    if false_negatives:
        print(f"\nFalse-negatives (validator allowed, human says not ready):")
        for fn in false_negatives:
            print(f"  {fn['record_id']:<10}  [{fn['category']}]  goal={fn['response_goal']}")
            if fn["reviewer_notes"]:
                print(f"    notes: {fn['reviewer_notes'][:80]}")

    # ── Export JSON ───────────────────────────────────────────────────────────
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_path = _OUTPUT_DIR / f"human_review_comparison_{ts}.json"

    report = {
        "run_at": datetime.now(tz=timezone.utc).isoformat(),
        "input_file": input_path.name,
        "total_rows": total,
        "reviewed": reviewed,
        "skipped": len(skipped),
        "agree": agree,
        "agreement_rate": round(agree_rate, 1),
        "disagree_total": disagree_total,
        "false_positive_count": len(false_positives),
        "false_positive_rate": round(fp_rate, 1),
        "false_negative_count": len(false_negatives),
        "false_negative_rate": round(fn_rate, 1),
        "category_disagreements": dict(
            sorted(category_disagreements.items(), key=lambda x: -x[1])
        ),
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }
    output_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport exported to: {output_path.relative_to(Path(__file__).parent.parent.parent)}")
    print(f"{'=' * 68}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare human review decisions against validator results")
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the filled calibration CSV",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON report path (default: tests/data/human_review_comparison_<timestamp>.json)",
    )
    args = parser.parse_args()
    run(input_path=args.input, output_path=args.output)


if __name__ == "__main__":
    main()
