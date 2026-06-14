#!/usr/bin/env python3
"""Response Preparation Test — 100 records from freeform_group_booking_response_preparation_test_100.json.

Routes each record by availability_decision.availability_status:
  - AVAILABLE                 → CONFIRM_AVAILABLE        (LLM warmth + copy blocks)
  - PENDING_DATE_CONFIRMATION → REQUEST_DATE_CONFIRMATION (LLM + clarification question)
  - INSUFFICIENT_INFORMATION  → REQUEST_MISSING_INFORMATION (LLM + clarification questions)
  - UNAVAILABLE               → RESPOND_UNAVAILABLE      (deterministic copy blocks)

Usage (from project root, with venv active):
    ANTHROPIC_API_KEY=... python tests/scripts/run_response_preparation_test_100.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

_SCRIPT_DIR = Path(__file__).resolve().parent
_TESTS_DIR = _SCRIPT_DIR.parent
_REPO_ROOT = _TESTS_DIR.parent
_API_ROOT = _REPO_ROOT / "services" / "api"
_FIXTURE_PATH = _TESTS_DIR / "data" / "freeform_group_booking_response_preparation_test_100.json"
_TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
_OUTPUT_PATH = _TESTS_DIR / "data" / f"response_prep_100_results_sprint15b_{_TS}.json"

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
    BLOCK_AVAILABILITY_CONFIRMED,
    BLOCK_AVAILABILITY_CONFIRMED_SHORT,
    BLOCK_AVAILABILITY_NOT_CHECKED,
    BLOCK_AVAILABILITY_UNAVAILABLE,
    BLOCK_UNAVAILABLE_NO_ALTERNATIVES,
    BLOCK_UNAVAILABLE_ONE_ALTERNATIVE,
    BLOCK_UNAVAILABLE_TWO_ALTERNATIVES,
    BLOCK_MINIMUM_SPEND,
    BLOCK_RDTC_AVAILABLE_OPENER,
    BLOCK_RDTC_NEXT_STEP,
    BLOCK_SIGNOFF,
    BLOCK_BOOKING_NEXT_STEP,
    BLOCK_AVAILABILITY_CHECK_NEXT_STEP,
    BLOCK_CLARIFICATION_NEXT_STEP,
)
from app.modules.ai.draft_compliance_validator import DraftComplianceValidator, ValidationContext
from app.modules.ai.auto_send_readiness_gate import AutoSendReadinessGate
from app.modules.ai.draft_post_processor import (
    DraftPostProcessor,
    strip_provisional_sentences as _strip_provisional_sentences,
)
from app.modules.enquiries.response_context_integrity_gate import IntegrityCheckResult

# ── Env setup ─────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
    sys.exit(1)

_registry = PromptRegistry()
_renderer = PromptRenderer()
_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
_defn = _registry.get(PROMPT_KEY_DRAFT_RESPONSE)
_DRAFT_TEMPERATURE = float(_defn.temperature) if _defn.temperature is not None else 0.4

# ── Safety check patterns ─────────────────────────────────────────────────────

_ROOM_NAME_RE = re.compile(
    r"\b(?:The\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+"
    r"(?:Room|Suite|Hall|Lounge|Terrace|Ballroom|Loft|Space|Bar|Gallery|Studio)\b"
)
_SUBJECT_LINE_RE = re.compile(
    r"^\s*\*{0,2}(?:Subject|Re|Email\s+subject)\s*:",
    re.IGNORECASE | re.MULTILINE,
)
_FORBIDDEN_TOPICS = [
    "menu", "dietary", "special touch", "decoration",
    "arrival time", "start time", "preferred timing",
]

# ── Goal routing ──────────────────────────────────────────────────────────────


def _goal_from_record(record: dict) -> str:
    prep = record["target_extraction"]["response_preparation_target"]
    av_status = prep.get("availability_decision", {}).get("availability_status", "")
    if av_status == "AVAILABLE":
        return "CONFIRM_AVAILABLE"
    if av_status == "UNAVAILABLE":
        return "RESPOND_UNAVAILABLE"
    if av_status == "PENDING_DATE_CONFIRMATION":
        return "REQUEST_DATE_CONFIRMATION"
    return "REQUEST_MISSING_INFORMATION"


# ── Copy block helpers ────────────────────────────────────────────────────────


def _extract_meal_period(record: dict) -> str:
    return record["target_extraction"].get("meal_period") or "dinner"


def _extract_event_date(record: dict) -> str:
    prep = record["target_extraction"]["response_preparation_target"]
    date_ctx = prep.get("date_context", {})
    dates = date_ctx.get("candidate_dates", [])
    if dates:
        return dates[0]
    dv = prep.get("draft_prompt_variables", {})
    ev_line = dv.get("event_date_line", "")
    m = re.search(r"\d{4}-\d{2}-\d{2}", ev_line)
    return m.group(0) if m else "the requested date"


def _extract_spend_amount(record: dict) -> str:
    prep = record["target_extraction"]["response_preparation_target"]
    spend_line = prep.get("draft_prompt_variables", {}).get("spend_line", "")
    m = re.search(r"[£$]([\d,]+)", spend_line)
    return m.group(1) if m else ""


# ── LLM call ─────────────────────────────────────────────────────────────────


def _call_llm(goal: str, prompt_vars: dict, record_id: str, idx: int, total: int) -> dict:
    system_prompt = _renderer.render_system(_defn, prompt_vars)
    user_prompt = _renderer.render_user(_defn, prompt_vars)
    path_label = {"CONFIRM_AVAILABLE": "CONF", "REQUEST_DATE_CONFIRMATION": "RDTC",
                  "REQUEST_MISSING_INFORMATION": "RMSN"}.get(goal, goal[:4])
    print(f"  [{idx:3d}/{total}] [llm/{path_label}] {record_id} ... ", end="", flush=True)
    message = _client.messages.create(
        model=DEFAULT_DRAFT_MODEL,
        max_tokens=DEFAULT_DRAFT_MAX_TOKENS,
        temperature=_DRAFT_TEMPERATURE,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = message.content[0].text if message.content else ""
    print(f"done ({message.usage.input_tokens}in/{message.usage.output_tokens}out)")
    return {
        "response": raw,
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
    }


# ── CONFIRM_AVAILABLE ─────────────────────────────────────────────────────────


def _build_confirm_available(record: dict, idx: int, total: int) -> dict:
    prep = record["target_extraction"]["response_preparation_target"]
    base_vars = deepcopy(prep.get("draft_prompt_variables", {}))
    persona_name = base_vars.get("persona_name", "Eleanor")
    spend_amount = _extract_spend_amount(record)
    meal_period = _extract_meal_period(record)
    event_date = _extract_event_date(record)

    # RESP-071: warmth-first structure — short opening block (no "Thank you" prefix)
    # follows the warmth sentence. Full block (with "Thank you") is used only without warmth.
    blocks: list[str] = ["APPROVED COPY BLOCKS — use these verbatim:\n"]
    opening_short = FirstResponseCopyLibrary.render_safe(
        BLOCK_AVAILABILITY_CONFIRMED_SHORT, {"meal_period": meal_period, "event_date": event_date}
    )
    if opening_short:
        blocks.append(f"[Opening]\n{opening_short}\n\n")
    if spend_amount:
        spend_text = FirstResponseCopyLibrary.render_safe(
            BLOCK_MINIMUM_SPEND, {"spend_amount": f"£{spend_amount}"}
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
        "You MUST use all the approved blocks above verbatim. "
        "You may add ONE warmth sentence before the Opening block only — "
        "it must acknowledge the occasion or guest context, not describe the venue. "
        "CRITICAL: Do NOT start the warmth sentence with 'Thank you', 'Thanks', or any "
        "acknowledgement phrase — the email already says thank you elsewhere. "
        "Use a celebratory opener instead, such as: "
        "'How wonderful —', 'How lovely —', 'How exciting —', "
        "'What a lovely occasion —', 'That sounds wonderful —'. "
        "Do NOT add any sentence about the room, space, or venue suitability. "
        "Forbidden phrases: 'excellent choice', 'perfect for', 'perfect setting', "
        "'ideal', 'ideal for', 'ideal setting', 'well accommodated', 'excellent fit', "
        "'intimate setting', 'excellent setting', 'would be ideal', 'ideally suited'. "
        "Do not paraphrase, shorten, or replace approved blocks.\n"
    )

    prompt_vars = {
        "persona_system_prompt": base_vars.get("persona_system_prompt", ""),
        "persona_name": persona_name,
        "restaurant_name": base_vars.get("restaurant_name", ""),
        "persona_tone": base_vars.get("persona_tone", ""),
        "persona_style": base_vars.get("persona_style", ""),
        "response_goal": "CONFIRM_AVAILABLE",
        "guest_first_name": base_vars.get("guest_first_name", ""),
        "guest_last_name": base_vars.get("guest_last_name", ""),
        "audience_type_line": base_vars.get("audience_type_line", ""),
        "event_type_line": base_vars.get("event_type_line", ""),
        "event_date_line": base_vars.get("event_date_line", ""),
        "party_size_line": base_vars.get("party_size_line", ""),
        "room_lines": base_vars.get("room_lines", ""),
        "availability_line": f"Availability status: CONFIRMED_AVAILABLE\nAvailability: Room is available for {event_date} {meal_period}.\n",
        "spend_line": f"Minimum spend: £{spend_amount}\n" if spend_amount else "",
        "guest_message_line": "",
        "confirmed_venue_facts_line": "",
        "requested_preferences_line": "",
        "prohibited_claims_line": "",
        "clarification_questions_line": "",
        "phrase_guidance_line": "",
        "allowed_sections_line": "",
        "forbidden_topics_line": "",
        "approved_copy_blocks_line": "".join(blocks),
    }

    llm = _call_llm("CONFIRM_AVAILABLE", prompt_vars, record["id"], idx, total)
    return {
        "generation_path": "llm",
        "approved_copy_blocks": {
            "opening": opening_short,
            "minimum_spend": FirstResponseCopyLibrary.render_safe(
                BLOCK_MINIMUM_SPEND, {"spend_amount": f"£{spend_amount}"}
            ) if spend_amount else None,
            "next_step": next_step,
            "signoff": signoff,
        },
        **llm,
    }


# ── REQUEST_DATE_CONFIRMATION — RESP-063 deterministic path ───────────────────


def _extract_clarification_questions(record: dict) -> list[str]:
    """Extract clarification questions from the fixture record's draft_prompt_variables."""
    prep = record["target_extraction"]["response_preparation_target"]
    base_vars = prep.get("draft_prompt_variables", {})
    clarif_line = base_vars.get("clarification_questions_line", "")
    if not clarif_line:
        return []
    questions = []
    for line in clarif_line.splitlines():
        stripped = line.lstrip("- ").strip()
        if stripped and not stripped.startswith("Clarification question"):
            questions.append(stripped)
    return questions


