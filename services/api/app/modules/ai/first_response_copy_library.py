"""First Response Copy Library (RESP-017).

Approved deterministic copy blocks for operationally sensitive first-response
statements.  The LLM must use these blocks verbatim (with variable interpolation)
rather than inventing operational wording.

Design rules:
- Every block is a string template using {variable} placeholders.
- Required variables are declared in ``REQUIRED_VARS`` per block key.
- Rendering fails safely if a required variable is missing (raises ValueError).
- No block contains: menu wording, special-touches language, call-scheduling
  invitations, or alternative-date suggestions.
- Blocks are keyed by logical name, not by response goal, so they compose cleanly.

Usage::

    from app.modules.ai.first_response_copy_library import FirstResponseCopyLibrary

    text = FirstResponseCopyLibrary.render("availability_confirmed", {
        "meal_period": "dinner",
        "event_date": "12th June",
    })
"""

from __future__ import annotations

# ── Copy block keys ───────────────────────────────────────────────────────────

BLOCK_AVAILABILITY_CONFIRMED = "availability_confirmed"
BLOCK_AVAILABILITY_NOT_CHECKED = "availability_not_checked"
BLOCK_AVAILABILITY_UNAVAILABLE = "availability_unavailable"
BLOCK_MINIMUM_SPEND = "minimum_spend"
BLOCK_BOOKING_NEXT_STEP = "booking_next_step"
# RESP-030: deterministic next-step for CONFIRM_AVAILABLE — no additional detail requests
BLOCK_CONFIRM_AVAILABLE_NEXT_STEP = "confirm_available_next_step"
BLOCK_AVAILABILITY_CHECK_NEXT_STEP = "availability_check_next_step"
BLOCK_CLARIFICATION_NEXT_STEP = "clarification_next_step"
BLOCK_SIGNOFF = "signoff"

# ── Template registry ──────────────────────────────────────────────────────────

_TEMPLATES: dict[str, str] = {
    # Confirmed available opening statement
    BLOCK_AVAILABILITY_CONFIRMED: (
        "Thank you for your enquiry — I'm delighted to confirm that we have availability "
        "for {meal_period} on {event_date}."
    ),
    # Availability not yet checked — acknowledge and promise follow-up
    BLOCK_AVAILABILITY_NOT_CHECKED: (
        "Thank you for your enquiry — I'll check availability for {meal_period} on "
        "{event_date} and come back to you shortly."
    ),
    # Confirmed unavailable opening statement
    BLOCK_AVAILABILITY_UNAVAILABLE: (
        "Thank you for your enquiry. Unfortunately, we are fully booked for "
        "{meal_period} on {event_date}."
    ),
    # Mandatory minimum spend statement — must use mandatory framing only
    BLOCK_MINIMUM_SPEND: (
        "Please note that our mandatory minimum spend for this space is {spend_amount}."
    ),
    # Next step after confirming availability (booking process)
    BLOCK_BOOKING_NEXT_STEP: (
        "To proceed, please reply with any additional details and our events team "
        "will be in touch to confirm the booking."
    ),
    # RESP-030: constrained next-step for CONFIRM_AVAILABLE — no extra detail requests
    # Communicates only: reply to proceed, events team will finalise booking.
    # Must not invite menu discussion, timing, special requests, or call scheduling.
    BLOCK_CONFIRM_AVAILABLE_NEXT_STEP: (
        "Please reply to this email to proceed and our events team will be in touch "
        "to finalise the booking."
    ),
    # Next step when availability is not yet checked
    BLOCK_AVAILABILITY_CHECK_NEXT_STEP: (
        "I will check availability and follow up with you as soon as possible."
    ),
    # Next step when clarification is required before checking availability
    BLOCK_CLARIFICATION_NEXT_STEP: (
        "Once we have the above details, we will be able to check availability "
        "and come back to you promptly."
    ),
    # Signoff guidance — persona name interpolated
    BLOCK_SIGNOFF: (
        "Warm regards,\n{persona_name}"
    ),
}

# Required variables per block key (empty set = no required vars)
_REQUIRED_VARS: dict[str, frozenset[str]] = {
    BLOCK_AVAILABILITY_CONFIRMED: frozenset({"meal_period", "event_date"}),
    BLOCK_AVAILABILITY_NOT_CHECKED: frozenset({"meal_period", "event_date"}),
    BLOCK_AVAILABILITY_UNAVAILABLE: frozenset({"meal_period", "event_date"}),
    BLOCK_MINIMUM_SPEND: frozenset({"spend_amount"}),
    BLOCK_BOOKING_NEXT_STEP: frozenset(),
    BLOCK_CONFIRM_AVAILABLE_NEXT_STEP: frozenset(),
    BLOCK_AVAILABILITY_CHECK_NEXT_STEP: frozenset(),
    BLOCK_CLARIFICATION_NEXT_STEP: frozenset(),
    BLOCK_SIGNOFF: frozenset({"persona_name"}),
}


# ── Public API ─────────────────────────────────────────────────────────────────


class FirstResponseCopyLibrary:
    """Registry of approved first-response copy blocks.

    All blocks are deterministic — no LLM calls are made here.
    """

    @classmethod
    def all_keys(cls) -> list[str]:
        """Return all registered copy block keys."""
        return list(_TEMPLATES.keys())

    @classmethod
    def required_vars(cls, key: str) -> frozenset[str]:
        """Return the set of variable names required to render ``key``."""
        if key not in _REQUIRED_VARS:
            raise KeyError(f"Unknown copy block key: {key!r}")
        return _REQUIRED_VARS[key]

    @classmethod
    def render(cls, key: str, variables: dict[str, str] | None = None) -> str:
        """Render copy block ``key`` with ``variables``.

        Args:
            key:       One of the ``BLOCK_*`` constants.
            variables: Mapping of placeholder names to values.

        Returns:
            Rendered string with all placeholders substituted.

        Raises:
            KeyError:   If ``key`` is not in the registry.
            ValueError: If a required variable is missing from ``variables``.
        """
        if key not in _TEMPLATES:
            raise KeyError(f"Unknown copy block key: {key!r}")

        vars_ = variables or {}
        required = _REQUIRED_VARS.get(key, frozenset())
        missing = required - set(vars_.keys())
        if missing:
            raise ValueError(
                f"Copy block {key!r} requires variables {sorted(missing)} "
                f"but they were not provided."
            )

        return _TEMPLATES[key].format(**vars_)

    @classmethod
    def render_safe(cls, key: str, variables: dict[str, str] | None = None) -> str | None:
        """Like ``render`` but returns ``None`` on any error instead of raising."""
        try:
            return cls.render(key, variables)
        except (KeyError, ValueError):
            return None
