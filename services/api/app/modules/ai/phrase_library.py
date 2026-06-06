"""Approved phrase library for draft response operational statements (RESP-007).

Provides controlled phrase snippets for high-risk response situations where
consistent, commercially-safe wording is required.  Phrases are keyed by
response goal or context type and are included in the V4 draft prompt as
per-goal guidance.

Usage::

    from app.modules.ai.phrase_library import APPROVED_PHRASES, get_phrase_guidance

    phrases = get_phrase_guidance("CONFIRM_AVAILABLE")
    # → "Approved opening: 'Thank you for your enquiry — ..."
"""

from __future__ import annotations

# ── Approved phrase constants ──────────────────────────────────────────────────

# Per response goal — one approved opening/framing phrase each.
PHRASE_CONFIRM_AVAILABLE = (
    "Thank you for your enquiry — I'm delighted to let you know that "
    "the date is available for your event."
)

PHRASE_RESPOND_UNAVAILABLE = (
    "Thank you for your enquiry. Unfortunately, we are fully booked "
    "for the requested date."
)

PHRASE_ACKNOWLEDGE_AND_CHECK = (
    "Thank you for your enquiry — I'll check availability for the requested "
    "date and come back to you shortly."
)

PHRASE_REQUEST_DATE_CONFIRMATION = (
    "We'd love to host your event — could you confirm the exact date "
    "you have in mind so we can check availability?"
)

PHRASE_REQUEST_MISSING_INFORMATION = (
    "Thank you for getting in touch — I just have a couple of quick "
    "questions before we can confirm availability."
)

PHRASE_REQUEST_WEBFORM = (
    "Thank you for your enquiry — to ensure we capture all the details "
    "for your event, could I ask you to complete our short enquiry form?"
)

PHRASE_ESCALATE_TO_HUMAN = (
    "Thank you for reaching out — a member of our events team will "
    "review your enquiry and be in touch shortly."
)

# Mandatory spend wording — must describe the spend as mandatory, never optional.
PHRASE_MINIMUM_SPEND = (
    "Please note that our minimum spend of £{amount} is a mandatory "
    "requirement for this event."
)

# ── Lookup ─────────────────────────────────────────────────────────────────────

APPROVED_PHRASES: dict[str, str] = {
    "CONFIRM_AVAILABLE": PHRASE_CONFIRM_AVAILABLE,
    "RESPOND_UNAVAILABLE": PHRASE_RESPOND_UNAVAILABLE,
    "ACKNOWLEDGE_AND_CHECK_AVAILABILITY": PHRASE_ACKNOWLEDGE_AND_CHECK,
    "REQUEST_DATE_CONFIRMATION": PHRASE_REQUEST_DATE_CONFIRMATION,
    "REQUEST_MISSING_INFORMATION": PHRASE_REQUEST_MISSING_INFORMATION,
    "REQUEST_WEBFORM": PHRASE_REQUEST_WEBFORM,
    "ESCALATE_TO_HUMAN": PHRASE_ESCALATE_TO_HUMAN,
    "MINIMUM_SPEND": PHRASE_MINIMUM_SPEND,
}


def get_phrase_guidance(response_goal: str) -> str:
    """Return a formatted approved-phrase guidance string for the given response goal.

    Returns an empty string when no phrase is defined for the goal.
    """
    phrase = APPROVED_PHRASES.get(response_goal)
    if not phrase:
        return ""
    return f"Approved opening phrase for this goal: \"{phrase}\"\n"