def _build_rdtc_deterministic(record: dict, idx: int, total: int) -> dict:
    """RESP-063/RESP-073: Build REQUEST_DATE_CONFIRMATION deterministically — no LLM call.

    RESP-073: leads with 'We have availability for {meal_period} on {assumed_date}
    — I just wanted to confirm that's the date you had in mind and not {alternative_date}?'
    when both assumed_date and alternative_date are present in date_context.
    """
    prep = record["target_extraction"]["response_preparation_target"]
    base_vars = prep.get("draft_prompt_variables", {})
    persona_name = base_vars.get("persona_name", "Eleanor")
    guest_first_name = base_vars.get("guest_first_name", "there")
    meal_period = _extract_meal_period(record)

    date_ctx = prep.get("date_context", {})
    assumed_date = date_ctx.get("assumed_date") or _extract_event_date(record)
    alternative_date = date_ctx.get("alternative_date") or ""

    next_step = FirstResponseCopyLibrary.render_safe(BLOCK_RDTC_NEXT_STEP)
    signoff = FirstResponseCopyLibrary.render_safe(BLOCK_SIGNOFF, {"persona_name": persona_name})
    clarification_questions = _extract_clarification_questions(record)

    if assumed_date and alternative_date:
        # RESP-073: clean single-sentence opener with both dates
        opening = FirstResponseCopyLibrary.render_safe(
            BLOCK_RDTC_AVAILABLE_OPENER,
            {"meal_period": meal_period, "assumed_date": assumed_date, "alternative_date": alternative_date},
        )
        body_parts = [
            f"Dear {guest_first_name},",
            "",
            opening or "",
            "",
            next_step or "",
            "",
            signoff or "",
        ]
    else:
        # Fallback: no alternative_date — use clarification question from fixture
        if clarification_questions:
            date_question = _strip_provisional_sentences(clarification_questions[0])
            if not date_question:
                date_question = "Could you please confirm which date you mean?"
        else:
            date_question = "Could you please confirm which date you mean?"
        body_parts = [
            f"Dear {guest_first_name},",
            "",
            "Thank you for your enquiry.",
            "",
            date_question,
            "",
            next_step or "",
            "",
            signoff or "",
        ]
        opening = None

    path_label = "det/RDTC"
    print(f"  [{idx:3d}/{total}] [{path_label}] {record['id']} ... done (deterministic)")
    draft = "\n".join(body_parts)

    return {
        "generation_path": "deterministic",
        "approved_copy_blocks": {
            "opening": opening,
            "next_step": next_step,
            "signoff": signoff,
        },
        "clarification_questions": clarification_questions,
        "clarification_questions_line": base_vars.get("clarification_questions_line", ""),
        "response": draft,
        "input_tokens": 0,
        "output_tokens": 0,
    }


