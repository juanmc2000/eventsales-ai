"""First Response Copy Library (RESP-017, updated RESP-037, RESP-043, RESP-051, RESP-057).

Approved deterministic copy blocks for operationally sensitive first-response
statements.  The LLM must use these blocks verbatim (with variable interpolation)
rather than inventing operational wording.

Design rules:
- Every block is a string template using {variable} placeholders.
- Required variables are declared in ``REQUIRED_VARS`` per block key.
- Rendering fails safely if a required variable is missing (raises ValueError).
- No block contains: menu wording, special-touches language, call-scheduling
  invitations.
- Blocks are keyed by logical name, not by response goal, so they compose cleanly.

RESP-037: Added ``confirm_available_next_step`` — a strict next-step block for
CONFIRM_AVAILABLE responses that prevents LLM from inventing booking-process
wording involving menus, dietary, special touches, calls, or booking forms.

RESP-043: Added alternative-date unavailability blocks (zero, one, two alternatives).
These blocks are rendered deterministically when a requested date is unavailable —
the LLM must use these verbatim and must not invent alternatives beyond what is
explicitly provided.

Usage::

    from app.modules.ai.first_response_copy_library import FirstResponseCopyLibrary

    text = FirstResponseCopyLibrary.render("availability_confirmed", {
        "meal_period": "dinner",
        "event_date": "12th June",
    })
"""

from __future__ import annotations

from app.modules.enquiries.date_formatting import format_event_date

# ── Copy block keys ───────────────────────────────────────────────────────────

BLOCK_AVAILABILITY_CONFIRMED = "availability_confirmed"
BLOCK_AVAILABILITY_NOT_CHECKED = "availability_not_checked"
BLOCK_AVAILABILITY_UNAVAILABLE = "availability_unavailable"
BLOCK_MINIMUM_SPEND = "minimum_spend"
BLOCK_BOOKING_NEXT_STEP = "booking_next_step"
# RESP-037: strict CONFIRM_AVAILABLE next step — no menu/special-touches/calls/forms
BLOCK_CONFIRM_AVAILABLE_NEXT_STEP = "confirm_available_next_step"
BLOCK_AVAILABILITY_CHECK_NEXT_STEP = "availability_check_next_step"
BLOCK_CLARIFICATION_NEXT_STEP = "clarification_next_step"
BLOCK_SIGNOFF = "signoff"
# RESP-043: alternative-date unavailability blocks — rendered deterministically
# from confirmed available alternatives only; LLM must not invent alternatives
BLOCK_UNAVAILABLE_NO_ALTERNATIVES = "unavailable_no_alternatives"
BLOCK_UNAVAILABLE_ONE_ALTERNATIVE = "unavailable_one_alternative"
BLOCK_UNAVAILABLE_TWO_ALTERNATIVES = "unavailable_two_alternatives"

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
    # RESP-037: strict CONFIRM_AVAILABLE next step — no menu/dietary/special-touches/calls/forms
    BLOCK_CONFIRM_AVAILABLE_NEXT_STEP: (
        "Please reply to this email to confirm you would like to proceed, and our "
        "events team will be in touch to finalise the booking."
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
    # RESP-043/RESP-051: unavailable — no confirmed alternatives available
    # Warmer tone: short empathy sentence added, remains concise
    BLOCK_UNAVAILABLE_NO_ALTERNATIVES: (
        "Thank you for your enquiry. Unfortunately, we are fully booked for "
        "{meal_period} on {requested_date}. We hope to be able to welcome you "
        "on another occasion."
    ),
    # RESP-043/RESP-051: unavailable — one confirmed alternative offered
    # States unavailable date, offers confirmed alternative, invites guest to confirm
    BLOCK_UNAVAILABLE_ONE_ALTERNATIVE: (
        "Thank you for your enquiry. Unfortunately, we are fully booked for "
        "{meal_period} on {requested_date}. However, we do have availability "
        "for {meal_period} on {alternative_date} — would that date work for you?"
    ),
    # RESP-043/RESP-051: unavailable — two confirmed alternatives offered
    # States unavailable date, offers both alternatives, invites guest to confirm
    BLOCK_UNAVAILABLE_TWO_ALTERNATIVES: (
        "Thank you for your enquiry. Unfortunately, we are fully booked for "
        "{meal_period} on {requested_date}. However, we do have availability "
        "for {meal_period} on {alternative_date_1} or {alternative_date_2} — "
        "would either of those dates work for you?"
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
    BLOCK_UNAVAILABLE_NO_ALTERNATIVES: frozenset({"meal_period", "requested_date"}),
    BLOCK_UNAVAILABLE_ONE_ALTERNATIVE: frozenset({"meal_period", "requested_date", "alternative_date"}),
    BLOCK_UNAVAILABLE_TWO_ALTERNATIVES: frozenset({"meal_period", "requested_date", "alternative_date_1", "alternative_date_2"}),
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

        # RESP-057: auto-format ISO date strings to natural hospitality format
        # so that callers never need to pre-format dates before rendering.
        formatted_vars = {
            k: format_event_date(v) if isinstance(v, str) else v
            for k, v in vars_.items()
        }
        return _TEMPLATES[key].format(**formatted_vars)

    @classmethod
    def render_safe(cls, key: str, variables: dict[str, str] | None = None) -> str | None:
        """Like ``render`` but returns ``None`` on any error instead of raising."""
        try:
            return cls.render(key, variables)
        except (KeyError, ValueError):
            return None
