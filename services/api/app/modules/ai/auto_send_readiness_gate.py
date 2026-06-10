"""Auto-Send Readiness Gate (RESP-014, updated RESP-022, AUTO-001).

Determines whether a generated draft is safe for automatic sending without
human review.  All checks are deterministic — no LLM calls are made.

The system prefers false negatives over false positives — when in doubt,
require human review.

Auto-send is allowed only when ALL of the following conditions are met:

  1. Draft compliance passed (DraftComplianceValidator returned passed=True).
  2. Response goal is in the auto-sendable set:
       CONFIRM_AVAILABLE, ACKNOWLEDGE_AND_CHECK_AVAILABILITY.
  3. Date status is explicitly resolved or resolved_with_confirmation.
  4. No human escalation is flagged (ESCALATE_TO_HUMAN goal).
  5. Context integrity gate passed (ResponseContextIntegrityGate returned passed=True).
  6. No unknown or approval-required policy questions present (RESP-048).

Usage::

    from app.modules.ai.auto_send_readiness_gate import AutoSendReadinessGate, AutoSendReadinessResult
    from app.modules.ai.draft_compliance_validator import ComplianceResult
    from app.modules.enquiries.response_context_integrity_gate import IntegrityCheckResult

    compliance = ComplianceResult(passed=True, violations=[], unsafe_to_send=False)
    integrity = IntegrityCheckResult(passed=True)
    result = AutoSendReadinessGate.evaluate(
        response_goal="CONFIRM_AVAILABLE",
        draft_compliance_result=compliance,
        date_status="resolved",
        integrity_result=integrity,
    )
    # result.auto_send_allowed → True
    # result.auto_send_blockers → []
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.modules.ai.draft_compliance_validator import ComplianceResult
    from app.modules.enquiries.response_context_integrity_gate import IntegrityCheckResult

# AUTO-001: Import policy constants from the canonical eligibility policy
from app.modules.ai.auto_send_policy import AutoSendEligibilityPolicy as _Policy  # noqa: E402

# Keep module-level aliases for backwards-compatibility with any external readers
_AUTO_SEND_GOALS: frozenset[str] = _Policy.ALLOWED_GOALS
_ALLOWED_DATE_STATUSES: frozenset[str] = _Policy.ALLOWED_DATE_STATUSES


# ── Output ─────────────────────────────────────────────────────────────────────


@dataclass
class AutoSendReadinessResult:
    """Result of AutoSendReadinessGate.evaluate().

    Attributes:
        auto_send_allowed:     True when all gate conditions pass.
        auto_send_blockers:    Ordered list of human-readable blocker descriptions.
        review_required_reason: Single-sentence summary when review is required; empty string otherwise.
    """

    auto_send_allowed: bool
    auto_send_blockers: list[str] = field(default_factory=list)
    review_required_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "auto_send_allowed": self.auto_send_allowed,
            "auto_send_blockers": self.auto_send_blockers,
            "review_required_reason": self.review_required_reason,
        }


# ── Gate ───────────────────────────────────────────────────────────────────────


class AutoSendReadinessGate:
    """Deterministic gate that decides whether a draft may be auto-sent.

    Call AutoSendReadinessGate.evaluate() with the draft's context.
    All checks run even after the first failure so that all blockers are
    reported together.

    Rules (in evaluation order):
      1. Draft compliance must pass.
      2. Response goal must be auto-sendable.
      3. Date status must be resolved or resolved_with_confirmation.
      4. Response goal must not be ESCALATE_TO_HUMAN.
      5. Context integrity gate must have passed.
      6. No high-risk unknown policy questions present (RESP-048).
    """

    @classmethod
    def evaluate(
        cls,
        response_goal: str,
        draft_compliance_result: ComplianceResult,
        date_status: str = "resolved",
        integrity_result: IntegrityCheckResult | None = None,
        availability_status: str | None = None,
        customer_type_confidence: float = 0.0,
        response_plan: dict[str, Any] | None = None,
        review_required_policy_questions: list[Any] | None = None,
    ) -> AutoSendReadinessResult:
        """Evaluate auto-send readiness.

        Args:
            response_goal:             Response goal from the deterministic plan.
            draft_compliance_result:   Result from DraftComplianceValidator.validate().
            date_status:               Date resolution status string (e.g. "resolved",
                                       "resolved_with_confirmation", "ambiguous", "unknown").
            integrity_result:          Result from ResponseContextIntegrityGate.check().
                                       None is treated as a failed integrity check.
            availability_status:       Availability decision status (informational).
            customer_type_confidence:  Confidence of customer type classification (0–1).
            response_plan:             The full ResponsePlan dict (reserved for future checks).
            review_required_policy_questions: List of policy questions that could not be
                                       answered and require human review (RESP-048).

        Returns:
            AutoSendReadinessResult.
        """
        blockers: list[str] = []

        # Rule 1: draft compliance must pass
        cls._check_compliance(draft_compliance_result, blockers)

        # Rule 2: response goal must be auto-sendable
        cls._check_response_goal(response_goal, blockers)

        # Rule 3: date must be explicitly resolved
        cls._check_date_status(date_status, blockers)

        # Rule 4: no human escalation
        cls._check_no_escalation(response_goal, blockers)

        # Rule 5: context integrity gate must have passed
        cls._check_integrity(integrity_result, blockers)

        # Rule 6: no high-risk unknown policy questions
        cls._check_policy_questions(review_required_policy_questions, blockers)

        auto_send_allowed = len(blockers) == 0
        review_required_reason = (
            "; ".join(blockers) if blockers else ""
        )

        return AutoSendReadinessResult(
            auto_send_allowed=auto_send_allowed,
            auto_send_blockers=blockers,
            review_required_reason=review_required_reason,
        )

    # ── Rule checkers ─────────────────────────────────────────────────────────

    @staticmethod
    def _check_compliance(
        compliance: ComplianceResult,
        blockers: list[str],
    ) -> None:
        """Block auto-send when the draft failed compliance validation."""
        if not compliance.passed:
            violation_summary = "; ".join(compliance.violations) if compliance.violations else "unknown"
            blockers.append(
                f"Draft failed compliance validation: {violation_summary}"
            )

    @staticmethod
    def _check_response_goal(
        response_goal: str,
        blockers: list[str],
    ) -> None:
        """Block auto-send when the response goal is not in the auto-sendable set."""
        reason = _Policy.goal_block_reason(response_goal)
        if reason is not None:
            blockers.append(reason)

    @staticmethod
    def _check_date_status(
        date_status: str,
        blockers: list[str],
    ) -> None:
        """Block auto-send when the date is not explicitly resolved."""
        reason = _Policy.date_status_block_reason(date_status)
        if reason is not None:
            blockers.append(reason)

    @staticmethod
    def _check_no_escalation(
        response_goal: str,
        blockers: list[str],
    ) -> None:
        """Block auto-send when the goal requires human review."""
        if response_goal == "ESCALATE_TO_HUMAN":
            blockers.append(
                "Response goal is ESCALATE_TO_HUMAN — human review is required before sending."
            )

    @staticmethod
    def _check_integrity(
        integrity_result: IntegrityCheckResult | None,
        blockers: list[str],
    ) -> None:
        """Block auto-send when the context integrity gate did not pass."""
        if integrity_result is None:
            blockers.append(
                "Context integrity gate result is absent — auto-send blocked as a precaution."
            )
        elif not integrity_result.passed:
            violation_summary = "; ".join(integrity_result.violations) if integrity_result.violations else "unknown"
            blockers.append(
                f"Context integrity gate failed: {violation_summary}"
            )

    @staticmethod
    def _check_policy_questions(
        review_required_policy_questions: list[Any] | None,
        blockers: list[str],
    ) -> None:
        """Block auto-send when unknown or approval-required policy questions exist (RESP-048).

        Sending a response that contains holding phrases without human confirmation
        of the actual policy answer is unsafe and could mislead the guest.
        """
        if review_required_policy_questions:
            count = len(review_required_policy_questions)
            blockers.append(
                f"{count} policy question(s) require human review before auto-send — "
                "unknown or approval-required policy questions must be resolved by a human."
            )
