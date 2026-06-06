"""Tests for RESP-021 — ResponseContextIntegrityGate.

Validates:
- Restaurant ID mismatch blocks draft generation
- Restaurant name mismatch (when IDs absent) blocks draft generation
- Room ID mismatch blocks draft generation
- Room name mismatch (when IDs absent) blocks draft generation
- Matching IDs passes
- Matching names (case-insensitive) passes
- Absent availability data passes (insufficient data to validate)
- requires_review=True on any violation
"""

from __future__ import annotations

import uuid

import pytest

from app.modules.enquiries.response_context_integrity_gate import (
    IntegrityCheckResult,
    ResponseContextIntegrityGate,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _check(**kwargs) -> IntegrityCheckResult:
    defaults = {
        "context_restaurant_name": "The Ivy Tower Bridge",
    }
    defaults.update(kwargs)
    return ResponseContextIntegrityGate.check(**defaults)


# ── IntegrityCheckResult ───────────────────────────────────────────────────────


class TestIntegrityCheckResult:
    def test_passed_result_has_no_violations(self) -> None:
        result = IntegrityCheckResult(passed=True)
        assert result.violations == []
        assert result.requires_review is False

    def test_failed_result_sets_requires_review(self) -> None:
        result = IntegrityCheckResult(passed=False, violations=["mismatch"], requires_review=True)
        assert result.requires_review is True

    def test_to_dict_contains_expected_keys(self) -> None:
        result = IntegrityCheckResult(passed=True)
        d = result.to_dict()
        assert "passed" in d
        assert "violations" in d
        assert "requires_review" in d


# ── No availability data — always pass ────────────────────────────────────────


class TestNoAvailabilityData:
    def test_passes_when_no_availability_names_or_ids(self) -> None:
        result = _check()
        assert result.passed is True

    def test_passes_when_only_context_name_provided(self) -> None:
        result = _check(context_restaurant_name="The Grand")
        assert result.passed is True

    def test_passes_when_room_context_set_but_no_availability_room(self) -> None:
        result = _check(context_room_name="Private Dining Room")
        assert result.passed is True


# ── Restaurant name comparison ────────────────────────────────────────────────


class TestRestaurantNameCheck:
    def test_matching_names_pass(self) -> None:
        result = _check(
            context_restaurant_name="The Ivy Tower Bridge",
            availability_restaurant_name="The Ivy Tower Bridge",
        )
        assert result.passed is True

    def test_matching_names_case_insensitive(self) -> None:
        result = _check(
            context_restaurant_name="the ivy tower bridge",
            availability_restaurant_name="THE IVY TOWER BRIDGE",
        )
        assert result.passed is True

    def test_matching_names_with_whitespace(self) -> None:
        result = _check(
            context_restaurant_name="  The Ivy Tower Bridge  ",
            availability_restaurant_name="The Ivy Tower Bridge",
        )
        assert result.passed is True

    def test_mismatched_restaurant_names_fail(self) -> None:
        result = _check(
            context_restaurant_name="The Ivy Tower Bridge",
            availability_restaurant_name="The Grand Ballroom",
        )
        assert result.passed is False
        assert result.requires_review is True
        assert any("restaurant" in v.lower() for v in result.violations)

    def test_mismatch_violation_includes_both_names(self) -> None:
        result = _check(
            context_restaurant_name="The Ivy Tower Bridge",
            availability_restaurant_name="The Mayfair Suite",
        )
        assert result.passed is False
        assert any("Ivy Tower Bridge" in v for v in result.violations)
        assert any("Mayfair Suite" in v for v in result.violations)


# ── Restaurant ID comparison ──────────────────────────────────────────────────


class TestRestaurantIdCheck:
    def test_matching_ids_pass(self) -> None:
        rid = uuid.uuid4()
        result = _check(
            context_restaurant_id=rid,
            availability_restaurant_id=rid,
        )
        assert result.passed is True

    def test_mismatched_ids_fail(self) -> None:
        result = _check(
            context_restaurant_id=uuid.uuid4(),
            availability_restaurant_id=uuid.uuid4(),
        )
        assert result.passed is False
        assert result.requires_review is True

    def test_id_check_takes_precedence_over_name_when_both_present(self) -> None:
        """When both IDs match, name mismatch is ignored."""
        rid = uuid.uuid4()
        result = _check(
            context_restaurant_name="The Ivy",
            availability_restaurant_name="The Grand",  # name mismatch
            context_restaurant_id=rid,
            availability_restaurant_id=rid,  # IDs match
        )
        assert result.passed is True  # ID match wins

    def test_id_mismatch_overrides_name_match(self) -> None:
        """When IDs don't match, name match doesn't save it."""
        result = _check(
            context_restaurant_name="The Ivy",
            availability_restaurant_name="The Ivy",  # names match
            context_restaurant_id=uuid.uuid4(),
            availability_restaurant_id=uuid.uuid4(),  # IDs differ
        )
        assert result.passed is False

    def test_one_id_missing_falls_back_to_name(self) -> None:
        """If only context has an ID (no availability ID), falls back to name comparison."""
        result = _check(
            context_restaurant_name="The Ivy",
            availability_restaurant_name="The Grand",
            context_restaurant_id=uuid.uuid4(),
            availability_restaurant_id=None,
        )
        # Falls back to name comparison — mismatch
        assert result.passed is False


# ── Room name comparison ───────────────────────────────────────────────────────


class TestRoomNameCheck:
    def test_matching_room_names_pass(self) -> None:
        result = _check(
            context_room_name="Private Dining Room",
            availability_room_name="Private Dining Room",
        )
        assert result.passed is True

    def test_matching_room_names_case_insensitive(self) -> None:
        result = _check(
            context_room_name="private dining room",
            availability_room_name="PRIVATE DINING ROOM",
        )
        assert result.passed is True

    def test_mismatched_room_names_fail(self) -> None:
        result = _check(
            context_room_name="Private Dining Room",
            availability_room_name="The Mayfair Suite",
        )
        assert result.passed is False
        assert result.requires_review is True
        assert any("room" in v.lower() for v in result.violations)

    def test_no_room_in_context_skips_room_check(self) -> None:
        result = _check(
            context_room_name=None,
            availability_room_name="Private Dining Room",
        )
        assert result.passed is True  # Cannot compare without context room

    def test_no_availability_room_skips_room_check(self) -> None:
        result = _check(
            context_room_name="Private Dining Room",
            availability_room_name=None,
        )
        assert result.passed is True  # Cannot compare without availability room


# ── Room ID comparison ────────────────────────────────────────────────────────


class TestRoomIdCheck:
    def test_matching_room_ids_pass(self) -> None:
        rid = uuid.uuid4()
        result = _check(
            context_room_id=rid,
            availability_room_id=rid,
        )
        assert result.passed is True

    def test_mismatched_room_ids_fail(self) -> None:
        result = _check(
            context_room_id=uuid.uuid4(),
            availability_room_id=uuid.uuid4(),
        )
        assert result.passed is False
        assert result.requires_review is True

    def test_room_id_match_ignores_name_mismatch(self) -> None:
        rid = uuid.uuid4()
        result = _check(
            context_room_name="Room A",
            availability_room_name="Room B",  # names differ
            context_room_id=rid,
            availability_room_id=rid,  # IDs match
        )
        assert result.passed is True


# ── Multiple violations ───────────────────────────────────────────────────────


class TestMultipleViolations:
    def test_both_restaurant_and_room_mismatch_recorded(self) -> None:
        result = _check(
            context_restaurant_name="The Ivy Tower Bridge",
            availability_restaurant_name="The Grand Ballroom",
            context_room_name="Private Dining Room",
            availability_room_name="The Mayfair Suite",
        )
        assert result.passed is False
        assert len(result.violations) == 2

    def test_to_dict_lists_all_violations(self) -> None:
        result = _check(
            context_restaurant_name="The Ivy",
            availability_restaurant_name="The Grand",
            context_room_name="Room A",
            availability_room_name="Room B",
        )
        d = result.to_dict()
        assert len(d["violations"]) == 2
        assert d["passed"] is False
        assert d["requires_review"] is True
