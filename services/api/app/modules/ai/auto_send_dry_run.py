"""Auto-Send Dry Run Service (AUTO-003).

Simulates the auto-send decision pipeline for an existing enquiry without
making any SMTP/Gmail calls.

Sequence:
  1. Load the latest draft message for the enquiry from the database.
  2. Load the latest response plan (for availability_contract, date_status,
     response_goal, and clarification_questions).
  3. Run DraftComplianceValidator on the draft body.
  4. Run ResponseContextIntegrityGate against the stored context names.
  5. Run AutoSendReadinessGate to determine if the draft would be auto-sent.
  6. Log the decision and return a structured result.

No email is sent under any circumstances.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ── Result dataclass ─────────────────────────────────────────────────────────


@dataclass
class AutoSendDryRunResult:
    """Structured output of a single dry-run simulation.

    Never triggers an email send — caller uses this for logging and display.
    """

    enquiry_id: uuid.UUID
    simulated_at: datetime

    # Draft metadata
    draft_message_id: uuid.UUID | None
    draft_subject: str | None
    draft_body: str | None
    draft_to_address: str | None         # guest email address

    # Compliance gate
    compliance_passed: bool
    compliance_violations: list[str]

    # Integrity gate
    integrity_passed: bool
    integrity_violations: list[str]

    # Auto-send gate
    auto_send_allowed: bool
    auto_send_blockers: list[str]

    # Context used for evaluation
    response_goal: str | None
    availability_contract: str
    date_status: str

    # Human-readable summary
    decision_summary: str = field(init=False)

    def __post_init__(self) -> None:
        if self.auto_send_allowed:
            self.decision_summary = "WOULD SEND — all gates passed"
        elif not self.compliance_passed:
            violations_str = "; ".join(self.compliance_violations[:2])
            self.decision_summary = f"BLOCKED — compliance failure: {violations_str}"
        elif not self.integrity_passed:
            self.decision_summary = "BLOCKED — context integrity mismatch"
        elif self.auto_send_blockers:
            self.decision_summary = f"BLOCKED — {self.auto_send_blockers[0]}"
        else:
            self.decision_summary = "BLOCKED — gate blocked"

    def to_dict(self) -> dict[str, Any]:
        return {
            "enquiry_id": str(self.enquiry_id),
            "simulated_at": self.simulated_at.isoformat(),
            "draft_message_id": str(self.draft_message_id) if self.draft_message_id else None,
            "draft_subject": self.draft_subject,
            "draft_body": self.draft_body,
            "draft_to_address": self.draft_to_address,
            "compliance_passed": self.compliance_passed,
            "compliance_violations": self.compliance_violations,
            "integrity_passed": self.integrity_passed,
            "integrity_violations": self.integrity_violations,
            "auto_send_allowed": self.auto_send_allowed,
            "auto_send_blockers": self.auto_send_blockers,
            "response_goal": self.response_goal,
            "availability_contract": self.availability_contract,
            "date_status": self.date_status,
            "decision_summary": self.decision_summary,
        }


# ── Service ──────────────────────────────────────────────────────────────────


class AutoSendDryRunService:
    """Simulate the auto-send decision for an existing enquiry.

    Never triggers an SMTP call or modifies any database rows.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def simulate(self, enquiry_id: uuid.UUID) -> AutoSendDryRunResult:
        """Run a dry-run simulation for the given enquiry.

        Raises:
            ValueError: if the enquiry does not exist in the database.
        """
        from app.modules.ai.draft_compliance_validator import (  # noqa: PLC0415
            DraftComplianceValidator,
            ValidationContext,
        )
        from app.modules.ai.auto_send_readiness_gate import AutoSendReadinessGate  # noqa: PLC0415
        from app.modules.enquiries.repository import (  # noqa: PLC0415
            EnquiryRepository,
            ResponsePlanRepository,
        )
        from app.modules.enquiries.response_context_integrity_gate import (  # noqa: PLC0415
            ResponseContextIntegrityGate,
        )

        repo = EnquiryRepository(self._db)

        # ── 1. Load enquiry ──────────────────────────────────────────────────
        enquiry = repo.get_by_id(enquiry_id)
        if enquiry is None:
            raise ValueError(f"Enquiry {enquiry_id} not found")

        # ── 2. Load latest draft message ─────────────────────────────────────
        draft_message = repo.get_latest_draft_message(enquiry_id)
        draft_body: str | None = draft_message.body if draft_message else None
        draft_subject: str | None = draft_message.subject if draft_message else None
        draft_message_id: uuid.UUID | None = draft_message.id if draft_message else None

        # ── 3. Load latest response plan ─────────────────────────────────────
        plan = ResponsePlanRepository(self._db).get_latest(enquiry_id)
        response_goal: str | None = None
        availability_contract = "NOT_CHECKED"
        date_status = "unknown"
        clarification_questions: list[str] = []
        context_restaurant_name: str = getattr(enquiry, "restaurant_id", None) and ""  # type: ignore[assignment]
        context_room_name: str | None = None
        availability_restaurant_name: str | None = None
        availability_room_name: str | None = None
        confirmed_minimum_spend: float | None = None

        if plan is not None:
            response_goal = getattr(plan, "response_goal", None)
            clarification_questions = list(getattr(plan, "clarification_questions", None) or [])

            avail_ctx = getattr(plan, "availability_context", None) or {}
            availability_contract = str(avail_ctx.get("availability_contract", "NOT_CHECKED"))

            date_ctx = getattr(plan, "date_context", None) or {}
            date_status = str(date_ctx.get("status", "unknown") or "unknown")

            # Restaurant + room names for integrity check
            known_facts = getattr(plan, "known_facts", None) or {}
            context_restaurant_name = str(known_facts.get("restaurant_name", "") or "")
            context_room_name = known_facts.get("room_name")
            availability_restaurant_name = str(avail_ctx.get("restaurant_name", "") or "")
            availability_room_name = avail_ctx.get("room_name")

            # Spend from known facts
            raw_spend = known_facts.get("confirmed_minimum_spend")
            if raw_spend is not None:
                try:
                    confirmed_minimum_spend = float(raw_spend)
                except (TypeError, ValueError):
                    pass

        # Fallback: restaurant name from related objects
        if not context_restaurant_name:
            from app.modules.restaurants.repository import RestaurantRepository  # noqa: PLC0415
            restaurant = RestaurantRepository(self._db).get_by_id(enquiry.restaurant_id)
            context_restaurant_name = restaurant.name if restaurant else ""

        # ── 4. Build ValidationContext ───────────────────────────────────────
        val_ctx = ValidationContext(
            availability_contract=availability_contract,
            response_goal=response_goal or "",
            confirmed_minimum_spend=confirmed_minimum_spend,
            clarification_questions=clarification_questions,
        )

        # ── 5. Run compliance validator ──────────────────────────────────────
        if draft_body:
            compliance = DraftComplianceValidator.validate(
                draft_text=draft_body,
                context=val_ctx,
            )
        else:
            # No draft — treat as compliance failure
            from app.modules.ai.draft_compliance_validator import ComplianceResult  # noqa: PLC0415
            compliance = ComplianceResult(
                passed=False,
                violations=["No draft message found for this enquiry"],
                unsafe_to_send=True,
            )

        # ── 6. Run integrity gate ────────────────────────────────────────────
        integrity = ResponseContextIntegrityGate.check(
            context_restaurant_name=context_restaurant_name,
            context_room_name=context_room_name,
            availability_restaurant_name=availability_restaurant_name or context_restaurant_name,
            availability_room_name=availability_room_name,
        )

        # ── 7. Run auto-send gate ────────────────────────────────────────────
        readiness = AutoSendReadinessGate.evaluate(
            response_goal=response_goal or "",
            draft_compliance_result=compliance,
            date_status=date_status,
            integrity_result=integrity,
        )

        # ── 8. Build and log result ──────────────────────────────────────────
        result = AutoSendDryRunResult(
            enquiry_id=enquiry_id,
            simulated_at=datetime.now(tz=timezone.utc),
            draft_message_id=draft_message_id,
            draft_subject=draft_subject,
            draft_body=draft_body,
            draft_to_address=getattr(enquiry, "email", None),
            compliance_passed=compliance.passed,
            compliance_violations=list(compliance.violations),
            integrity_passed=integrity.passed,
            integrity_violations=list(integrity.violations),
            auto_send_allowed=readiness.auto_send_allowed,
            auto_send_blockers=list(readiness.auto_send_blockers),
            response_goal=response_goal,
            availability_contract=availability_contract,
            date_status=date_status,
        )

        logger.info(
            "AutoSendDryRun: enquiry=%s goal=%s compliance=%s integrity=%s auto_send=%s — %s",
            enquiry_id,
            response_goal,
            "PASS" if compliance.passed else "FAIL",
            "PASS" if integrity.passed else "FAIL",
            "ALLOW" if readiness.auto_send_allowed else "BLOCK",
            result.decision_summary,
        )

        return result
