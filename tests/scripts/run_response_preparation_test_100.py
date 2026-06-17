#!/usr/bin/env python3
"""Response Preparation Test — 100 records from freeform_group_booking_response_preparation_test_100.json.

Routes each record by availability_decision.availability_status:
  - AVAILABLE                 → CONFIRM_AVAILABLE        (LLM warmth + copy blocks)
  - PENDING_DATE_CONFIRMATION → REQUEST_DATE_CONFIRMATION (LLM + clarification question)
  - INSUFFICIENT_INFORMATION  → REQUEST_MISSING_INFORMATION (LLM + clarification questions)
  - UNAVAILABLE               → RESPOND_UNAVAILABLE      (deterministic copy blocks)

TEST-023: Also reports persona-fit scoring as an additional evaluation layer.
Persona-fit measures whether the tone of the draft matches the audience type.
This layer is reported separately and does not affect compliance or auto-send scores.

RESP-078: CONFIRM_AVAILABLE warmth instruction is now audience-conditional.
Corporate/agency: no warmth sentence permitted.
Luxury: refined, understated warmth only.
Social: celebratory warmth (unchanged).
Unknown: neutral professional warmth.

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
from app.modules.ai.audience_tone_validator import AudienceToneValidator
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

# ── Persona-fit patterns (TEST-023) ───────────────────────────────────────────
# Mirror the forbidden phrase sets from AudienceToneValidator (RESP-075) so
# that the test runner can detect corporate tone degradation without importing
# the production validator (which lives in the API service tree).

_PERSONA_CORPORATE_AGENCY_FORBIDDEN: list[tuple[str, re.Pattern[str]]] = [
    ("how wonderful",              re.compile(r"\bhow\s+wonderful\b",               re.IGNORECASE)),
    ("how lovely",                 re.compile(r"\bhow\s+lovely\b",                  re.IGNORECASE)),
    ("how exciting",               re.compile(r"\bhow\s+exciting\b",                re.IGNORECASE)),
    ("how delightful",             re.compile(r"\bhow\s+delightful\b",              re.IGNORECASE)),
    ("what a lovely occasion",     re.compile(r"\bwhat\s+a\s+lovely\s+occasion\b",  re.IGNORECASE)),
    ("what a wonderful",           re.compile(r"\bwhat\s+a\s+wonderful\b",          re.IGNORECASE)),
    ("such a special occasion",    re.compile(r"\bsuch\s+a\s+special\s+occasion\b", re.IGNORECASE)),
    ("such a meaningful occasion", re.compile(r"\bsuch\s+a\s+meaningful\s+occasion\b", re.IGNORECASE)),
    ("celebration with us",        re.compile(r"\bcelebration\s+with\s+us\b",       re.IGNORECASE)),
    ("will be special",            re.compile(r"\bwill\s+be\s+special\b",           re.IGNORECASE)),
    ("delighted to celebrate",     re.compile(r"\bdelighted\s+to\s+celebrate\b",    re.IGNORECASE)),
    ("thrilled",                   re.compile(r"\bthrilled\b",                      re.IGNORECASE)),
]

_PERSONA_LUXURY_FORBIDDEN: list[tuple[str, re.Pattern[str]]] = [
    ("amazing",      re.compile(r"\bamazing\b",   re.IGNORECASE)),
    ("fantastic",    re.compile(r"\bfantastic\b", re.IGNORECASE)),
    ("brilliant",    re.compile(r"\bbrilliant\b", re.IGNORECASE)),
    ("super",        re.compile(r"\bsuper\b",     re.IGNORECASE)),
    ("totally",      re.compile(r"\btotally\b",   re.IGNORECASE)),
    ("can't wait",   re.compile(r"can'?t\s+wait", re.IGNORECASE)),
    ("how exciting", re.compile(r"\bhow\s+exciting\b", re.IGNORECASE)),
]

_PERSONA_TONE_RULES: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    "corporate": _PERSONA_CORPORATE_AGENCY_FORBIDDEN,
    "agency":    _PERSONA_CORPORATE_AGENCY_FORBIDDEN,
    "luxury":    _PERSONA_LUXURY_FORBIDDEN,
    "social":    [],
    "unknown":   [],
}

# Opener-tone classification patterns (first non-blank, non-greeting line)
_OPENER_WARM_CELEBRATORY = re.compile(
    r"^(how wonderful|how lovely|how exciting|how delightful|"
    r"what a lovely|what a wonderful|that sounds wonderful|"
    r"that sounds like a lovely|that sounds like a wonderful)",
    re.IGNORECASE,
)
_OPENER_REFINED = re.compile(
    r"^(it would be a pleasure|we look forward to hosting|"
    r"we are honoured|we would be honoured)",
    re.IGNORECASE,
)
_OPENER_PROFESSIONAL = re.compile(
    r"^(we would be (delighted|pleased)|we are pleased|we look forward|"
    r"we can confirm|i'm pleased to confirm|i am pleased to confirm|"
    r"thank you for your enquiry)",
    re.IGNORECASE,
)

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

# RESP-078: shared room-suitability forbidden phrase suffix used by all warmth instructions.
_WARMTH_FORBIDDEN_ROOM = (
    "Forbidden phrases: 'excellent choice', 'perfect for', 'perfect setting', "
    "'ideal', 'ideal for', 'ideal setting', 'well accommodated', 'excellent fit', "
    "'intimate setting', 'excellent setting', 'would be ideal', 'ideally suited'. "
    "Do not paraphrase, shorten, or replace approved blocks.\n"
)


def _warmth_instruction_for_audience(audience_type: str) -> str:
    """Return the warmth-sentence instruction appropriate for the given audience type.

    RESP-078: Audience-conditional instruction replaces the previous hardcoded
    social-warmth-first instruction. Matches the audience-specific system prompts
    in generate_warmth_sentence() (RESP-076) and the forbidden-phrase sets in
    AudienceToneValidator (RESP-075).
    """
    aud = (audience_type or "unknown").lower()
    if aud == "social":
        return (
            "You MUST use all the approved blocks above verbatim. "
            "You may add ONE warmth sentence before the Opening block only — "
            "it must acknowledge the occasion or guest context, not describe the venue. "
            "CRITICAL: Do NOT start the warmth sentence with 'Thank you', 'Thanks', or any "
            "acknowledgement phrase — the email already says thank you elsewhere. "
            "Use a celebratory opener instead, such as: "
            "'How wonderful —', 'How lovely —', 'How exciting —', "
            "'What a lovely occasion —', 'That sounds wonderful —'. "
            "Do NOT add any sentence about the room, space, or venue suitability. "
            + _WARMTH_FORBIDDEN_ROOM
        )
    if aud in ("corporate", "agency"):
        return (
            "You MUST use all the approved blocks above verbatim. "
            "Do NOT add a warmth sentence before the Opening block. "
            "This is a professional booking — start the email body directly with the Opening block. "
            "FORBIDDEN openers: Do not write 'How wonderful', 'How lovely', 'How exciting', "
            "'How delightful', 'What a lovely occasion', 'What a wonderful', "
            "'such a special occasion', 'celebration with us', 'thrilled', "
            "'delighted to celebrate', or any celebratory opener. "
            "Do NOT add any sentence about the room, space, or venue suitability. "
            + _WARMTH_FORBIDDEN_ROOM
        )
    if aud == "luxury":
        return (
            "You MUST use all the approved blocks above verbatim. "
            "You may add ONE warmth sentence before the Opening block only — "
            "it must be refined, understated, and gracious. "
            "CRITICAL: Do NOT start the warmth sentence with 'Thank you', 'Thanks', or any "
            "acknowledgement phrase — the email already says thank you elsewhere. "
            "Use refined openers such as: "
            "'It would be a pleasure to welcome your guests —', "
            "'We look forward to hosting your private dinner —', "
            "'We would be honoured to accommodate your guests on this occasion —'. "
            "FORBIDDEN casual words: 'amazing', 'fantastic', 'brilliant', 'super', 'totally', "
            "\"can't wait\", 'how exciting'. "
            "Do NOT add any sentence about the room, space, or venue suitability. "
            + _WARMTH_FORBIDDEN_ROOM
        )
    # unknown / fallback: neutral professional tone
    return (
        "You MUST use all the approved blocks above verbatim. "
        "You may add ONE warmth sentence before the Opening block only — "
        "it must be courteous and professional. "
        "CRITICAL: Do NOT start the warmth sentence with 'Thank you', 'Thanks', or any "
        "acknowledgement phrase — the email already says thank you elsewhere. "
        "Use neutral professional openers such as: "
        "'We would be pleased to assist with your event —', "
        "'We look forward to welcoming your guests —'. "
        "Do NOT add any sentence about the room, space, or venue suitability. "
        + _WARMTH_FORBIDDEN_ROOM
    )


def _build_confirm_available(record: dict, idx: int, total: int) -> dict:
    prep = record["target_extraction"]["response_preparation_target"]
    base_vars = deepcopy(prep.get("draft_prompt_variables", {}))
    persona_name = base_vars.get("persona_name", "Eleanor")
    spend_amount = _extract_spend_amount(record)
    meal_period = _extract_meal_period(record)
    event_date = _extract_event_date(record)
    # RESP-078: extract audience type to select the correct warmth instruction
    audience_type = _extract_audience_type(record)

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
    # RESP-078: audience-conditional warmth instruction replaces hardcoded social-warmth-first
    blocks.append(_warmth_instruction_for_audience(audience_type))

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


def _run_auto_send_gate(
    goal: str,
    compliance_passed: bool,
    violations: list[str],
    tone_validation_result=None,
) -> dict:
    from app.modules.ai.draft_compliance_validator import ComplianceResult
    compliance = ComplianceResult(
        passed=compliance_passed,
        violations=violations,
        unsafe_to_send=not compliance_passed,
    )
    integrity = IntegrityCheckResult(passed=True)
    # HOTFIX-007: RDTC carries pending_date_confirmation — matches service.py pipeline
    date_status = "pending_date_confirmation" if goal == "REQUEST_DATE_CONFIRMATION" else "resolved"
    # RESP-079: tone_validation_result wires Rule 7 — None skips the check (backwards-compatible)
    result = AutoSendReadinessGate.evaluate(
        response_goal=goal,
        draft_compliance_result=compliance,
        date_status=date_status,
        integrity_result=integrity,
        review_required_policy_questions=None,
        tone_validation_result=tone_validation_result,
    )
    return result.to_dict()


# ── Persona-fit scoring (TEST-023) ────────────────────────────────────────────


def _extract_audience_type(record: dict) -> str:
    """Extract normalised audience_type from the fixture record."""
    dpv = (
        record.get("target_extraction", {})
        .get("response_preparation_target", {})
        .get("draft_prompt_variables", {})
    )
    aud_line = dpv.get("audience_type_line", "")
    m = re.search(r"Audience\s+type:\s*(\w+)", aud_line, re.IGNORECASE)
    return m.group(1).lower() if m else "unknown"


def _classify_opener_tone(draft: str) -> str:
    """Return the tone category of the first meaningful sentence in the draft.

    Categories: warm_celebratory | refined | professional | neutral
    """
    for line in draft.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("dear ") or line.lower().startswith("subject:"):
            continue
        if _OPENER_WARM_CELEBRATORY.match(line):
            return "warm_celebratory"
        if _OPENER_REFINED.match(line):
            return "refined"
        if _OPENER_PROFESSIONAL.match(line):
            return "professional"
        return "neutral"
    return "neutral"


def _run_persona_fit(draft: str, audience_type: str) -> dict:
    """Deterministic persona-fit check — no LLM calls.

    Checks the draft against audience-appropriate forbidden phrase patterns.
    Returns a dict with persona_fit_passed, persona_fit_score,
    persona_fit_violations, opener_tone_category, and forbidden_phrase_hits.
    """
    patterns = _PERSONA_TONE_RULES.get(audience_type, [])
    violations: list[str] = []
    hits: list[str] = []

    for label, pattern in patterns:
        if pattern.search(draft):
            violations.append(f"persona_tone_violation: {audience_type} — '{label}' detected")
            hits.append(label)

    passed = len(violations) == 0
    score = 1.0 if passed else round(max(0.0, 1.0 - 0.25 * len(violations)), 2)
    opener_tone = _classify_opener_tone(draft)

    return {
        "audience_type": audience_type,
        "persona_fit_passed": passed,
        "persona_fit_score": score,
        "persona_fit_violations": violations,
        "opener_tone_category": opener_tone,
        "forbidden_phrase_hits": hits,
    }


# ── Independent 12-layer evaluation (TEST-030) ────────────────────────────────


def _tone_matches_expected(actual_tone: str, expected_aud: str) -> bool:
    """Return True if opener tone is appropriate for the expected audience type.

    Corporate/agency/luxury: warm_celebratory is forbidden.
    Social/unknown: any tone is acceptable.
    """
    if expected_aud in ("corporate", "agency", "luxury"):
        return actual_tone != "warm_celebratory"
    return True  # social, unknown


_SUITABILITY_CLAIMS = [
    "ideal for", "perfect for", "ideal setting", "excellent choice",
    "perfect setting", "well accommodated", "excellent fit",
    "intimate setting", "excellent setting", "would be ideal", "ideally suited",
]

_CLARIFICATION_TRIGGERS = [
    "could you let us know", "would you be able to confirm", "could you confirm if",
    "could you also let us know", "please let us know if",
]


def _run_independent_evaluation(result: dict, record: dict) -> dict:
    """TEST-030: 12-layer independent evaluation against fixture expected values.

    Compares actual output against oracle expected_* values in the fixture.
    Does NOT trust the pipeline's own metadata as proof of correctness.

    Layers:
      L1  Extraction correctness
      L2  Audience classification correctness
      L3  Response goal correctness
      L4  Date handling correctness
      L5  Availability workflow (compliance)
      L6  Tone/persona fit against expected audience
      L7  Factual accuracy (safety checks)
      L8  Hallucination risk (suitability claims)
      L9  Information utilisation (required fields in response)
      L10 Auto-send reviewer agreement
      L11 Commercial quality (unnecessary friction)
      L12 Regression risk (forbidden phrases for expected audience)
    """
    expected_aud = record.get("expected_audience_type", "unknown")
    expected_goal = record.get("expected_response_goal", "")
    expected_date_status = record.get("expected_date_status", "resolved")
    expected_meal_period = record.get("expected_meal_period", "dinner")
    expected_auto_send = record.get("expected_auto_send_allowed", True)
    expected_req_fields = record.get("expected_required_fields_used", [])
    expected_forbidden = record.get("expected_forbidden_phrases", [])

    draft = result.get("response", "")
    draft_lower = draft.lower()
    actual_aud = result["persona_fit"]["audience_type"]
    actual_goal = result["response_goal"]
    actual_auto_send = result["auto_send"]["auto_send_allowed"]
    actual_tone_cat = result["persona_fit"]["opener_tone_category"]
    actual_meal_period = record["target_extraction"].get("meal_period") or "dinner"

    # L1: Extraction correctness
    l1_pass = actual_meal_period == expected_meal_period
    l1 = {"passed": l1_pass, "expected_meal_period": expected_meal_period,
          "actual_meal_period": actual_meal_period}

    # L2: Audience classification correctness
    l2_pass = actual_aud == expected_aud
    l2 = {"passed": l2_pass, "expected": expected_aud, "actual": actual_aud}

    # L3: Response goal correctness
    l3_pass = actual_goal == expected_goal
    l3 = {"passed": l3_pass, "expected": expected_goal, "actual": actual_goal}

    # L4: Date handling correctness
    _date_status_map = {
        "REQUEST_DATE_CONFIRMATION": "pending_date_confirmation",
        "REQUEST_MISSING_INFORMATION": "insufficient_information",
        "RESPOND_UNAVAILABLE": "resolved",
    }
    actual_date_status = _date_status_map.get(actual_goal, "resolved")
    l4_pass = actual_date_status == expected_date_status
    l4 = {"passed": l4_pass, "expected": expected_date_status, "actual": actual_date_status}

    # L5: Availability workflow (compliance)
    l5_pass = result["compliance"]["passed"]
    l5 = {"passed": l5_pass, "violations": result["compliance"]["violations"]}

    # L6: Tone/persona fit against EXPECTED audience (not actual)
    l6_pass = _tone_matches_expected(actual_tone_cat, expected_aud)
    l6 = {"passed": l6_pass, "expected_audience": expected_aud,
          "actual_tone_category": actual_tone_cat}

    # L7: Factual accuracy (safety checks)
    l7_pass = not result["safety_checks"]["has_issues"]
    l7 = {"passed": l7_pass, "issues": result["safety_checks"]["issues"]}

    # L8: Hallucination risk (unsupported suitability claims)
    hallu_hits = [p for p in _SUITABILITY_CLAIMS if p in draft_lower]
    l8_pass = len(hallu_hits) == 0
    l8 = {"passed": l8_pass, "suitability_claims": hallu_hits}

    # L9: Information utilisation (required fields present in response)
    l9_failures: list[str] = []
    for field_spec in expected_req_fields:
        if ":" in field_spec:
            kind, value = field_spec.split(":", 1)
            if kind == "event_date" and value not in draft:
                l9_failures.append(f"event_date {value} missing from response")
            elif kind == "minimum_spend":
                amount = value.replace("£", "").replace(",", "")
                if amount not in draft and value not in draft:
                    l9_failures.append(f"spend {value} missing from response")
    l9_pass = len(l9_failures) == 0
    l9 = {"passed": l9_pass, "missing_fields": l9_failures}

    # L10: Auto-send reviewer agreement
    # A reviewer would block auto-send if classification, tone, or compliance fails.
    reviewer_blocks: list[str] = []
    if not l2_pass:
        reviewer_blocks.append("audience_misclassification")
    if not l6_pass:
        reviewer_blocks.append("inappropriate_tone")
    if not l5_pass:
        reviewer_blocks.append("compliance_failure")
    reviewer_would_send = actual_auto_send and len(reviewer_blocks) == 0
    l10_pass = reviewer_would_send == expected_auto_send
    l10 = {"passed": l10_pass, "expected_auto_send": expected_auto_send,
           "gate_auto_send": actual_auto_send, "reviewer_would_send": reviewer_would_send,
           "reviewer_blocks": reviewer_blocks}

    # L11: Commercial quality (unnecessary clarification in CONFIRM_AVAILABLE)
    l11_issues: list[str] = []
    if actual_goal == "CONFIRM_AVAILABLE":
        for phrase in _CLARIFICATION_TRIGGERS:
            if phrase in draft_lower:
                l11_issues.append(f'unnecessary_clarification: "{phrase}"')
    l11_pass = len(l11_issues) == 0
    l11 = {"passed": l11_pass, "issues": l11_issues}

    # L12: Regression risk (forbidden phrases for expected audience)
    l12_hits = [p for p in expected_forbidden if p in draft_lower]
    l12_pass = len(l12_hits) == 0
    l12 = {"passed": l12_pass, "forbidden_phrase_hits": l12_hits,
           "expected_audience": expected_aud}

    layers = {
        "L1_extraction": l1,
        "L2_audience_classification": l2,
        "L3_response_goal": l3,
        "L4_date_handling": l4,
        "L5_availability_workflow": l5,
        "L6_persona_fit": l6,
        "L7_factual_accuracy": l7,
        "L8_hallucination_risk": l8,
        "L9_information_utilisation": l9,
        "L10_auto_send_readiness": l10,
        "L11_commercial_quality": l11,
        "L12_regression_risk": l12,
    }

    _critical = {
        "L2_audience_classification", "L3_response_goal", "L5_availability_workflow",
        "L6_persona_fit", "L8_hallucination_risk", "L12_regression_risk",
    }
    critical_failures = [k for k, v in layers.items() if not v["passed"] and k in _critical]
    all_pass = all(v["passed"] for v in layers.values())

    return {
        "layers": layers,
        "all_layers_passed": all_pass,
        "critical_failures": critical_failures,
        "layer_pass_count": sum(1 for v in layers.values() if v["passed"]),
        "layer_total": len(layers),
    }


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

    # TEST-023: persona-fit scoring (additional layer — does not affect compliance/auto-send)
    audience_type = _extract_audience_type(record)
    persona_fit = _run_persona_fit(draft, audience_type)

    # RESP-079: tone validation for CONFIRM_AVAILABLE — result wires Rule 7 in the auto-send gate.
    # None for other goals: Rule 7 skips the check (backwards-compatible per RESP-077 design).
    tone_result = None
    if goal == "CONFIRM_AVAILABLE":
        tone_result = AudienceToneValidator.validate(draft, audience_type)

    auto_send = _run_auto_send_gate(
        goal,
        compliance["passed"],
        compliance["violations"],
        tone_validation_result=tone_result,
    )

    partial_result = {
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
        "tone_validation": {
            "passed": tone_result.passed,
            "audience_type": tone_result.audience_type,
            "violations": tone_result.violations,
        } if tone_result is not None else None,
        "persona_fit": persona_fit,
    }

    # TEST-030: 12-layer independent evaluation against fixture expected values
    independent_eval = _run_independent_evaluation(partial_result, record)
    return {**partial_result, "independent_evaluation": independent_eval}


# ── Summary ───────────────────────────────────────────────────────────────────


def _print_summary(results: list[dict]) -> None:
    total = len(results)
    goals: dict[str, int] = {}
    compliance_pass = 0
    auto_send_allowed = 0
    safety_issues = 0
    persona_fit_pass = 0
    persona_fit_failures: list[dict] = []
    tone_category_counts: dict[str, int] = {}

    for r in results:
        g = r["response_goal"]
        goals[g] = goals.get(g, 0) + 1
        if r["compliance"]["passed"]:
            compliance_pass += 1
        if r["auto_send"]["auto_send_allowed"]:
            auto_send_allowed += 1
        if r["safety_checks"]["has_issues"]:
            safety_issues += 1

        pf = r.get("persona_fit", {})
        if pf.get("persona_fit_passed", True):
            persona_fit_pass += 1
        else:
            persona_fit_failures.append({
                "record_id": r["record_id"],
                "audience_type": pf.get("audience_type"),
                "violations": pf.get("persona_fit_violations", []),
                "forbidden_phrase_hits": pf.get("forbidden_phrase_hits", []),
                "opener_tone_category": pf.get("opener_tone_category"),
            })
        cat = pf.get("opener_tone_category", "neutral")
        tone_category_counts[cat] = tone_category_counts.get(cat, 0) + 1

    # Per-audience persona-fit breakdown (TEST-025)
    audience_pf: dict[str, dict[str, int]] = {}
    for r in results:
        pf = r.get("persona_fit", {})
        aud = pf.get("audience_type") or "unknown"
        if aud not in audience_pf:
            audience_pf[aud] = {"pass": 0, "fail": 0}
        if pf.get("persona_fit_passed", True):
            audience_pf[aud]["pass"] += 1
        else:
            audience_pf[aud]["fail"] += 1

    # TEST-030: aggregate 12-layer independent evaluation
    layer_names = [
        "L1_extraction", "L2_audience_classification", "L3_response_goal",
        "L4_date_handling", "L5_availability_workflow", "L6_persona_fit",
        "L7_factual_accuracy", "L8_hallucination_risk", "L9_information_utilisation",
        "L10_auto_send_readiness", "L11_commercial_quality", "L12_regression_risk",
    ]
    layer_pass_counts: dict[str, int] = {ln: 0 for ln in layer_names}
    layer_failures: dict[str, list[dict]] = {ln: [] for ln in layer_names}
    records_all_layers_pass = 0
    records_with_critical_failures = 0
    all_critical_failures: list[dict] = []

    for r in results:
        ie = r.get("independent_evaluation", {})
        layers = ie.get("layers", {})
        if ie.get("all_layers_passed", False):
            records_all_layers_pass += 1
        if ie.get("critical_failures"):
            records_with_critical_failures += 1
            all_critical_failures.append({
                "record_id": r["record_id"],
                "critical_failures": ie["critical_failures"],
            })
        for ln in layer_names:
            ldata = layers.get(ln, {})
            if ldata.get("passed", True):
                layer_pass_counts[ln] += 1
            else:
                layer_failures[ln].append({
                    "record_id": r["record_id"],
                    "detail": ldata,
                })

    sep = "=" * 70
    print(f"\n{sep}")
    print(f"RESPONSE PREPARATION TEST — {total} records")
    print(sep)
    print(f"\nGoal breakdown:")
    for g, n in sorted(goals.items()):
        print(f"  {g:<45}: {n:>3}")

    print(f"\n--- Legacy metrics ---")
    print(f"Compliance pass rate  : {compliance_pass}/{total} ({compliance_pass/total*100:.1f}%)")
    print(f"Auto-send allowed     : {auto_send_allowed}/{total} ({auto_send_allowed/total*100:.1f}%)")
    print(f"Safety issues found   : {safety_issues}/{total}")

    print(f"\n--- Persona-Fit (TEST-023 / TEST-025) ---")
    print(f"Persona-fit pass rate : {persona_fit_pass}/{total} ({persona_fit_pass/total*100:.1f}%)")
    print(f"\nPer-audience persona-fit:")
    for aud in ("social", "corporate", "agency", "luxury", "unknown"):
        counts = audience_pf.get(aud, {"pass": 0, "fail": 0})
        aud_total = counts["pass"] + counts["fail"]
        if aud_total == 0:
            continue
        pct = counts["pass"] / aud_total * 100
        print(f"  {aud:<12}: {counts['pass']}/{aud_total} ({pct:.0f}%)")
    print(f"\nOpener tone distribution:")
    for cat, n in sorted(tone_category_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat:<25}: {n:>3}")
    if persona_fit_failures:
        print(f"\nTop persona-fit failures:")
        for failure in persona_fit_failures[:10]:
            hits_str = ", ".join(f"'{h}'" for h in failure["forbidden_phrase_hits"])
            print(f"  {failure['record_id']:<12} [{failure['audience_type']}]"
                  f" opener={failure['opener_tone_category']}  hits={hits_str}")

    # TEST-030: 12-layer independent evaluation report
    print(f"\n{sep}")
    print(f"12-LAYER INDEPENDENT EVALUATION (TEST-030)")
    print(sep)
    print(f"Records — all 12 layers passed : {records_all_layers_pass}/{total}")
    print(f"Records — critical layer failed: {records_with_critical_failures}/{total}")
    print(f"\nPer-layer pass rates:")
    layer_labels = {
        "L1_extraction":               "L1  Extraction correctness",
        "L2_audience_classification":  "L2  Audience classification",
        "L3_response_goal":            "L3  Response goal correctness",
        "L4_date_handling":            "L4  Date handling correctness",
        "L5_availability_workflow":    "L5  Availability workflow",
        "L6_persona_fit":              "L6  Tone/persona fit (vs expected audience)",
        "L7_factual_accuracy":         "L7  Factual accuracy",
        "L8_hallucination_risk":       "L8  Hallucination risk",
        "L9_information_utilisation":  "L9  Information utilisation",
        "L10_auto_send_readiness":     "L10 Auto-send reviewer agreement",
        "L11_commercial_quality":      "L11 Commercial quality",
        "L12_regression_risk":         "L12 Regression risk",
    }
    _critical_set = {
        "L2_audience_classification", "L3_response_goal", "L5_availability_workflow",
        "L6_persona_fit", "L8_hallucination_risk", "L12_regression_risk",
    }
    for ln in layer_names:
        n_pass = layer_pass_counts[ln]
        n_fail = total - n_pass
        pct = n_pass / total * 100
        crit_tag = " [CRITICAL]" if ln in _critical_set else ""
        fail_tag = f"  ← {n_fail} FAILED" if n_fail > 0 else ""
        print(f"  {layer_labels[ln]:<45}: {n_pass:>3}/{total} ({pct:>5.1f}%){crit_tag}{fail_tag}")

    # Failure tables by layer
    any_failure_printed = False
    for ln in layer_names:
        failures = layer_failures[ln]
        if not failures:
            continue
        if not any_failure_printed:
            print(f"\n--- Failure tables by layer ---")
            any_failure_printed = True
        crit_tag = " [CRITICAL]" if ln in _critical_set else ""
        print(f"\n{layer_labels[ln]}{crit_tag} — {len(failures)} failed:")
        for f in failures[:20]:
            detail = f["detail"]
            exp = detail.get("expected") or detail.get("expected_meal_period", "")
            act = detail.get("actual") or detail.get("actual_meal_period", "") or detail.get("actual_tone_category", "")
            issues = (detail.get("violations") or detail.get("issues") or
                      detail.get("suitability_claims") or detail.get("forbidden_phrase_hits") or
                      detail.get("missing_fields") or detail.get("reviewer_blocks") or [])
            issues_str = f"  [{', '.join(str(i) for i in issues[:3])}]" if issues else ""
            if exp and act:
                print(f"    {f['record_id']:<12}  expected={exp}  actual={act}{issues_str}")
            else:
                print(f"    {f['record_id']:<12}{issues_str}")
        if len(failures) > 20:
            print(f"    ... and {len(failures) - 20} more")

    # Overall verdict
    has_critical = records_with_critical_failures > 0
    all_layers_100pct = all(layer_pass_counts[ln] == total for ln in layer_names)
    print(f"\n--- Overall verdict ---")
    if has_critical:
        print(f"RESULT: CRITICAL FAILURES PRESENT — {records_with_critical_failures} record(s) failed "
              f"one or more critical layers. Do NOT report as 10/10.")
        print(f"Critical failure records:")
        for cf in all_critical_failures[:10]:
            print(f"  {cf['record_id']}: {cf['critical_failures']}")
    elif not all_layers_100pct:
        failed_layers = [ln for ln in layer_names if layer_pass_counts[ln] < total]
        print(f"RESULT: NON-CRITICAL FAILURES — layers with failures: {failed_layers}")
    else:
        print(f"RESULT: ALL 12 LAYERS PASSED — {total}/{total} records fully verified.")

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