# ── REQUEST_MISSING_INFORMATION ───────────────────────────────────────────────


def _build_rmi_llm(record: dict, idx: int, total: int) -> dict:
    prep = record["target_extraction"]["response_preparation_target"]
    base_vars = deepcopy(prep.get("draft_prompt_variables", {}))
    persona_name = base_vars.get("persona_name", "Eleanor")
    meal_period = _extract_meal_period(record)
    event_date = _extract_event_date(record)

    blocks: list[str] = ["APPROVED COPY BLOCKS — use these verbatim:\n"]
    opening = FirstResponseCopyLibrary.render_safe(
        BLOCK_AVAILABILITY_NOT_CHECKED, {"meal_period": meal_period, "event_date": event_date}
    )
    if opening:
        blocks.append(f"[Opening]\n{opening}\n\n")
    next_step = FirstResponseCopyLibrary.render_safe(BLOCK_CLARIFICATION_NEXT_STEP)
    if next_step:
        blocks.append(f"[Next step]\n{next_step}\n\n")
    signoff = FirstResponseCopyLibrary.render_safe(BLOCK_SIGNOFF, {"persona_name": persona_name})
    if signoff:
        blocks.append(f"[Sign-off]\n{signoff}\n\n")
    blocks.append("You MUST use the approved blocks above verbatim. Do not paraphrase or replace them.\n")

    clarif_line = base_vars.get("clarification_questions_line", "")
    clarification_questions = _extract_clarification_questions({"target_extraction": record["target_extraction"]})
    prompt_vars = {
        "persona_system_prompt": base_vars.get("persona_system_prompt", ""),
        "persona_name": persona_name,
        "restaurant_name": base_vars.get("restaurant_name", ""),
        "persona_tone": base_vars.get("persona_tone", ""),
        "persona_style": base_vars.get("persona_style", ""),
        "response_goal": "REQUEST_MISSING_INFORMATION",
        "guest_first_name": base_vars.get("guest_first_name", ""),
        "guest_last_name": base_vars.get("guest_last_name", ""),
        "audience_type_line": base_vars.get("audience_type_line", ""),
        "event_type_line": base_vars.get("event_type_line", ""),
        "event_date_line": base_vars.get("event_date_line", ""),
        "party_size_line": base_vars.get("party_size_line", ""),
        "room_lines": base_vars.get("room_lines", ""),
        "availability_line": base_vars.get("availability_line", ""),
        "spend_line": "",
        "guest_message_line": "",
        "confirmed_venue_facts_line": "",
        "requested_preferences_line": "",
        "prohibited_claims_line": "",
        "clarification_questions_line": clarif_line,
        "phrase_guidance_line": "",
        "allowed_sections_line": "",
        "forbidden_topics_line": "",
        "approved_copy_blocks_line": "".join(blocks),
    }

    llm = _call_llm("REQUEST_MISSING_INFORMATION", prompt_vars, record["id"], idx, total)
    return {
        "generation_path": "llm",
        "approved_copy_blocks": {"opening": opening, "next_step": next_step, "signoff": signoff},
        "clarification_questions": clarification_questions,
        "clarification_questions_line": clarif_line,
        **llm,
    }


