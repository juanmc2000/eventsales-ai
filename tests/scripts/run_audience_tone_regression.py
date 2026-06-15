#!/usr/bin/env python3
"""Audience Tone Regression Runner — TEST-022.

Generates CONFIRM_AVAILABLE responses for 30 audience-specific tone scenarios
and evaluates each against:
  1. Factual compliance (DraftComplianceValidator — unchanged from Sprint 15)
  2. Tone compliance (audience-specific forbidden pattern check — new)

Factual and tone compliance are reported separately so the Sprint 15
compliance baseline remains comparable.

Usage (from project root, venv active):
    ANTHROPIC_API_KEY=... python tests/scripts/run_audience_tone_regression.py

Output:
    tests/data/audience_tone_regression_results_<timestamp>.json
    tests/data/audience_tone_regression_summary_<timestamp>.md
"""

from __future__ import annotations

import json
import os
import re
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

_SCRIPT_DIR = Path(__file__).resolve().parent
_TESTS_DIR  = _SCRIPT_DIR.parent
_REPO_ROOT  = _TESTS_DIR.parent
_API_ROOT   = _REPO_ROOT / "services" / "api"
_FIXTURE    = _TESTS_DIR / "data" / "audience_tone_regression_fixture_30.json"
_TS         = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
_JSON_OUT   = _TESTS_DIR / "data" / f"audience_tone_regression_results_{_TS}.json"
_MD_OUT     = _TESTS_DIR / "data" / f"audience_tone_regression_summary_{_TS}.md"

if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

# ── Imports ───────────────────────────────────────────────────────────────────

import anthropic

from app.modules.ai.prompt_registry import PromptRegistry
from app.modules.ai.prompt_renderer import PromptRenderer
from app.modules.ai.constants import (
    PROMPT_KEY_DRAFT_RESPONSE,
    DEFAULT_DRAFT_MODEL,
    DEFAULT_DRAFT_MAX_TOKENS,
)
from app.modules.ai.first_response_copy_library import (
    FirstResponseCopyLibrary,
    BLOCK_AVAILABILITY_CONFIRMED_SHORT,
    BLOCK_MINIMUM_SPEND,
    BLOCK_SIGNOFF,
)
from app.modules.ai.draft_compliance_validator import DraftComplianceValidator, ValidationContext
from app.modules.ai.draft_post_processor import DraftPostProcessor

# ── Env ───────────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
    sys.exit(1)

_registry    = PromptRegistry()
_renderer    = PromptRenderer()
_client      = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
_defn        = _registry.get(PROMPT_KEY_DRAFT_RESPONSE)
_TEMPERATURE = float(_defn.temperature) if _defn.temperature is not None else 0.4

# ── Tone violation patterns (deterministic, no LLM) ───────────────────────────

# Patterns that signal inappropriate social warmth in corporate/agency contexts
_CORPORATE_AGENCY_FORBIDDEN: list[str] = [
    r"how wonderful",
    r"how lovely",
    r"such a special occasion",
    r"such a meaningful",
    r"celebration with us",
    r"will be special",
    r"what a lovely occasion",
    r"how exciting",
    r"thrilled",
    r"we['']re so excited",
    r"how delightful",
    r"what a wonderful",
    r"how sweet",
]

# Patterns that signal casual/enthusiastic language in luxury context
_LUXURY_FORBIDDEN: list[str] = [
    r"\bamazing\b",
    r"\bfantastic\b",
    r"\bbrilliant\b",
    r"\bsuper\b",
    r"\btotally\b",
    r"can'?t wait",
    r"how exciting",
]

_TONE_RULES: dict[str, list[str]] = {
    "corporate": _CORPORATE_AGENCY_FORBIDDEN,
    "agency":    _CORPORATE_AGENCY_FORBIDDEN,
    "luxury":    _LUXURY_FORBIDDEN,
    "social":    [],   # social allows celebratory language
    "unknown":   [],   # unknown uses neutral; no forbidden patterns enforced here
}


