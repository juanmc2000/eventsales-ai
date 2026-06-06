"""Response Content Policy (RESP-010).

Defines which topics, sections, and claims are allowed or forbidden for each
response goal.  All decisions are deterministic — no LLM calls are made.

Usage::

    from app.modules.enquiries.response_content_policy import ResponseContentPolicy

    policy = ResponseContentPolicy.for_goal("CONFIRM_AVAILABLE")
    # policy.allowed_topics   → ["acknowledgement", "availability_confirmation", ...]
    # policy.forbidden_topics → ["exact_timing_confirmation", "menu_discussion", ...]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Topic constants ────────────────────────────────────────────────────────────

# Allowed topic keys
TOPIC_ACKNOWLEDGEMENT = "acknowledgement"
TOPIC_AVAILABILITY_CONFIRMATION = "availability_confirmation"
TOPIC_AVAILABILITY_CHECK_PENDING = "availability_check_pending"
TOPIC_UNAVAILABILITY_STATEMENT = "unavailability_statement"
TOPIC_DATE_SUMMARY = "date_summary"
TOPIC_GUEST_COUNT_SUMMARY = "guest_count_summary"
TOPIC_OCCASION_SUMMARY = "occasion_summary"
TOPIC_MEAL_PERIOD_SUMMARY = "meal_period_summary"
TOPIC_VENUE_ROOM_SUITABILITY = "venue_room_suitability"
TOPIC_MINIMUM_SPEND_MANDATORY = "minimum_spend_mandatory"
TOPIC_SIMPLE_NEXT_STEP = "simple_next_step"
TOPIC_POLITE_CLOSING = "polite_closing"
TOPIC_SIGNOFF = "signoff"
TOPIC_APPROVED_CLARIFICATION_QUESTIONS = "approved_clarification_questions"
TOPIC_DATE_CONFIRMATION_QUESTION = "date_confirmation_question"
TOPIC_WEBFORM_REQUEST = "webform_request"

# Forbidden topic keys
TOPIC_EXACT_TIMING_CONFIRMATION = "exact_timing_confirmation"
TOPIC_MENU_DISCUSSION = "menu_discussion"
TOPIC_DIETARY_REQUIREMENTS = "dietary_requirements"
TOPIC_SPECIAL_TOUCHES = "special_touches"
TOPIC_CALL_SCHEDULING = "call_scheduling"
TOPIC_ALTERNATIVE_DATES = "alternative_dates"
TOPIC_ALTERNATIVE_ROOMS = "alternative_rooms"
TOPIC_CALENDAR_CHECKING = "calendar_checking"
TOPIC_HOSTING_LANGUAGE = "hosting_language"
TOPIC_AVAILABILITY_IMPLICATION = "availability_implication"
TOPIC_INVENTED_QUESTIONS = "invented_questions"
TOPIC_INVENTED_SLA = "invented_sla"
TOPIC_FAKE_LINKS = "fake_links"
TOPIC_SPEND_SOFT_LANGUAGE = "spend_soft_language"


# ── Policy dataclass ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ContentPolicy:
    """Allowed and forbidden topic sets for a specific response goal.

    Attributes:
        response_goal:   The goal this policy applies to.
        allowed_topics:  Topics the LLM may include in the draft.
        forbidden_topics: Topics that must not appear in the draft.
        policy_notes:    Human-readable rationale for key decisions.
    """

    response_goal: str
    allowed_topics: tuple[str, ...]
    forbidden_topics: tuple[str, ...]
    policy_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_goal": self.response_goal,
            "allowed_topics": list(self.allowed_topics),
            "forbidden_topics": list(self.forbidden_topics),
            "policy_notes": self.policy_notes,
        }

    def is_allowed(self, topic: str) -> bool:
        return topic in self.allowed_topics

    def is_forbidden(self, topic: str) -> bool:
        return topic in self.forbidden_topics


# ── Per-goal policies ──────────────────────────────────────────────────────────

_POLICY_CONFIRM_AVAILABLE = ContentPolicy(
    response_goal="CONFIRM_AVAILABLE",
    allowed_topics=(
        TOPIC_ACKNOWLEDGEMENT,
        TOPIC_AVAILABILITY_CONFIRMATION,
        TOPIC_DATE_SUMMARY,
        TOPIC_GUEST_COUNT_SUMMARY,
        TOPIC_OCCASION_SUMMARY,
        TOPIC_VENUE_ROOM_SUITABILITY,
        TOPIC_MINIMUM_SPEND_MANDATORY,
        TOPIC_SIMPLE_NEXT_STEP,
        TOPIC_POLITE_CLOSING,
        TOPIC_SIGNOFF,
    ),
    forbidden_topics=(
        TOPIC_EXACT_TIMING_CONFIRMATION,
        TOPIC_MENU_DISCUSSION,
        TOPIC_DIETARY_REQUIREMENTS,
        TOPIC_SPECIAL_TOUCHES,
        TOPIC_CALL_SCHEDULING,
        TOPIC_ALTERNATIVE_DATES,
        TOPIC_HOSTING_LANGUAGE,
        TOPIC_INVENTED_QUESTIONS,
        TOPIC_INVENTED_SLA,
        TOPIC_FAKE_LINKS,
        TOPIC_SPEND_SOFT_LANGUAGE,
    ),
    policy_notes=(
        "First-response confirmation. Say only what is confirmed. "
        "Do not invite follow-up discussion of timing, menus, or special arrangements."
    ),
)

_POLICY_RESPOND_UNAVAILABLE = ContentPolicy(
    response_goal="RESPOND_UNAVAILABLE",
    allowed_topics=(
        TOPIC_ACKNOWLEDGEMENT,
        TOPIC_UNAVAILABILITY_STATEMENT,
        TOPIC_POLITE_CLOSING,
        TOPIC_SIGNOFF,
    ),
    forbidden_topics=(
        TOPIC_ALTERNATIVE_DATES,
        TOPIC_ALTERNATIVE_ROOMS,
        TOPIC_CALENDAR_CHECKING,
        TOPIC_HOSTING_LANGUAGE,
        TOPIC_AVAILABILITY_IMPLICATION,
        TOPIC_EXACT_TIMING_CONFIRMATION,
        TOPIC_MENU_DISCUSSION,
        TOPIC_INVENTED_QUESTIONS,
        TOPIC_INVENTED_SLA,
        TOPIC_CALL_SCHEDULING,
        TOPIC_FAKE_LINKS,
    ),
    policy_notes=(
        "Slot is confirmed unavailable. Acknowledge warmly and close. "
        "Do not suggest alternatives — the system has not identified any."
    ),
)

_POLICY_ACKNOWLEDGE_AND_CHECK = ContentPolicy(
    response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
    allowed_topics=(
        TOPIC_ACKNOWLEDGEMENT,
        TOPIC_AVAILABILITY_CHECK_PENDING,
        TOPIC_DATE_SUMMARY,
        TOPIC_GUEST_COUNT_SUMMARY,
        TOPIC_OCCASION_SUMMARY,
        TOPIC_MEAL_PERIOD_SUMMARY,
        TOPIC_POLITE_CLOSING,
        TOPIC_SIGNOFF,
    ),
    forbidden_topics=(
        TOPIC_HOSTING_LANGUAGE,
        TOPIC_AVAILABILITY_IMPLICATION,
        TOPIC_AVAILABILITY_CONFIRMATION,
        TOPIC_EXACT_TIMING_CONFIRMATION,
        TOPIC_MENU_DISCUSSION,
        TOPIC_DIETARY_REQUIREMENTS,
        TOPIC_SPECIAL_TOUCHES,
        TOPIC_CALL_SCHEDULING,
        TOPIC_ALTERNATIVE_DATES,
        TOPIC_INVENTED_QUESTIONS,
        TOPIC_INVENTED_SLA,
        TOPIC_FAKE_LINKS,
    ),
    policy_notes=(
        "No availability check has been performed. Say we will check and come back. "
        "Do not imply hosting capability or discuss venue specifics as if confirmed."
    ),
)

_POLICY_REQUEST_MISSING_INFORMATION = ContentPolicy(
    response_goal="REQUEST_MISSING_INFORMATION",
    allowed_topics=(
        TOPIC_ACKNOWLEDGEMENT,
        TOPIC_APPROVED_CLARIFICATION_QUESTIONS,
        TOPIC_POLITE_CLOSING,
        TOPIC_SIGNOFF,
    ),
    forbidden_topics=(
        TOPIC_INVENTED_QUESTIONS,
        TOPIC_HOSTING_LANGUAGE,
        TOPIC_AVAILABILITY_CONFIRMATION,
        TOPIC_AVAILABILITY_IMPLICATION,
        TOPIC_ALTERNATIVE_DATES,
        TOPIC_EXACT_TIMING_CONFIRMATION,
        TOPIC_MENU_DISCUSSION,
        TOPIC_INVENTED_SLA,
        TOPIC_FAKE_LINKS,
    ),
    policy_notes=(
        "Ask only the approved clarification questions. "
        "Do not ask additional questions or introduce topics not in the question list."
    ),
)

_POLICY_REQUEST_DATE_CONFIRMATION = ContentPolicy(
    response_goal="REQUEST_DATE_CONFIRMATION",
    allowed_topics=(
        TOPIC_ACKNOWLEDGEMENT,
        TOPIC_DATE_CONFIRMATION_QUESTION,
        TOPIC_POLITE_CLOSING,
        TOPIC_SIGNOFF,
    ),
    forbidden_topics=(
        TOPIC_AVAILABILITY_CONFIRMATION,
        TOPIC_AVAILABILITY_IMPLICATION,
        TOPIC_HOSTING_LANGUAGE,
        TOPIC_EXACT_TIMING_CONFIRMATION,
        TOPIC_MENU_DISCUSSION,
        TOPIC_INVENTED_QUESTIONS,
        TOPIC_INVENTED_SLA,
        TOPIC_FAKE_LINKS,
        TOPIC_ALTERNATIVE_DATES,
    ),
    policy_notes=(
        "Date is ambiguous. Ask only the date confirmation question. "
        "Do not assume or confirm availability."
    ),
)

_POLICY_REQUEST_WEBFORM = ContentPolicy(
    response_goal="REQUEST_WEBFORM",
    allowed_topics=(
        TOPIC_ACKNOWLEDGEMENT,
        TOPIC_WEBFORM_REQUEST,
        TOPIC_POLITE_CLOSING,
        TOPIC_SIGNOFF,
    ),
    forbidden_topics=(
        TOPIC_FAKE_LINKS,
        TOPIC_AVAILABILITY_CONFIRMATION,
        TOPIC_AVAILABILITY_IMPLICATION,
        TOPIC_HOSTING_LANGUAGE,
        TOPIC_INVENTED_QUESTIONS,
        TOPIC_INVENTED_SLA,
        TOPIC_ALTERNATIVE_DATES,
        TOPIC_EXACT_TIMING_CONFIRMATION,
        TOPIC_MENU_DISCUSSION,
    ),
    policy_notes=(
        "Direct the guest to the webform only if a real URL is in the context. "
        "No placeholder links, no invented booking-form text."
    ),
)

_POLICY_ESCALATE_TO_HUMAN = ContentPolicy(
    response_goal="ESCALATE_TO_HUMAN",
    allowed_topics=(
        TOPIC_ACKNOWLEDGEMENT,
        TOPIC_POLITE_CLOSING,
        TOPIC_SIGNOFF,
    ),
    forbidden_topics=(
        TOPIC_AVAILABILITY_CONFIRMATION,
        TOPIC_AVAILABILITY_IMPLICATION,
        TOPIC_HOSTING_LANGUAGE,
        TOPIC_EXACT_TIMING_CONFIRMATION,
        TOPIC_MENU_DISCUSSION,
        TOPIC_INVENTED_QUESTIONS,
        TOPIC_INVENTED_SLA,
        TOPIC_ALTERNATIVE_DATES,
        TOPIC_FAKE_LINKS,
    ),
    policy_notes=(
        "Acknowledge and hand off. The team will follow up. "
        "Do not commit to any specifics."
    ),
)


# ── Registry ───────────────────────────────────────────────────────────────────

_POLICIES: dict[str, ContentPolicy] = {
    "CONFIRM_AVAILABLE": _POLICY_CONFIRM_AVAILABLE,
    "RESPOND_UNAVAILABLE": _POLICY_RESPOND_UNAVAILABLE,
    "ACKNOWLEDGE_AND_CHECK_AVAILABILITY": _POLICY_ACKNOWLEDGE_AND_CHECK,
    "REQUEST_MISSING_INFORMATION": _POLICY_REQUEST_MISSING_INFORMATION,
    "REQUEST_DATE_CONFIRMATION": _POLICY_REQUEST_DATE_CONFIRMATION,
    "REQUEST_WEBFORM": _POLICY_REQUEST_WEBFORM,
    "ESCALATE_TO_HUMAN": _POLICY_ESCALATE_TO_HUMAN,
}


# ── Public API ─────────────────────────────────────────────────────────────────


class ResponseContentPolicy:
    """Deterministic content governance for each response goal.

    Call ResponseContentPolicy.for_goal(goal) to retrieve the ContentPolicy
    for a given response goal.
    """

    @staticmethod
    def for_goal(response_goal: str) -> ContentPolicy:
        """Return the ContentPolicy for the given response goal.

        Falls back to a safe deny-all policy for unknown goals.
        """
        return _POLICIES.get(response_goal, _unknown_policy(response_goal))

    @staticmethod
    def all_goals() -> list[str]:
        """Return all response goals that have an explicit policy."""
        return list(_POLICIES.keys())


def _unknown_policy(response_goal: str) -> ContentPolicy:
    """Deny-all fallback for unrecognised goals."""
    return ContentPolicy(
        response_goal=response_goal,
        allowed_topics=(TOPIC_ACKNOWLEDGEMENT, TOPIC_SIGNOFF),
        forbidden_topics=(
            TOPIC_AVAILABILITY_CONFIRMATION,
            TOPIC_HOSTING_LANGUAGE,
            TOPIC_INVENTED_QUESTIONS,
            TOPIC_INVENTED_SLA,
            TOPIC_FAKE_LINKS,
        ),
        policy_notes=f"Unknown response goal '{response_goal}' — conservative deny-all policy applied.",
    )
