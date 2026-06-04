"""Availability Decision Service (ORCH-002).

Deterministic service that converts candidate-date and room availability results
into a single, response-ready availability status.

The draft LLM must not inspect raw candidate-date rows or infer availability
from partial data.  This service produces a clean AvailabilityDecision that
downstream components (ResponseGoalEngine, ResponsePreparationBuilder) consume
verbatim.

Supported statuses:
  AVAILABLE                — one or more candidate dates confirmed available
  UNAVAILABLE              — candidate dates exist but none are available
  PARTIALLY_AVAILABLE      — some dates available, some not
  PENDING_DATE_CONFIRMATION — date is ambiguous; availability cannot be checked
  INSUFFICIENT_INFORMATION  — required inputs missing; cannot make a decision
  NOT_CHECKED              — availability data was never fetched

Inputs (passed as plain Python objects, not ORM rows):
  - candidate_dates: list of CandidateDateInfo records (or dicts)
  - date_resolution_status: DateResolutionStatus | None from DATE-002
  - guest_count: int | None
  - meal_period: str | None
  - room_availability_results: dict | None — from processing snapshot

Outputs:
  AvailabilityDecision with:
  - availability_status
  - selected_candidate_date: ISO date string | None
  - available_options: list of ISO date strings
  - unavailable_options: list of ISO date strings
  - availability_reason: human-readable explanation

No LLM calls are made.  No database mutations are performed.

Usage::

    from app.modules.enquiries.availability_decision_service import (
        AvailabilityDecisionService,
        STATUS_AVAILABLE,
    )

    decision = AvailabilityDecisionService.decide(
        candidate_dates=[{"candidate_date": "2026-06-21", "availability_status": "available"}],
        date_resolution_status=date_status,
        guest_count=30,
        meal_period="dinner",
        room_availability_results={"status": "available"},
    )
    # decision.availability_status → "AVAILABLE"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.modules.enquiries.date_resolution_status import (
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_RESOLVED_WITH_CONFIRMATION,
    STATUS_UNKNOWN,
    DateResolutionStatus,
)

if TYPE_CHECKING:
    pass  # No forward-declared types needed yet

# ── Status constants ───────────────────────────────────────────────────────────

STATUS_AVAILABLE = "AVAILABLE"
STATUS_UNAVAILABLE = "UNAVAILABLE"
STATUS_PARTIALLY_AVAILABLE = "PARTIALLY_AVAILABLE"
STATUS_PENDING_DATE_CONFIRMATION = "PENDING_DATE_CONFIRMATION"
STATUS_INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
STATUS_NOT_CHECKED = "NOT_CHECKED"

ALL_AVAILABILITY_STATUSES = {
    STATUS_AVAILABLE,
    STATUS_UNAVAILABLE,
    STATUS_PARTIALLY_AVAILABLE,
    STATUS_PENDING_DATE_CONFIRMATION,
    STATUS_INSUFFICIENT_INFORMATION,
    STATUS_NOT_CHECKED,
}

# Candidate availability status values (from processing_service / DB)
_CANDIDATE_AVAILABLE = "available"
_CANDIDATE_UNAVAILABLE = "unavailable"
_CANDIDATE_UNKNOWN = "unknown"

# ── Output ─────────────────────────────────────────────────────────────────────


@dataclass
class AvailabilityDecision:
    """Outcome of AvailabilityDecisionService.decide().

    Attributes:
        availability_status:      One of the STATUS_* constants.
        selected_candidate_date:  Best available date (ISO) or None.
        available_options:        All confirmed-available candidate dates (ISO).
        unavailable_options:      All confirmed-unavailable candidate dates (ISO).
        availability_reason:      Human-readable explanation.
    """

    availability_status: str
    selected_candidate_date: str | None = None
    available_options: list[str] = field(default_factory=list)
    unavailable_options: list[str] = field(default_factory=list)
    availability_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "availability_status": self.availability_status,
            "selected_candidate_date": self.selected_candidate_date,
            "available_options": self.available_options,
            "unavailable_options": self.unavailable_options,
            "availability_reason": self.availability_reason,
        }


# ── Service ────────────────────────────────────────────────────────────────────


class AvailabilityDecisionService:
    """Converts candidate-date and availability data into a single decision.

    Decision precedence (first match wins):
      1. PENDING_DATE_CONFIRMATION — date status is ambiguous
      2. INSUFFICIENT_INFORMATION  — no guest count and no candidate dates
      3. NOT_CHECKED               — no room_availability_results provided
      4. AVAILABLE / PARTIALLY_AVAILABLE / UNAVAILABLE — from candidate analysis
    """

    @classmethod
    def decide(
        cls,
        candidate_dates: list[Any] | None = None,
        date_resolution_status: DateResolutionStatus | None = None,
        guest_count: int | None = None,
        meal_period: str | None = None,
        room_availability_results: dict | None = None,
    ) -> AvailabilityDecision:
        """Produce an AvailabilityDecision from the supplied inputs.

        Args:
            candidate_dates:          List of candidate-date objects/dicts.
                                      Each item must expose ``candidate_date`` (ISO
                                      string) and optionally ``availability_status``
                                      ("available" | "unavailable" | "unknown").
            date_resolution_status:   DateResolutionStatus (DATE-002) or None.
            guest_count:              Number of guests or None.
            meal_period:              "lunch" | "dinner" | None.
            room_availability_results: Availability result dict from processing
                                       snapshot or None.

        Returns:
            AvailabilityDecision.
        """
        candidates = candidate_dates or []
        date_status = (
            date_resolution_status.status if date_resolution_status else STATUS_UNKNOWN
        )

        # ── Rule 1 — Date ambiguous; availability cannot be checked ──────────
        if date_status == STATUS_AMBIGUOUS:
            return AvailabilityDecision(
                availability_status=STATUS_PENDING_DATE_CONFIRMATION,
                availability_reason=(
                    "Date is ambiguous; availability cannot be checked until "
                    "the guest confirms which date they meant."
                ),
            )

        # ── Rule 2 — Insufficient inputs ──────────────────────────────────────
        if not candidates and guest_count is None:
            return AvailabilityDecision(
                availability_status=STATUS_INSUFFICIENT_INFORMATION,
                availability_reason=(
                    "Neither candidate dates nor guest count are available; "
                    "availability cannot be assessed."
                ),
            )

        # ── Rule 3 — No availability data fetched ────────────────────────────
        if room_availability_results is None and not _any_candidate_has_status(candidates):
            return AvailabilityDecision(
                availability_status=STATUS_NOT_CHECKED,
                availability_reason=(
                    "No room availability results were provided; "
                    "availability has not been checked."
                ),
            )

        # ── Rule 4 — Analyse candidate dates ─────────────────────────────────
        available: list[str] = []
        unavailable: list[str] = []

        for cd in candidates:
            date_str = _get_field(cd, "candidate_date")
            avail_status = _get_field(cd, "availability_status") or _CANDIDATE_UNKNOWN
            if not date_str:
                continue
            if avail_status == _CANDIDATE_AVAILABLE:
                available.append(str(date_str))
            elif avail_status == _CANDIDATE_UNAVAILABLE:
                unavailable.append(str(date_str))
            # "unknown" status: not classified either way

        if not candidates:
            # No candidate dates at all — fall back to room_availability_results dict
            return cls._decide_from_snapshot(room_availability_results)

        if available and unavailable:
            return AvailabilityDecision(
                availability_status=STATUS_PARTIALLY_AVAILABLE,
                selected_candidate_date=available[0],
                available_options=available,
                unavailable_options=unavailable,
                availability_reason=(
                    f"{len(available)} date(s) available, {len(unavailable)} unavailable."
                ),
            )

        if available:
            return AvailabilityDecision(
                availability_status=STATUS_AVAILABLE,
                selected_candidate_date=available[0],
                available_options=available,
                unavailable_options=unavailable,
                availability_reason=(
                    f"{len(available)} candidate date(s) confirmed available."
                ),
            )

        if unavailable:
            return AvailabilityDecision(
                availability_status=STATUS_UNAVAILABLE,
                available_options=[],
                unavailable_options=unavailable,
                availability_reason=(
                    f"No candidate dates are available. "
                    f"{len(unavailable)} date(s) checked and unavailable."
                ),
            )

        # Candidates exist but none have a classified status — use snapshot
        return cls._decide_from_snapshot(room_availability_results)

    # ── Internal helpers ───────────────────────────────────────────────────────

    @classmethod
    def _decide_from_snapshot(
        cls, snapshot: dict | None
    ) -> AvailabilityDecision:
        """Derive a decision from a processing snapshot dict when no classified candidates."""
        if not snapshot:
            return AvailabilityDecision(
                availability_status=STATUS_NOT_CHECKED,
                availability_reason="No availability data available.",
            )
        snap_status = snapshot.get("status", "")
        if snap_status == "available":
            date_str = snapshot.get("date")
            return AvailabilityDecision(
                availability_status=STATUS_AVAILABLE,
                selected_candidate_date=date_str,
                available_options=[date_str] if date_str else [],
                availability_reason="Availability confirmed via processing snapshot.",
            )
        if snap_status in ("unavailable", "full"):
            return AvailabilityDecision(
                availability_status=STATUS_UNAVAILABLE,
                availability_reason=snapshot.get("reason", "Date is unavailable."),
            )
        return AvailabilityDecision(
            availability_status=STATUS_NOT_CHECKED,
            availability_reason=(
                f"Availability snapshot status '{snap_status}' is not conclusive."
            ),
        )


# ── Helpers ────────────────────────────────────────────────────────────────────


def _get_field(obj: Any, key: str) -> Any:
    """Get a field from either a dict or an object attribute."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _any_candidate_has_status(candidates: list[Any]) -> bool:
    """Return True if at least one candidate has a known availability_status."""
    for cd in candidates:
        status = _get_field(cd, "availability_status")
        if status and status != _CANDIDATE_UNKNOWN:
            return True
    return False
