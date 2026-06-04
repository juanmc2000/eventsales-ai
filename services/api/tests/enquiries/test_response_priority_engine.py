"""Tests for ResponsePriorityEngine (ORCH-004)."""

from __future__ import annotations

from datetime import date

import pytest

from app.modules.enquiries.date_resolution_status import (
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_UNKNOWN,
)
from app.modules.enquiries.response_priority_engine import (
    ALL_PRIORITIES,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
    PRIORITY_URGENT,
    THRESHOLD_HIGH_DAYS,
    THRESHOLD_NORMAL_DAYS,
    THRESHOLD_URGENT_DAYS,
    ResponsePriorityEngine,
    ResponsePriorityResult,
)

ANCHOR = date(2026, 6, 4)  # Fixed anchor date for deterministic tests


# ── Constants ─────────────────────────────────────────────────────────────────


def test_all_priorities_has_four_values():
    assert len(ALL_PRIORITIES) == 4


def test_threshold_constants():
    assert THRESHOLD_URGENT_DAYS == 1
    assert THRESHOLD_HIGH_DAYS == 14
    assert THRESHOLD_NORMAL_DAYS == 90


# ── ResponsePriorityResult ────────────────────────────────────────────────────


def test_to_dict_has_all_keys():
    r = ResponsePriorityResult(response_priority=PRIORITY_NORMAL, priority_reason="ok")
    assert set(r.to_dict().keys()) == {"response_priority", "priority_reason"}


# ── URGENT — today ────────────────────────────────────────────────────────────


def test_today_is_urgent():
    r = ResponsePriorityEngine.decide(
        resolved_event_date=ANCHOR.isoformat(),
        anchor_date=ANCHOR,
    )
    assert r.response_priority == PRIORITY_URGENT


def test_tomorrow_is_urgent():
    tomorrow = date(2026, 6, 5)
    r = ResponsePriorityEngine.decide(
        resolved_event_date=tomorrow.isoformat(),
        anchor_date=ANCHOR,
    )
    assert r.response_priority == PRIORITY_URGENT


# ── URGENT — past date ────────────────────────────────────────────────────────


def test_past_date_is_urgent():
    r = ResponsePriorityEngine.decide(
        resolved_event_date="2026-06-01",
        anchor_date=ANCHOR,
    )
    assert r.response_priority == PRIORITY_URGENT
    assert "past" in r.priority_reason.lower()


# ── HIGH — within 14 days ─────────────────────────────────────────────────────


def test_two_days_away_is_high():
    r = ResponsePriorityEngine.decide(
        resolved_event_date="2026-06-06",
        anchor_date=ANCHOR,
    )
    assert r.response_priority == PRIORITY_HIGH


def test_fourteen_days_away_is_high():
    r = ResponsePriorityEngine.decide(
        resolved_event_date="2026-06-18",
        anchor_date=ANCHOR,
    )
    assert r.response_priority == PRIORITY_HIGH


# ── NORMAL — within 90 days ───────────────────────────────────────────────────


def test_fifteen_days_away_is_normal():
    r = ResponsePriorityEngine.decide(
        resolved_event_date="2026-06-19",
        anchor_date=ANCHOR,
    )
    assert r.response_priority == PRIORITY_NORMAL


def test_ninety_days_away_is_normal():
    r = ResponsePriorityEngine.decide(
        resolved_event_date="2026-09-02",
        anchor_date=ANCHOR,
    )
    assert r.response_priority == PRIORITY_NORMAL


# ── LOW — beyond 90 days ──────────────────────────────────────────────────────


def test_ninety_one_days_away_is_low():
    r = ResponsePriorityEngine.decide(
        resolved_event_date="2026-09-03",
        anchor_date=ANCHOR,
    )
    assert r.response_priority == PRIORITY_LOW


def test_far_future_is_low():
    r = ResponsePriorityEngine.decide(
        resolved_event_date="2027-06-04",
        anchor_date=ANCHOR,
    )
    assert r.response_priority == PRIORITY_LOW


# ── Missing / ambiguous date → NORMAL ────────────────────────────────────────


def test_no_date_defaults_to_normal():
    r = ResponsePriorityEngine.decide(
        resolved_event_date=None,
        candidate_dates=None,
        date_status=STATUS_UNKNOWN,
        anchor_date=ANCHOR,
    )
    assert r.response_priority == PRIORITY_NORMAL
    assert "No resolved event date" in r.priority_reason


def test_ambiguous_date_status_defaults_to_normal():
    r = ResponsePriorityEngine.decide(
        resolved_event_date=None,
        date_status=STATUS_AMBIGUOUS,
        anchor_date=ANCHOR,
    )
    assert r.response_priority == PRIORITY_NORMAL


# ── Candidate date fallback ───────────────────────────────────────────────────


def test_uses_earliest_candidate_when_no_resolved_date():
    r = ResponsePriorityEngine.decide(
        resolved_event_date=None,
        candidate_dates=["2026-09-03", "2026-06-06"],
        anchor_date=ANCHOR,
    )
    # Earliest is 2026-06-06 = 2 days away → HIGH
    assert r.response_priority == PRIORITY_HIGH


def test_single_candidate_date_used():
    r = ResponsePriorityEngine.decide(
        resolved_event_date=None,
        candidate_dates=["2026-06-05"],
        anchor_date=ANCHOR,
    )
    assert r.response_priority == PRIORITY_URGENT


def test_invalid_candidate_dates_skipped():
    r = ResponsePriorityEngine.decide(
        resolved_event_date=None,
        candidate_dates=["not-a-date", "2026-09-03"],
        anchor_date=ANCHOR,
    )
    assert r.response_priority == PRIORITY_LOW


# ── Priority reason text ──────────────────────────────────────────────────────


def test_urgent_reason_mentions_days():
    r = ResponsePriorityEngine.decide(
        resolved_event_date=ANCHOR.isoformat(),
        anchor_date=ANCHOR,
    )
    assert "URGENT" in r.priority_reason or "urgent" in r.priority_reason.lower()


def test_low_reason_mentions_days():
    r = ResponsePriorityEngine.decide(
        resolved_event_date="2027-01-01",
        anchor_date=ANCHOR,
    )
    assert "LOW" in r.priority_reason or "low" in r.priority_reason.lower()