# ── Safety checks ─────────────────────────────────────────────────────────────


def _safety_checks(draft: str, goal: str, record: dict) -> dict:
    issues: list[str] = []

    # Subject-line leakage
    if _SUBJECT_LINE_RE.search(draft):
        issues.append("subject_line_leakage")

    # Forbidden topics
    lower = draft.lower()
    for topic in _FORBIDDEN_TOPICS:
        if topic in lower:
            issues.append(f"forbidden_topic:{topic}")

    # Invented room names (only when known_room_names provided)
    known_rooms: list[str] = record.get("known_room_names", [])
    if known_rooms:
        known_lower = {r.lower() for r in known_rooms}
        for m in _ROOM_NAME_RE.finditer(draft):
            if m.group(0).lower() not in known_lower:
                issues.append(f"invented_room:{m.group(0)}")

    # Availability overclaim in non-CONFIRM goals
    # RESP-073: REQUEST_DATE_CONFIRMATION is exempt for "have availability" —
    # the rdtc_available_opener copy block intentionally states provisional
    # availability for the assumed date before asking for date confirmation.
    if goal != "CONFIRM_AVAILABLE":
        for phrase in ("is available", "are available", "have availability", "confirmed available"):
            if phrase in lower:
                if phrase == "have availability" and goal == "REQUEST_DATE_CONFIRMATION":
                    continue  # RESP-073: approved RDTC opener phrase
                issues.append(f"availability_overclaim:{phrase}")

    # ACKNOWLEDGE room pre-commitment
    if goal in ("REQUEST_DATE_CONFIRMATION", "REQUEST_MISSING_INFORMATION"):
        for phrase in ("would be ideal", "perfect for your group", "recommended room",
                       "suitable room", "can accommodate", "seats up to"):
            if phrase in lower:
                issues.append(f"room_precommitment:{phrase}")

    return {
        "issues": issues,
        "issue_count": len(issues),
        "has_issues": len(issues) > 0,
    }


