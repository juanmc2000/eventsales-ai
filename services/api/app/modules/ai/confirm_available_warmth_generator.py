"""CONFIRM_AVAILABLE Audience Opener Generator (RESP-039 / RESP-041 / RESP-076).

Generates an optional single opener sentence for CONFIRM_AVAILABLE drafts.
The opener is audience-aware: each audience type receives a distinct system
prompt that constrains the LLM to produce contextually appropriate language.

Rules (RESP-039 / RESP-041 / RESP-076):
  - Sends only structured context — no raw guest message.
  - Asks for exactly one sentence, max 20 words.
  - Selects a system prompt appropriate for the audience type.
  - Runs an inline audience-tone guard before returning the output.
  - Returns None when validation fails — caller uses deterministic fallback.

Usage::

    from app.modules.ai.confirm_available_warmth_generator import generate_warmth_sentence

    raw = generate_warmth_sentence(
        api_key="sk-ant-...",
        occasion="birthday",
        audience_type="social",
        party_size=12,
        meal_period="dinner",
    )
    # raw → "How wonderful — a birthday celebration is always a special occasion!"
    # Returns None for corporate/agency/luxury if celebratory language appears.
"""

from __future__ import annotations

import logging
import re

import anthropic

logger = logging.getLogger(__name__)

_WARMTH_MODEL = "claude-haiku-4-5-20251001"
_WARMTH_MAX_TOKENS = 60
_WARMTH_TEMPERATURE = 0.4

# ── Audience-specific system prompts (RESP-076) ───────────────────────────────

# Shared base rules that apply to all audience types.
_BASE_RULES = (
    "Rules:\n"
    "- Write exactly one sentence.\n"
    "- Maximum 20 words.\n"
    "- Base the sentence only on the provided context fields.\n"
    "- Do NOT start with 'Thank you', 'Thanks', or any acknowledgement phrase.\n"
    "- Do NOT mention: menus, dietary requirements, timing, arrival time, "
    "  booking forms, calls, pricing, minimum spend, room names, special touches, "
    "  availability, or any operational detail.\n"
    "- Do NOT describe or endorse the room, space, or venue suitability. "
    "  Forbidden phrases: 'excellent choice', 'perfect for', 'perfect setting', "
    "  'ideal', 'ideal for', 'ideal setting', 'well accommodated', 'excellent fit', "
    "  'intimate setting', 'excellent setting', 'would be ideal', 'ideally suited'.\n"
    "- Output only the opener sentence — no preamble, no quotes."
)

_SYSTEM_PROMPT_SOCIAL = (
    "You are a hospitality events assistant writing one warm, celebratory sentence "
    "acknowledging a guest's social occasion. "
    "The tone should be warm, enthusiastic, and personal. "
    "Use celebratory openers such as: "
    "'How wonderful —', 'How lovely —', 'How exciting —', "
    "'What a lovely occasion —', 'That sounds wonderful —'.\n\n"
    + _BASE_RULES
)

_SYSTEM_PROMPT_CORPORATE = (
    "You are a hospitality events assistant writing one professional, polished sentence "
    "acknowledging a corporate booking. "
    "The tone must be business-appropriate: efficient, courteous, and commercially direct. "
    "Do NOT use celebratory or emotionally enthusiastic language. "
    "FORBIDDEN openers and phrases: 'How wonderful', 'How lovely', 'How exciting', "
    "'How delightful', 'What a lovely', 'What a wonderful', 'such a special occasion', "
    "'such a meaningful', 'celebration with us', 'will be special', 'thrilled', "
    "'so excited', 'delighted to celebrate'.\n"
    "Use professional openers such as: "
    "'We would be delighted to accommodate your team —', "
    "'We look forward to supporting your event —', "
    "'We are pleased to assist with your upcoming dinner —'.\n\n"
    + _BASE_RULES
)

_SYSTEM_PROMPT_AGENCY = (
    "You are a hospitality events assistant writing one clear, operational sentence "
    "acknowledging a booking made by an event planner or agency. "
    "The tone must be professional, logistics-focused, and planner-friendly. "
    "Do NOT use emotional or celebratory language. "
    "FORBIDDEN openers and phrases: 'How wonderful', 'How lovely', 'How exciting', "
    "'celebration with us', 'thrilled', 'delighted to celebrate', 'such a special occasion'.\n"
    "Use clear, direct openers such as: "
    "'We can confirm availability for your client event —', "
    "'We are pleased to assist with the upcoming booking —'.\n\n"
    + _BASE_RULES
)

_SYSTEM_PROMPT_LUXURY = (
    "You are a hospitality events assistant writing one refined, understated sentence "
    "acknowledging an enquiry from a luxury or high-net-worth guest. "
    "The tone must be calm, gracious, and high-touch — never casual or over-enthusiastic. "
    "FORBIDDEN words and phrases: 'amazing', 'fantastic', 'brilliant', 'super', "
    "'totally', \"can't wait\", 'how exciting'.\n"
    "Use refined openers such as: "
    "'It would be a pleasure to welcome your guests —', "
    "'We look forward to hosting your private dinner —'.\n\n"
    + _BASE_RULES
)

