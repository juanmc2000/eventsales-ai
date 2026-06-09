"""Alternative Date Service (RESP-042).

When a requested date is UNAVAILABLE, checks D-1 and D+1 for confirmed
available alternatives.  Only dates confirmed available in room_availability
data are offered — no invented alternatives are returned.

Rules:
- Check one day before the requested date (D-1)
- Check one day after the requested date (D+1)
- Same restaurant
- Same room (if room_id provided) or any active room in the restaurant
- Same meal period
- Only return dates with status == "available" in room_availability

No LLM calls are made.  No database mutations are performed.

Usage::

    from app.modules.enquiries.alternative_date_service import AlternativeDateService

    result = AlternativeDateService.find_alternatives(
        db=db,
        restaurant_id=restaurant_id,
        requested_date=date(2026, 7, 15),
        meal_period="dinner",
        room_id=room_id,  # optional
        guest_count=30,   # optional — used for capacity filtering
    )
    # result.alternative_dates  → ["2026-07-14", "2026-07-16"]
    # result.alternatives_found → True
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.modules.restaurants.repository import RoomAvailabilityRepository, RoomRepository

# Availability slot status
_STATUS_AVAILABLE = "available"


# ── Output ─────────────────────────────────────────────────────────────────────


@dataclass
class AlternativeDateResult:
    """Result of AlternativeDateService.find_alternatives().

    Attributes:
        requested_date:    ISO date string that was unavailable.
        alternative_dates: Confirmed-available alternative dates (max 2, ISO strings).
        alternatives_found: True when at least one alternative exists.
        checked_dates:     All candidate dates that were checked (for traceability).
        check_reason:      Human-readable summary of the check.
    """

    requested_date: str
    alternative_dates: list[str] = field(default_factory=list)
    alternatives_found: bool = False
    checked_dates: list[str] = field(default_factory=list)
    check_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_date": self.requested_date,
            "alternative_dates": self.alternative_dates,
            "alternatives_found": self.alternatives_found,
            "checked_dates": self.checked_dates,
            "check_reason": self.check_reason,
        }


# ── Service ────────────────────────────────────────────────────────────────────


class AlternativeDateService:
    """Deterministic service that finds alternative dates when a slot is unavailable.

    Checks D-1 and D+1 for the same restaurant, room, and meal period.
    Only returns dates that are confirmed available in the room_availability table.
    """

    @classmethod
    def find_alternatives(
        cls,
        db: Session,
        restaurant_id: uuid.UUID,
        requested_date: date,
        meal_period: str,
        room_id: uuid.UUID | None = None,
        guest_count: int | None = None,
    ) -> AlternativeDateResult:
        """Find confirmed available alternative dates for D-1 and D+1.

        Args:
            db:              SQLAlchemy session.
            restaurant_id:   Restaurant to search within.
            requested_date:  The original date that was unavailable.
            meal_period:     "lunch" or "dinner".
            room_id:         Specific room to check; if None checks all active rooms.
            guest_count:     Optional — used to filter rooms by seated capacity.

        Returns:
            AlternativeDateResult with up to two confirmed-available dates.
        """
        avail_repo = RoomAvailabilityRepository(db)
        room_repo = RoomRepository(db)

        candidate_dates = [
            requested_date - timedelta(days=1),
            requested_date + timedelta(days=1),
        ]
        checked: list[str] = []
        confirmed: list[str] = []

        # Determine which rooms to check
        room_ids: list[uuid.UUID] = []
        if room_id is not None:
            room_ids = [room_id]
        else:
            rooms = room_repo.list_for_restaurant(restaurant_id, active_only=True)
            for room in rooms:
                # Filter by capacity when guest_count is provided
                if guest_count is not None and room.seated_capacity is not None:
                    if guest_count > room.seated_capacity:
                        continue
                room_ids.append(room.id)

        if not room_ids:
            return AlternativeDateResult(
                requested_date=requested_date.isoformat(),
                check_reason="No suitable rooms found for the restaurant.",
            )

        for cand_date in candidate_dates:
            cand_iso = cand_date.isoformat()
            checked.append(cand_iso)
            if cls._any_room_available(avail_repo, room_ids, cand_date, meal_period):
                confirmed.append(cand_iso)
            if len(confirmed) == 2:
                break  # we only offer up to two alternatives

        return AlternativeDateResult(
            requested_date=requested_date.isoformat(),
            alternative_dates=confirmed,
            alternatives_found=len(confirmed) > 0,
            checked_dates=checked,
            check_reason=(
                f"Checked {len(checked)} candidate date(s) (D-1/D+1) for "
                f"{meal_period}; found {len(confirmed)} available alternative(s)."
            ),
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _any_room_available(
        avail_repo: RoomAvailabilityRepository,
        room_ids: list[uuid.UUID],
        check_date: date,
        meal_period: str,
    ) -> bool:
        """Return True if any of the given rooms has an available slot for the date/period."""
        for rid in room_ids:
            slots = avail_repo.get_for_room_date(rid, check_date)
            for slot in slots:
                if slot.meal_period == meal_period and slot.status == _STATUS_AVAILABLE:
                    return True
        return False
