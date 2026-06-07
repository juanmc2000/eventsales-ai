"""Draft Review Status Lifecycle (AUTO-002).

Tracks whether a draft is safe, blocked, needs human review, or is
eligible for auto-send.  All evaluations are deterministic — no LLM calls.

Status flow:

  DRAFT_CREATED
      │
      ├── compliance fails → VALIDATION_FAILED
      │
      ├── compliance passes + goal/date blocked → HUMAN_REVIEW_REQUIRED
      │
      ├── compliance passes + all gate rules pass → AUTO_SEND_ELIGIBLE
      │
      ├── human reviewer approves → APPROVED_TO_SEND
      │
      └── message sent → SENT

Usage::

    from app.modules.ai.draft_review_state import DraftReviewStateService

    state = DraftReviewStateService.evaluate(
        compliance_result=compliance,
        readiness_result=readiness,
    )
    # state.status → "AUTO_SEND_ELIGIBLE" or "HUMAN_REVIEW_REQUIRED" etc.
    # state.blockers → ["..."]
    # state.auto_send_allowed → True / False
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Status constants ────────────────────────────────────────────────────────────

DRAFT_CREATED = "DRAFT_CREATED"
VALIDATION_FAILED = "VALIDATION_FAILED"
HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
AUTO_SEND_ELIGIBLE = "AUTO_SEND_ELIGIBLE"
APPROVED_TO_SEND = "APPROVED_TO_SEND"
SENT = "SENT"

# All valid statuses (ordered by lifecycle stage)
ALL_STATUSES: tuple[str, ...] = (
    DRAFT_CREATED,
    VALIDATION_FAILED,
    HUMAN_REVIEW_REQUIRED,
    AUTO_SEND_ELIGIBLE,
    APPROVED_TO_SEND,
    SENT,
)


# ── State dataclass ─────────────────────────────────────────────────────────────


@dataclass
class DraftReviewState:
    """Captured lifecycle state of a draft response.

    Attributes:
        status:              One of the DRAFT_* / *_TO_SEND / SENT constants.
        auto_send_allowed:   True when all auto-send gate conditions pass.
        blockers:            Human-readable reasons why auto-send is blocked (may be empty).
        validation_passed:   True when DraftComplianceValidator returned passed=True.
        validation_violations: List of compliance violation strings (may be empty).
        auto_send_blockers:  Subset of blockers from the AutoSendReadinessGate.
        reviewer_notes:      Optional free-text notes added during human review.
    """

    status: str
    auto_send_allowed: bool = False
    blockers: list[str] = field(default_factory=list)
    validation_passed: bool = True
    validation_violations: list[str] = field(default_factory=list)
    auto_send_blockers: list[str] = field(default_factory=list)
    reviewer_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "auto_send_allowed": self.auto_send_allowed,
            "blockers": self.blockers,
            "validation_passed": self.validation_passed,
            "validation_violations": self.validation_violations,
            "auto_send_blockers": self.auto_send_blockers,
            "reviewer_notes": self.reviewer_notes,
        }


# ── Service ─────────────────────────────────────────────────────────────────────


class DraftReviewStateService:
    """Evaluates the review lifecycle state of a draft response.

    All evaluations are deterministic.  Accepts ComplianceResult and
    AutoSendReadinessResult to produce a DraftReviewState.
    """

    @classmethod
    def evaluate(
        cls,
        compliance_result: Any,
        readiness_result: Any | None = None,
        reviewer_notes: str = "",
    ) -> DraftReviewState:
        """Evaluate the draft lifecycle state.

        Args:
            compliance_result:  Result from DraftComplianceValidator.validate().
            readiness_result:   Result from AutoSendReadinessGate.evaluate().
                                None is treated as gate-not-run (→ HUMAN_REVIEW_REQUIRED).
            reviewer_notes:     Optional human notes (set during review).

        Returns:
            DraftReviewState with status, blockers, and validation information.
        """
        validation_passed = getattr(compliance_result, "passed", False)
        validation_violations: list[str] = list(
            getattr(compliance_result, "violations", []) or []
        )

        # Stage 1: compliance must pass
        if not validation_passed:
            return DraftReviewState(
                status=VALIDATION_FAILED,
                auto_send_allowed=False,
                blockers=list(validation_violations),
                validation_passed=False,
                validation_violations=validation_violations,
                auto_send_blockers=list(validation_violations),
                reviewer_notes=reviewer_notes,
            )

        # Stage 2: auto-send gate evaluation
        if readiness_result is None:
            # Gate was not run — require human review
            return DraftReviewState(
                status=HUMAN_REVIEW_REQUIRED,
                auto_send_allowed=False,
                blockers=["Auto-send readiness gate was not evaluated."],
                validation_passed=True,
                validation_violations=[],
                auto_send_blockers=["Auto-send readiness gate was not evaluated."],
                reviewer_notes=reviewer_notes,
            )

        auto_send_allowed = getattr(readiness_result, "auto_send_allowed", False)
        gate_blockers: list[str] = list(
            getattr(readiness_result, "auto_send_blockers", []) or []
        )

        if auto_send_allowed:
            return DraftReviewState(
                status=AUTO_SEND_ELIGIBLE,
                auto_send_allowed=True,
                blockers=[],
                validation_passed=True,
                validation_violations=[],
                auto_send_blockers=[],
                reviewer_notes=reviewer_notes,
            )

        return DraftReviewState(
            status=HUMAN_REVIEW_REQUIRED,
            auto_send_allowed=False,
            blockers=list(gate_blockers),
            validation_passed=True,
            validation_violations=[],
            auto_send_blockers=list(gate_blockers),
            reviewer_notes=reviewer_notes,
        )

    @classmethod
    def approved(cls, current_state: DraftReviewState, reviewer_notes: str = "") -> DraftReviewState:
        """Transition a HUMAN_REVIEW_REQUIRED or AUTO_SEND_ELIGIBLE draft to APPROVED_TO_SEND.

        Args:
            current_state: The existing DraftReviewState.
            reviewer_notes: Optional reviewer comments.

        Returns:
            New DraftReviewState with status=APPROVED_TO_SEND.
        """
        from dataclasses import replace
        return replace(
            current_state,
            status=APPROVED_TO_SEND,
            reviewer_notes=reviewer_notes or current_state.reviewer_notes,
        )

    @classmethod
    def sent(cls, current_state: DraftReviewState) -> DraftReviewState:
        """Transition a draft to SENT status.

        Returns:
            New DraftReviewState with status=SENT.
        """
        from dataclasses import replace
        return replace(current_state, status=SENT)
