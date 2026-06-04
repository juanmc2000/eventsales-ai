"""Response Goal Engine (ORCH-001).

Deterministic engine that decides what the system should do next before draft
generation.  The LLM must never decide operational workflow — this engine owns
that decision.

Supported response goals (in precedence order):
  UNABLE_TO_PROCESS            — no usable information; cannot form any response
  ESCALATE_TO_HUMAN            — insufficient information but some context exists
  REQUEST_DATE_CONFIRMATION    — date is ambiguous or requires confirmation
  REQUEST_WEBFORM              — multiple critical fields missing; direct to form
  REQUEST_MISSING_INFORMATION  — 1–2 fields missing; ask by email
  READY_TO_CONFIRM_AVAILABILITY — all key facts present; proceed to availability reply

Inputs:
  - readiness_evaluation: ReadinessEvaluation from EnquiryReadinessEvaluator
  - date_resolution_status: DateResolutionStatus | None from DATE-002
  - missing_information_result: MissingInformationResult | None from ORCH-003
  - availability_decision: AvailabilityDecision | None from ORCH-002
  - customer_type: str — resolved audience type (social | corporate | agency | unknown)

Outputs:
  ResponseGoalResult with:
  - response_goal: one of the GOAL_* constants
  - goal_reason: human-readable explanation of the decision
  - blocking_fields: list of fields that caused a non-READY goal
  - can_generate_draft: whether LLM2 may be invoked

No LLM calls are made.  No database mutations are performed.

Usage::

    from app.modules.enquiries.response_goal_engine import ResponseGoalEngine

    result = ResponseGoalEngine.decide(
        readiness_evaluation=readiness,
        date_resolution_status=date_status,
        missing_information_result=missing_info,
        availability_decision=avail_decision,
        customer_type="corporate",
    )
    # result.response_goal → "READY_TO_CONFIRM_AVAILABILITY"
    # result.can_generate_draft → True
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.modules.enquiries.date_resolution_status import (
    STATUS_AMBIGUOUS,
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

if TYPE_CHECKING:
    # Defined by ORCH-002 and ORCH-003 respectively.
    from app.modules.enquiries.availability_decision_service import AvailabilityDecision
    from app.modules.enquiries.missing_information_engine import MissingInformationResult

# ── Response goal constants ────────────────────────────────────────────────────

GOAL_READY_TO_CONFIRM_AVAILABILITY = "READY_TO_CONFIRM_AVAILABILITY"
GOAL_REQUEST_MISSING_INFORMATION = "REQUEST_MISSING_INFORMATION"
GOAL_REQUEST_DATE_CONFIRMATION = "REQUEST_DATE_CONFIRMATION"
GOAL_REQUEST_WEBFORM = "REQUEST_WEBFORM"
GOAL_ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
GOAL_UNABLE_TO_PROCESS = "UNABLE_TO_PROCESS"

ALL_GOALS = {
    GOAL_READY_TO_CONFIRM_AVAILABILITY,
    GOAL_REQUEST_MISSING_INFORMATION,
    GOAL_REQUEST_DATE_CONFIRMATION,
    GOAL_REQUEST_WEBFORM,
    GOAL_ESCALATE_TO_HUMAN,
    GOAL_UNABLE_TO_PROCESS,
}

# Goals that permit LLM draft generation
GOALS_ALLOWING_DRAFT = {
    GOAL_READY_TO_CONFIRM_AVAILABILITY,
    GOAL_REQUEST_MISSING_INFORMATION,
    GOAL_REQUEST_DATE_CONFIRMATION,
    GOAL_REQUEST_WEBFORM,
}

# ── Output ─────────────────────────────────────────────────────────────────────


@dataclass
class ResponseGoalResult:
    """Outcome of ResponseGoalEngine.decide().

    Attributes:
        response_goal:      One of the GOAL_* constants.
        goal_reason:        Human-readable explanation of why this goal was chosen.
        blocking_fields:    Fields that prevented a READY goal (may be empty).
        can_generate_draft: True when the draft LLM may be invoked for this goal.
    """

    response_goal: str
    goal_reason: str
    blocking_fields: list[str] = field(default_factory=list)
    can_generate_draft: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_goal": self.response_goal,
            "goal_reason": self.goal_reason,
            "blocking_fields": self.blocking_fields,
            "can_generate_draft": self.can_generate_draft,
        }


# ── Engine ─────────────────────────────────────────────────────────────────────


class ResponseGoalEngine:
    """Deterministic engine that assigns a response goal to an enquiry.

    All decisions are made by inspecting the provided inputs in precedence
    order.  No LLM calls are made.  No database state is mutated.

    Precedence (first match wins):
      1. UNABLE_TO_PROCESS            — completely unusable enquiry
      2. ESCALATE_TO_HUMAN            — insufficient_information with some context
      3. REQUEST_DATE_CONFIRMATION    — date ambiguous or needs confirmation
      4. REQUEST_WEBFORM              — should_send_webform OR webform_required
      5. REQUEST_MISSING_INFORMATION  — 1–2 critical fields missing
      6. READY_TO_CONFIRM_AVAILABILITY — all clear
    """

    @classmethod
    def decide(
        cls,
        readiness_evaluation: ReadinessEvaluation,
        date_resolution_status: DateResolutionStatus | None = None,
        missing_information_result: Any | None = None,
        availability_decision: Any | None = None,
        customer_type: str = "unknown",
    ) -> ResponseGoalResult:
        """Decide the response goal for an enquiry.

        Args:
            readiness_evaluation:       Result of EnquiryReadinessEvaluator.evaluate().
            date_resolution_status:     DateResolutionStatus (DATE-002) or None.
            missing_information_result: MissingInformationResult (ORCH-003) or None.
            availability_decision:      AvailabilityDecision (ORCH-002) or None.
            customer_type:              Resolved audience type string.

        Returns:
            ResponseGoalResult.
        """
        readiness_status = readiness_evaluation.status
        date_status = (
            date_resolution_status.status if date_resolution_status else STATUS_UNKNOWN
        )

        # ── Rule 1 — Completely unusable enquiry ──────────────────────────────
        if (
            readiness_status == STATUS_INSUFFICIENT_INFORMATION
            and date_status == STATUS_UNKNOWN
            and not readiness_evaluation.occasion_understood
            and not readiness_evaluation.guest_count_present
        ):
            return ResponseGoalResult(
                response_goal=GOAL_UNABLE_TO_PROCESS,
                goal_reason=(
                    "Readiness is insufficient, no date extracted, no occasion understood, "
                    "and no guest count present — cannot form any useful response."
                ),
                blocking_fields=["date", "guest_count", "occasion"],
                can_generate_draft=False,
            )

        # ── Rule 2 — Insufficient information but some context exists ─────────
        if readiness_status == STATUS_INSUFFICIENT_INFORMATION:
            blocking = list(readiness_evaluation.missing_for_availability or [])
            return ResponseGoalResult(
                response_goal=GOAL_ESCALATE_TO_HUMAN,
                goal_reason=(
                    f"Readiness status is {readiness_status}; "
                    "insufficient information for automated handling. "
                    f"Missing: {', '.join(blocking) if blocking else 'unknown fields'}."
                ),
                blocking_fields=blocking,
                can_generate_draft=False,
            )

        # ── Rule 3 — Date needs confirmation ──────────────────────────────────
        if date_status in (STATUS_AMBIGUOUS, STATUS_RESOLVED_WITH_CONFIRMATION):
            clarification = (
                date_resolution_status.clarification_question
                if date_resolution_status and date_resolution_status.clarification_question
                else None
            )
            reason = (
                f"Date status is '{date_status}'; "
                "availability lookup is blocked until the guest confirms the date."
            )
            if clarification:
                reason += f" Clarification question: {clarification}"
            return ResponseGoalResult(
                response_goal=GOAL_REQUEST_DATE_CONFIRMATION,
                goal_reason=reason,
                blocking_fields=["date_confirmation"],
                can_generate_draft=True,
            )

        # ── Rule 4 — Webform required ─────────────────────────────────────────
        should_send_webform = readiness_status == STATUS_WEBFORM_REQUIRED
        webform_reason = "Readiness evaluator requires webform." if should_send_webform else ""

        if missing_information_result is not None and not should_send_webform:
            if getattr(missing_information_result, "should_send_webform", False):
                should_send_webform = True
                webform_reason = getattr(
                    missing_information_result,
                    "missing_info_reason",
                    "Multiple critical fields missing.",
                )

        if should_send_webform:
            blocking = _extract_blocking_fields(missing_information_result, readiness_evaluation)
            return ResponseGoalResult(
                response_goal=GOAL_REQUEST_WEBFORM,
                goal_reason=webform_reason,
                blocking_fields=blocking,
                can_generate_draft=True,
            )

        # ── Rule 5 — 1–2 missing fields; ask by email ─────────────────────────
        if readiness_status == STATUS_NEEDS_CLARIFICATION:
            blocking = _extract_blocking_fields(missing_information_result, readiness_evaluation)
            reason_parts: list[str] = [f"Readiness status is {readiness_status}."]
            if readiness_evaluation.notes:
                reason_parts.append(readiness_evaluation.notes)
            return ResponseGoalResult(
                response_goal=GOAL_REQUEST_MISSING_INFORMATION,
                goal_reason=" ".join(reason_parts),
                blocking_fields=blocking,
                can_generate_draft=True,
            )

        # Also check missing_information_result critical fields when readiness is READY
        if missing_information_result is not None:
            critical = getattr(missing_information_result, "critical_missing_fields", [])
            if critical:
                return ResponseGoalResult(
                    response_goal=GOAL_REQUEST_MISSING_INFORMATION,
                    goal_reason=(
                        "Critical missing fields detected by MissingInformationEngine: "
                        f"{', '.join(critical)}."
                    ),
                    blocking_fields=list(critical),
                    can_generate_draft=True,
                )

        # ── Rule 6 — Ready to confirm availability ────────────────────────────
        return ResponseGoalResult(
            response_goal=GOAL_READY_TO_CONFIRM_AVAILABILITY,
            goal_reason=(
                f"Readiness status is {readiness_status} and date is {date_status}; "
                "all key facts are present — proceeding to availability confirmation."
            ),
            blocking_fields=[],
            can_generate_draft=True,
        )


# ── Helpers ────────────────────────────────────────────────────────────────────


def _extract_blocking_fields(
    missing_info: Any | None,
    readiness: ReadinessEvaluation,
) -> list[str]:
    """Extract the list of blocking fields from available inputs."""
    if missing_info is not None:
        critical = getattr(missing_info, "critical_missing_fields", None)
        if critical:
            return list(critical)
        missing = getattr(missing_info, "missing_fields", None)
        if missing:
            return list(missing)
    return list(readiness.missing_for_availability or [])
