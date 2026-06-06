"""Response Section Builder (RESP-011, updated RESP-016).

Deterministically specifies which sections the draft LLM is allowed to write,
which are required, and which must be omitted.  No LLM calls are made.

The builder narrows the model's freedom from "write a response" to
"assemble exactly these sections in this order".

RESP-016: Replaced generic ``simple_next_step`` with deterministic,
goal-specific next-step section types so the model cannot invent arbitrary
closing copy:

  - CONFIRM_AVAILABLE            → ``booking_next_step``
  - ACKNOWLEDGE_AND_CHECK_AVAILABILITY → ``availability_check_next_step``
  - RESPOND_UNAVAILABLE          → no next-step section
  - REQUEST_MISSING_INFORMATION  → ``clarification_next_step``

Usage::

    from app.modules.enquiries.response_section_builder import ResponseSectionBuilder

    result = ResponseSectionBuilder.build("CONFIRM_AVAILABLE", time_confirmed=False)
    # result.allowed_sections  → ["opening", "enquiry_summary", ...]
    # result.required_sections → ["opening", "minimum_spend", "signoff"]
    # result.omitted_sections  → ["exact_timing", "menu_discussion", ...]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Section name constants ────────────────────────────────────────────────────

SECTION_OPENING = "opening"
SECTION_ENQUIRY_SUMMARY = "enquiry_summary"
SECTION_AVAILABILITY_CONFIRMATION = "availability_confirmation"
SECTION_AVAILABILITY_CHECK_PENDING = "availability_check_pending"
SECTION_UNAVAILABILITY_ACKNOWLEDGEMENT = "unavailability_acknowledgement"
SECTION_ROOM_SUITABILITY = "room_suitability"
SECTION_MINIMUM_SPEND = "minimum_spend"
SECTION_CLARIFICATION_QUESTIONS = "clarification_questions"
SECTION_DATE_CONFIRMATION_QUESTION = "date_confirmation_question"
SECTION_WEBFORM_REDIRECT = "webform_redirect"
# RESP-016: deterministic next-step sections replace generic simple_next_step
SECTION_BOOKING_NEXT_STEP = "booking_next_step"
SECTION_AVAILABILITY_CHECK_NEXT_STEP = "availability_check_next_step"
SECTION_CLARIFICATION_NEXT_STEP = "clarification_next_step"
SECTION_SIGNOFF = "signoff"

# Sections that are forbidden by policy but named for explicit omission messages
SECTION_EXACT_TIMING = "exact_timing"
SECTION_MENU_DISCUSSION = "menu_discussion"
SECTION_SPECIAL_TOUCHES = "special_touches"
SECTION_CALL_SCHEDULING = "call_scheduling"
SECTION_ALTERNATIVE_DATES = "alternative_dates"
SECTION_HOSTING_LANGUAGE = "hosting_language"
SECTION_INVENTED_QUESTIONS = "invented_questions"
SECTION_INVENTED_SLA = "invented_sla"


# ── Output dataclass ───────────────────────────────────────────────────────────


@dataclass
class SectionPlan:
    """Output from ResponseSectionBuilder.build().

    Attributes:
        response_goal:     The goal this plan was built for.
        allowed_sections:  Sections the LLM may write (ordered).
        required_sections: Sections the LLM must include.
        omitted_sections:  Sections the LLM must not write.
        section_reasoning: Human-readable note per omitted section.
    """

    response_goal: str
    allowed_sections: list[str] = field(default_factory=list)
    required_sections: list[str] = field(default_factory=list)
    omitted_sections: list[str] = field(default_factory=list)
    section_reasoning: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_goal": self.response_goal,
            "allowed_sections": self.allowed_sections,
            "required_sections": self.required_sections,
            "omitted_sections": self.omitted_sections,
            "section_reasoning": self.section_reasoning,
        }


# ── Builder ────────────────────────────────────────────────────────────────────


class ResponseSectionBuilder:
    """Builds a SectionPlan for a given response goal and context flags.

    Context flags gate optional sections:
      - has_minimum_spend:     include minimum_spend section when True
      - has_room_context:      include room_suitability section when True
      - time_confirmed:        allow exact_timing section only when True
      - alternatives_provided: allow alternative_dates section only when True
      - has_clarification_questions: include clarification_questions when True
      - has_webform_url:       include webform_redirect only when True
    """

    @classmethod
    def build(
        cls,
        response_goal: str,
        has_minimum_spend: bool = False,
        has_room_context: bool = False,
        time_confirmed: bool = False,
        alternatives_provided: bool = False,
        has_clarification_questions: bool = False,
        has_webform_url: bool = False,
    ) -> SectionPlan:
        """Build a SectionPlan for the given goal and context flags."""
        method = _BUILDERS.get(response_goal)
        if method is None:
            return cls._build_unknown(response_goal)
        return method(
            has_minimum_spend=has_minimum_spend,
            has_room_context=has_room_context,
            time_confirmed=time_confirmed,
            alternatives_provided=alternatives_provided,
            has_clarification_questions=has_clarification_questions,
            has_webform_url=has_webform_url,
        )

    # ── Per-goal builders ─────────────────────────────────────────────────────

    @staticmethod
    def _build_confirm_available(
        has_minimum_spend: bool,
        has_room_context: bool,
        time_confirmed: bool,
        **_: Any,
    ) -> SectionPlan:
        allowed = [
            SECTION_OPENING,
            SECTION_ENQUIRY_SUMMARY,
            SECTION_AVAILABILITY_CONFIRMATION,
        ]
        required = [SECTION_OPENING, SECTION_AVAILABILITY_CONFIRMATION, SECTION_SIGNOFF]

        if has_room_context:
            allowed.append(SECTION_ROOM_SUITABILITY)
        if has_minimum_spend:
            allowed.append(SECTION_MINIMUM_SPEND)
            required.append(SECTION_MINIMUM_SPEND)

        # RESP-016: booking_next_step replaces generic simple_next_step
        allowed.extend([SECTION_BOOKING_NEXT_STEP, SECTION_SIGNOFF])

        omitted = [
            SECTION_EXACT_TIMING,
            SECTION_MENU_DISCUSSION,
            SECTION_SPECIAL_TOUCHES,
            SECTION_CALL_SCHEDULING,
            SECTION_ALTERNATIVE_DATES,
            SECTION_INVENTED_QUESTIONS,
            SECTION_INVENTED_SLA,
        ]
        if time_confirmed:
            omitted.remove(SECTION_EXACT_TIMING)
            allowed.insert(3, SECTION_EXACT_TIMING)

        reasoning: dict[str, str] = {}
        if SECTION_EXACT_TIMING in omitted:
            reasoning[SECTION_EXACT_TIMING] = (
                "Time was not confirmed by the venue — state only as a preference to discuss."
            )
        reasoning[SECTION_MENU_DISCUSSION] = "First response must not open menu negotiation."
        reasoning[SECTION_SPECIAL_TOUCHES] = "Special arrangements are out of scope for first response."
        reasoning[SECTION_CALL_SCHEDULING] = "No call has been scheduled — do not invite one."
        reasoning[SECTION_ALTERNATIVE_DATES] = "Slot is confirmed available — no alternatives needed."
        reasoning[SECTION_INVENTED_QUESTIONS] = "No clarification questions were provided — ask none."
        reasoning[SECTION_INVENTED_SLA] = "No SLA has been committed — do not invent one."

        return SectionPlan(
            response_goal="CONFIRM_AVAILABLE",
            allowed_sections=allowed,
            required_sections=required,
            omitted_sections=omitted,
            section_reasoning=reasoning,
        )

    @staticmethod
    def _build_respond_unavailable(
        alternatives_provided: bool,
        **_: Any,
    ) -> SectionPlan:
        allowed = [
            SECTION_OPENING,
            SECTION_UNAVAILABILITY_ACKNOWLEDGEMENT,
            SECTION_SIGNOFF,
        ]
        required = [
            SECTION_OPENING,
            SECTION_UNAVAILABILITY_ACKNOWLEDGEMENT,
            SECTION_SIGNOFF,
        ]

        omitted = [
            SECTION_ALTERNATIVE_DATES,
            SECTION_HOSTING_LANGUAGE,
            SECTION_EXACT_TIMING,
            SECTION_MENU_DISCUSSION,
            SECTION_INVENTED_QUESTIONS,
            SECTION_INVENTED_SLA,
            SECTION_CALL_SCHEDULING,
        ]
        if alternatives_provided:
            omitted.remove(SECTION_ALTERNATIVE_DATES)
            allowed.insert(2, SECTION_ALTERNATIVE_DATES)

        reasoning: dict[str, str] = {}
        if SECTION_ALTERNATIVE_DATES in omitted:
            reasoning[SECTION_ALTERNATIVE_DATES] = (
                "No alternatives were provided in the context — do not invent them."
            )
        reasoning[SECTION_HOSTING_LANGUAGE] = (
            "The slot is unavailable — do not use hosting language implying the event will happen."
        )
        reasoning[SECTION_INVENTED_QUESTIONS] = "No clarification questions are relevant for an unavailable slot."
        reasoning[SECTION_INVENTED_SLA] = "Do not commit to any follow-up timeline."

        return SectionPlan(
            response_goal="RESPOND_UNAVAILABLE",
            allowed_sections=allowed,
            required_sections=required,
            omitted_sections=omitted,
            section_reasoning=reasoning,
        )

    @staticmethod
    def _build_acknowledge_and_check(
        has_minimum_spend: bool,
        has_room_context: bool,
        **_: Any,
    ) -> SectionPlan:
        # RESP-016: availability_check_next_step replaces generic simple_next_step
        allowed = [
            SECTION_OPENING,
            SECTION_ENQUIRY_SUMMARY,
            SECTION_AVAILABILITY_CHECK_PENDING,
            SECTION_AVAILABILITY_CHECK_NEXT_STEP,
            SECTION_SIGNOFF,
        ]
        required = [SECTION_OPENING, SECTION_AVAILABILITY_CHECK_PENDING, SECTION_SIGNOFF]

        omitted = [
            SECTION_HOSTING_LANGUAGE,
            SECTION_AVAILABILITY_CONFIRMATION,
            SECTION_EXACT_TIMING,
            SECTION_MENU_DISCUSSION,
            SECTION_SPECIAL_TOUCHES,
            SECTION_CALL_SCHEDULING,
            SECTION_ALTERNATIVE_DATES,
            SECTION_INVENTED_QUESTIONS,
            SECTION_INVENTED_SLA,
        ]

        reasoning: dict[str, str] = {
            SECTION_HOSTING_LANGUAGE: (
                "Availability not checked — do not use phrases like 'would be perfect' or "
                "'looking forward to hosting'."
            ),
            SECTION_AVAILABILITY_CONFIRMATION: "Availability has not been checked — do not confirm it.",
            SECTION_EXACT_TIMING: "Time has not been confirmed — do not state or imply a specific time.",
            SECTION_MENU_DISCUSSION: "Menu discussion is premature before availability is confirmed.",
            SECTION_INVENTED_QUESTIONS: "No clarification questions are listed — do not invent any.",
            SECTION_INVENTED_SLA: (
                "Do not commit to a specific response time (e.g. 'within 24 hours')."
            ),
        }

        return SectionPlan(
            response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
            allowed_sections=allowed,
            required_sections=required,
            omitted_sections=omitted,
            section_reasoning=reasoning,
        )

    @staticmethod
    def _build_request_missing_information(
        has_clarification_questions: bool,
        **_: Any,
    ) -> SectionPlan:
        # RESP-016: clarification_next_step replaces generic simple_next_step
        allowed = [SECTION_OPENING, SECTION_CLARIFICATION_NEXT_STEP, SECTION_SIGNOFF]
        required = [SECTION_OPENING, SECTION_SIGNOFF]

        if has_clarification_questions:
            allowed.insert(1, SECTION_CLARIFICATION_QUESTIONS)
            required.insert(1, SECTION_CLARIFICATION_QUESTIONS)

        omitted = [
            SECTION_HOSTING_LANGUAGE,
            SECTION_AVAILABILITY_CONFIRMATION,
            SECTION_EXACT_TIMING,
            SECTION_MENU_DISCUSSION,
            SECTION_INVENTED_QUESTIONS,
            SECTION_INVENTED_SLA,
            SECTION_ALTERNATIVE_DATES,
        ]

        reasoning: dict[str, str] = {
            SECTION_INVENTED_QUESTIONS: (
                "Ask only the approved clarification questions — do not add others."
            ),
            SECTION_AVAILABILITY_CONFIRMATION: "Do not confirm availability while information is missing.",
        }

        return SectionPlan(
            response_goal="REQUEST_MISSING_INFORMATION",
            allowed_sections=allowed,
            required_sections=required,
            omitted_sections=omitted,
            section_reasoning=reasoning,
        )

    @staticmethod
    def _build_request_date_confirmation(**_: Any) -> SectionPlan:
        allowed = [
            SECTION_OPENING,
            SECTION_DATE_CONFIRMATION_QUESTION,
            SECTION_SIGNOFF,
        ]
        required = [SECTION_OPENING, SECTION_DATE_CONFIRMATION_QUESTION, SECTION_SIGNOFF]
        omitted = [
            SECTION_AVAILABILITY_CONFIRMATION,
            SECTION_HOSTING_LANGUAGE,
            SECTION_EXACT_TIMING,
            SECTION_MENU_DISCUSSION,
            SECTION_INVENTED_QUESTIONS,
            SECTION_INVENTED_SLA,
        ]
        reasoning = {
            SECTION_AVAILABILITY_CONFIRMATION: "Date is not confirmed — cannot check availability.",
            SECTION_INVENTED_QUESTIONS: "Ask only the date confirmation question.",
        }
        return SectionPlan(
            response_goal="REQUEST_DATE_CONFIRMATION",
            allowed_sections=allowed,
            required_sections=required,
            omitted_sections=omitted,
            section_reasoning=reasoning,
        )

    @staticmethod
    def _build_request_webform(has_webform_url: bool, **_: Any) -> SectionPlan:
        allowed = [SECTION_OPENING, SECTION_SIGNOFF]
        required = [SECTION_OPENING, SECTION_SIGNOFF]

        if has_webform_url:
            allowed.insert(1, SECTION_WEBFORM_REDIRECT)
            required.insert(1, SECTION_WEBFORM_REDIRECT)

        omitted = [
            SECTION_AVAILABILITY_CONFIRMATION,
            SECTION_HOSTING_LANGUAGE,
            SECTION_INVENTED_QUESTIONS,
            SECTION_INVENTED_SLA,
            SECTION_ALTERNATIVE_DATES,
            SECTION_EXACT_TIMING,
            SECTION_MENU_DISCUSSION,
        ]
        reasoning = {
            SECTION_WEBFORM_REDIRECT if not has_webform_url else "": (
                "No webform URL was provided — do not include a link."
            ) if not has_webform_url else "",
            SECTION_INVENTED_QUESTIONS: "Do not add questions beyond the webform request.",
        }
        # Remove empty key if present
        reasoning.pop("", None)

        return SectionPlan(
            response_goal="REQUEST_WEBFORM",
            allowed_sections=allowed,
            required_sections=required,
            omitted_sections=omitted,
            section_reasoning=reasoning,
        )

    @staticmethod
    def _build_escalate_to_human(**_: Any) -> SectionPlan:
        allowed = [SECTION_OPENING, SECTION_SIGNOFF]
        required = [SECTION_OPENING, SECTION_SIGNOFF]
        omitted = [
            SECTION_AVAILABILITY_CONFIRMATION,
            SECTION_HOSTING_LANGUAGE,
            SECTION_EXACT_TIMING,
            SECTION_MENU_DISCUSSION,
            SECTION_INVENTED_QUESTIONS,
            SECTION_INVENTED_SLA,
            SECTION_ALTERNATIVE_DATES,
        ]
        reasoning = {
            SECTION_AVAILABILITY_CONFIRMATION: "Human review required before any commitment.",
            SECTION_INVENTED_SLA: "Do not commit to a specific follow-up time.",
        }
        return SectionPlan(
            response_goal="ESCALATE_TO_HUMAN",
            allowed_sections=allowed,
            required_sections=required,
            omitted_sections=omitted,
            section_reasoning=reasoning,
        )

    @staticmethod
    def _build_unknown(response_goal: str) -> SectionPlan:
        return SectionPlan(
            response_goal=response_goal,
            allowed_sections=[SECTION_OPENING, SECTION_SIGNOFF],
            required_sections=[SECTION_OPENING, SECTION_SIGNOFF],
            omitted_sections=[
                SECTION_AVAILABILITY_CONFIRMATION,
                SECTION_HOSTING_LANGUAGE,
                SECTION_INVENTED_QUESTIONS,
                SECTION_INVENTED_SLA,
            ],
            section_reasoning={
                SECTION_AVAILABILITY_CONFIRMATION: "Unknown goal — conservative policy applied.",
            },
        )


# ── Builder dispatch table ─────────────────────────────────────────────────────

_BUILDERS = {
    "CONFIRM_AVAILABLE": ResponseSectionBuilder._build_confirm_available,
    "RESPOND_UNAVAILABLE": ResponseSectionBuilder._build_respond_unavailable,
    "ACKNOWLEDGE_AND_CHECK_AVAILABILITY": ResponseSectionBuilder._build_acknowledge_and_check,
    "REQUEST_MISSING_INFORMATION": ResponseSectionBuilder._build_request_missing_information,
    "REQUEST_DATE_CONFIRMATION": ResponseSectionBuilder._build_request_date_confirmation,
    "REQUEST_WEBFORM": ResponseSectionBuilder._build_request_webform,
    "ESCALATE_TO_HUMAN": ResponseSectionBuilder._build_escalate_to_human,
}
