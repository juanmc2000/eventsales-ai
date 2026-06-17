#!/usr/bin/env python3
"""Response Preparation Evaluation Report Exporter (OBSERVE-004).

Reads a response-preparation JSON results file produced by
run_response_preparation_test_100.py and writes a human-readable
Markdown evaluation report.

Usage::

    # Export from a specific JSON file
    python tests/scripts/export_response_preparation_report.py \\
        tests/data/response_prep_100_results_sprint15b_20260617T183121Z.json \\
        [--out tests/data/my_report.md]

    # Auto-detect the most recent results JSON in tests/data/
    python tests/scripts/export_response_preparation_report.py

Output sections:
  1. Run metadata
  2. Headline metrics
  3. Response goal distribution
  4. Audience distribution
  5. Tone validation summary
  6. Auto-send summary
  7. Safety and compliance summary
  8. Failed records table
  9. Top regression risks
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# ── Path constants ─────────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIR = _REPO_ROOT / "tests" / "data"


# ── JSON loader ───────────────────────────────────────────────────────────────


def _find_latest_json() -> Path | None:
    """Return the most recent response_prep_*_results*.json file."""
    candidates = list(_DATA_DIR.glob("response_prep_*results*.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _load(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


# ── Metric helpers ────────────────────────────────────────────────────────────


def _pct(n: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{100 * n / total:.1f}%"


def _compliance_passed(record: dict) -> bool:
    return record.get("compliance", {}).get("passed", False)


def _auto_send_allowed(record: dict) -> bool:
    return record.get("auto_send", {}).get("auto_send_allowed", False)


def _persona_fit_passed(record: dict) -> bool:
    return record.get("persona_fit", {}).get("persona_fit_passed", False)


def _tone_passed(record: dict) -> bool:
    tv = record.get("tone_validation")
    if tv is None:
        return True  # backwards-compatible — not checked
    return tv.get("passed", True)


def _has_safety_issues(record: dict) -> bool:
    return record.get("safety_checks", {}).get("has_issues", False)


def _audience(record: dict) -> str:
    return record.get("persona_fit", {}).get("audience_type", "unknown")


def _goal(record: dict) -> str:
    return record.get("response_goal", "unknown")


def _record_id(record: dict) -> str:
    return str(record.get("record_id", "?"))


# ── Markdown builder ───────────────────────────────────────────────────────────


def build_report(data: dict, source_path: Path) -> str:
    results: list[dict] = data.get("results", [])
    total = len(results)
    generated_at = data.get("generated_at", "unknown")
    run_id = data.get("run_id", "unknown")
    prompt_version = data.get("prompt_version", "unknown")
    llm_model = data.get("llm_model", "unknown")
    fixture = data.get("fixture", "unknown")

    # ── Compute metrics ────────────────────────────────────────────────────────
    compliance_pass = sum(1 for r in results if _compliance_passed(r))
    auto_send_pass = sum(1 for r in results if _auto_send_allowed(r))
    persona_pass = sum(1 for r in results if _persona_fit_passed(r))
    # Only count records where tone_validation was actually checked (not None)
    tone_checked_records = [r for r in results if r.get("tone_validation") is not None]
    tone_checked = len(tone_checked_records)
    tone_pass = sum(1 for r in tone_checked_records if _tone_passed(r))
    safety_clean = sum(1 for r in results if not _has_safety_issues(r))

    # ── Goal distribution ─────────────────────────────────────────────────────
    goal_dist: dict[str, int] = {}
    for r in results:
        g = _goal(r)
        goal_dist[g] = goal_dist.get(g, 0) + 1

    # ── Audience distribution ─────────────────────────────────────────────────
    aud_dist: dict[str, int] = {}
    for r in results:
        a = _audience(r)
        aud_dist[a] = aud_dist.get(a, 0) + 1

    # ── Tone violations by audience ────────────────────────────────────────────
    tone_by_aud: dict[str, dict[str, int]] = {}
    for r in results:
        a = _audience(r)
        tv = r.get("tone_validation")
        if tv is None:
            continue
        if a not in tone_by_aud:
            tone_by_aud[a] = {"total": 0, "failed": 0}
        tone_by_aud[a]["total"] += 1
        if not tv.get("passed", True):
            tone_by_aud[a]["failed"] += 1

    # ── Auto-send blockers ────────────────────────────────────────────────────
    auto_send_blocked = total - auto_send_pass
    blocker_freq: dict[str, int] = {}
    for r in results:
        for b in r.get("auto_send", {}).get("auto_send_blockers", []):
            blocker_freq[b] = blocker_freq.get(b, 0) + 1

    # ── Compliance violations ─────────────────────────────────────────────────
    compliance_violations: dict[str, int] = {}
    for r in results:
        for v in r.get("compliance", {}).get("violations", []):
            compliance_violations[v] = compliance_violations.get(v, 0) + 1

    # ── Safety issues ─────────────────────────────────────────────────────────
    safety_issues: dict[str, int] = {}
    for r in results:
        for issue in r.get("safety_checks", {}).get("issues", []):
            safety_issues[issue] = safety_issues.get(issue, 0) + 1

    # ── Failed records (any layer) ────────────────────────────────────────────
    failed: list[dict] = []
    for r in results:
        reasons = []
        if not _compliance_passed(r):
            viols = r.get("compliance", {}).get("violations", [])
            reasons.append(f"compliance: {', '.join(viols) if viols else 'failed'}")
        if not _auto_send_allowed(r):
            blockers = r.get("auto_send", {}).get("auto_send_blockers", [])
            reasons.append(f"auto-send blocked: {', '.join(blockers) if blockers else 'blocked'}")
        if not _persona_fit_passed(r):
            viols = r.get("persona_fit", {}).get("persona_fit_violations", [])
            reasons.append(f"persona-fit: {', '.join(viols) if viols else 'failed'}")
        if not _tone_passed(r):
            viols = r.get("tone_validation", {}).get("violations", [])
            reasons.append(f"tone: {', '.join(viols) if viols else 'failed'}")
        if _has_safety_issues(r):
            issues = r.get("safety_checks", {}).get("issues", [])
            reasons.append(f"safety: {', '.join(issues) if issues else 'issue'}")
        if reasons:
            failed.append({
                "id": _record_id(r),
                "audience": _audience(r),
                "goal": _goal(r),
                "reasons": reasons,
            })

    # ── Independent evaluation regressions ────────────────────────────────────
    regression_risks: list[dict] = []
    for r in results:
        ie = r.get("independent_evaluation", {})
        if not ie:
            continue
        crit = ie.get("critical_failures", [])
        if crit:
            regression_risks.append({
                "id": _record_id(r),
                "audience": _audience(r),
                "goal": _goal(r),
                "critical_failures": crit,
            })

    # ── Build Markdown ─────────────────────────────────────────────────────────
    export_ts = datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
    lines: list[str] = []

    def h(level: int, text: str) -> None:
        lines.append(f"\n{'#' * level} {text}\n")

    def table_row(*cells: str) -> str:
        return "| " + " | ".join(str(c) for c in cells) + " |"

    def table_sep(*widths: int) -> str:
        return "| " + " | ".join("-" * w for w in widths) + " |"

    # ── 1. Title ──────────────────────────────────────────────────────────────
    lines.append(f"# Response Preparation Evaluation Report\n")
    lines.append(f"**Generated:** {export_ts}  ")
    lines.append(f"**Source file:** `{source_path.name}`  ")
    lines.append(f"**Run ID:** `{run_id}`  ")
    lines.append(f"**Model:** `{llm_model}`  ")
    lines.append(f"**Prompt version:** `{prompt_version}`  ")
    lines.append(f"**Fixture:** `{fixture}`  ")
    lines.append(f"**Records evaluated:** {total}  ")

    # ── 2. Headline metrics ────────────────────────────────────────────────────
    h(2, "Headline Metrics")
    lines.append(table_row("Metric", "Pass", "Total", "Rate"))
    lines.append(table_sep(30, 6, 6, 8))
    lines.append(table_row("Compliance", compliance_pass, total, _pct(compliance_pass, total)))
    lines.append(table_row("Auto-send allowed", auto_send_pass, total, _pct(auto_send_pass, total)))
    lines.append(table_row("Persona fit", persona_pass, total, _pct(persona_pass, total)))
    lines.append(table_row(
        "Tone validation",
        tone_pass if tone_checked else "n/a",
        tone_checked if tone_checked else "n/a",
        _pct(tone_pass, tone_checked) if tone_checked else "n/a",
    ))
    lines.append(table_row("Safety clean", safety_clean, total, _pct(safety_clean, total)))

    # ── 3. Response goal distribution ─────────────────────────────────────────
    h(2, "Response Goal Distribution")
    lines.append(table_row("Goal", "Count", "Share"))
    lines.append(table_sep(40, 6, 8))
    for goal, count in sorted(goal_dist.items(), key=lambda x: -x[1]):
        lines.append(table_row(f"`{goal}`", count, _pct(count, total)))

    # ── 4. Audience distribution ───────────────────────────────────────────────
    h(2, "Audience Distribution")
    lines.append(table_row("Audience", "Count", "Share"))
    lines.append(table_sep(15, 6, 8))
    for aud, count in sorted(aud_dist.items(), key=lambda x: -x[1]):
        lines.append(table_row(aud, count, _pct(count, total)))

    # ── 5. Tone validation by audience ────────────────────────────────────────
    h(2, "Tone Validation by Audience")
    if not tone_by_aud:
        lines.append("_Tone validation not recorded in this run._\n")
    else:
        lines.append(table_row("Audience", "Checked", "Failed", "Pass Rate"))
        lines.append(table_sep(15, 8, 8, 10))
        for aud, counts in sorted(tone_by_aud.items()):
            passed_tone = counts["total"] - counts["failed"]
            lines.append(table_row(
                aud, counts["total"], counts["failed"],
                _pct(passed_tone, counts["total"]),
            ))

    # ── 6. Auto-send summary ───────────────────────────────────────────────────
    h(2, "Auto-Send Summary")
    lines.append(f"**Allowed:** {auto_send_pass}/{total} ({_pct(auto_send_pass, total)})  ")
    lines.append(f"**Blocked:** {auto_send_blocked}/{total}  ")
    if blocker_freq:
        lines.append("")
        lines.append("**Blocker frequency:**\n")
        lines.append(table_row("Blocker", "Count"))
        lines.append(table_sep(50, 6))
        for blocker, count in sorted(blocker_freq.items(), key=lambda x: -x[1]):
            lines.append(table_row(blocker, count))

    # ── 7. Safety and compliance summary ──────────────────────────────────────
    h(2, "Safety and Compliance Summary")
    lines.append(f"**Safety clean:** {safety_clean}/{total} ({_pct(safety_clean, total)})  ")
    lines.append(f"**Compliance passed:** {compliance_pass}/{total} ({_pct(compliance_pass, total)})  ")
    if safety_issues:
        lines.append("")
        lines.append("**Safety issues detected:**\n")
        lines.append(table_row("Issue", "Count"))
        lines.append(table_sep(50, 6))
        for issue, count in sorted(safety_issues.items(), key=lambda x: -x[1]):
            lines.append(table_row(issue, count))
    if compliance_violations:
        lines.append("")
        lines.append("**Compliance violations:**\n")
        lines.append(table_row("Violation", "Count"))
        lines.append(table_sep(50, 6))
        for v, count in sorted(compliance_violations.items(), key=lambda x: -x[1]):
            lines.append(table_row(v, count))

    # ── 8. Failed records table ────────────────────────────────────────────────
    h(2, "Failed Records")
    if not failed:
        lines.append("_No failures detected._\n")
    else:
        lines.append(f"**{len(failed)} record(s) failed one or more checks.**\n")
        lines.append(table_row("ID", "Audience", "Goal", "Failure Reasons"))
        lines.append(table_sep(6, 12, 35, 60))
        for f in failed:
            reasons_str = "; ".join(f["reasons"])
            lines.append(table_row(f["id"], f["audience"], f"`{f['goal']}`", reasons_str))

    # ── 9. Top regression risks ────────────────────────────────────────────────
    h(2, "Top Regression Risks")
    if not regression_risks:
        lines.append("_No independent evaluation critical failures detected._\n")
        lines.append(
            "_(Requires `independent_evaluation` field from TEST-030 in the JSON.)_\n"
        )
    else:
        lines.append(f"**{len(regression_risks)} record(s) with critical independent evaluation failures.**\n")
        lines.append(table_row("ID", "Audience", "Goal", "Critical Failures"))
        lines.append(table_sep(6, 12, 35, 50))
        for rr in regression_risks:
            crit_str = ", ".join(rr["critical_failures"])
            lines.append(table_row(
                rr["id"], rr["audience"], f"`{rr['goal']}`", crit_str
            ))

    lines.append("\n---\n")
    lines.append(f"_Report generated by `export_response_preparation_report.py` at {export_ts}._\n")

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export a Markdown evaluation report from response-preparation JSON."
    )
    parser.add_argument(
        "source",
        nargs="?",
        help=(
            "Path to the JSON results file. "
            "Defaults to the most recent response_prep_*results*.json in tests/data/."
        ),
    )
    parser.add_argument(
        "--out",
        help="Output Markdown file path. Defaults to <source_stem>_report.md.",
    )
    args = parser.parse_args()

    # Resolve source
    if args.source:
        source = Path(args.source)
    else:
        source = _find_latest_json()
        if source is None:
            print("ERROR: No response_prep_*results*.json found in tests/data/", file=sys.stderr)
            return 1
        print(f"Auto-detected: {source.name}")

    if not source.exists():
        print(f"ERROR: file not found: {source}", file=sys.stderr)
        return 1

    data = _load(source)

    # Resolve output path
    if args.out:
        out_path = Path(args.out)
    else:
        out_path = source.parent / (source.stem + "_report.md")

    report = build_report(data, source)
    out_path.write_text(report, encoding="utf-8")
    print(f"Report written to: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