def _run_compliance(
    draft: str,
    goal: str,
    availability_contract: str,
    clarification_questions: list[str] | None = None,
) -> dict:
    ctx = ValidationContext(
        availability_contract=availability_contract,
        response_goal=goal,
        clarification_questions=clarification_questions or [],
    )
    result = DraftComplianceValidator.validate(draft, ctx)
    return {
        "passed": result.passed,
        "violations": result.violations,
    }


def _run_auto_send_gate(goal: str, compliance_passed: bool, violations: list[str]) -> dict:
    from app.modules.ai.draft_compliance_validator import ComplianceResult
    compliance = ComplianceResult(
        passed=compliance_passed,
        violations=violations,
        unsafe_to_send=not compliance_passed,
    )
    integrity = IntegrityCheckResult(passed=True)
    # HOTFIX-007: RDTC carries pending_date_confirmation — matches service.py pipeline
    date_status = "pending_date_confirmation" if goal == "REQUEST_DATE_CONFIRMATION" else "resolved"
    result = AutoSendReadinessGate.evaluate(
        response_goal=goal,
        draft_compliance_result=compliance,
        date_status=date_status,
        integrity_result=integrity,
        review_required_policy_questions=None,
    )
    return result.to_dict()


# ── Process one record ────────────────────────────────────────────────────────


