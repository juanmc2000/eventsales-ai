"""Missing Information Decision Engine (ORCH-003).

Deterministic service that identifies which details are missing and decides
how they should be requested from the customer.

This is a NEW engine with richer outputs than the existing
`missing_information_decision_engine.py` (RESP-002).  Both coexist —
RESP-002 serves the legacy response preparation pipeline; this engine
(ORCH-003) serves the Sprint 10 orchestration layer.

Decision principles:
  - Prefer email clarification when only 1–2 details are missing.
  - Prefer webform when 3+ critical fields are missing.
  - Date ambiguity always generates a targeted date clarification question.
  - A complete enquiry produces no missing-info action.

Inputs:
  - date_status: str — from DateResolutionStatus.status (DATE-002)
  - date_clarification_question: str | None — from DateResolutionStatus
  - guest_count_present: bool — from ReadinessEvaluation
  - occasion_understood: bool — from ReadinessEvaluation
  - meal_period_present: bool — from ReadinessEvaluation
  - contact_details_required: bool — whether contact details are mandatory

Outputs:
  MissingInformationResult with:
  - missing_fields: all fields with absent or uncertain values
  - critical_missing_fields: fields that block availability / draft generation
  - clarification_questions: ordered list of questions to put to the guest
  - can_ask_by_email: True when email clarification is sufficient
  - should_send_webform: True when multiple critical fields require structured input
  - missing_info_reason: human-readable summary of the missing-information state

No LLM calls are made.  No database mutations are performed.

Usage::

    from app.modules.enquiries.missing_information_engine import (
        MissingInformationDecisionEngine,
    )

    result = MissingInformationDecisionEngine.decide(
        date_status="ambiguous",
        date_clarification_question="Did you mean 7 June or 6 July?",
        guest_count_present=True,
        occasion_understood=True,
        meal_period_present=True,
    )
    # result.critical_missing_fields → ["date_confirmation"]
    # result.can_ask_by_email → True
    # result.should_send_webform → False
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.modules.enquiries.date_resolution_status import (
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_RESOLVED_WITH_CONFIRMATION,
    STATUS_UNKNOWN,
)

# ── Webform threshold ─────────────────────────────────────────────────────────

# When this many or more critical fields are missing, direct the guest to the
# structured webform rather than asking individual questions by email.
WEBFORM_THRESHOLD = 3

# ── Output ─────────────────────────────────────────────────────────────────────


@dataclass
class MissingInformationResult:
    """Outcome of MissingInformationDecisionEngine.decide().

    Attributes:
        missing_fields:           All fields absent or uncertain.
        critical_missing_fields:  Fields that block availability / drafting.
        clarification_questions:  Ordered questions to ask the guest.
        can_ask_by_email:         True when 1–2 fields; email is sufficient.
        should_send_webform:      True when 3+ critical fields are missing.
        missing_info_reason:      Human-readable summary.
    """

    missing_fields: list[str] = field(default_factory=list)
    critical_missing_fields: list[str] = field(default_factory=list)
    clarification_questions: list[str] = field(default_factory=list)
    can_ask_by_email: bool = False
    should_send_webform: bool = False
    missing_info_reason: str = ""

    @property
    def requires_action(self) -> bool:
        """True when any information is missing."""
        return bool(self.missing_fields or self.critical_missing_fields)

    def to_dict(self) -> dict[str, Any]:
        return {
            "missing_fields": self.missing_fields,
            "critical_missing_fields": self.critical_missing_fields,
            "clarification_questions": self.clarification_questions,
            "can_ask_by_email": self.can_ask_by_email,
            "should_send_webform": self.should_send_webform,
            "missing_info_reason": self.missing_info_reason,
        }


# ── Engine ─────────────────────────────────────────────────────────────────────


class MissingInformationDecisionEngine:
    """Identifies missing information and decides how to request it.

    Evaluation order:
      1. Date status — ambiguous / confirmation-needed / missing
      2. Guest count — critical field
      3. Occasion — non-critical but useful
      4. Meal period — non-critical but useful
      5. Contact details — optional; only when contact_details_required=True
      6. Classify: email vs webform based on critical field count
    """

    @classmethod
    def decide(
        cls,
        date_status: str = STATUS_UNKNOWN,
        date_clarification_question: str | None = None,
        guest_count_present: bool = True,
        occasion_understood: bool = True,
        meal_period_present: bool = True,
        contact_details_required: bool = False,
        contact_details_present: bool = True,
    ) -> MissingInformationResult:
        """Evaluate missing information and decide how to request it.

        Args:
            date_status:                 DateResolutionStatus.status string.
            date_clarification_question: Human-readable question from DateResolutionStatus.
            guest_count_present:         Whether guest count was extracted.
            occasion_understood:         Whether occasion was extracted.
            meal_period_present:         Whether meal period was extracted.
            contact_details_required:    Whether contact details are mandatory.
            contact_details_present:     Whether contact details are present.

        Returns:
            MissingInformationResult.
        """
        missing_fields: list[str] = []
        critical_missing_fields: list[str] = []
        clarification_questions: list[str] = []

        # ── Date evaluation ───────────────────────────────────────────────────
        if date_status == STATUS_AMBIGUOUS:
            critical_missing_fields.append("date_confirmation")
            missing_fields.append("date_confirmation")
            question = (
                date_clarification_question
                or "Could you clarify the date you had in mind?"
            )
            clarification_questions.append(question)

        elif date_status == STATUS_RESOLVED_WITH_CONFIRMATION:
            critical_missing_fields.append("date_confirmation")
            missing_fields.append("date_confirmation")
            question = (
                date_clarification_question
                or "Could you confirm the date you mentioned?"
            )
            clarification_questions.append(question)

        elif date_status in (STATUS_UNKNOWN, None):
            critical_missing_fields.append("event_date")
            missing_fields.append("event_date")
            clarification_questions.append(
                "Could you let us know when you would like to book?"
            )

        # date_status == STATUS_RESOLVED: no date action needed

        # ── Guest count ───────────────────────────────────────────────────────
        if not guest_count_present:
            critical_missing_fields.append("guest_count")
            missing_fields.append("guest_count")
            clarification_questions.append("How many guests will be joining you?")

        # ── Occasion ──────────────────────────────────────────────────────────
        if not occasion_understood:
            missing_fields.append("occasion")
            # Occasion is not critical enough to block availability; no question added

        # ── Meal period ───────────────────────────────────────────────────────
        if not meal_period_present:
            missing_fields.append("meal_period")
            # Not critical for availability; no standalone question

        # ── Contact details ───────────────────────────────────────────────────
        if contact_details_required and not contact_details_present:
            critical_missing_fields.append("contact_details")
            missing_fields.append("contact_details")
            clarification_questions.append(
                "Could you provide your contact details so we can reach you?"
            )

        # ── Classify: email vs webform ────────────────────────────────────────
        num_critical = len(critical_missing_fields)

        if num_critical == 0:
            return MissingInformationResult(
                missing_fields=missing_fields,
                critical_missing_fields=[],
                clarification_questions=[],
                can_ask_by_email=False,
                should_send_webform=False,
                missing_info_reason="All critical information is present.",
            )

        should_send_webform = num_critical >= WEBFORM_THRESHOLD
        can_ask_by_email = not should_send_webform

        if should_send_webform:
            reason = (
                f"{num_critical} critical field(s) are missing "
                f"({', '.join(critical_missing_fields)}); "
                "directing guest to the booking webform."
            )
        else:
            reason = (
                f"{num_critical} critical field(s) missing "
                f"({', '.join(critical_missing_fields)}); "
                "will ask by email."
            )

        return MissingInformationResult(
            missing_fields=missing_fields,
            critical_missing_fields=critical_missing_fields,
            clarification_questions=clarification_questions,
            can_ask_by_email=can_ask_by_email,
            should_send_webform=should_send_webform,
            missing_info_reason=reason,
        )
