"""Response Preparation Service (RESP-001).

Deterministic orchestration layer that prepares response context before
draft generation. The LLM should never decide availability actions,
clarification actions, or date-ambiguity handling — those decisions belong here.

Inputs:
  - readiness_evaluation: ReadinessEvaluation from EnquiryReadinessEvaluator
  - processing_snapshot_summary: Optional dict from EnquiryProcessingService snapshot
  - audience_type: resolved audience type string (social | corporate | agency | unknown)
  - date_resolution_status: Optional DateResolutionStatus from DATE-002

Outputs:
  ResponseContext containing:
  - response_goal: one of RESPONSE_GOAL_* constants
  - clarification_questions: list of questions to put to the guest
  - response_context: structured dict of facts for the LLM to use

Supported response goals (in precedence order):
  ESCALATE_TO_HUMAN            — enquiry cannot be handled automatically
  REQUEST_DATE_CONFIRMATION    — date is ambiguous; availability must not proceed
  READY_FOR_RESPONSE           — all key facts available; proceed to draft
  REQUEST_MISSING_INFORMATION  — guest must supply missing details
  REQUEST_WEBFORM              — too many unknowns; direct guest to structured form

No LLM calls are made.

Usage::

    from app.modules.enquiries.response_preparation_service import (
        ResponsePreparationService, RESPONSE_GOAL_READY_FOR_RESPONSE
    )

    ctx = ResponsePreparationService.prepare(
        readiness_evaluation=evaluation,
        date_resolution_status=date_status,
        audience_type="corporate",
    )
    # ctx.response_goal → "READY_FOR_RESPONSE"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.modules.enquiries.date_resolution_status import (
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_RESOLVED_WITH_CONFIRMATION,
    STATUS_UNKNOWN,
    DateResolutionStatus,
)
from app.modules.enquiries.readiness_evaluator import (
    STATUS_INSUFFICIENT_INFORMATION,
    STATUS_NEEDS_CLARIFICATION,
    STATUS_READY_FOR_AVAILABILITY,
    STATUS_WEBFORM_REQUIRED,
    ReadinessEvaluation,
)

# ── Response goal constants ────────────────────────────────────────────────────

RESPONSE_GOAL_READY_FOR_RESPONSE = "READY_FOR_RESPONSE"
RESPONSE_GOAL_REQUEST_MISSING_INFORMATION = "REQUEST_MISSING_INFORMATION"
RESPONSE_GOAL_REQUEST_DATE_CONFIRMATION = "REQUEST_DATE_CONFIRMATION"
RESPONSE_GOAL_REQUEST_WEBFORM = "REQUEST_WEBFORM"
RESPONSE_GOAL_ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"

ALL_RESPONSE_GOALS = {
    RESPONSE_GOAL_READY_FOR_RESPONSE,
    RESPONSE_GOAL_REQUEST_MISSING_INFORMATION,
    RESPONSE_GOAL_REQUEST_DATE_CONFIRMATION,
    RESPONSE_GOAL_REQUEST_WEBFORM,
    RESPONSE_GOAL_ESCALATE_TO_HUMAN,
}

# ── Response context ──────────────────────────────────────────────────────────


@dataclass
class ResponseContext:
    """Prepared response context ready for consumption by the draft LLM.

    The draft generator should use this object verbatim and must not
    re-evaluate availability, pricing, or date ambiguity.
    """

    response_goal: str
    clarification_questions: list[str]
    response_context: dict[str, Any]
    audience_type: str
    decision_reasons: list[str] = field(default_factory=list)

    @property
    def requires_clarification(self) -> bool:
        return bool(self.clarification_questions)

    @property
    def can_draft_response(self) -> bool:
        return self.response_goal in (
            RESPONSE_GOAL_READY_FOR_RESPONSE,
            RESPONSE_GOAL_REQUEST_MISSING_INFORMATION,
            RESPONSE_GOAL_REQUEST_DATE_CONFIRMATION,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_goal": self.response_goal,
            "clarification_questions": self.clarification_questions,
            "response_context": self.response_context,
            "audience_type": self.audience_type,
            "decision_reasons": self.decision_reasons,
            "requires_clarification": self.requires_clarification,
            "can_draft_response": self.can_draft_response,
        }


# ── Service ───────────────────────────────────────────────────────────────────


class ResponsePreparationService:
    """Orchestration layer that prepares response context before draft generation.

    All decisions are deterministic. No LLM calls are made.

    Goal precedence (evaluated in order, first match wins):
      1. ESCALATE_TO_HUMAN      — readiness=insufficient AND no date extracted
      2. REQUEST_DATE_CONFIRMATION — date status is ambiguous
      3. REQUEST_DATE_CONFIRMATION — date status is resolved_with_confirmation
      4. READY_FOR_RESPONSE     — readiness=ready_for_availability
      5. REQUEST_MISSING_INFORMATION — readiness=needs_clarification
      6. REQUEST_WEBFORM        — readiness=webform_required
      7. ESCALATE_TO_HUMAN      — readiness=insufficient (fallback)
    """

    @classmethod
    def prepare(
        cls,
        readiness_evaluation: ReadinessEvaluation,
        date_resolution_status: DateResolutionStatus | None = None,
        audience_type: str = "unknown",
        processing_snapshot_summary: dict[str, Any] | None = None,
    ) -> ResponseContext:
        """Prepare a ResponseContext from the given inputs.

        Args:
            readiness_evaluation: Result of EnquiryReadinessEvaluator.evaluate().
            date_resolution_status: Result of DateResolutionStatus construction.
                When None, date status is treated as unknown.
            audience_type: Resolved audience type string.
            processing_snapshot_summary: Optional summary dict from the processing
                snapshot (availability, pricing, candidate_date_summary). May be None.

        Returns:
            ResponseContext with response_goal, clarification_questions, and
            response_context ready for the draft LLM.
        """
        clarification_questions: list[str] = []
        decision_reasons: list[str] = []

        readiness_status = readiness_evaluation.status
        date_status = date_resolution_status.status if date_resolution_status else STATUS_UNKNOWN

        # ── Rule 1 — Escalate when we have nothing to work with ───────────────
        if (
            readiness_status == STATUS_INSUFFICIENT_INFORMATION
            and date_status == STATUS_UNKNOWN
            and not readiness_evaluation.occasion_understood
        ):
            decision_reasons.append(
                "Readiness status is insufficient and no date was extracted; "
                "cannot form any useful customer response."
            )
            return ResponseContext(
                response_goal=RESPONSE_GOAL_ESCALATE_TO_HUMAN,
                clarification_questions=[],
                response_context=cls._build_context(
                    readiness_evaluation, date_resolution_status,
                    audience_type, processing_snapshot_summary,
                ),
                audience_type=audience_type,
                decision_reasons=decision_reasons,
            )

        # ── Rule 2 — Ambiguous date: availability must not proceed ─────────────
        if date_status == STATUS_AMBIGUOUS:
            question = (
                date_resolution_status.clarification_question
                if date_resolution_status and date_resolution_status.clarification_question
                else cls._generic_date_clarification_question(date_resolution_status)
            )
            clarification_questions.append(question)
            decision_reasons.append(
                f"Date is ambiguous (status={date_status}); "
                "availability lookup blocked until guest confirms."
            )
            return ResponseContext(
                response_goal=RESPONSE_GOAL_REQUEST_DATE_CONFIRMATION,
                clarification_questions=clarification_questions,
                response_context=cls._build_context(
                    readiness_evaluation, date_resolution_status,
                    audience_type, processing_snapshot_summary,
                ),
                audience_type=audience_type,
                decision_reasons=decision_reasons,
            )

        # ── Rule 3 — Resolved with confirmation: include clarification question ─
        if date_status == STATUS_RESOLVED_WITH_CONFIRMATION:
            question = (
                date_resolution_status.clarification_question
                if date_resolution_status and date_resolution_status.clarification_question
                else cls._generic_date_clarification_question(date_resolution_status)
            )
            clarification_questions.append(question)
            decision_reasons.append(
                f"Date status is resolved_with_confirmation; "
                "a date clarification question must accompany the response."
            )
            return ResponseContext(
                response_goal=RESPONSE_GOAL_REQUEST_DATE_CONFIRMATION,
                clarification_questions=clarification_questions,
                response_context=cls._build_context(
                    readiness_evaluation, date_resolution_status,
                    audience_type, processing_snapshot_summary,
                ),
                audience_type=audience_type,
                decision_reasons=decision_reasons,
            )

        # ── Rule 4 — Ready for full availability response ─────────────────────
        if readiness_status == STATUS_READY_FOR_AVAILABILITY:
            decision_reasons.append(
                "Readiness status is ready_for_availability and date is resolved; "
                "proceeding to full response."
            )
            return ResponseContext(
                response_goal=RESPONSE_GOAL_READY_FOR_RESPONSE,
                clarification_questions=[],
                response_context=cls._build_context(
                    readiness_evaluation, date_resolution_status,
                    audience_type, processing_snapshot_summary,
                ),
                audience_type=audience_type,
                decision_reasons=decision_reasons,
            )

        # ── Rule 5 — Needs clarification (date or guest count missing) ─────────
        if readiness_status == STATUS_NEEDS_CLARIFICATION:
            clarification_questions.extend(
                cls._build_clarification_questions(readiness_evaluation, date_resolution_status)
            )
            decision_reasons.append(
                f"Readiness status is needs_clarification: {readiness_evaluation.notes}"
            )
            return ResponseContext(
                response_goal=RESPONSE_GOAL_REQUEST_MISSING_INFORMATION,
                clarification_questions=clarification_questions,
                response_context=cls._build_context(
                    readiness_evaluation, date_resolution_status,
                    audience_type, processing_snapshot_summary,
                ),
                audience_type=audience_type,
                decision_reasons=decision_reasons,
            )

        # ── Rule 6 — Webform required ──────────────────────────────────────────
        if readiness_status == STATUS_WEBFORM_REQUIRED:
            decision_reasons.append(
                "Readiness status is webform_required; directing guest to structured form."
            )
            return ResponseContext(
                response_goal=RESPONSE_GOAL_REQUEST_WEBFORM,
                clarification_questions=[],
                response_context=cls._build_context(
                    readiness_evaluation, date_resolution_status,
                    audience_type, processing_snapshot_summary,
                ),
                audience_type=audience_type,
                decision_reasons=decision_reasons,
            )

        # ── Rule 7 — Fallback escalation ──────────────────────────────────────
        decision_reasons.append(
            f"Readiness status is {readiness_status}; escalating to human review."
        )
        return ResponseContext(
            response_goal=RESPONSE_GOAL_ESCALATE_TO_HUMAN,
            clarification_questions=[],
            response_context=cls._build_context(
                readiness_evaluation, date_resolution_status,
                audience_type, processing_snapshot_summary,
            ),
            audience_type=audience_type,
            decision_reasons=decision_reasons,
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _build_context(
        readiness: ReadinessEvaluation,
        date_status: DateResolutionStatus | None,
        audience_type: str,
        snapshot_summary: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Build the response_context dict passed to the draft LLM."""
        ctx: dict[str, Any] = {
            "audience_type": audience_type,
            "readiness_status": readiness.status,
            "date_understood": readiness.date_understood,
            "guest_count_present": readiness.guest_count_present,
            "occasion_understood": readiness.occasion_understood,
            "meal_period_present": readiness.meal_period_present,
            "audience_identified": readiness.audience_identified,
            "missing_for_availability": readiness.missing_for_availability,
            "availability_check_possible": readiness.availability_check_possible,
        }

        if date_status:
            ctx["date_status"] = date_status.status
            ctx["date_original_text"] = date_status.original_text
            ctx["date_resolved"] = date_status.resolved_date
            ctx["date_alternative"] = date_status.alternative_date
            ctx["date_clarification_required"] = date_status.clarification_required
            ctx["date_clarification_question"] = date_status.clarification_question
            ctx["date_candidate_dates"] = date_status.candidate_dates
        else:
            ctx["date_status"] = STATUS_UNKNOWN
            ctx["date_resolved"] = None
            ctx["date_clarification_required"] = True

        if snapshot_summary:
            ctx["processing_snapshot"] = snapshot_summary

        return ctx

    @staticmethod
    def _build_clarification_questions(
        readiness: ReadinessEvaluation,
        date_status: DateResolutionStatus | None,
    ) -> list[str]:
        """Build a list of targeted clarification questions based on missing fields."""
        questions: list[str] = []

        if readiness.date_clarification_required:
            if date_status and date_status.clarification_question:
                questions.append(date_status.clarification_question)
            else:
                questions.append("Could you let us know when you would like to book?")

        if not readiness.guest_count_present:
            questions.append("How many guests will be joining you?")

        return questions

    @staticmethod
    def _generic_date_clarification_question(
        date_status: DateResolutionStatus | None,
    ) -> str:
        """Return a generic date clarification question when no specific one is available."""
        if date_status and date_status.original_text:
            return (
                f"Could you clarify the date you had in mind? "
                f"You mentioned '{date_status.original_text}' — "
                "could you confirm the exact date?"
            )
        return "Could you let us know the exact date you have in mind?"