def _process_record(record: dict, idx: int, total: int) -> dict:
    record_id = record["id"]
    goal = _goal_from_record(record)
    prep = record["target_extraction"]["response_preparation_target"]
    av_status = prep.get("availability_decision", {}).get("availability_status", "")
    availability_contract = {
        "AVAILABLE": "CONFIRMED_AVAILABLE",
        "UNAVAILABLE": "CONFIRMED_UNAVAILABLE",
        "PENDING_DATE_CONFIRMATION": "PENDING_DATE_CONFIRMATION",
        "INSUFFICIENT_INFORMATION": "INSUFFICIENT_INFORMATION",
    }.get(av_status, "NOT_CHECKED")

    # Generate
    gen_info: dict = {}
    if goal == "CONFIRM_AVAILABLE":
        gen_info = _build_confirm_available(record, idx, total)
    elif goal == "REQUEST_DATE_CONFIRMATION":
        gen_info = _build_rdtc_deterministic(record, idx, total)
    else:
        gen_info = _build_rmi_llm(record, idx, total)

    draft = gen_info.get("response", "")
    # Mirror live pipeline: apply DraftPostProcessor before validation
    # (strips subject lines, section labels — same as service.py)
    if gen_info.get("generation_path") == "llm":
        draft = DraftPostProcessor.process(draft).cleaned_body
    clarification_questions: list[str] = gen_info.get("clarification_questions") or []

    # Checks
    safety = _safety_checks(draft, goal, record)
    compliance = _run_compliance(draft, goal, availability_contract, clarification_questions)
    auto_send = _run_auto_send_gate(goal, compliance["passed"], compliance["violations"])

    return {
        "record_id": record_id,
        "subject": record.get("subject", ""),
        "body_preview": record.get("body", "")[:120],
        "response_goal": goal,
        "availability_status": av_status,
        "generation_path": gen_info.get("generation_path"),
        "prompt_version": _defn.version,
        "llm_model": DEFAULT_DRAFT_MODEL,
        "input_tokens": gen_info.get("input_tokens", 0),
        "output_tokens": gen_info.get("output_tokens", 0),
        "approved_copy_blocks": gen_info.get("approved_copy_blocks"),
        "clarification_questions_line": gen_info.get("clarification_questions_line", ""),
        "response": draft,
        "safety_checks": safety,
        "compliance": compliance,
        "auto_send": auto_send,
    }


# ── Summary ───────────────────────────────────────────────────────────────────


def _print_summary(results: list[dict]) -> None:
    total = len(results)
    goals: dict[str, int] = {}
    compliance_pass = 0
    auto_send_allowed = 0
    safety_issues = 0

    for r in results:
        g = r["response_goal"]
        goals[g] = goals.get(g, 0) + 1
        if r["compliance"]["passed"]:
            compliance_pass += 1
        if r["auto_send"]["auto_send_allowed"]:
            auto_send_allowed += 1
        if r["safety_checks"]["has_issues"]:
            safety_issues += 1

    sep = "=" * 70
    print(f"\n{sep}")
    print("RESPONSE PREPARATION TEST — 100 records")
    print(sep)
    print(f"\nGoal breakdown:")
    for g, n in sorted(goals.items()):
        print(f"  {g:<45}: {n:>3}")
    print(f"\nCompliance pass rate  : {compliance_pass}/{total} ({compliance_pass/total*100:.1f}%)")
    print(f"Auto-send allowed     : {auto_send_allowed}/{total} ({auto_send_allowed/total*100:.1f}%)")
    print(f"Safety issues found   : {safety_issues}/{total}")
    print(sep)


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    print(f"Loading fixture: {_FIXTURE_PATH}")
    if not _FIXTURE_PATH.exists():
        print(f"ERROR: Fixture not found at {_FIXTURE_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(_FIXTURE_PATH) as f:
        fixture = json.load(f)

    records = fixture["records"]
    total = len(records)
    print(f"Records: {total}  |  Model: {DEFAULT_DRAFT_MODEL}, temperature: {_DRAFT_TEMPERATURE}")
    print("-" * 70)

    results: list[dict] = []
    for idx, record in enumerate(records, start=1):
        result = _process_record(record, idx, total)
        results.append(result)

    run_id = uuid.uuid4().hex[:8]
    output = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fixture": _FIXTURE_PATH.name,
        "total_records": total,
        "prompt_version": _defn.version,
        "llm_model": DEFAULT_DRAFT_MODEL,
        "results": results,
    }

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {_OUTPUT_PATH}")
    _print_summary(results)


if __name__ == "__main__":
    main()
