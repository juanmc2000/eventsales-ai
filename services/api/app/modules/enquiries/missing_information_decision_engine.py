"""Missing Information Decision Engine (RESP-002).

Determines what information must be requested from the customer before
availability processing can continue.

The engine answers three questions:
  1. Is clarification required?
  2. Which questions should be asked?
  3. Are availability checks allowed?

Decision rules (evaluated in order):
  Rule 1 — Date is ambiguous (DateResolutionStatus.status == "ambiguous")
            → clarification required, availability blocked
            → question: ask guest to confirm which date they meant
  Rule 2 — Date is resolved_with_confirmation
            → clarification required but availability may proceed with assumed date
            → question: present clarification question from DateResolutionStatus
  Rule 3 — No date extracted (DateResolutionStatus.status == "unknown" or None)
            → clarification required, availability blocked
            → question: ask guest for a date
  Rule 4 — Guest count missing (from ReadinessEvaluation)
            → clarification required, availability blocked
            → question: ask guest how many people
  Rule 5 — All critical information present and date is resolved
            → no clarification required, availability allowed

No LLM calls are made.

Usage::

    from app.modules.enquiries.missing_information_decision_engine import (
        MissingInformationDecisionEngine, DECISION_PROCEED,
    )

    decision = MissingInformationDecisionEngine.decide(
        date_resolution_status=date_status,
        readiness_evaluation=readiness,
    )
    # decision.decision → "REQUEST_DATE_CONFIRMATION"
    # decision.availability_allowed → False
    # decision.questions → ["Could you confirm whether you meant 7 June or 6 July?"]
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.enquiries.date_resolution_status import (
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_RESOLVED_WITH_CONFIRMATION,
    STATUS_UNKNOWN,
    DateResolutionStatus,
)
from app.modules.enquiries.readiness_evaluator import ReadinessEvaluation

# ── Decision constants ─────────────────────────────────────────────────────────

DECISION_PROCEED = "PROCEED"
DECISION_REQUEST_DATE_CONFIRMATION = "REQUEST_DATE_CONFIRMATION"
DECISION_REQUEST_DATE = "REQUEST_DATE"
DECISION_REQUEST_GUEST_COUNT = "REQUEST_GUEST_COUNT"
DECISION_REQUEST_MULTIPLE = "REQUEST_MULTIPLE"

ALL_DECISIONS = {
    DECISION_PROCEED,
    DECISION_REQUEST_DATE_CONFIRMATION,
    DECISION_REQUEST_DATE,
    DECISION_REQUEST_GUEST_COUNT,
    DECISION_REQUEST_MULTIPLE,
}


# ── Decision result ───────────────────────────────────────────────────────────


@dataclass
class MissingInformationDecision:
    """Result of the missing information decision engine.

    Fields:
        decision:             One of ALL_DECISIONS.
        availability_allowed: True only when availability checks may proceed.
        questions:            Ordered list of questions to put to the guest.
        blocking_reasons:     Machine-readable reasons why availability is blocked.
    """

    decision: str
    availability_allowed: bool
    questions: list[str]
    blocking_reasons: list[str] = field(default_factory=list)

    @property
    def requires_clarification(self) -> bool:
        return self.decision != DECISION_PROCEED

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "availability_allowed": self.availability_allowed,
            "questions": self.questions,
            "blocking_reasons": self.blocking_reasons,
            "requires_clarification": self.requires_clarification,
        }


# ── Engine ────────────────────────────────────────────────────────────────────


class MissingInformationDecisionEngine:
    """Determine what information must be requested before availability processing.

    All logic is deterministic — no LLM calls are made.
    """

    @classmethod
    def decide(
        cls,
        date_resolution_status: DateResolutionStatus | None,
        readiness_evaluation: ReadinessEvaluation | None = None,
    ) -> MissingInformationDecision:
        """Evaluate the date status and readiness to produce a decision.

        Args:
            date_resolution_status: Result from DateResolutionStatus. May be None
                when no date information was found.
            readiness_evaluation: ReadinessEvaluation from EnquiryReadinessEvaluator.
                May be None; when not provided, guest-count check is skipped.

        Returns:
            MissingInformationDecision with decision, availability_allowed, and questions.
        """
        questions: list[str] = []
        blocking_reasons: list[str] = []
        decision_types: list[str] = []

        date_status = date_resolution_status.status if date_resolution_status else STATUS_UNKNOWN

        # ── Rule 1 — Ambiguous date: availability must not proceed ─────────────
        if date_status == STATUS_AMBIGUOUS:
            question = cls._date_ambiguity_question(date_resolution_status)
            questions.append(question)
            blocking_reasons.append(
                f"Date is ambiguous (status={date_status}); availability blocked "
                "until guest confirms which interpretation is correct."
            )
            decision_types.append(DECISION_REQUEST_DATE_CONFIRMATION)

        # ── Rule 2 — Resolved with confirmation: note but do not block ─────────
        elif date_status == STATUS_RESOLVED_WITH_CONFIRMATION:
            if date_resolution_status and date_resolution_status.clarification_question:
                questions.append(date_resolution_status.clarification_question)
            else:
                questions.append(cls._date_ambiguity_question(date_resolution_status))
            # Availability may proceed with the assumed date (not blocking)
            decision_types.append(DECISION_REQUEST_DATE_CONFIRMATION)

        # ── Rule 3 — No date extracted: availability blocked ───────────────────
        elif date_status == STATUS_UNKNOWN:
            questions.append(
                date_resolution_status.clarification_question
                if date_resolution_status and date_resolution_status.clarification_question
                else "Could you let us know when you would like to book?"
            )
            blocking_reasons.append(
                "No date was extracted from the enquiry; availability cannot proceed."
            )
            decision_types.append(DECISION_REQUEST_DATE)

        # ── Rule 4 — Guest count missing ──────────────────────────────────────
        guest_count_missing = (
            readiness_evaluation is not None
            and not readiness_evaluation.guest_count_present
        )
        if guest_count_missing:
            questions.append("How many guests will be joining you?")
            blocking_reasons.append(
                "Guest count is missing; availability cannot be checked without party size."
            )
            decision_types.append(DECISION_REQUEST_GUEST_COUNT)

        # ── Determine final decision ───────────────────────────────────────────
        if not decision_types:
            # Rule 5 — All critical information present
            return MissingInformationDecision(
                decision=DECISION_PROCEED,
                availability_allowed=True,
                questions=[],
                blocking_reasons=[],
            )

        # Multiple decision types → collapse to REQUEST_MULTIPLE
        if len(decision_types) > 1:
            decision = DECISION_REQUEST_MULTIPLE
        else:
            decision = decision_types[0]

        # Availability is allowed only when:
        # - date is resolved_with_confirmation AND guest count is present
        # (i.e. only Rule 2 triggered, nothing else blocking)
        availability_allowed = (
            date_status == STATUS_RESOLVED_WITH_CONFIRMATION
            and not guest_count_missing
        )

        return MissingInformationDecision(
            decision=decision,
            availability_allowed=availability_allowed,
            questions=questions,
            blocking_reasons=blocking_reasons,
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _date_ambiguity_question(
        date_status: DateResolutionStatus | None,
    ) -> str:
        """Build a clarification question for an ambiguous date."""
        if date_status and date_status.clarification_question:
            return date_status.clarification_question

        if date_status and date_status.original_text:
            text = date_status.original_text
            resolved = date_status.resolved_date
            alternative = date_status.alternative_date
            if resolved and alternative:
                return (
                    f"Could you confirm whether you meant {resolved} or {alternative}? "
                    f"I've provisionally checked availability for {resolved}."
                )
            return f"Could you confirm the date you had in mind? You mentioned '{text}'."

        return (
            "Could you clarify the date you had in mind? "
            "I want to make sure I check availability for the right date."
        )
