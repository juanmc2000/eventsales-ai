"""RESP-009 — Draft Response Quality Evaluation Runner.

Offline evaluation script for the V4 draft generation prompt.
Runs 20 scenarios from draft_quality_test_scenarios.json through:
  1. LLM2 (draft generation) — V4 prompt, claude-haiku-4-5-20251001
  2. LLM evaluator — structured scoring on 6 dimensions

Scoring dimensions (each 1–5, higher = better):
  operational_accuracy  — Correct goal, availability contract, spend language
  tone_fit              — Matches persona_tone
  persona_fit           — Consistent with persona name and style
  commercial_quality    — Commercially-minded; advances the booking
  hallucination_risk    — 5 = no invented facts; 1 = significant fabrication
  ready_to_send         — Boolean; would you send without editing?

Usage (from project root, with venv active):
    python tests/scripts/run_draft_quality_eval.py

Output: tests/data/draft_quality_eval_results.json

Environment:
    ANTHROPIC_API_KEY  — required
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

# ── Paths ─────────────────────────────────────────────────────────────────────

_SCRIPT_DIR = Path(__file__).resolve().parent        # tests/scripts/
_TESTS_DIR = _SCRIPT_DIR.parent                      # tests/
_REPO_ROOT = _TESTS_DIR.parent                       # project root
_SCENARIOS_FILE = _TESTS_DIR / "data" / "draft_quality_test_scenarios.json"
_RESULTS_FILE = _TESTS_DIR / "data" / "draft_quality_eval_results.json"

# ── Model config ──────────────────────────────────────────────────────────────

DRAFT_MODEL = "claude-haiku-4-5-20251001"
EVAL_MODEL = "claude-haiku-4-5-20251001"
DRAFT_TEMPERATURE = 0.7
DRAFT_MAX_TOKENS = 800
EVAL_MAX_TOKENS = 600
EVAL_TEMPERATURE = 0.1

# ── V4 system/user templates (mirrors prompt_registry.py _DRAFT_RESPONSE_V4) ──

_V4_SYSTEM_TEMPLATE = (
    "{persona_system_prompt}\n\n"
    "You are {persona_name}, a hospitality sales professional at {restaurant_name}. "
    "Your tone is {persona_tone} and your style is {persona_style}.\n\n"
    "RESPONSE GOAL: {response_goal}\n\n"
    "Goal instructions:\n"
    "- CONFIRM_AVAILABLE: The venue system confirmed the slot is available. "
    "Communicate the confirmed availability and provide relevant venue details. "
    "Be warm and commercially-minded. "
    "Approved opening: 'Thank you for your enquiry \u2014 I'm delighted to let you know "
    "that the date is available for your event.'\n"
    "- RESPOND_UNAVAILABLE: The slot is fully booked. "
    "Acknowledge the enquiry warmly. "
    "Do NOT invent or suggest alternative dates, rooms, or times. "
    "Approved opening: 'Thank you for your enquiry. Unfortunately, we are fully booked "
    "for the requested date.'\n"
    "- ACKNOWLEDGE_AND_CHECK_AVAILABILITY: No availability check has been performed yet. "
    "Acknowledge the enquiry and tell the guest the team will check availability and be in touch. "
    "Do NOT state or imply the date is available. "
    "Approved opening: 'Thank you for your enquiry \u2014 I'll check availability for the "
    "requested date and come back to you shortly.'\n"
    "- REQUEST_MISSING_INFORMATION: Politely ask ONLY the clarification questions "
    "provided. Do not ask for information that is already known. "
    "Approved opening: 'Thank you for getting in touch \u2014 I just have a couple of quick "
    "questions before we can confirm availability.'\n"
    "- REQUEST_DATE_CONFIRMATION: The date is ambiguous. Ask the guest to confirm "
    "the exact date using ONLY the clarification question provided. "
    "Approved opening: 'We\u2019d love to host your event \u2014 could you confirm the exact date "
    "you have in mind so we can check availability?'\n"
    "- REQUEST_WEBFORM: Multiple key details are missing. Direct the guest to the "
    "booking enquiry form to provide structured details. "
    "Approved opening: 'Thank you for your enquiry \u2014 to ensure we capture all the details "
    "for your event, could I ask you to complete our short enquiry form?'\n"
    "- ESCALATE_TO_HUMAN: Acknowledge the enquiry warmly and let the guest know "
    "that a member of the team will be in touch shortly. "
    "Approved opening: 'Thank you for reaching out \u2014 a member of our events team will "
    "review your enquiry and be in touch shortly.'\n\n"
    "{phrase_guidance_line}"
    "AVAILABILITY CONTRACT \u2014 you will receive an 'Availability status' line in the "
    "enquiry details. Honour these rules exactly:\n"
    "- CONFIRMED_AVAILABLE: The venue system confirmed the slot is available. "
    "You may tell the guest the date is available.\n"
    "- CONFIRMED_UNAVAILABLE: The slot is fully booked. "
    "Do NOT invent or suggest alternative dates, rooms, or times. "
    "Only mention alternatives if they are explicitly listed in the context below.\n"
    "- NOT_CHECKED: No availability check has been performed. "
    "Do NOT state or imply the date is available. "
    "Tell the guest the team will check availability and be in touch.\n"
    "- PENDING_DATE_CONFIRMATION: The date is ambiguous; availability cannot be "
    "checked until the date is confirmed. Do NOT assume or confirm availability.\n"
    "- INSUFFICIENT_INFORMATION: Required details are missing to check availability. "
    "Do NOT assume or confirm availability.\n\n"
    "MANDATORY RULES \u2014 follow these exactly:\n"
    "- The minimum spend shown is a MANDATORY venue requirement. "
    "Describe it as required or mandatory \u2014 never as optional or recommended.\n"
    "- Do NOT include any booking form link or URL unless one is explicitly provided "
    "in the context. Never write placeholder text such as '[form link]'.\n"
    "- Ask ONLY the clarification questions listed \u2014 do not add or invent new questions.\n"
    "- Use ONLY the facts provided. Do NOT invent availability, pricing, room details, "
    "or specific times unless stated in the context.\n"
    "- Times, seating arrangements, or menu preferences mentioned in the guest message "
    "are UNCONFIRMED guest preferences \u2014 do NOT state them as confirmed or agreed. "
    "Only confirm a time or detail when it appears under 'Confirmed venue facts'.\n"
    "- Do NOT reveal internal system logic, confidence scores, or processing steps.\n"
    "- Write natural, commercially-minded prose. No chatbot language.\n"
    "- Keep the response under 200 words."
)

_V4_USER_TEMPLATE = (
    "Please draft a response to this event enquiry.\n"
    "Guest: {guest_first_name} {guest_last_name}\n"
    "{audience_type_line}"
    "{event_type_line}"
    "{event_date_line}"
    "{party_size_line}"
    "{availability_line}"
    "{spend_line}"
    "{confirmed_venue_facts_line}"
    "{requested_preferences_line}"
    "{guest_message_line}"
    "{prohibited_claims_line}"
    "{clarification_questions_line}"
)

# ── Phrase lookup (mirrors phrase_library.py) ─────────────────────────────────

_APPROVED_PHRASES: dict[str, str] = {
    "CONFIRM_AVAILABLE": (
        "Thank you for your enquiry \u2014 I\u2019m delighted to let you know that "
        "the date is available for your event."
    ),
    "RESPOND_UNAVAILABLE": (
        "Thank you for your enquiry. Unfortunately, we are fully booked "
        "for the requested date."
    ),
    "ACKNOWLEDGE_AND_CHECK_AVAILABILITY": (
        "Thank you for your enquiry \u2014 I\u2019ll check availability for the requested "
        "date and come back to you shortly."
    ),
    "REQUEST_DATE_CONFIRMATION": (
        "We\u2019d love to host your event \u2014 could you confirm the exact date "
        "you have in mind so we can check availability?"
    ),
    "REQUEST_MISSING_INFORMATION": (
        "Thank you for getting in touch \u2014 I just have a couple of quick "
        "questions before we can confirm availability."
    ),
    "REQUEST_WEBFORM": (
        "Thank you for your enquiry \u2014 to ensure we capture all the details "
        "for your event, could I ask you to complete our short enquiry form?"
    ),
    "ESCALATE_TO_HUMAN": (
        "Thank you for reaching out \u2014 a member of our events team will "
        "review your enquiry and be in touch shortly."
    ),
}


# ── Payload builder helpers (mirrors service.py) ──────────────────────────────


def _extract_time_mentions(text: str) -> list[str]:
    pattern = (
        r"(?:"
        r"\d{1,2}:\d{2}\s*(?:am|pm)?"
        r"|\d{1,2}\s+or\s+\d{1,2}\s*(?:am|pm)"
        r"|(?:around|from|at)\s+\d{1,2}:\d{2}\s*(?:am|pm)?"
        r"|(?:around|from|at)\s+\d{1,2}\s*(?:am|pm)?"
        r"|\d{1,2}\s*(?:am|pm)"
        r")"
    )
    seen: set[str] = set()
    results: list[str] = []
    for m in re.finditer(pattern, text, re.IGNORECASE):
        val = m.group(0).strip()
        if val not in seen:
            seen.add(val)
            results.append(val)
    return results


def _build_availability_line(sc: dict) -> str:
    contract = sc.get("availability_contract", "NOT_CHECKED")
    date_str = sc.get("availability_date") or sc.get("event_date") or ""
    period = sc.get("availability_meal_period", "") or ""
    slot = f"{date_str} {period}".strip()
    if contract == "CONFIRMED_AVAILABLE":
        return (
            f"Availability status: CONFIRMED_AVAILABLE\n"
            f"Availability: Room is available for {slot}.\n"
        )
    if contract == "CONFIRMED_UNAVAILABLE":
        return (
            f"Availability status: CONFIRMED_UNAVAILABLE\n"
            f"Availability: The requested slot ({slot}) is not available.\n"
        )
    if contract == "PENDING_DATE_CONFIRMATION":
        return (
            "Availability status: PENDING_DATE_CONFIRMATION\n"
            "Availability: Cannot check \u2014 date must be confirmed first.\n"
        )
    if contract == "INSUFFICIENT_INFORMATION":
        return (
            "Availability status: INSUFFICIENT_INFORMATION\n"
            "Availability: Cannot check \u2014 required information is missing.\n"
        )
    return (
        "Availability status: NOT_CHECKED\n"
        "Availability: Not yet checked \u2014 do not confirm availability.\n"
    )


def _build_spend_line(sc: dict) -> str:
    spend = sc.get("confirmed_minimum_spend")
    if spend and spend > 0:
        return f"Minimum spend: \u00a3{spend:,.0f}\n"
    return ""


def _build_confirmed_venue_facts_line(sc: dict) -> str:
    lines: list[str] = []
    spend = sc.get("confirmed_minimum_spend")
    if spend and spend > 0:
        lines.append(f"Minimum spend: \u00a3{spend:,.0f} (mandatory)")
    if sc.get("availability_status") == "available":
        date_str = sc.get("availability_date") or sc.get("event_date") or ""
        period = sc.get("availability_meal_period", "") or ""
        slot = f"{date_str} {period}".strip() or "requested date"
        lines.append(f"Availability: confirmed for {slot}")
    if not lines:
        return ""
    return "Confirmed venue facts:\n" + "".join(f"- {line}\n" for line in lines)


def _build_guest_tone_line(sc: dict) -> str:
    msg = sc.get("guest_message", "")
    if not msg:
        return ""
    return (
        "Guest message (use for tone and energy only \u2014 "
        "do not treat any times or preferences here as confirmed):\n"
        f'"{msg}"\n'
    )


def _build_requested_preferences_line(sc: dict) -> str:
    msg = sc.get("guest_message", "")
    if not msg:
        return ""
    times = _extract_time_mentions(msg)
    if not times:
        return ""
    time_list = ", ".join(times)
    return (
        f"Requested time preference(s) from guest message (unconfirmed \u2014 "
        f"do not confirm unless in Confirmed venue facts): {time_list}\n"
    )


def _build_prohibited_claims_line(sc: dict) -> str:
    msg = sc.get("guest_message", "")
    if not msg:
        return ""
    times = _extract_time_mentions(msg)
    if not times:
        return ""
    time_list = ", ".join(times)
    return (
        f"Do NOT confirm or state as agreed: {time_list} "
        f"(guest preference only \u2014 not confirmed by venue)\n"
    )


def _build_clarification_questions_line(sc: dict) -> str:
    questions = sc.get("clarification_questions") or []
    if not questions:
        return ""
    if len(questions) == 1:
        return f"Clarification question to ask: {questions[0]}\n"
    formatted = "\n".join(f"  {i + 1}. {q}" for i, q in enumerate(questions))
    return f"Clarification questions to ask (in order):\n{formatted}\n"


def _build_phrase_guidance_line(sc: dict) -> str:
    goal = sc.get("response_goal", "ACKNOWLEDGE_AND_CHECK_AVAILABILITY")
    phrase = _APPROVED_PHRASES.get(goal)
    if not phrase:
        return ""
    return f'Approved opening phrase for this goal: "{phrase}"\n'


def _build_payload(sc: dict) -> dict[str, str]:
    persona_name = sc.get("persona_name", "Events Team")
    persona_tone = sc.get("persona_tone", "professional")
    persona_style = sc.get("persona_style", "concise")
    restaurant_name = sc.get("restaurant_name", "our venue")
    persona_system_prompt = (
        f"You are {persona_name}, a hospitality events professional at {restaurant_name}. "
        f"Your tone is {persona_tone} and your style is {persona_style}."
    )
    response_goal = sc.get("response_goal", "ACKNOWLEDGE_AND_CHECK_AVAILABILITY")
    audience_type = sc.get("audience_type", "")

    return {
        "persona_system_prompt": persona_system_prompt,
        "persona_name": persona_name,
        "restaurant_name": restaurant_name,
        "persona_tone": persona_tone,
        "persona_style": persona_style,
        "response_goal": response_goal,
        "guest_first_name": sc.get("guest_first_name", ""),
        "guest_last_name": sc.get("guest_last_name", ""),
        "audience_type_line": f"Audience type: {audience_type}\n" if audience_type else "",
        "event_type_line": (
            f"Event type: {sc['event_type'].replace('_', ' ').title()}\n"
            if sc.get("event_type") else ""
        ),
        "event_date_line": f"Event date: {sc['event_date']}\n" if sc.get("event_date") else "",
        "party_size_line": f"Party size: {sc['party_size']}\n" if sc.get("party_size") else "",
        "availability_line": _build_availability_line(sc),
        "spend_line": _build_spend_line(sc),
        "confirmed_venue_facts_line": _build_confirmed_venue_facts_line(sc),
        "requested_preferences_line": _build_requested_preferences_line(sc),
        "guest_message_line": _build_guest_tone_line(sc),
        "prohibited_claims_line": _build_prohibited_claims_line(sc),
        "clarification_questions_line": _build_clarification_questions_line(sc),
        "phrase_guidance_line": _build_phrase_guidance_line(sc),
    }


def _render(template: str, payload: dict[str, str]) -> str:
    """Simple format_map render, treating missing keys as empty string."""
    class _DefaultDict(dict):
        def __missing__(self, key: str) -> str:
            return ""
    return template.format_map(_DefaultDict(payload))


# ── Draft generation ───────────────────────────────────────────────────────────


def generate_draft(client: anthropic.Anthropic, sc: dict) -> tuple[str, str, str]:
    """Call LLM2 to generate a draft for the given scenario.

    Returns (draft_text, rendered_system, rendered_user).
    """
    payload = _build_payload(sc)
    system_prompt = _render(_V4_SYSTEM_TEMPLATE, payload)
    user_message = _render(_V4_USER_TEMPLATE, payload)

    response = client.messages.create(
        model=DRAFT_MODEL,
        max_tokens=DRAFT_MAX_TOKENS,
        temperature=DRAFT_TEMPERATURE,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    draft_text = response.content[0].text.strip()
    return draft_text, system_prompt, user_message


# ── Evaluation ────────────────────────────────────────────────────────────────

_EVAL_SYSTEM = (
    "You are a quality evaluator for AI-generated hospitality sales email drafts. "
    "You will receive a scenario specification and a generated draft. "
    "Score the draft on each dimension and return ONLY a valid JSON object. "
    "No explanation. No preamble. No markdown fences."
)

_EVAL_USER_TEMPLATE = """\
Scenario:
- Response goal: {response_goal}
- Availability contract: {availability_contract}
- Audience type: {audience_type}
- Persona: {persona_name} ({persona_tone} tone, {persona_style} style)
- Event: {event_type} for {party_size} guests on {event_date}
- Confirmed minimum spend: {confirmed_minimum_spend}
- Clarification questions expected: {clarification_questions}
- Guest message: {guest_message}

