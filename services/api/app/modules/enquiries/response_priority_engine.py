"""Response Priority Engine (ORCH-004).

Deterministic engine that classifies how urgently an enquiry should be handled.

Priority is informational only in Sprint 10 — no jobs are scheduled or delayed.
It is recorded in the response plan for future SLA monitoring and workflow
timing use.

Priority rules (applied in order, first match wins):
  URGENT — event is today or tomorrow
  HIGH   — event is within 14 days
  NORMAL — event is within 90 days
  LOW    — event is more than 90 days away
  NORMAL — date is ambiguous, unknown, or missing (default)

Inputs:
  - resolved_event_date: ISO date string | None — primary resolved date
  - candidate_dates: list of ISO date strings — all candidate dates
  - date_status: str — from DateResolutionStatus.status
  - received_at: datetime | None — when the enquiry was received
  - anchor_date: date | None — override for "today" (used in tests)

Outputs:
  ResponsePriorityResult with:
  - response_priority: one of PRIORITY_* constants
  - priority_reason: human-readable explanation

No LLM calls are made.  No database mutations are performed.

Usage::

    from datetime import date
    from app.modules.enquiries.response_priority_engine import ResponsePriorityEngine

    result = ResponsePriorityEngine.decide(
        resolved_event_date="2026-06-06",
        anchor_date=date(2026, 6, 4),
    )
    # result.response_priority → "URGENT"
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.modules.enquiries.date_resolution_status import (
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_UNKNOWN,
)

# ── Priority constants ─────────────────────────────────────────────────────────

PRIORITY_URGENT = "URGENT"
PRIORITY_HIGH = "HIGH"
PRIORITY_NORMAL = "NORMAL"
PRIORITY_LOW = "LOW"

ALL_PRIORITIES = {PRIORITY_URGENT, PRIORITY_HIGH, PRIORITY_NORMAL, PRIORITY_LOW}

# Day thresholds (inclusive)
THRESHOLD_URGENT_DAYS = 1   # 0–1 days away → URGENT
THRESHOLD_HIGH_DAYS = 14    # 2–14 days away → HIGH
THRESHOLD_NORMAL_DAYS = 90  # 15–90 days away → NORMAL
# > 90 days → LOW

# ── Output ─────────────────────────────────────────────────────────────────────


@dataclass
class ResponsePriorityResult:
    """Outcome of ResponsePriorityEngine.decide().

    Attributes:
        response_priority: One of the PRIORITY_* constants.
        priority_reason:   Human-readable explanation.
    """

    response_priority: str
    priority_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_priority": self.response_priority,
            "priority_reason": self.priority_reason,
        }


# ── Engine ─────────────────────────────────────────────────────────────────────


class ResponsePriorityEngine:
    """Classifies enquiry urgency from resolved event date.

    All decisions are deterministic and informational only.  No jobs are
    scheduled or delayed by this engine.
    """

    @classmethod
    def decide(
        cls,
        resolved_event_date: str | None = None,
        candidate_dates: list[str] | None = None,
        date_status: str = STATUS_UNKNOWN,
        received_at: datetime | None = None,
        anchor_date: date | None = None,
    ) -> ResponsePriorityResult:
        """Decide the response priority for an enquiry.

        Args:
            resolved_event_date: ISO date string of the primary event date,
                                 or None if not resolved.
            candidate_dates:     List of ISO date strings for all candidates.
                                 The earliest candidate is used when
                                 resolved_event_date is absent.
            date_status:         DateResolutionStatus.status string.
            received_at:         When the enquiry arrived (unused in POC but
                                 reserved for future SLA calculations).
            anchor_date:         Override for today's date (for testing).

        Returns:
            ResponsePriorityResult.
        """
        today = anchor_date or date.today()

        event_date = cls._pick_event_date(resolved_event_date, candidate_dates)

        if event_date is None:
            return ResponsePriorityResult(
                response_priority=PRIORITY_NORMAL,
                priority_reason=(
                    "No resolved event date available "
                    f"(date_status={date_status}); defaulting to NORMAL."
                ),
            )

        days_away = (event_date - today).days

        if days_away < 0:
            # Event is in the past — treat as URGENT so it gets human review
            return ResponsePriorityResult(
                response_priority=PRIORITY_URGENT,
                priority_reason=(
                    f"Event date {event_date.isoformat()} is in the past "
                    f"({abs(days_away)} day(s) ago); flagging as URGENT."
                ),
            )

        if days_away <= THRESHOLD_URGENT_DAYS:
            return ResponsePriorityResult(
                response_priority=PRIORITY_URGENT,
                priority_reason=(
                    f"Event is {days_away} day(s) away ({event_date.isoformat()}); "
                    "responding today or tomorrow is URGENT."
                ),
            )

        if days_away <= THRESHOLD_HIGH_DAYS:
            return ResponsePriorityResult(
                response_priority=PRIORITY_HIGH,
                priority_reason=(
                    f"Event is {days_away} day(s) away ({event_date.isoformat()}); "
                    f"within {THRESHOLD_HIGH_DAYS} days — HIGH priority."
                ),
            )

        if days_away <= THRESHOLD_NORMAL_DAYS:
            return ResponsePriorityResult(
                response_priority=PRIORITY_NORMAL,
                priority_reason=(
                    f"Event is {days_away} day(s) away ({event_date.isoformat()}); "
                    f"within {THRESHOLD_NORMAL_DAYS} days — NORMAL priority."
                ),
            )

        return ResponsePriorityResult(
            response_priority=PRIORITY_LOW,
            priority_reason=(
                f"Event is {days_away} day(s) away ({event_date.isoformat()}); "
                f"beyond {THRESHOLD_NORMAL_DAYS} days — LOW priority."
            ),
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _pick_event_date(
        resolved: str | None,
        candidates: list[str] | None,
    ) -> date | None:
        """Parse and return the best available event date."""
        if resolved:
            try:
                return date.fromisoformat(resolved)
            except ValueError:
                pass

        if candidates:
            parsed: list[date] = []
            for c in candidates:
                try:
                    parsed.append(date.fromisoformat(str(c)))
                except ValueError:
                    continue
            if parsed:
                return min(parsed)

        return None
