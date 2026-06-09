#!/usr/bin/env python3
"""Process all 100 records from availability_fixture_100.json — Sprint 11 state.

Record routing (Sprint 11 — RESP-037 to RESP-041):
  - availability.is_available == True  → CONFIRM_AVAILABLE  (deterministic + optional warmth LLM)
  - availability.is_available == False → RESPOND_UNAVAILABLE (deterministic — RESP-023)
  - availability is None               → ACKNOWLEDGE_AND_CHECK_AVAILABILITY (deterministic — RESP-036)

Sprint 11 changes vs post-RESP-036:
  RESP-037: confirm_available_next_step copy block (no menu/dietary/special-touches/calls/forms)
  RESP-038: CONFIRM_AVAILABLE is now fully deterministic — LLM only for optional warmth sentence
  RESP-039: LLM warmth sentence is max 1 sentence, max 20 words
  RESP-040: WarmthSentenceValidator — warmth sentence validated; dropped on any violation
  RESP-041: Raw guest message NOT passed to warmth LLM — structured context only

Expected full-LLM calls: 0
Expected warmth-LLM calls: up to 25 (CONFIRM_AVAILABLE records with extractable context)
Expected deterministic calls: 100 (all records)

Metrics reported:
  - llm_warmth_calls:           Number of warmth LLM calls attempted
  - warmth_sentences_accepted:  Warmth sentences that passed WarmthSentenceValidator
  - warmth_sentences_dropped:   Warmth sentences dropped (validation failure)
  - deterministic_calls:        Deterministic records (all 100)
  - menu_discussion_count:      Drafts mentioning menu/food choices
  - special_touches_count:      Drafts mentioning special touches/personalisation
  - booking_form_count:         Drafts containing booking form references or URLs
  - auto_send_eligible_count:   Drafts with no compliance violations (ready-to-send)
  - auto_send_eligibility_rate: auto_send_eligible_count / total

Usage (from project root, with venv active):
    ANTHROPIC_API_KEY=... python tests/scripts/run_draft_llm2_availability_100_sprint11.py

Environment:
    ANTHROPIC_API_KEY  -- required
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

# -- Paths --------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_TESTS_DIR = _SCRIPT_DIR.parent
_REPO_ROOT = _TESTS_DIR.parent
_API_ROOT = _REPO_ROOT / "services" / "api"
_FIXTURE_PATH = _TESTS_DIR / "data" / "availability_fixture_100.json"
_OUTPUT_PATH = _TESTS_DIR / "data" / "draft_llm2_availability_100_sprint11_results.json"

if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

# -- Imports ------------------------------------------------------------------

import anthropic

from app.modules.ai.first_response_copy_library import FirstResponseCopyLibrary
from app.modules.ai.confirm_available_warmth_validator import WarmthSentenceValidator
from app.modules.ai.prompt_registry import PromptRegistry
from app.modules.ai.constants import PROMPT_KEY_DRAFT_RESPONSE, DEFAULT_DRAFT_MODEL

# -- Setup --------------------------------------------------------------------

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    print("ERROR: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
    sys.exit(1)

_registry = PromptRegistry()
_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_defn = _registry.get(PROMPT_KEY_DRAFT_RESPONSE)

# Warmth LLM uses a lightweight Haiku model, not the full draft model
_WARMTH_MODEL = "claude-haiku-4-5-20251001"
_WARMTH_MAX_TOKENS = 60
_WARMTH_TEMPERATURE = 0.4


# -- Warmth sentence generation (RESP-039 / RESP-041) ------------------------


def _generate_warmth_sentence(
    occasion: str | None,
    audience_type: str | None,
    party_size: int | None,
    meal_period: str | None,
) -> str | None:
    """Call LLM for one short warmth sentence only.

    Sends a minimal structured prompt — no raw guest message (RESP-041) — and
    asks the model to produce a single sentence of at most 20 words.

    Returns the raw sentence string, or None on any failure.
    The caller must validate the result (RESP-040).
    """
    context_parts: list[str] = []
    if occasion:
        context_parts.append(f"Occasion: {occasion.replace('_', ' ')}")
    if audience_type:
        context_parts.append(f"Audience type: {audience_type}")
    if party_size:
        context_parts.append(f"Party size: {party_size}")
    if meal_period:
        context_parts.append(f"Meal period: {meal_period}")

    if not context_parts:
        return None

    context_str = "\n".join(context_parts)

    system_prompt = (
        "You are a hospitality events assistant writing one very short sentence "
        "that warmly acknowledges a guest's occasion. "
        "Rules:\n"
        "- Write exactly one sentence.\n"
        "- Maximum 20 words.\n"
        "- Base the sentence only on the provided context fields.\n"
        "- Do NOT mention: menus, dietary requirements, timing, arrival time, "
        "  booking forms, calls, pricing, minimum spend, room names, special touches, "
        "  availability, or any operational detail.\n"
        "- Do NOT use the phrase 'perfect for' or 'ideal for'.\n"
        "- Output only the warmth sentence — no preamble, no quotes."
    )
    user_prompt = (
        f"Write one warm sentence (max 20 words) acknowledging the guest's occasion.\n\n"
        f"{context_str}"
    )

    try:
        response = _client.messages.create(
            model=_WARMTH_MODEL,
            max_tokens=_WARMTH_MAX_TOKENS,
            temperature=_WARMTH_TEMPERATURE,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text.strip()
        return (text, response.usage) if text else (None, response.usage)
    except Exception as exc:  # noqa: BLE001
        print(f"    [warmth LLM error] {exc}", file=sys.stderr)
        return None, None


# -- Deterministic draft builders ---------------------------------------------


def _build_deterministic_confirm_available_draft(
    av: dict,
    record: dict,
    persona_name: str,
    guest_first_name: str,
) -> tuple[str, str, dict | None, dict | None]:
    """Build the CONFIRM_AVAILABLE draft from approved copy blocks + optional warmth.

    Returns (draft_text, generation_path, warmth_usage, warmth_validation_result).

    generation_path is "deterministic+warmth" when warmth sentence is accepted,
    "deterministic" otherwise.
    """
    meal_period = av.get("meal_period", "dinner") or "dinner"
    event_date = av.get("event_date", "the requested date")
    guest_name = guest_first_name or "there"

    opening = FirstResponseCopyLibrary.render(
        "availability_confirmed",
        {"meal_period": meal_period, "event_date": event_date},
    )
    next_step = FirstResponseCopyLibrary.render("confirm_available_next_step")
    signoff = FirstResponseCopyLibrary.render("signoff", {"persona_name": persona_name})

    # RESP-039 / RESP-041: attempt optional warmth LLM sentence
    ext = record["target_extraction"]
    occasion = ext.get("occasion")
    audience_type = ext.get("audience_type") or ext.get("audience_type_from_content")
    party_size = ext.get("guest_count")

    warmth_sentence: str | None = None
    warmth_usage: dict | None = None
    warmth_validation_info: dict | None = None
    generation_path = "deterministic"

    if occasion or audience_type or party_size:
        raw_warmth, usage = _generate_warmth_sentence(
            occasion=occasion,
            audience_type=audience_type,
            party_size=party_size,
            meal_period=meal_period,
        )
        if usage is not None:
            warmth_usage = {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
            }
        if raw_warmth:
            validation = WarmthSentenceValidator.validate(raw_warmth)
            warmth_validation_info = {
                "raw_text": raw_warmth,
                "passed": validation.passed,
                "violation_code": validation.violation_code,
                "violation_msg": validation.violation_msg,
            }
            if validation.passed:
                warmth_sentence = raw_warmth
                generation_path = "deterministic+warmth"

    # Spend block
    prep = ext.get("response_preparation_target", {})
    draft_vars = prep.get("draft_prompt_variables", {})
    spend_line = draft_vars.get("spend_line", "")
    spend_amount = ""
    spend_block = ""
    if spend_line:
        match = re.search(r"[£$]([\d,]+)", spend_line)
        if match:
            spend_amount = match.group(1)
            spend_block = FirstResponseCopyLibrary.render(
                "minimum_spend", {"spend_amount": f"£{spend_amount}"}
            )

    body_parts: list[str] = [f"Dear {guest_name},", "", opening]
    if warmth_sentence:
        body_parts.append(warmth_sentence)
    if spend_block:
        body_parts.extend(["", spend_block])
    body_parts.extend(["", next_step, "", signoff])
    draft_text = "\n".join(body_parts)

    return draft_text, generation_path, warmth_usage, warmth_validation_info


def _build_deterministic_unavailable_draft(av: dict, persona_name: str, guest_first_name: str) -> str:
    meal_period = av.get("meal_period", "dinner")
    event_date = av.get("event_date", "the requested date")
    guest_name = guest_first_name or "there"
    opening = FirstResponseCopyLibrary.render(
        "availability_unavailable",
        {"meal_period": meal_period, "event_date": event_date},
    )
    signoff = FirstResponseCopyLibrary.render("signoff", {"persona_name": persona_name})
    return f"Dear {guest_name},\n\n{opening}\n\n{signoff}"


def _build_deterministic_acknowledge_draft(record: dict, persona_name: str, guest_first_name: str) -> str:
    ext = record["target_extraction"]
    prep = ext["response_preparation_target"]
    date_ctx = prep.get("date_context", {})
    dates = date_ctx.get("candidate_dates", [])
    meal_period = ext.get("meal_period", "dinner") or "dinner"
    event_date = dates[0] if dates else "the requested date"
    guest_name = guest_first_name or "there"

    opening = FirstResponseCopyLibrary.render(
        "availability_not_checked",
        {"meal_period": meal_period, "event_date": event_date},
    )
    next_step = FirstResponseCopyLibrary.render("availability_check_next_step")
    signoff = FirstResponseCopyLibrary.render("signoff", {"persona_name": persona_name})
    return f"Dear {guest_name},\n\n{opening}\n\n{next_step}\n\n{signoff}"


# -- Compliance scan (for metrics) -------------------------------------------


_MENU_SCAN = re.compile(r"\bmenu\b|\bdietary\b|\bfood\s+(?:options?|choices?|preferences?)\b|\bcuisine\b", re.IGNORECASE)
_SPECIAL_TOUCHES_SCAN = re.compile(r"\bspecial\s+touch(?:es)?\b|\bpersonal(?:is(?:e|ed|ation|ing))?\b|\bdecorations?\b|\bfloral\b", re.IGNORECASE)
_BOOKING_FORM_SCAN = re.compile(r"\bbooking\s+form\b|\bfill\s+(?:in|out)\b|\bsubmit\s+(?:a|the)?\s*form\b|https?://|\[(?:form|link|url)\]", re.IGNORECASE)


def _compliance_flags(draft: str) -> dict:
    return {
        "menu_mention": bool(_MENU_SCAN.search(draft)),
        "special_touches_mention": bool(_SPECIAL_TOUCHES_SCAN.search(draft)),
        "booking_form_mention": bool(_BOOKING_FORM_SCAN.search(draft)),
    }


# -- Record processors --------------------------------------------------------


def _get_prompt_vars(record: dict) -> dict:
    ext = record["target_extraction"]
    prep = ext["response_preparation_target"]
    return deepcopy(prep.get("draft_prompt_variables", {}))


def _process_deterministic_confirm_available(record: dict, av: dict, idx: int, total: int) -> dict:
    base_vars = _get_prompt_vars(record)
    persona_name = base_vars.get("persona_name", "")
    guest_first_name = base_vars.get("guest_first_name", "")
    record_id = record["id"]

    print(f"  [{idx:3d}/{total}] [det+warmth?/CONF] {record_id} ... ", end="", flush=True)
    draft, generation_path, warmth_usage, warmth_validation = _build_deterministic_confirm_available_draft(
        av=av,
        record=record,
        persona_name=persona_name,
        guest_first_name=guest_first_name,
    )
    flags = _compliance_flags(draft)
    warmth_accepted = generation_path == "deterministic+warmth"
    warmth_tokens = warmth_usage.get("input_tokens", 0) + warmth_usage.get("output_tokens", 0) if warmth_usage else 0
    print(f"done ({generation_path}, warmth_tokens={warmth_tokens})")

    return {
        "record_id": record_id,
        "subject": record.get("subject", ""),
        "body": record.get("body", ""),
        "sender": record.get("sender", {}),
        "availability": av,
        "generation_path": generation_path,
        "response_goal": "CONFIRM_AVAILABLE",
        "llm2_prompt": None,  # no full LLM call
        "prompt_inputs": {
            "generation_rule": "RESP-038",
            "persona_name": persona_name,
            "guest_first_name": guest_first_name,
            "copy_block_opening": "availability_confirmed",
            "copy_block_opening_vars": {
                "meal_period": av.get("meal_period", "dinner"),
                "event_date": av.get("event_date", "the requested date"),
            },
            "copy_block_next_step": "confirm_available_next_step",
            "copy_block_signoff": "signoff",
            "copy_block_signoff_vars": {"persona_name": persona_name},
            "warmth_sentence_result": warmth_validation,
            "warmth_sentence_accepted": warmth_accepted,
            "prompt_version": _defn.version,
            "model": generation_path,
            "temperature": _WARMTH_TEMPERATURE if warmth_usage else None,
        },
        "prompt_context": {
            "response_goal": "CONFIRM_AVAILABLE",
            "generation_path": generation_path,
            "prompt_version": _defn.version,
            "availability_status": av.get("availability_status", "CONFIRMED_AVAILABLE"),
            "availability_date": av.get("event_date"),
            "availability_meal_period": av.get("meal_period"),
            "room_name": av.get("room_name"),
            "restaurant_name": av.get("restaurant_name"),
            "resp038_applied": True,
            "resp039_warmth_accepted": warmth_accepted,
            "compliance_flags": flags,
        },
        "prompt_key": _defn.key,
        "prompt_version": _defn.version,
        "model": generation_path,
        "temperature": _WARMTH_TEMPERATURE if warmth_usage else None,
        "response": draft,
        "usage": warmth_usage or {"input_tokens": 0, "output_tokens": 0},
        # Sprint 11 extra fields
        "warmth_usage": warmth_usage,
        "warmth_validation": warmth_validation,
        "compliance_flags": flags,
    }


def _process_deterministic_unavailable(record: dict, av: dict, idx: int, total: int) -> dict:
    base_vars = _get_prompt_vars(record)
    persona_name = base_vars.get("persona_name", "")
    guest_first_name = base_vars.get("guest_first_name", "")
    record_id = record["id"]

    print(f"  [{idx:3d}/{total}] [det/RESP] {record_id} ... done (RESP-023 deterministic)")
    draft = _build_deterministic_unavailable_draft(av, persona_name, guest_first_name)
    flags = _compliance_flags(draft)

    return {
        "record_id": record_id,
        "subject": record.get("subject", ""),
        "body": record.get("body", ""),
        "sender": record.get("sender", {}),
        "availability": av,
        "generation_path": "deterministic",
        "response_goal": "RESPOND_UNAVAILABLE",
        "llm2_prompt": None,
        "prompt_inputs": {
            "generation_rule": "RESP-023",
            "persona_name": persona_name,
            "guest_first_name": guest_first_name,
            "copy_block_opening": "availability_unavailable",
            "copy_block_opening_vars": {
                "meal_period": av.get("meal_period", "dinner"),
                "event_date": av.get("event_date", "the requested date"),
            },
            "copy_block_signoff": "signoff",
            "copy_block_signoff_vars": {"persona_name": persona_name},
            "prompt_version": _defn.version,
            "model": "deterministic",
            "temperature": None,
        },
        "prompt_context": {
            "response_goal": "RESPOND_UNAVAILABLE",
            "generation_path": "deterministic",
            "prompt_version": _defn.version,
            "availability_status": av.get("availability_status", "unknown"),
            "availability_date": av.get("event_date"),
            "availability_meal_period": av.get("meal_period"),
            "room_name": av.get("room_name"),
            "restaurant_name": av.get("restaurant_name"),
            "resp023_applied": True,
            "compliance_flags": flags,
        },
        "prompt_key": _defn.key,
        "prompt_version": _defn.version,
        "model": "deterministic",
        "temperature": None,
        "response": draft,
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "warmth_usage": None,
        "warmth_validation": None,
        "compliance_flags": flags,
    }


def _process_deterministic_acknowledge(record: dict, idx: int, total: int) -> dict:
    ext = record["target_extraction"]
    prep = ext["response_preparation_target"]
    base_vars = deepcopy(prep.get("draft_prompt_variables", {}))
    persona_name = base_vars.get("persona_name", "")
    guest_first_name = base_vars.get("guest_first_name", "")
    record_id = record["id"]

    date_ctx = prep.get("date_context", {})
    dates = date_ctx.get("candidate_dates", [])
    meal_period = ext.get("meal_period", "dinner") or "dinner"
    event_date = dates[0] if dates else "the requested date"

    print(f"  [{idx:3d}/{total}] [det/ACKN] {record_id} ... done (RESP-036 deterministic)")
    draft = _build_deterministic_acknowledge_draft(record, persona_name, guest_first_name)
    flags = _compliance_flags(draft)

    return {
        "record_id": record_id,
        "subject": record.get("subject", ""),
        "body": record.get("body", ""),
        "sender": record.get("sender", {}),
        "availability": None,
        "generation_path": "deterministic",
        "response_goal": "ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
        "llm2_prompt": None,
        "prompt_inputs": {
            "generation_rule": "RESP-036",
            "persona_name": persona_name,
            "guest_first_name": guest_first_name,
            "copy_block_opening": "availability_not_checked",
            "copy_block_opening_vars": {
                "meal_period": meal_period,
                "event_date": event_date,
            },
            "copy_block_next_step": "availability_check_next_step",
            "copy_block_signoff": "signoff",
            "copy_block_signoff_vars": {"persona_name": persona_name},
            "prompt_version": _defn.version,
            "model": "deterministic",
            "temperature": None,
        },
        "prompt_context": {
            "response_goal": "ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
            "generation_path": "deterministic",
            "prompt_version": _defn.version,
            "availability_status": "not_checked",
            "availability_date": event_date,
            "availability_meal_period": meal_period,
            "room_name": None,
            "restaurant_name": base_vars.get("restaurant_name"),
            "resp036_applied": True,
            "compliance_flags": flags,
        },
        "prompt_key": _defn.key,
        "prompt_version": _defn.version,
        "model": "deterministic",
        "temperature": None,
        "response": draft,
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "warmth_usage": None,
        "warmth_validation": None,
        "compliance_flags": flags,
    }


# -- Main run -----------------------------------------------------------------


def run() -> dict:
    if not _FIXTURE_PATH.exists():
        print(f"ERROR: fixture not found: {_FIXTURE_PATH}", file=sys.stderr)
        sys.exit(1)

    with _FIXTURE_PATH.open(encoding="utf-8") as fh:
        fixture = json.load(fh)

    all_records = fixture["records"]
    total = len(all_records)

    confirm_recs     = [r for r in all_records if r.get("availability") and r["availability"].get("is_available") is True]
    unavail_recs     = [r for r in all_records if r.get("availability") and r["availability"].get("is_available") is False]
    not_checked_recs = [r for r in all_records if r.get("availability") is None]

    print(f"\nDraft 100-record runner (Sprint 11 — RESP-037 to RESP-041)")
    print(f"Prompt v{_defn.version} | warmth model {_WARMTH_MODEL}")
    print(f"\nPipeline state (S11):")
    print(f"  RESP-023: RESPOND_UNAVAILABLE       → deterministic (copy-block only)")
    print(f"  RESP-036: ACKNOWLEDGE_AND_CHECK      → deterministic (copy-block only)")
    print(f"  RESP-037: confirm_available_next_step copy block added")
    print(f"  RESP-038: CONFIRM_AVAILABLE          → deterministic + optional warmth LLM")
    print(f"  RESP-039: warmth LLM — max 1 sentence, max 20 words")
    print(f"  RESP-040: WarmthSentenceValidator — warmth dropped on any violation")
    print(f"  RESP-041: raw guest message NOT passed to warmth LLM")
    print(f"\nRecord breakdown:")
    print(f"  CONFIRM_AVAILABLE (det+warmth?):           {len(confirm_recs):3d}")
    print(f"  RESPOND_UNAVAILABLE (deterministic):       {len(unavail_recs):3d}")
    print(f"  ACKNOWLEDGE_AND_CHECK_AVAILABILITY (det):  {len(not_checked_recs):3d}")
    print(f"  Total:                                     {total:3d}")
    print(f"\nExpected full-LLM calls: 0 | Warmth-LLM calls: up to {len(confirm_recs)}\n")

    results: list[dict] = []
    warmth_call_count = 0
    warmth_accepted_count = 0
    warmth_dropped_count = 0
    det_count = 0
    idx = 0

    print("--- CONFIRM_AVAILABLE (deterministic + optional warmth LLM) ---")
    for record in confirm_recs:
        idx += 1
        av = record["availability"]
        result = _process_deterministic_confirm_available(record, av, idx, total)
        results.append(result)
        det_count += 1
        if result.get("warmth_validation") is not None:
            warmth_call_count += 1
            if result["warmth_validation"]["passed"]:
                warmth_accepted_count += 1
            else:
                warmth_dropped_count += 1
        elif result["generation_path"] == "deterministic+warmth":
            warmth_accepted_count += 1

    print("\n--- RESPOND_UNAVAILABLE (deterministic — RESP-023) ---")
    for record in unavail_recs:
        idx += 1
        av = record["availability"]
        result = _process_deterministic_unavailable(record, av, idx, total)
        results.append(result)
        det_count += 1

    print("\n--- ACKNOWLEDGE_AND_CHECK_AVAILABILITY (deterministic — RESP-036) ---")
    for record in not_checked_recs:
        idx += 1
        result = _process_deterministic_acknowledge(record, idx, total)
        results.append(result)
        det_count += 1

    # Sort back into original fixture order
    order = {r["id"]: i for i, r in enumerate(all_records)}
    results.sort(key=lambda r: order.get(r["record_id"], 9999))

    # Metrics
    menu_count = sum(1 for r in results if r.get("compliance_flags", {}).get("menu_mention"))
    special_count = sum(1 for r in results if r.get("compliance_flags", {}).get("special_touches_mention"))
    booking_form_count = sum(1 for r in results if r.get("compliance_flags", {}).get("booking_form_mention"))
    hallucination_count = menu_count + special_count + booking_form_count
    auto_send_eligible = sum(
        1 for r in results
        if not any(r.get("compliance_flags", {}).values())
    )
    auto_send_rate = auto_send_eligible / total if total else 0

    total_warmth_input = sum(
        (r["warmth_usage"]["input_tokens"] for r in results if r.get("warmth_usage")), 0
    )
    total_warmth_output = sum(
        (r["warmth_usage"]["output_tokens"] for r in results if r.get("warmth_usage")), 0
    )

    print(f"\n{'─'*60}")
    print(f"Sprint 11 — 100-record run summary")
    print(f"{'─'*60}")
    print(f"  Total records:                  {total}")
    print(f"  Full LLM calls:                 0  (all paths deterministic)")
    print(f"  Warmth LLM calls attempted:     {warmth_call_count}")
    print(f"  Warmth sentences accepted:      {warmth_accepted_count}")
    print(f"  Warmth sentences dropped:       {warmth_dropped_count}")
    print(f"  Deterministic calls (all):      {det_count}")
    print(f"")
    print(f"  Compliance scan:")
    print(f"    Menu discussion:              {menu_count}")
    print(f"    Special touches:              {special_count}")
    print(f"    Booking form hallucination:   {booking_form_count}")
    print(f"    Total hallucinations:         {hallucination_count}")
    print(f"")
    print(f"  Auto-send eligible:             {auto_send_eligible}/{total}  ({auto_send_rate:.1%})")
    print(f"")
    print(f"  Warmth LLM tokens:              {total_warmth_input:,} in / {total_warmth_output:,} out")
    print(f"{'─'*60}")

    output = {
        "run_id": str(uuid.uuid4()),
        "run_at": datetime.now(timezone.utc).isoformat(),
        "source_fixture": "availability_fixture_100.json",
        "pipeline_version": "sprint11",
        "pipeline_changes": [
            "RESP-023: RESPOND_UNAVAILABLE deterministic — no LLM call",
            "RESP-036: ACKNOWLEDGE_AND_CHECK_AVAILABILITY deterministic — no LLM call",
            "RESP-037: confirm_available_next_step copy block (strict next step)",
            "RESP-038: CONFIRM_AVAILABLE fully deterministic + optional warmth LLM",
            "RESP-039: warmth LLM — max 1 sentence, max 20 words",
            "RESP-040: WarmthSentenceValidator — warmth dropped on any violation",
            "RESP-041: raw guest message NOT passed to warmth LLM",
        ],
        "prompt_key": _defn.key,
        "prompt_version": _defn.version,
        "output_schema_version": _defn.output_schema_version,
        "model_llm_full": "none",
        "model_warmth": _WARMTH_MODEL,
        "model_deterministic": "deterministic",
        "warmth_temperature": _WARMTH_TEMPERATURE,
        "total_records": total,
        "full_llm_calls": 0,
        "warmth_llm_calls_attempted": warmth_call_count,
        "warmth_sentences_accepted": warmth_accepted_count,
        "warmth_sentences_dropped": warmth_dropped_count,
        "deterministic_calls": det_count,
        "menu_discussion_count": menu_count,
        "special_touches_count": special_count,
        "booking_form_hallucination_count": booking_form_count,
        "total_hallucination_count": hallucination_count,
        "auto_send_eligible_count": auto_send_eligible,
        "auto_send_eligibility_rate": round(auto_send_rate, 4),
        "total_warmth_input_tokens": total_warmth_input,
        "total_warmth_output_tokens": total_warmth_output,
        "records": results,
    }

    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _OUTPUT_PATH.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2, ensure_ascii=False)

    print(f"\nOutput saved to: {_OUTPUT_PATH}")
    return output


if __name__ == "__main__":
    run()