def _check_tone(draft: str, audience_type: str, fixture_forbidden: list[str]) -> dict:
    """Return tone compliance result for a draft.

    Checks:
    1. Built-in audience-type forbidden pattern list (deterministic)
    2. Per-record forbidden_patterns from fixture (deterministic)

    Never calls an LLM.
    """
    lower = draft.lower()
    hits: list[str] = []

    # Built-in audience patterns
    for pattern in _TONE_RULES.get(audience_type, []):
        if re.search(pattern, lower, re.IGNORECASE):
            hits.append(f"[built-in/{audience_type}] {pattern}")

    # Per-record fixture patterns
    for pattern in fixture_forbidden:
        if pattern.lower() in lower:
            hits.append(f"[fixture] {pattern}")

    return {
        "tone_passed": len(hits) == 0,
        "tone_violations": hits,
        "audience_type": audience_type,
    }


# ── Copy block helpers ────────────────────────────────────────────────────────


def _spend_amount(record: dict) -> str:
    spend_line = record["target_extraction"]["response_preparation_target"] \
        .get("draft_prompt_variables", {}).get("spend_line", "")
    m = re.search(r"[£$]([\d,]+)", spend_line)
    return m.group(1) if m else ""


def _event_date(record: dict) -> str:
    dc = record["target_extraction"]["response_preparation_target"].get("date_context", {})
    return dc.get("assumed_date") or (dc.get("candidate_dates") or ["the requested date"])[0]


def _meal_period(record: dict) -> str:
    return record["target_extraction"].get("meal_period") or "dinner"


# ── LLM call ─────────────────────────────────────────────────────────────────


