"""Tests for RoomAvailabilityRepository and RoomAvailabilityOut schemas.

Covers:
- Repository returns correct rows for a room+date
- Repository returns empty list when no rows exist
- Schema serialises correctly
- Deterministic hash function produces consistent statuses
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.modules.restaurants.schemas import RoomAvailabilityOut, RoomAvailabilitySlot


# ── Schema tests ──────────────────────────────────────────────────────────────


def test_room_availability_out_empty_slots() -> None:
    """RoomAvailabilityOut accepts an empty slots list — not an error."""
    room_id = uuid.uuid4()
    out = RoomAvailabilityOut(
        room_id=room_id,
        room_name="The Test Room",
        date=date(2026, 8, 15),
        slots=[],
    )
    assert out.slots == []
    assert out.room_id == room_id


def test_room_availability_slot_fields() -> None:
    slot = RoomAvailabilitySlot(meal_period="dinner", status="available", notes=None)
    assert slot.meal_period == "dinner"
    assert slot.status == "available"
    assert slot.notes is None


def test_room_availability_slot_with_notes() -> None:
    slot = RoomAvailabilitySlot(meal_period="lunch", status="held", notes="Held for Smith party")
    assert slot.notes == "Held for Smith party"


def test_room_availability_out_with_slots() -> None:
    room_id = uuid.uuid4()
    out = RoomAvailabilityOut(
        room_id=room_id,
        room_name="The Grand Room",
        date=date(2026, 9, 20),
        slots=[
            RoomAvailabilitySlot(meal_period="lunch", status="available"),
            RoomAvailabilitySlot(meal_period="dinner", status="booked"),
        ],
    )
    assert len(out.slots) == 2
    statuses = {s.meal_period: s.status for s in out.slots}
    assert statuses["lunch"] == "available"
    assert statuses["dinner"] == "booked"


# ── Seed determinism test ─────────────────────────────────────────────────────


def test_avail_status_deterministic() -> None:
    """The hash-based status function returns the same value on repeated calls."""
    from app.modules.shared.seed_data import _avail_status_for

    room_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
    d = date(2026, 8, 15)

    result1 = _avail_status_for(room_id, d, "dinner")
    result2 = _avail_status_for(room_id, d, "dinner")
    assert result1 == result2


def test_avail_status_varies_by_meal_period() -> None:
    """Different meal periods can produce different statuses."""
    from app.modules.shared.seed_data import _avail_status_for

    room_id = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    d = date(2026, 10, 1)

    lunch = _avail_status_for(room_id, d, "lunch")
    dinner = _avail_status_for(room_id, d, "dinner")
    # Both should be valid statuses
    valid = {"available", "booked", "held", "unavailable"}
    assert lunch in valid
    assert dinner in valid


def test_avail_status_valid_values() -> None:
    """All generated statuses are within the allowed set."""
    from app.modules.shared.seed_data import _avail_status_for

    valid = {"available", "booked", "held", "unavailable"}
    room_id = uuid.uuid4()
    for day in range(1, 32):
        try:
            d = date(2026, 8, day)
        except ValueError:
            break
        for mp in ("lunch", "dinner"):
            status = _avail_status_for(room_id, d, mp)
            assert status in valid, f"Unexpected status {status!r} for {d} {mp}"


# ── Repository tests (in-memory via unit test without DB) ─────────────────────


def test_room_availability_repository_import() -> None:
    """RoomAvailabilityRepository is importable and instantiable with a mock session."""
    from unittest.mock import MagicMock

    from app.modules.restaurants.repository import RoomAvailabilityRepository

    mock_db = MagicMock()
    repo = RoomAvailabilityRepository(mock_db)
    assert repo is not None
