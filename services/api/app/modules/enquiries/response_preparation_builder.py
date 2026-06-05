"""Response Preparation Builder (ORCH-006).

Central assembler that combines all deterministic outputs into a single
ResponsePlan for draft generation.

LLM2 should never receive fragmented extraction, date, availability, or
persona data.  It should receive one clean ResponsePlan containing:
  - what is known
  - what is missing
  - what availability says
  - what the customer type is
  - what tone / persona should be used
  - what the response should achieve

No LLM calls are made.  No database mutations are performed.

Usage::

    from app.modules.enquiries.response_preparation_builder import (
        ResponsePreparationBuilder,
    )

    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=readiness,
        date_resolution_status=date_status,
        candidate_dates=candidate_dates,
        customer_type="corporate",
        availability_decision=avail,
        missing_information_result=missing,
        persona_routing_context=persona_ctx,
        response_priority_result=priority,
    )
    # plan.response_goal  → "READY_TO_CONFIRM_AVAILABILITY"
    # plan.can_generate_draft → True
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.modules.enquiries.response_goal_engine import (
    ResponseGoalEngine,
    ResponseGoalResult,
)
from app.modules.enquiries.response_priority_engine import (
    PRIORITY_NORMAL,
    ResponsePriorityEngine,
    ResponsePriorityResult,
)

if TYPE_CHECKING:
    from app.modules.enquiries.availability_decision_service import AvailabilityDecision
    from app.modules.enquiries.date_resolution_status import DateResolutionStatus
    from app.modules.enquiries.missing_information_engine import MissingInformationResult
    from app.modules.enquiries.persona_routing_context import PersonaRoutingContext
    from app.modules.enquiries.readiness_evaluator import ReadinessEvaluation

# ── Response plan ─────────────────────────────────────────────────────────────


@dataclass
class ResponsePlan:
    """Complete deterministic response plan for LLM2 draft generation.

    Attributes:
        response_goal:          One of the GOAL_* constants from ResponseGoalEngine.
        response_priority:      One of the PRIORITY_* constants.
        can_generate_draft:     Whether LLM2 may be invoked.
        goal_reason:            Human-readable explanation of the response goal.
        blocking_fields:        Fields that prevented a READY goal.
        known_facts:            Assembled facts for the draft LLM.
        missing_information:    Missing-field summary from ORCH-003.
        clarification_questions: Ordered questions to include in the response.
        date_context:           Date resolution context for the LLM.
        availability_context:   Availability decision context.
        customer_type_context:  Customer type and confidence context.
        persona_context:        Selected persona and tone guidance.
        draft_instructions:     Structured instructions for LLM2.
    """

    response_goal: str
    response_priority: str
    can_generate_draft: bool
    goal_reason: str
    blocking_fields: list[str] = field(default_factory=list)
    known_facts: dict[str, Any] = field(default_factory=dict)
    missing_information: dict[str, Any] = field(default_factory=dict)
    clarification_questions: list[str] = field(default_factory=list)
    date_context: dict[str, Any] = field(default_factory=dict)
    availability_context: dict[str, Any] = field(default_factory=dict)
    customer_type_context: dict[str, Any] = field(default_factory=dict)
    persona_context: dict[str, Any] = field(default_factory=dict)
    draft_instructions: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_goal": self.response_goal,
            "response_priority": self.response_priority,
            "can_generate_draft": self.can_generate_draft,
            "goal_reason": self.goal_reason,
            "blocking_fields": self.blocking_fields,
            "known_facts": self.known_facts,
            "missing_information": self.missing_information,
            "clarification_questions": self.clarification_questions,
            "date_context": self.date_context,
            "availability_context": self.availability_context,
            "customer_type_context": self.customer_type_context,
            "persona_context": self.persona_context,
            "draft_instructions": self.draft_instructions,
        }


# ── Builder ───────────────────────────────────────────────────────────────────


class ResponsePreparationBuilder:
    """Assembles all deterministic service outputs into a single ResponsePlan.

    The builder:
      1. Calls ResponseGoalEngine.decide() to determine the response goal.
      2. Uses the provided ResponsePriorityResult or derives one on the fly.
      3. Assembles all context sections.
      4. Builds draft_instructions for LLM2.
      5. Returns a ResponsePlan dataclass.

    No database mutations are made.
    """

    @classmethod
    def build(
        cls,
        readiness_evaluation: ReadinessEvaluation,
        date_resolution_status: DateResolutionStatus | None = None,
        candidate_dates: list[Any] | None = None,
        customer_type: str = "unknown",
        customer_type_confidence: float = 0.0,
        customer_type_reason: str = "",
        availability_decision: AvailabilityDecision | None = None,
        missing_information_result: MissingInformationResult | None = None,
        persona_routing_context: PersonaRoutingContext | None = None,
        response_priority_result: ResponsePriorityResult | None = None,
    ) -> ResponsePlan:
        """Build a ResponsePlan from all deterministic service outputs.

        Args:
            readiness_evaluation:       ReadinessEvaluation from ENQ-004.
            date_resolution_status:     DateResolutionStatus from DATE-002.
            candidate_dates:            List of candidate-date objects/dicts.
            customer_type:              Resolved customer type string.
            customer_type_confidence:   Confidence score 0.0–1.0.
            customer_type_reason:       How the customer type was resolved.
            availability_decision:      AvailabilityDecision from ORCH-002.
            missing_information_result: MissingInformationResult from ORCH-003.
            persona_routing_context:    PersonaRoutingContext from ORCH-005.
            response_priority_result:   ResponsePriorityResult from ORCH-004.
                                        Computed on the fly when not provided.

        Returns:
            ResponsePlan.
        """
        # ── Step 1: response goal ─────────────────────────────────────────────
        goal_result: ResponseGoalResult = ResponseGoalEngine.decide(
            readiness_evaluation=readiness_evaluation,
            date_resolution_status=date_resolution_status,
            missing_information_result=missing_information_result,
            availability_decision=availability_decision,
            customer_type=customer_type,
        )

        # ── Step 2: response priority ─────────────────────────────────────────
        priority_result: ResponsePriorityResult
        if response_priority_result is not None:
            priority_result = response_priority_result
        else:
            resolved_date = (
                date_resolution_status.resolved_date
                if date_resolution_status
                else None
            )
            candidate_iso: list[str] = []
            for cd in (candidate_dates or []):
                d = _get_field(cd, "candidate_date")
                if d:
                    candidate_iso.append(str(d))
            date_status_str = (
                date_resolution_status.status if date_resolution_status else "unknown"
            )
            priority_result = ResponsePriorityEngine.decide(
                resolved_event_date=resolved_date,
                candidate_dates=candidate_iso,
                date_status=date_status_str,
            )

        # ── Step 3: assemble context sections ─────────────────────────────────
        date_ctx = cls._build_date_context(date_resolution_status)
        avail_ctx = cls._build_availability_context(availability_decision)
        customer_ctx = cls._build_customer_type_context(
            customer_type, customer_type_confidence, customer_type_reason
        )
        persona_ctx = cls._build_persona_context(persona_routing_context)
        missing_info = cls._build_missing_information(missing_information_result)
        known_facts = cls._build_known_facts(readiness_evaluation, date_resolution_status)

        # ── Step 4: clarification questions ───────────────────────────────────
        clarification_questions: list[str] = []
        if missing_information_result is not None:
            clarification_questions = list(
                getattr(missing_information_result, "clarification_questions", [])
            )
        elif date_resolution_status and date_resolution_status.clarification_question:
            clarification_questions = [date_resolution_status.clarification_question]

        # ── Step 5: draft instructions ────────────────────────────────────────
        draft_instructions = cls._build_draft_instructions(
            goal_result=goal_result,
            persona_routing_context=persona_routing_context,
            availability_decision=availability_decision,
            clarification_questions=clarification_questions,
        )

        return ResponsePlan(
            response_goal=goal_result.response_goal,
            response_priority=priority_result.response_priority,
            can_generate_draft=goal_result.can_generate_draft,
            goal_reason=goal_result.goal_reason,
            blocking_fields=goal_result.blocking_fields,
            known_facts=known_facts,
            missing_information=missing_info,
            clarification_questions=clarification_questions,
            date_context=date_ctx,
            availability_context=avail_ctx,
            customer_type_context=customer_ctx,
            persona_context=persona_ctx,
            draft_instructions=draft_instructions,
        )

    # ── Context builders ───────────────────────────────────────────────────────

    @staticmethod
    def _build_date_context(date_status: DateResolutionStatus | None) -> dict[str, Any]:
        if date_status is None:
            return {
                "status": "unknown",
                "resolved_date": None,
                "original_text": None,
                "clarification_required": True,
                "clarification_question": None,
                "candidate_dates": [],
            }
        return {
            "status": date_status.status,
            "resolved_date": getattr(date_status, "resolved_date", None),
            "original_text": getattr(date_status, "original_text", None),
            "clarification_required": getattr(date_status, "clarification_required", False),
            "clarification_question": getattr(date_status, "clarification_question", None),
            "candidate_dates": list(getattr(date_status, "candidate_dates", []) or []),
        }

    @staticmethod
    def _build_availability_context(
        avail: AvailabilityDecision | None,
    ) -> dict[str, Any]:
        if avail is None:
            return {
                "availability_status": "NOT_CHECKED",
                "selected_candidate_date": None,
                "available_options": [],
                "unavailable_options": [],
                "availability_reason": "Availability not checked.",
            }
        return avail.to_dict()

    @staticmethod
    def _build_customer_type_context(
        customer_type: str,
        confidence: float,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "final_customer_type": customer_type,
            "confidence": confidence,
            "resolution_reason": reason,
        }

    @staticmethod
    def _build_persona_context(
        persona_ctx: PersonaRoutingContext | None,
    ) -> dict[str, Any]:
        if persona_ctx is None:
            return {
                "selected_persona_id": None,
                "selected_persona_name": None,
                "customer_type": "unknown",
                "tone_guidance": ["professional"],
                "routing_reason": "No persona routing context provided.",
            }
        return persona_ctx.to_dict()

    @staticmethod
    def _build_missing_information(
        missing: MissingInformationResult | None,
    ) -> dict[str, Any]:
        if missing is None:
            return {
                "missing_fields": [],
                "critical_missing_fields": [],
                "clarification_questions": [],
                "can_ask_by_email": False,
                "should_send_webform": False,
                "missing_info_reason": "No missing information analysis available.",
            }
        return missing.to_dict()

    @staticmethod
    def _build_known_facts(
        readiness: ReadinessEvaluation,
        date_status: DateResolutionStatus | None,
    ) -> dict[str, Any]:
        return {
            "date_understood": readiness.date_understood,
            "guest_count_present": readiness.guest_count_present,
            "occasion_understood": readiness.occasion_understood,
            "meal_period_present": readiness.meal_period_present,
            "audience_identified": readiness.audience_identified,
            "availability_check_possible": readiness.availability_check_possible,
            "readiness_status": readiness.status,
            "date_original_text": (
                getattr(date_status, "original_text", None) if date_status else None
            ),
        }

    @staticmethod
    def _build_draft_instructions(
        goal_result: ResponseGoalResult,
        persona_routing_context: PersonaRoutingContext | None,
        availability_decision: AvailabilityDecision | None,
        clarification_questions: list[str],
    ) -> dict[str, Any]:
        tone_guidance: list[str] = (
            list(persona_routing_context.tone_guidance)
            if persona_routing_context
            else ["professional"]
        )
        include_availability = availability_decision is not None and (
            getattr(availability_decision, "availability_status", "") in (
                "AVAILABLE", "PARTIALLY_AVAILABLE", "UNAVAILABLE"
            )
        )
        return {
            "response_goal": goal_result.response_goal,
            "tone_guidance": tone_guidance,
            "clarification_questions": list(clarification_questions),
            "include_availability": include_availability,
            "can_generate_draft": goal_result.can_generate_draft,
        }


# ── Helpers ────────────────────────────────────────────────────────────────────


def _get_field(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)