def _call_llm(prompt_vars: dict, record_id: str, idx: int, total: int) -> dict:
    system_prompt = _renderer.render_system(_defn, prompt_vars)
    user_prompt   = _renderer.render_user(_defn, prompt_vars)
    print(f"  [{idx:2d}/{total}] [llm/CONF] {record_id} ... ", end="", flush=True)
    msg = _client.messages.create(
        model=DEFAULT_DRAFT_MODEL,
        max_tokens=DEFAULT_DRAFT_MAX_TOKENS,
        temperature=_TEMPERATURE,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = msg.content[0].text if msg.content else ""
    print(f"done ({msg.usage.input_tokens}in/{msg.usage.output_tokens}out)")
    return {
        "response": raw,
        "input_tokens": msg.usage.input_tokens,
        "output_tokens": msg.usage.output_tokens,
    }


# ── Build CONFIRM_AVAILABLE prompt vars ──────────────────────────────────────


def _build_vars(record: dict) -> dict:
    prep  = record["target_extraction"]["response_preparation_target"]
    base  = deepcopy(prep.get("draft_prompt_variables", {}))
    persona_name  = base.get("persona_name", "Eleanor")
    spend         = _spend_amount(record)
    meal          = _meal_period(record)
    event_dt      = _event_date(record)

    blocks: list[str] = ["APPROVED COPY BLOCKS — use these verbatim:\n"]
    opening = FirstResponseCopyLibrary.render_safe(
        BLOCK_AVAILABILITY_CONFIRMED_SHORT, {"meal_period": meal, "event_date": event_dt}
    )
    if opening:
        blocks.append(f"[Opening]\n{opening}\n\n")
    if spend:
        spend_text = FirstResponseCopyLibrary.render_safe(
            BLOCK_MINIMUM_SPEND, {"spend_amount": f"£{spend}"}
        )
        if spend_text:
            blocks.append(f"[Minimum spend]\n{spend_text}\n\n")
    next_step = FirstResponseCopyLibrary.render_safe("confirm_available_next_step")
    if next_step:
        blocks.append(f"[Next step]\n{next_step}\n\n")
    signoff = FirstResponseCopyLibrary.render_safe(BLOCK_SIGNOFF, {"persona_name": persona_name})
    if signoff:
        blocks.append(f"[Sign-off]\n{signoff}\n\n")
    blocks.append(
        "WARMTH INSTRUCTION: Write ONE warm opening sentence appropriate for this audience. "
        "Do not write 'Thank you'. Use the copy blocks above verbatim. Nothing else."
    )
    base["approved_copy_blocks"] = "\n".join(blocks)
    base["response_goal"] = "CONFIRM_AVAILABLE"
    return base


# ── Compliance check ─────────────────────────────────────────────────────────


def _check_compliance(draft: str, record: dict, prompt_vars: dict) -> dict:
    prep     = record["target_extraction"]["response_preparation_target"]
    persona  = prep.get("persona_context", {})
    av       = prep.get("availability_decision", {})
    ctx = ValidationContext(
        response_goal="CONFIRM_AVAILABLE",
        availability_status=av.get("availability_status", "AVAILABLE"),
        persona_name=persona.get("persona_name", "Eleanor"),
        approved_copy_blocks=prompt_vars.get("approved_copy_blocks", ""),
        clarification_questions_line="",
        audience_type=record.get("audience_type", "unknown"),
    )
    result = DraftComplianceValidator.validate(draft, ctx)
    return {
        "passed": result.passed,
        "violations": result.violations,
    }


# ── Process one record ────────────────────────────────────────────────────────


def _process(record: dict, idx: int, total: int) -> dict:
    record_id    = record["id"]
    audience     = record.get("audience_type", "unknown")
    tone_family  = record.get("expected_tone_family", "neutral")
    tone_exp     = record.get("tone_expectations", {})
    forbidden    = tone_exp.get("forbidden_patterns", [])

    prompt_vars = _build_vars(record)
    llm_result  = _call_llm(prompt_vars, record_id, idx, total)
    raw_draft   = llm_result["response"]

    # Mirror live pipeline: apply DraftPostProcessor before validation
    draft = DraftPostProcessor.process(raw_draft).cleaned_body

    compliance = _check_compliance(draft, record, prompt_vars)
    tone       = _check_tone(draft, audience, forbidden)

    return {
        "record_id":            record_id,
        "audience_type":        audience,
        "expected_tone_family": tone_family,
        "occasion":             record["target_extraction"].get("occasion"),
        "guest_count":          record["target_extraction"].get("guest_count"),
        "draft":                draft,
        "input_tokens":         llm_result["input_tokens"],
        "output_tokens":        llm_result["output_tokens"],
        "factual_compliance":   compliance,
        "tone_compliance":      tone,
        "overall_passed":       compliance["passed"] and tone["tone_passed"],
    }


# ── Summary helpers ───────────────────────────────────────────────────────────


def _audience_summary(results: list[dict]) -> dict[str, dict]:
    summary: dict[str, dict] = {}
    for r in results:
        aud = r["audience_type"]
        if aud not in summary:
            summary[aud] = {"total": 0, "factual_pass": 0, "tone_pass": 0, "both_pass": 0, "tone_failures": []}
        summary[aud]["total"]       += 1
        summary[aud]["factual_pass"] += int(r["factual_compliance"]["passed"])
        summary[aud]["tone_pass"]    += int(r["tone_compliance"]["tone_passed"])
        summary[aud]["both_pass"]    += int(r["overall_passed"])
        if not r["tone_compliance"]["tone_passed"]:
            summary[aud]["tone_failures"].append({
                "record_id":  r["record_id"],
                "violations": r["tone_compliance"]["tone_violations"],
                "draft_excerpt": r["draft"][:200],
            })
    return summary


def _write_markdown(results: list[dict], audience_summary: dict, run_id: str) -> None:
    total         = len(results)
    factual_pass  = sum(1 for r in results if r["factual_compliance"]["passed"])
    tone_pass     = sum(1 for r in results if r["tone_compliance"]["tone_passed"])
    both_pass     = sum(1 for r in results if r["overall_passed"])
    total_in      = sum(r["input_tokens"] for r in results)
    total_out     = sum(r["output_tokens"] for r in results)

    lines: list[str] = []
    lines.append("# Audience Tone Regression — Results")
    lines.append(f"## TEST-022 — Run {_TS}\n")
    lines.append("## Executive Summary\n")
    lines.append(f"| Metric | Score |")
    lines.append(f"|---|---|")
    lines.append(f"| Records | {total} |")
    lines.append(f"| Factual compliance | **{factual_pass}/{total}** ({factual_pass/total*100:.0f}%) |")
    lines.append(f"| Tone compliance | **{tone_pass}/{total}** ({tone_pass/total*100:.0f}%) |")
    lines.append(f"| Both passed | **{both_pass}/{total}** ({both_pass/total*100:.0f}%) |")
    lines.append(f"| Total tokens | {total_in:,} in / {total_out:,} out |")
    lines.append("")
    lines.append("## By Audience Type\n")
    lines.append("| Audience | Records | Factual | Tone | Both |")
    lines.append("|---|---|---|---|---|")
    for aud, s in sorted(audience_summary.items()):
        t = s["total"]
        lines.append(
            f"| {aud} | {t} | {s['factual_pass']}/{t} | {s['tone_pass']}/{t} | {s['both_pass']}/{t} |"
        )
    lines.append("")

    # Tone failures
    all_tone_failures = [r for r in results if not r["tone_compliance"]["tone_passed"]]
    if all_tone_failures:
        lines.append(f"## Tone Failures ({len(all_tone_failures)})\n")
        for r in all_tone_failures:
            lines.append(f"### {r['record_id']} [{r['audience_type']}]")
            for v in r["tone_compliance"]["tone_violations"]:
                lines.append(f"- `{v}`")
            lines.append(f"\n**Draft excerpt:**")
            lines.append(f"```")
            lines.append(r["draft"][:300])
            lines.append("```\n")
    else:
        lines.append("## Tone Failures\n\nNone.\n")

    # Factual failures
    factual_failures = [r for r in results if not r["factual_compliance"]["passed"]]
    if factual_failures:
        lines.append(f"## Factual Compliance Failures ({len(factual_failures)})\n")
        for r in factual_failures:
            lines.append(f"### {r['record_id']} [{r['audience_type']}]")
            for v in r["factual_compliance"]["violations"]:
                lines.append(f"- {v}")
            lines.append("")
    else:
        lines.append("## Factual Compliance Failures\n\nNone.\n")

    _MD_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Markdown: {_MD_OUT}")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    with open(_FIXTURE) as f:
        fixture = json.load(f)

    records = fixture["records"]
    total   = len(records)
    run_id  = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    print(f"TEST-022 Audience Tone Regression — {total} records")
    print(f"Fixture:  {_FIXTURE}")
    print(f"Model:    {DEFAULT_DRAFT_MODEL}\n")

    results: list[dict] = []
    for idx, record in enumerate(records, 1):
        result = _process(record, idx, total)
        results.append(result)

    aud_summary = _audience_summary(results)

    # JSON output
    output = {
        "run_id":       run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fixture":      str(_FIXTURE.name),
        "total_records": total,
        "results":      results,
        "summary": {
            "by_audience": aud_summary,
            "totals": {
                "factual_pass": sum(1 for r in results if r["factual_compliance"]["passed"]),
                "tone_pass":    sum(1 for r in results if r["tone_compliance"]["tone_passed"]),
                "both_pass":    sum(1 for r in results if r["overall_passed"]),
            },
        },
    }
    _JSON_OUT.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nJSON:     {_JSON_OUT}")

    _write_markdown(results, aud_summary, run_id)

    # Console summary
    t = output["summary"]["totals"]
    print(f"\n{'='*60}")
    print(f"Factual compliance: {t['factual_pass']}/{total}")
    print(f"Tone compliance:    {t['tone_pass']}/{total}")
    print(f"Both passed:        {t['both_pass']}/{total}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