Expected qualities: {expected_qualities}

Generated draft:
{draft}

Score the draft by returning this JSON object with no other text:
{{
  "operational_accuracy": <integer 1-5>,
  "tone_fit": <integer 1-5>,
  "persona_fit": <integer 1-5>,
  "commercial_quality": <integer 1-5>,
  "hallucination_risk": <integer 1-5 where 5=no fabrication>,
  "ready_to_send": <true or false>,
  "notes": "<one sentence summary of key issues or strengths>"
}}

Scoring guidance:
- operational_accuracy: Does the draft correctly handle the goal, availability contract, spend, and clarification questions? 5=perfect, 1=multiple errors.
- tone_fit: Does the draft's tone match the specified persona tone? 5=perfect match, 1=completely wrong tone.
- persona_fit: Is the response consistent with the named persona and style? 5=natural and in-character, 1=generic or off-character.
- commercial_quality: Is the draft commercially-minded, professional, and likely to advance the booking? 5=excellent, 1=ineffective.
- hallucination_risk: Does the draft avoid inventing facts not in the scenario? 5=no invented facts, 1=significant fabrication.
- ready_to_send: Would you send this draft without editing? true=yes, false=needs revision.
"""


def evaluate_draft(client: anthropic.Anthropic, sc: dict, draft: str) -> dict[str, Any]:
    """Call LLM evaluator to score the draft on 6 dimensions.

    Returns a dict with scores; falls back to error dict on parse failure.
    """
    user_message = _EVAL_USER_TEMPLATE.format(
        response_goal=sc.get("response_goal", ""),
        availability_contract=sc.get("availability_contract", ""),
        audience_type=sc.get("audience_type", ""),
        persona_name=sc.get("persona_name", ""),
        persona_tone=sc.get("persona_tone", ""),
        persona_style=sc.get("persona_style", ""),
        event_type=sc.get("event_type", "N/A"),
        party_size=sc.get("party_size", "N/A"),
        event_date=sc.get("event_date", "N/A"),
        confirmed_minimum_spend=(
            f"£{sc['confirmed_minimum_spend']:,.0f}"
            if sc.get("confirmed_minimum_spend") else "None"
        ),
        clarification_questions=json.dumps(sc.get("clarification_questions") or []),
        guest_message=sc.get("guest_message", ""),
        expected_qualities=json.dumps(sc.get("expected_qualities", {})),
        draft=draft,
    )
    response = client.messages.create(
        model=EVAL_MODEL,
        max_tokens=EVAL_MAX_TOKENS,
        temperature=EVAL_TEMPERATURE,
        system=_EVAL_SYSTEM,
        messages=[{"role": "user", "content": user_message}],
    )
    raw = response.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "operational_accuracy": None,
            "tone_fit": None,
            "persona_fit": None,
            "commercial_quality": None,
            "hallucination_risk": None,
            "ready_to_send": None,
            "notes": f"Evaluation parse error: {exc}",
            "_raw": raw,
        }


# ── Aggregation ───────────────────────────────────────────────────────────────


def _aggregate(results: list[dict]) -> dict:
    """Compute summary statistics from individual scenario results."""
    scored = [r for r in results if r.get("evaluation", {}).get("operational_accuracy") is not None]
    if not scored:
        return {"total_scenarios": len(results), "scored": 0}

    dimensions = [
        "operational_accuracy", "tone_fit", "persona_fit",
        "commercial_quality", "hallucination_risk",
    ]
    averages = {}
    for dim in dimensions:
        vals = [r["evaluation"][dim] for r in scored if r["evaluation"].get(dim) is not None]
        averages[dim] = round(sum(vals) / len(vals), 2) if vals else None

    ready_count = sum(
        1 for r in scored
        if r.get("evaluation", {}).get("ready_to_send") is True
    )
    ready_pct = round(ready_count / len(scored) * 100, 1)

    # Per-goal breakdown
    goals: dict[str, list[dict]] = {}
    for r in scored:
        goal = r.get("scenario_goal", "unknown")
        goals.setdefault(goal, []).append(r["evaluation"])

    goal_summary: dict[str, dict] = {}
    for goal, evals in goals.items():
        op_scores = [e["operational_accuracy"] for e in evals if e.get("operational_accuracy") is not None]
        rts_count = sum(1 for e in evals if e.get("ready_to_send") is True)
        goal_summary[goal] = {
            "n": len(evals),
            "avg_operational_accuracy": round(sum(op_scores) / len(op_scores), 2) if op_scores else None,
            "ready_to_send_pct": round(rts_count / len(evals) * 100, 1),
        }

    overall = round(
        sum(v for v in averages.values() if v is not None)
        / sum(1 for v in averages.values() if v is not None),
        2,
    )

    return {
        "total_scenarios": len(results),
        "scored": len(scored),
        "draft_model": DRAFT_MODEL,
        "eval_model": EVAL_MODEL,
        "averages": averages,
        "overall_average": overall,
        "ready_to_send_pct": ready_pct,
        "by_goal": goal_summary,
    }


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    if not _SCENARIOS_FILE.exists():
        print(f"ERROR: Scenarios file not found: {_SCENARIOS_FILE}", file=sys.stderr)
        sys.exit(1)

    scenarios_data = json.loads(_SCENARIOS_FILE.read_text())
    scenarios = scenarios_data["scenarios"]
    print(f"Loaded {len(scenarios)} scenarios from {_SCENARIOS_FILE.name}")
    print(f"Draft model: {DRAFT_MODEL}  |  Eval model: {EVAL_MODEL}")
    print("-" * 70)

    client = anthropic.Anthropic(api_key=api_key)
    results: list[dict] = []

    for i, sc in enumerate(scenarios, start=1):
        sc_id = sc.get("id", f"sc_{i:02d}")
        goal = sc.get("response_goal", "unknown")
        print(f"[{i:02d}/{len(scenarios)}] {sc_id}  goal={goal} ...", end=" ", flush=True)

        # Step 1: Generate draft
        try:
            draft_text, rendered_system, rendered_user = generate_draft(client, sc)
        except Exception as exc:
            print(f"DRAFT ERROR: {exc}")
            results.append({
                "scenario_id": sc_id,
                "scenario_goal": goal,
                "draft": None,
                "evaluation": None,
                "error": str(exc),
            })
            continue

        # Step 2: Evaluate draft
        try:
            evaluation = evaluate_draft(client, sc, draft_text)
        except Exception as exc:
            print(f"EVAL ERROR: {exc}")
            evaluation = {"error": str(exc)}

        score = evaluation.get("operational_accuracy", "?")
        rts = evaluation.get("ready_to_send", "?")
        print(f"op_acc={score}/5  ready={rts}")

        results.append({
            "scenario_id": sc_id,
            "scenario_goal": goal,
            "audience_type": sc.get("audience_type"),
            "availability_contract": sc.get("availability_contract"),
            "draft": draft_text,
            "rendered_system": rendered_system,
            "rendered_user": rendered_user,
            "evaluation": evaluation,
        })

        # Brief pause to stay well within rate limits
        if i < len(scenarios):
            time.sleep(0.5)

    # Aggregate
    summary = _aggregate(results)

    output = {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "scenarios_file": str(_SCENARIOS_FILE),
        "draft_model": DRAFT_MODEL,
        "eval_model": EVAL_MODEL,
        "summary": summary,
        "results": results,
    }

    _RESULTS_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print("-" * 70)
    print(f"Results saved to: {_RESULTS_FILE}")
    print()
    print("Summary:")
    print(f"  Scenarios scored:    {summary['scored']}/{summary['total_scenarios']}")
    print(f"  Overall average:     {summary.get('overall_average', 'N/A')}/5.0")
    print(f"  Ready-to-send:       {summary.get('ready_to_send_pct', 'N/A')}%")
    print()
    print("  Dimension averages:")
    for dim, val in (summary.get("averages") or {}).items():
        print(f"    {dim:<25} {val}/5.0")
    print()
    print("  By response goal:")
    for goal, gs in (summary.get("by_goal") or {}).items():
        print(
            f"    {goal:<40} "
            f"n={gs['n']}  "
            f"op_acc={gs['avg_operational_accuracy']}/5  "
            f"ready={gs['ready_to_send_pct']}%"
        )


if __name__ == "__main__":
    main()
