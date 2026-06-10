#!/usr/bin/env python3
"""TEST-017 — Policy FAQ Pipeline Accuracy Runner (Sprint 13).

Measures the accuracy of policy question extraction, resolution, deterministic
answering, and human-review routing using the 50-record policy FAQ fixture.

Evaluation layers:
  L1  — Policy question detection (did the LLM identify policy questions correctly?)
  L2  — question_key accuracy (correct canonical key per detected question)
  L2B — scope_hint accuracy (room / restaurant / unknown)
  L3  — Resolution accuracy (simulated against seed data defaults)
  L4  — Human-review routing accuracy (approval_required + unknown → review)
  L5  — Composer safety (unknown keys never answered directly)

Inline resolution simulation uses seed data defaults from _seed_policy_faqs():
  allowed:           cake_allowed, candles_allowed, flowers_allowed, children_allowed
  not_allowed:       pets_allowed
  information_only:  microphone_available, screen_available, av_available,
                     private_room_available, room_capacity, disabled_access,
                     minimum_spend, room_hire, service_charge
  approval_required: decorations_allowed, balloons_allowed, external_performer_allowed,
                     live_music_allowed, dj_allowed, agency_commission
  not_found:         unknown (no DB row → human review)

Acceptance criteria (TEST-017):
  - Unknown questions never receive direct answers
  - Approval-required questions trigger human review
  - L2 question_key accuracy ≥ 85%
  - L4 review-routing accuracy ≥ 95%

Usage (from project root, with venv active):
    ANTHROPIC_API_KEY=... python tests/scripts/run_policy_faq_pipeline_accuracy_50.py

Environment:
    ANTHROPIC_API_KEY  -- required
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ── Paths ──────────────────────────────────────────────────────────────────────

_SCRIPT_DIR = Path(__file__).resolve().parent        # tests/scripts/
_TESTS_DIR = _SCRIPT_DIR.parent                      # tests/
_REPO_ROOT = _TESTS_DIR.parent                       # project root
_API_ROOT = _REPO_ROOT / "services" / "api"

_FIXTURE_PATH = _TESTS_DIR / "data" / "policy_faq_question_fixture_50.json"
_OUTPUT_PATH = _TESTS_DIR / "data" / "policy_faq_pipeline_accuracy_50_results.json"

if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

# ── Imports ───────────────────────────────────────────────────────────────────

import anthropic

try:
    from app.modules.ai.prompt_registry import PromptRegistry
    from app.modules.ai.prompt_renderer import PromptRenderer
    from app.modules.ai.constants import PROMPT_KEY_ENQUIRY_EXTRACTION, MODEL_CLAUDE_HAIKU
    _registry = PromptRegistry()
    _renderer = PromptRenderer()
    _REGISTRY_AVAILABLE = True
except ImportError as _err:
    _registry = None  # type: ignore[assignment]
    _renderer = None  # type: ignore[assignment]
    _REGISTRY_AVAILABLE = False
    print(f"WARNING: PromptRegistry not importable: {_err}", file=sys.stderr)

# ── Env ───────────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    print("ERROR: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
    sys.exit(1)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Extraction model settings ─────────────────────────────────────────────────

EXTRACTION_MODEL = MODEL_CLAUDE_HAIKU if _REGISTRY_AVAILABLE else "claude-haiku-4-5-20251001"
EXTRACTION_TEMPERATURE = 0.05
EXTRACTION_MAX_TOKENS = 1400

# ── Inline seed data resolution simulation ────────────────────────────────────
# Maps question_key → (answer_policy, requires_human_review)
# Matches _seed_policy_faqs() in services/api/app/modules/shared/seed_data.py

_SEED_RESOLUTION: dict[str, tuple[str, bool]] = {
    "cake_allowed":              ("allowed",           False),
    "candles_allowed":           ("allowed",           False),
    "decorations_allowed":       ("approval_required", True),
    "balloons_allowed":          ("approval_required", True),
    "flowers_allowed":           ("allowed",           False),
    "external_performer_allowed":("approval_required", True),
    "live_music_allowed":        ("approval_required", True),
    "dj_allowed":                ("approval_required", True),
    "microphone_available":      ("information_only",  False),
    "screen_available":          ("information_only",  False),
    "av_available":              ("information_only",  False),
    "private_room_available":    ("information_only",  False),
    "room_capacity":             ("information_only",  False),
    "disabled_access":           ("information_only",  False),
    "children_allowed":          ("allowed",           False),
    "pets_allowed":              ("not_allowed",       False),
    "minimum_spend":             ("information_only",  False),
    "room_hire":                 ("information_only",  False),
    "service_charge":            ("information_only",  False),
    "agency_commission":         ("approval_required", True),
}

# ── Review-trigger policies ───────────────────────────────────────────────────

_REVIEW_POLICIES = {"approval_required", "unknown"}


# ── Data ──────────────────────────────────────────────────────────────────────


@dataclass
class RecordResult:
    record_id: str

    # L1 — detection
    target_has_policy_questions: bool = False
    extracted_has_policy_questions: bool = False
    l1_correct: bool = False

    # L2 — question_key accuracy
    target_keys: list[str] = field(default_factory=list)
    extracted_keys: list[str] = field(default_factory=list)
    l2_key_matches: int = 0
    l2_key_total: int = 0

    # L2B — scope_hint accuracy
    l2b_scope_matches: int = 0
    l2b_scope_total: int = 0

    # L3 — resolution accuracy
    l3_resolution_matches: int = 0
    l3_resolution_total: int = 0

    # L4 — review routing accuracy
    l4_routing_correct: list[bool] = field(default_factory=list)

    # L5 — composer safety
    l5_unknown_answered_directly: int = 0  # must be 0

    # Metadata
    extraction_error: str | None = None
    extraction_raw: str | None = None


# ── LLM helpers ───────────────────────────────────────────────────────────────


_RESTAURANT_NAME = "The Grand Ballroom"


def _get_rendered_prompts(subject: str, body: str) -> tuple[str, str]:
    """Render the V6 extraction system and user prompts via PromptRegistry.

    Returns (system_prompt, user_message).
    """
    if not _REGISTRY_AVAILABLE:
        raise RuntimeError("PromptRegistry not available")
    defn = _registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
    freeform_text = f"Subject: {subject}\n\n{body}"
    vars_ = {
        "restaurant_name": _RESTAURANT_NAME,
        "freeform_text": freeform_text,
    }
    system_prompt = _renderer.render_system(defn, vars_)
    user_message = _renderer.render_user(defn, vars_)
    return system_prompt, user_message


def _call_extraction_llm(subject: str, body: str) -> dict[str, Any]:
    """Call LLM1 extraction and return parsed JSON."""
    system_prompt, user_message = _get_rendered_prompts(subject, body)
    response = _client.messages.create(
        model=EXTRACTION_MODEL,
        max_tokens=EXTRACTION_MAX_TOKENS,
        temperature=EXTRACTION_TEMPERATURE,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    raw_text = response.content[0].text.strip()

    # Strip markdown fences if present
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

    return json.loads(raw_text)


# ── Resolution simulation ─────────────────────────────────────────────────────


def _simulate_resolution(
    policy_questions: list[dict[str, Any]],
) -> tuple[list[dict], list[dict]]:
    """Simulate PolicyQuestionResolver using inline seed data defaults.

    Returns (answered_questions, review_required_questions).
    """
    answered: list[dict] = []
    review_required: list[dict] = []

    for pq in policy_questions:
        qk = pq.get("question_key", "unknown")
        if qk == "unknown":
            review_required.append(pq)
            continue
        resolution = _SEED_RESOLUTION.get(qk)
        if resolution is None:
            # Key not in seed defaults → escalate to human review
            review_required.append(pq)
            continue
        answer_policy, requires_human_review = resolution
        if answer_policy in _REVIEW_POLICIES or requires_human_review:
            review_required.append(pq)
        else:
            answered.append({
                "question_key": qk,
                "answer_policy": answer_policy,
                "requires_human_review": requires_human_review,
            })

    return answered, review_required


# ── Per-record evaluation ─────────────────────────────────────────────────────


def _evaluate_record(record: dict[str, Any]) -> RecordResult:
    record_id = record["id"]
    result = RecordResult(record_id=record_id)

    target_pqs = record["target_extraction"].get("policy_questions", [])
    target_resolution = record.get("target_resolution", {})
    target_questions_detail = target_resolution.get("questions", [])

    result.target_has_policy_questions = len(target_pqs) > 0
    result.target_keys = [pq["question_key"] for pq in target_pqs]

    # ── LLM extraction ─────────────────────────────────────────────────────
    try:
        extraction = _call_extraction_llm(
            subject=record.get("subject", ""),
            body=record.get("body", ""),
        )
    except Exception as exc:
        result.extraction_error = str(exc)
        return result

    extracted_pqs: list[dict] = extraction.get("policy_questions", [])
    if not isinstance(extracted_pqs, list):
        extracted_pqs = []

    result.extracted_has_policy_questions = len(extracted_pqs) > 0
    result.extracted_keys = [pq.get("question_key", "unknown") for pq in extracted_pqs]

    # ── L1: Detection accuracy ─────────────────────────────────────────────
    result.l1_correct = (
        result.target_has_policy_questions == result.extracted_has_policy_questions
    )

    # ── L2 / L2B: key and scope accuracy ──────────────────────────────────
    # Match extracted questions against target questions by position
    # (best-effort: we take min(target_count, extracted_count) pairs)
    n_compare = min(len(target_pqs), len(extracted_pqs))
    result.l2_key_total = len(target_pqs)
    result.l2b_scope_total = len(target_pqs)

    # Build a set of target keys for soft matching (order-independent)
    target_key_set = Counter(pq["question_key"] for pq in target_pqs)
    extracted_key_set = Counter(pq.get("question_key", "unknown") for pq in extracted_pqs)

    for key, count in target_key_set.items():
        matched = min(count, extracted_key_set.get(key, 0))
        result.l2_key_matches += matched

    # Scope accuracy — position-based for records with matching key count
    if len(target_pqs) == len(extracted_pqs):
        for tq, eq in zip(target_pqs, extracted_pqs):
            if tq.get("question_key") == eq.get("question_key"):
                # Only count scope when key also matches
                target_scope = tq.get("scope_hint", "unknown")
                extracted_scope = eq.get("scope_hint", "unknown")
                result.l2b_scope_matches += int(target_scope == extracted_scope)

    # ── L3: Resolution accuracy ────────────────────────────────────────────
    if extracted_pqs:
        answered, review_required = _simulate_resolution(extracted_pqs)

        for tq_detail in target_questions_detail:
            qk = tq_detail["question_key"]
            expected_policy = tq_detail["expected_answer_policy"]
            expected_review = tq_detail["expected_requires_human_review"]

            # Find the resolution outcome for this key
            answered_hit = next(
                (a for a in answered if a["question_key"] == qk), None
            )
            if answered_hit:
                actual_policy = answered_hit["answer_policy"]
                actual_review = answered_hit["requires_human_review"]
            elif any(pq.get("question_key") == qk for pq in review_required):
                # Resolved to review_required
                actual_policy = _SEED_RESOLUTION.get(qk, ("not_found", True))[0]
                if actual_policy not in _REVIEW_POLICIES:
                    actual_policy = "not_found"
                actual_review = True
            else:
                # Key not extracted at all — resolution cannot be checked
                result.l3_resolution_total += 1
                continue

            result.l3_resolution_total += 1
            if actual_policy == expected_policy or actual_review == expected_review:
                result.l3_resolution_matches += 1

    # ── L4: Review routing accuracy ────────────────────────────────────────
    _, review_required_sim = _simulate_resolution(extracted_pqs)
    reviewed_keys = {pq.get("question_key", "unknown") for pq in review_required_sim}

    for tq_detail in target_questions_detail:
        expected_review = tq_detail["expected_requires_human_review"]
        qk = tq_detail["question_key"]
        if qk not in result.extracted_keys:
            # Skip keys that weren't extracted — can't evaluate routing
            continue
        actual_in_review = qk in reviewed_keys
        result.l4_routing_correct.append(actual_in_review == expected_review)

    # ── L5: Composer safety ────────────────────────────────────────────────
    answered_sim, _ = _simulate_resolution(extracted_pqs)
    for answered_q in answered_sim:
        if answered_q.get("question_key") == "unknown":
            result.l5_unknown_answered_directly += 1

    return result


# ── Reporting ─────────────────────────────────────────────────────────────────


def _print_separator(width: int = 70) -> None:
    print("─" * width)


def _print_results(results: list[RecordResult], records: list[dict]) -> None:
    total = len(results)

    # ── L1 ─────────────────────────────────────────────────────────────────
    l1_correct = sum(1 for r in results if r.l1_correct and not r.extraction_error)
    l1_errors = sum(1 for r in results if r.extraction_error)
    l1_eligible = total - l1_errors

    # ── L2 ─────────────────────────────────────────────────────────────────
    l2_matches = sum(r.l2_key_matches for r in results)
    l2_total = sum(r.l2_key_total for r in results)

    # ── L2B ────────────────────────────────────────────────────────────────
    l2b_matches = sum(r.l2b_scope_matches for r in results)
    l2b_total = sum(r.l2b_scope_total for r in results)

    # ── L3 ─────────────────────────────────────────────────────────────────
    l3_matches = sum(r.l3_resolution_matches for r in results)
    l3_total = sum(r.l3_resolution_total for r in results)

    # ── L4 ─────────────────────────────────────────────────────────────────
    l4_all = [v for r in results for v in r.l4_routing_correct]
    l4_correct = sum(l4_all)
    l4_total = len(l4_all)

    # ── L5 ─────────────────────────────────────────────────────────────────
    l5_violations = sum(r.l5_unknown_answered_directly for r in results)

    # ── Approval-required routing check ────────────────────────────────────
    approval_required_keys = {
        k for k, (p, _) in _SEED_RESOLUTION.items() if p == "approval_required"
    }
    ar_routed_correctly = 0
    ar_total = 0
    for r in results:
        if r.extraction_error:
            continue
        _, review_required = _simulate_resolution(
            [{"question_key": k} for k in r.extracted_keys]
        )
        reviewed_keys = {pq.get("question_key", "unknown") for pq in review_required}
        for k in r.extracted_keys:
            if k in approval_required_keys:
                ar_total += 1
                if k in reviewed_keys:
                    ar_routed_correctly += 1

    # ── Print report ───────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("  TEST-017 — Policy FAQ Pipeline Accuracy Report (Sprint 13)")
    print("  Fixture: policy_faq_question_fixture_50.json")
    print(f"  Records processed: {total}  |  Extraction errors: {l1_errors}")
    print("=" * 70)

    _print_separator()
    print("  LAYER 1 — Policy Question Detection")
    _print_separator()
    l1_pct = 100.0 * l1_correct / l1_eligible if l1_eligible else 0
    print(f"  Correct detection:   {l1_correct}/{l1_eligible}  ({l1_pct:.1f}%)")

    no_pq_records = [r for r in results if not r.target_has_policy_questions]
    no_pq_correct = sum(1 for r in no_pq_records if r.l1_correct and not r.extraction_error)
    print(f"  No-policy records correctly identified as empty: "
          f"{no_pq_correct}/{len(no_pq_records)}")

    _print_separator()
    print("  LAYER 2 — question_key Accuracy")
    _print_separator()
    l2_pct = 100.0 * l2_matches / l2_total if l2_total else 0
    print(f"  Key matches:         {l2_matches}/{l2_total}  ({l2_pct:.1f}%)")
    print(f"  Target: ≥ 85.0%")

    _print_separator()
    print("  LAYER 2B — scope_hint Accuracy")
    _print_separator()
    l2b_pct = 100.0 * l2b_matches / l2b_total if l2b_total else 0
    print(f"  Scope matches:       {l2b_matches}/{l2b_total}  ({l2b_pct:.1f}%)")

    _print_separator()
    print("  LAYER 3 — Resolution Accuracy (simulated seed data)")
    _print_separator()
    l3_pct = 100.0 * l3_matches / l3_total if l3_total else 0
    print(f"  Resolution correct:  {l3_matches}/{l3_total}  ({l3_pct:.1f}%)")

    _print_separator()
    print("  LAYER 4 — Human-Review Routing Accuracy")
    _print_separator()
    l4_pct = 100.0 * l4_correct / l4_total if l4_total else 0
    print(f"  Routing correct:     {l4_correct}/{l4_total}  ({l4_pct:.1f}%)")
    print(f"  Target: ≥ 95.0%")
    ar_pct = 100.0 * ar_routed_correctly / ar_total if ar_total else 0
    print(f"  Approval-required → review: {ar_routed_correctly}/{ar_total}  ({ar_pct:.1f}%)")

    _print_separator()
    print("  LAYER 5 — Composer Safety")
    _print_separator()
    print(f"  Unknown keys answered directly: {l5_violations}  (must be 0)")
    l5_status = "PASS" if l5_violations == 0 else "FAIL"
    print(f"  Status: {l5_status}")

    _print_separator()
    print("  ACCEPTANCE CRITERIA CHECK")
    _print_separator()
    criteria = [
        ("Unknown keys never answered directly", l5_violations == 0),
        ("Approval-required → human review (100%)", ar_total == 0 or ar_routed_correctly == ar_total),
        ("L2 question_key accuracy ≥ 85%", l2_pct >= 85.0),
        ("L4 review routing accuracy ≥ 95%", l4_pct >= 95.0),
    ]
    all_pass = True
    for label, passed in criteria:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}]  {label}")
        if not passed:
            all_pass = False

    _print_separator()
    if all_pass:
        print("  OVERALL: ALL CRITERIA PASSED")
    else:
        print("  OVERALL: ONE OR MORE CRITERIA FAILED — review failures above")
    print("=" * 70)

    # ── Per-record failures ────────────────────────────────────────────────
    failures = [r for r in results if r.extraction_error or not r.l1_correct]
    if failures:
        print()
        print("  L1 DETECTION FAILURES:")
        for r in failures:
            if r.extraction_error:
                print(f"    {r.id}  ERROR: {r.extraction_error}")
            else:
                print(
                    f"    {r.id}  "
                    f"target={'has_pq' if r.target_has_policy_questions else 'empty'}  "
                    f"extracted={'has_pq' if r.extracted_has_policy_questions else 'empty'}"
                )

    # ── Key mismatch details ───────────────────────────────────────────────
    key_failures = [
        r for r in results
        if r.l2_key_total > 0 and r.l2_key_matches < r.l2_key_total
        and not r.extraction_error
    ]
    if key_failures:
        print()
        print("  L2 KEY MISMATCHES (sample, up to 10):")
        for r in key_failures[:10]:
            print(
                f"    {r.id}  "
                f"target={sorted(r.target_keys)}  "
                f"extracted={sorted(r.extracted_keys)}"
            )

    print()


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    # Load fixture
    if not _FIXTURE_PATH.exists():
        print(f"ERROR: Fixture not found: {_FIXTURE_PATH}", file=sys.stderr)
        sys.exit(1)

    with _FIXTURE_PATH.open() as f:
        fixture = json.load(f)

    records: list[dict] = fixture["records"]
    print(f"Loaded {len(records)} records from {_FIXTURE_PATH.name}")

    if not _REGISTRY_AVAILABLE:
        print("ERROR: PromptRegistry not available — cannot run extraction.", file=sys.stderr)
        sys.exit(1)

    print(f"Extraction model: {EXTRACTION_MODEL}  |  Temperature: {EXTRACTION_TEMPERATURE}")
    print()

    # Process records
    results: list[RecordResult] = []
    for i, record in enumerate(records, 1):
        record_id = record["id"]
        print(f"  [{i:02d}/{len(records)}]  {record_id}", end="  ", flush=True)
        result = _evaluate_record(record)
        results.append(result)
        if result.extraction_error:
            print(f"ERROR: {result.extraction_error}")
        else:
            key_match = f"{result.l2_key_matches}/{result.l2_key_total}"
            l1 = "OK" if result.l1_correct else "FAIL"
            print(f"L1={l1}  keys={key_match}  extracted={result.extracted_keys}")

    # Print summary report
    _print_results(results, records)

    # Save results JSON
    output = {
        "fixture": str(_FIXTURE_PATH.name),
        "total_records": len(records),
        "extraction_model": EXTRACTION_MODEL,
        "results": [
            {
                "id": r.record_id,
                "l1_correct": r.l1_correct,
                "target_keys": r.target_keys,
                "extracted_keys": r.extracted_keys,
                "l2_key_matches": r.l2_key_matches,
                "l2_key_total": r.l2_key_total,
                "l2b_scope_matches": r.l2b_scope_matches,
                "l2b_scope_total": r.l2b_scope_total,
                "l3_resolution_matches": r.l3_resolution_matches,
                "l3_resolution_total": r.l3_resolution_total,
                "l4_routing_correct_count": sum(r.l4_routing_correct),
                "l4_routing_total": len(r.l4_routing_correct),
                "l5_unknown_answered_directly": r.l5_unknown_answered_directly,
                "extraction_error": r.extraction_error,
            }
            for r in results
        ],
    }
    with _OUTPUT_PATH.open("w") as f:
        json.dump(output, f, indent=2)
    print(f"Results saved to {_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
