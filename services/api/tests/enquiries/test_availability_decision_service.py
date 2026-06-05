"""Tests for AvailabilityDecisionService (ORCH-002)."""

from __future__ import annotations

import pytest

from app.modules.enquiries.availability_decision_service import (
    ALL_AVAILABILITY_STATUSES,
    STATUS_AVAILABLE,
    STATUS_INSUFFICIENT_INFORMATION,
    STATUS_NOT_CHECKED,
    STATUS_PARTIALLY_AVAILABLE,
    STATUS_PENDING_DATE_CONFIRMATION,
    STATUS_UNAVAILABLE,
    AvailabilityDecision,
    AvailabilityDecisionService,
)
from app.modules.enquiries.date_resolution_status import (
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_UNKNOWN,
    DateResolutionStatus,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _date_status(status: str = STATUS_RESOLVED) -> DateResolutionStatus:
    return DateResolutionStatus(
        status=status,
        original_text="next Saturday",
        resolution_method="deterministic",
        resolved_date="2026-06-21" if status == STATUS_RESOLVED else None,
        alternative_date=None,
        clarification_required=status == STATUS_AMBIGUOUS,
        clarification_reason=None,
        clarification_question=None,
    )


def _candidate(date: str, avail: str = "available") -> dict:
    return {"candidate_date": date, "availability_status": avail}


# ── Constants ─────────────────────────────────────────────────────────────────


def test_all_statuses_has_six_values():
    assert len(ALL_AVAILABILITY_STATUSES) == 6


# ── AvailabilityDecision.to_dict ──────────────────────────────────────────────


def test_to_dict_has_all_keys():
    d = AvailabilityDecision(availability_status=STATUS_AVAILABLE).to_dict()
    assert set(d.keys()) == {
        "availability_status",
        "selected_candidate_date",
        "available_options",
        "unavailable_options",
        "availability_reason",
    }


# ── Rule 1: PENDING_DATE_CONFIRMATION ────────────────────────────────────────


def test_ambiguous_date_returns_pending():
    result = AvailabilityDecisionService.decide(
        candidate_dates=[_candidate("2026-06-21")],
        date_resolution_status=_date_status(STATUS_AMBIGUOUS),
        guest_count=20,
    )
    assert result.availability_status == STATUS_PENDING_DATE_CONFIRMATION
    assert result.selected_candidate_date is None


def test_ambiguous_date_with_no_candidates_still_pending():
    result = AvailabilityDecisionService.decide(
        candidate_dates=[],
        date_resolution_status=_date_status(STATUS_AMBIGUOUS),
        guest_count=20,
    )
    assert result.availability_status == STATUS_PENDING_DATE_CONFIRMATION


# ── Rule 2: INSUFFICIENT_INFORMATION ─────────────────────────────────────────


def test_no_candidates_and_no_guest_count_returns_insufficient():
    result = AvailabilityDecisionService.decide(
        candidate_dates=[],
        date_resolution_status=_date_status(STATUS_RESOLVED),
        guest_count=None,
    )
    assert result.availability_status == STATUS_INSUFFICIENT_INFORMATION


def test_none_candidate_dates_and_no_guest_count_returns_insufficient():
    result = AvailabilityDecisionService.decide(
        candidate_dates=None,
        date_resolution_status=_date_status(STATUS_RESOLVED),
        guest_count=None,
    )
    assert result.availability_status == STATUS_INSUFFICIENT_INFORMATION


# ── Rule 3: NOT_CHECKED ───────────────────────────────────────────────────────


def test_no_availability_results_and_unknown_candidates_returns_not_checked():
    result = AvailabilityDecisionService.decide(
        candidate_dates=[{"candidate_date": "2026-06-21", "availability_status": "unknown"}],
        date_resolution_status=_date_status(STATUS_RESOLVED),
        guest_count=10,
        room_availability_results=None,
    )
    assert result.availability_status == STATUS_NOT_CHECKED


def test_no_candidates_and_no_results_returns_not_checked():
    result = AvailabilityDecisionService.decide(
        candidate_dates=[],
        date_resolution_status=_date_status(STATUS_RESOLVED),
        guest_count=10,
        room_availability_results=None,
    )
    assert result.availability_status == STATUS_NOT_CHECKED


# ── Rule 4: AVAILABLE ─────────────────────────────────────────────────────────


def test_single_available_candidate_returns_available():
    result = AvailabilityDecisionService.decide(
        candidate_dates=[_candidate("2026-06-21", "available")],
        date_resolution_status=_date_status(STATUS_RESOLVED),
        guest_count=20,
        room_availability_results={"status": "available"},
    )
    assert result.availability_status == STATUS_AVAILABLE
    assert result.selected_candidate_date == "2026-06-21"
    assert "2026-06-21" in result.available_options


def test_multiple_available_candidates_returns_available():
    result = AvailabilityDecisionService.decide(
        candidate_dates=[
            _candidate("2026-06-21", "available"),
            _candidate("2026-06-28", "available"),
        ],
        date_resolution_status=_date_status(STATUS_RESOLVED),
        guest_count=30,
    )
    assert result.availability_status == STATUS_AVAILABLE
    assert result.selected_candidate_date == "2026-06-21"
    assert len(result.available_options) == 2


# ── Rule 4: UNAVAILABLE ───────────────────────────────────────────────────────


def test_all_unavailable_candidates_returns_unavailable():
    result = AvailabilityDecisionService.decide(
        candidate_dates=[
            _candidate("2026-06-21", "unavailable"),
            _candidate("2026-06-28", "unavailable"),
        ],
        date_resolution_status=_date_status(STATUS_RESOLVED),
        guest_count=20,
    )
    assert result.availability_status == STATUS_UNAVAILABLE
    assert result.selected_candidate_date is None
    assert len(result.unavailable_options) == 2


# ── Rule 4: PARTIALLY_AVAILABLE ───────────────────────────────────────────────


def test_mixed_candidates_returns_partially_available():
    result = AvailabilityDecisionService.decide(
        candidate_dates=[
            _candidate("2026-06-21", "available"),
            _candidate("2026-06-28", "unavailable"),
        ],
        date_resolution_status=_date_status(STATUS_RESOLVED),
        guest_count=25,
    )
    assert result.availability_status == STATUS_PARTIALLY_AVAILABLE
    assert result.selected_candidate_date == "2026-06-21"
    assert "2026-06-21" in result.available_options
    assert "2026-06-28" in result.unavailable_options


# ── Snapshot fallback ─────────────────────────────────────────────────────────


def test_snapshot_available_when_no_candidates():
    result = AvailabilityDecisionService.decide(
        candidate_dates=[],
        date_resolution_status=_date_status(STATUS_RESOLVED),
        guest_count=10,
        room_availability_results={"status": "available", "date": "2026-06-21"},
    )
    assert result.availability_status == STATUS_AVAILABLE
    assert result.selected_candidate_date == "2026-06-21"


def test_snapshot_unavailable_when_no_candidates():
    result = AvailabilityDecisionService.decide(
        candidate_dates=[],
        date_resolution_status=_date_status(STATUS_RESOLVED),
        guest_count=10,
        room_availability_results={"status": "unavailable", "reason": "Date is full."},
    )
    assert result.availability_status == STATUS_UNAVAILABLE


# ── ORM-object-style input ────────────────────────────────────────────────────


class _FakeCandidateDate:
    def __init__(self, candidate_date: str, availability_status: str = "available") -> None:
        self.candidate_date = candidate_date
        self.availability_status = availability_status


def test_orm_style_objects_work():
    result = AvailabilityDecisionService.decide(
        candidate_dates=[_FakeCandidateDate("2026-06-21", "available")],
        date_resolution_status=_date_status(STATUS_RESOLVED),
        guest_count=15,
    )
    assert result.availability_status == STATUS_AVAILABLE
    assert result.selected_candidate_date == "2026-06-21"


# ── No date_resolution_status ─────────────────────────────────────────────────


def test_works_with_no_date_resolution_status():
    result = AvailabilityDecisionService.decide(
        candidate_dates=[_candidate("2026-06-21", "available")],
        date_resolution_status=None,
        guest_count=10,
    )
    assert result.availability_status == STATUS_AVAILABLE