_SYSTEM_PROMPT_UNKNOWN = (
    "You are a hospitality events assistant writing one neutral, professional sentence "
    "acknowledging a guest's enquiry. "
    "The tone should be courteous and professional. "
    "Do NOT use overly enthusiastic or celebratory language. "
    "Use neutral openers such as: "
    "'We would be pleased to assist with your event —', "
    "'We look forward to welcoming your guests —'.\n\n"
    + _BASE_RULES
)

_AUDIENCE_SYSTEM_PROMPTS: dict[str, str] = {
    "social":    _SYSTEM_PROMPT_SOCIAL,
    "corporate": _SYSTEM_PROMPT_CORPORATE,
    "agency":    _SYSTEM_PROMPT_AGENCY,
    "luxury":    _SYSTEM_PROMPT_LUXURY,
    "unknown":   _SYSTEM_PROMPT_UNKNOWN,
}

# ── Inline audience tone guard (RESP-076) ─────────────────────────────────────
# Applied after LLM generation to catch any prompt-instruction failures.
# Patterns mirror those in AudienceToneValidator (RESP-075) — kept inline here
# so the generator is self-contained and can be used before RESP-075 is merged.

_CORPORATE_AGENCY_GUARD: list[re.Pattern[str]] = [
    re.compile(r"\bhow\s+wonderful\b",               re.IGNORECASE),
    re.compile(r"\bhow\s+lovely\b",                  re.IGNORECASE),
    re.compile(r"\bsuch\s+a\s+special\s+occasion\b", re.IGNORECASE),
    re.compile(r"\bsuch\s+a\s+meaningful\s+occasion\b", re.IGNORECASE),
    re.compile(r"\bcelebration\s+with\s+us\b",       re.IGNORECASE),
    re.compile(r"\bwill\s+be\s+special\b",           re.IGNORECASE),
    re.compile(r"\bwhat\s+a\s+lovely\s+occasion\b",  re.IGNORECASE),
    re.compile(r"\bhow\s+exciting\b",                re.IGNORECASE),
    re.compile(r"\bthrilled\b",                      re.IGNORECASE),
    re.compile(r"\bdelighted\s+to\s+celebrate\b",    re.IGNORECASE),
]

_LUXURY_GUARD: list[re.Pattern[str]] = [
    re.compile(r"\bamazing\b",   re.IGNORECASE),
    re.compile(r"\bfantastic\b", re.IGNORECASE),
    re.compile(r"\bbrilliant\b", re.IGNORECASE),
    re.compile(r"\bsuper\b",     re.IGNORECASE),
    re.compile(r"\btotally\b",   re.IGNORECASE),
    re.compile(r"can'?t\s+wait", re.IGNORECASE),
    re.compile(r"\bhow\s+exciting\b", re.IGNORECASE),
]

_AUDIENCE_GUARDS: dict[str, list[re.Pattern[str]]] = {
    "corporate": _CORPORATE_AGENCY_GUARD,
    "agency":    _CORPORATE_AGENCY_GUARD,
    "luxury":    _LUXURY_GUARD,
}


def _audience_tone_guard(text: str, audience_type: str) -> bool:
    """Return True if the text passes the audience tone guard.

    Returns False if any forbidden pattern for the given audience type is found.
    Social and unknown types always pass — no restrictions apply.
    """
    patterns = _AUDIENCE_GUARDS.get((audience_type or "").lower(), [])
    return not any(p.search(text) for p in patterns)


def generate_warmth_sentence(
    api_key: str,
    occasion: str | None,
    audience_type: str | None,
    party_size: int | None,
    meal_period: str | None,
) -> str | None:
    """Call LLM for one short audience-appropriate opener sentence.

    Sends a minimal structured prompt — no raw guest message (RESP-041) — and
    selects an audience-specific system prompt (RESP-076) to constrain the LLM
    to produce contextually appropriate language.

    After generation, an inline audience tone guard is applied (RESP-076).
    If the output fails, None is returned — the caller falls back to the
    deterministic audience opener (RESP-074 / RESP-076 fallback).

    Args:
        api_key:       Anthropic API key.
        occasion:      Normalised occasion string (e.g. "birthday", "board dinner").
        audience_type: Audience type classification (e.g. "social", "corporate").
        party_size:    Number of guests.
        meal_period:   "dinner", "lunch", etc.

    Returns:
        Audience-appropriate opener sentence, or None on any failure or validation
        failure. Caller must also validate with WarmthSentenceValidator (RESP-040).
    """
    if not api_key:
        return None

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

    aud = (audience_type or "unknown").lower().strip()
    system_prompt = _AUDIENCE_SYSTEM_PROMPTS.get(aud, _SYSTEM_PROMPT_UNKNOWN)

    context_str = "\n".join(context_parts)
    user_prompt = (
        f"Write one audience-appropriate opener sentence (max 20 words).\n\n"
        f"{context_str}"
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=_WARMTH_MODEL,
            max_tokens=_WARMTH_MAX_TOKENS,
            temperature=_WARMTH_TEMPERATURE,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text.strip()
        if not text:
            return None

        # RESP-076: inline audience tone guard — drop on violation
        if not _audience_tone_guard(text, aud):
            logger.debug(
                "RESP-076: audience tone guard failed for %s opener — dropping", aud
            )
            return None

        return text
    except Exception as exc:  # noqa: BLE001
        logger.debug("Opener sentence LLM call failed: %s", exc)
        return None
