"""Tests for AlternativeDateService (RESP-042)."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch
import uuid

import pytest

from app.modules.enquiries.alternative_date_service import (
    AlternativeDateResult,
    AlternativeDateService,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _slot(meal_period: str, status: str) -> MagicMock:
    slot = MagicMock()
    slot.meal_period = meal_period
    slot.status = status
    return slot


def _room(room_id: uuid.UUID, capacity: int | None = 50) -> MagicMock:
    r = MagicMock()
    r.id = room_id
    r.seated_capacity = capacity
    return r


RESTAURANT_ID = uuid.uuid4()
ROOM_ID = uuid.uuid4()
REQ_DATE = date(2026, 7, 15)


# ── Result dataclass ───────────────────────────────────────────────────────────


def test_result_no_alternatives():
    result = AlternativeDateResult(
        requested_date="2026-07-15",
        alternative_dates=[],
        alternatives_found=False,
    )
    assert result.alternatives_found is False
    assert result.alternative_dates == []
    assert result.to_dict()["alternatives_found"] is False


def test_result_one_alternative():
    result = AlternativeDateResult(
        requested_date="2026-07-15",
        alternative_dates=["2026-07-14"],
        alternatives_found=True,
    )
    assert result.alternatives_found is True
    assert result.alternative_dates == ["2026-07-14"]


def test_result_two_alternatives():
    result = AlternativeDateResult(
        requested_date="2026-07-15",
        alternative_dates=["2026-07-14", "2026-07-16"],
        alternatives_found=True,
    )
    assert len(result.alternative_dates) == 2


# ── Service: zero alternatives ─────────────────────────────────────────────────


def test_no_room_found_returns_empty():
    db = MagicMock()
    avail_repo = MagicMock()
    room_repo = MagicMock()
    room_repo.list_for_restaurant.return_value = []

    with patch(
        "app.modules.enquiries.alternative_date_service.RoomAvailabilityRepository",
        return_value=avail_repo,
    ), patch(
        "app.modules.enquiries.alternative_date_service.RoomRepository",
        return_value=room_repo,
    ):
        result = AlternativeDateService.find_alternatives(
            db=db,
            restaurant_id=RESTAURANT_ID,
            requested_date=REQ_DATE,
            meal_period="dinner",
        )

    assert result.alternatives_found is False
    assert result.alternative_dates == []
    assert "No suitable rooms" in result.check_reason


def test_no_available_slots_returns_empty():
    db = MagicMock()
    room = _room(ROOM_ID)
    avail_repo = MagicMock()
    avail_repo.get_for_room_date.return_value = [_slot("dinner", "booked")]
    room_repo = MagicMock()
    room_repo.list_for_restaurant.return_value = [room]

    with patch(
        "app.modules.enquiries.alternative_date_service.RoomAvailabilityRepository",
        return_value=avail_repo,
    ), patch(
        "app.modules.enquiries.alternative_date_service.RoomRepository",
        return_value=room_repo,
    ):
        result = AlternativeDateService.find_alternatives(
            db=db,
            restaurant_id=RESTAURANT_ID,
            requested_date=REQ_DATE,
            meal_period="dinner",
        )

    assert result.alternatives_found is False
    assert len(result.checked_dates) == 2  # D-1 and D+1 were checked


# ── Service: one alternative ───────────────────────────────────────────────────


def test_one_alternative_d_minus_1():
    db = MagicMock()
    room = _room(ROOM_ID)
    room_repo = MagicMock()
    room_repo.list_for_restaurant.return_value = [room]

    d_minus_1 = date(2026, 7, 14)
    d_plus_1 = date(2026, 7, 16)

    def _get_slots(room_id, check_date):
        if check_date == d_minus_1:
            return [_slot("dinner", "available")]
        if check_date == d_plus_1:
            return [_slot("dinner", "booked")]
        return []

    avail_repo = MagicMock()
    avail_repo.get_for_room_date.side_effect = _get_slots

    with patch(
        "app.modules.enquiries.alternative_date_service.RoomAvailabilityRepository",
        return_value=avail_repo,
    ), patch(
        "app.modules.enquiries.alternative_date_service.RoomRepository",
        return_value=room_repo,
    ):
        result = AlternativeDateService.find_alternatives(
            db=db,
            restaurant_id=RESTAURANT_ID,
            requested_date=REQ_DATE,
            meal_period="dinner",
        )

    assert result.alternatives_found is True
    assert result.alternative_dates == ["2026-07-14"]


# ── Service: two alternatives ──────────────────────────────────────────────────


def test_two_alternatives_both_available():
    db = MagicMock()
    room = _room(ROOM_ID)
    room_repo = MagicMock()
    room_repo.list_for_restaurant.return_value = [room]
    avail_repo = MagicMock()
    avail_repo.get_for_room_date.return_value = [_slot("dinner", "available")]

    with patch(
        "app.modules.enquiries.alternative_date_service.RoomAvailabilityRepository",
        return_value=avail_repo,
    ), patch(
        "app.modules.enquiries.alternative_date_service.RoomRepository",
        return_value=room_repo,
    ):
        result = AlternativeDateService.find_alternatives(
            db=db,
            restaurant_id=RESTAURANT_ID,
            requested_date=REQ_DATE,
            meal_period="dinner",
        )

    assert result.alternatives_found is True
    assert len(result.alternative_dates) == 2
    assert "2026-07-14" in result.alternative_dates
    assert "2026-07-16" in result.alternative_dates


# ── Service: specific room_id ──────────────────────────────────────────────────


def test_specific_room_id_skips_room_lookup():
    db = MagicMock()
    avail_repo = MagicMock()
    avail_repo.get_for_room_date.return_value = [_slot("dinner", "available")]
    room_repo = MagicMock()

    with patch(
        "app.modules.enquiries.alternative_date_service.RoomAvailabilityRepository",
        return_value=avail_repo,
    ), patch(
        "app.modules.enquiries.alternative_date_service.RoomRepository",
        return_value=room_repo,
    ):
        result = AlternativeDateService.find_alternatives(
            db=db,
            restaurant_id=RESTAURANT_ID,
            requested_date=REQ_DATE,
            meal_period="dinner",
            room_id=ROOM_ID,
        )

    # room_repo.list_for_restaurant should NOT be called when room_id is given
    room_repo.list_for_restaurant.assert_not_called()
    assert result.alternatives_found is True


# ── Service: capacity filtering ────────────────────────────────────────────────


def test_capacity_filter_excludes_small_room():
    db = MagicMock()
    small_room = _room(uuid.uuid4(), capacity=10)
    room_repo = MagicMock()
    room_repo.list_for_restaurant.return_value = [small_room]
    avail_repo = MagicMock()

    with patch(
        "app.modules.enquiries.alternative_date_service.RoomAvailabilityRepository",
        return_value=avail_repo,
    ), patch(
        "app.modules.enquiries.alternative_date_service.RoomRepository",
        return_value=room_repo,
    ):
        result = AlternativeDateService.find_alternatives(
            db=db,
            restaurant_id=RESTAURANT_ID,
            requested_date=REQ_DATE,
            meal_period="dinner",
            guest_count=50,  # exceeds room capacity of 10
        )

    assert result.alternatives_found is False
    assert "No suitable rooms" in result.check_reason
