"""CONFIRM_AVAILABLE Warmth Sentence Generator (RESP-039 / RESP-041).

Generates an optional single warmth sentence for CONFIRM_AVAILABLE drafts.

Rules (RESP-039 / RESP-041):
  - Sends only structured context — no raw guest message.
  - Asks for exactly one sentence, max 20 words.
  - Returns the raw LLM output; caller must validate (RESP-040).

Usage::

    from app.modules.ai.confirm_available_warmth_generator import generate_warmth_sentence

    raw = generate_warmth_sentence(
        api_key="sk-ant-...",
        occasion="birthday",
        audience_type="social",
        party_size=12,
        meal_period="dinner",
    )
    # raw → "Wishing you a wonderful birthday celebration with your guests!"
"""

from __future__ import annotations

import logging

import anthropic

logger = logging.getLogger(__name__)

_WARMTH_MODEL = "claude-haiku-4-5-20251001"
_WARMTH_MAX_TOKENS = 60
_WARMTH_TEMPERATURE = 0.4

_SYSTEM_PROMPT = (
    "You are a hospitality events assistant writing one very short sentence "
    "that warmly acknowledges a guest's occasion. "
    "Rules:\n"
    "- Write exactly one sentence.\n"
    "- Maximum 20 words.\n"
    "- Base the sentence only on the provided context fields.\n"
    "- Do NOT mention: menus, dietary requirements, timing, arrival time, "
    "  booking forms, calls, pricing, minimum spend, room names, special touches, "
    "  availability, or any operational detail.\n"
    "- Do NOT describe or endorse the room, space, or venue suitability. "
    "  Forbidden phrases: 'excellent choice', 'perfect for', 'perfect setting', "
    "  'ideal', 'ideal for', 'ideal setting', 'well accommodated', 'excellent fit', "
    "  'intimate setting', 'excellent setting', 'would be ideal', 'ideally suited'.\n"
    "- Output only the warmth sentence — no preamble, no quotes."
)


def generate_warmth_sentence(
    api_key: str,
    occasion: str | None,
    audience_type: str | None,
    party_size: int | None,
    meal_period: str | None,
) -> str | None:
    """Call LLM for one short warmth sentence only.

    Sends a minimal structured prompt — no raw guest message (RESP-041) — and
    asks the model to produce a single sentence of at most 20 words acknowledging
    the occasion or audience type.

    Args:
        api_key:       Anthropic API key.
        occasion:      Normalised occasion string (e.g. "birthday", "corporate_dinner").
        audience_type: Audience type classification (e.g. "social", "corporate").
        party_size:    Number of guests.
        meal_period:   "dinner", "lunch", etc.

    Returns:
        Raw sentence text from the LLM, or None on any failure (no API key,
        no context, network error, empty response).
        The caller must validate the result with WarmthSentenceValidator (RESP-040).
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

    context_str = "\n".join(context_parts)
    user_prompt = (
        f"Write one warm sentence (max 20 words) acknowledging the guest's occasion.\n\n"
        f"{context_str}"
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=_WARMTH_MODEL,
            max_tokens=_WARMTH_MAX_TOKENS,
            temperature=_WARMTH_TEMPERATURE,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text.strip()
        return text if text else None
    except Exception as exc:  # noqa: BLE001
        logger.debug("Warmth sentence LLM call failed: %s", exc)
        return None
