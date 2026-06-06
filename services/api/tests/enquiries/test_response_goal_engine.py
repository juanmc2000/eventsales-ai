"""Tests for ResponseGoalEngine (ORCH-001)."""

from __future__ import annotations

import pytest

from app.modules.enquiries.date_resolution_status import (
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_RESOLVED_WITH_CONFIRMATION,
    STATUS_UNKNOWN,
    DateResolutionStatus,
)
from app.modules.enquiries.readiness_evaluator import (
    STATUS_INSUFFICIENT_INFORMATION,
    STATUS_NEEDS_CLARIFICATION,
    STATUS_READY_FOR_AVAILABILITY,
    STATUS_WEBFORM_REQUIRED,
    ReadinessEvaluation,
)
from app.modules.enquiries.response_goal_engine import (
    ALL_GOALS,
    GOAL_ACKNOWLEDGE_AND_CHECK_AVAILABILITY,
    GOAL_CONFIRM_AVAILABLE,
    GOAL_ESCALATE_TO_HUMAN,
    GOAL_READY_TO_CONFIRM_AVAILABILITY,
    GOAL_REQUEST_DATE_CONFIRMATION,
    GOAL_REQUEST_MISSING_INFORMATION,
    GOAL_REQUEST_WEBFORM,
    GOAL_RESPOND_UNAVAILABLE,
    GOAL_UNABLE_TO_PROCESS,
    ResponseGoalEngine,
    ResponseGoalResult,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _readiness(
    status: str = STATUS_READY_FOR_AVAILABILITY,
    date_understood: bool = True,
    guest_count_present: bool = True,
    occasion_understood: bool = True,
    meal_period_present: bool = True,
    audience_identified: bool = True,
    date_clarification_required: bool = False,
    availability_check_possible: bool = True,
    missing_for_availability: list[str] | None = None,
    notes: str = "",
) -> ReadinessEvaluation:
    return ReadinessEvaluation(
        status=status,
        date_understood=date_understood,
        guest_count_present=guest_count_present,
        occasion_understood=occasion_understood,
        meal_period_present=meal_period_present,
        audience_identified=audience_identified,
        date_clarification_required=date_clarification_required,
        availability_check_possible=availability_check_possible,
        missing_for_availability=missing_for_availability or [],
        notes=notes,
    )


def _date_status(
    status: str = STATUS_RESOLVED,
    original_text: str = "next Saturday",
    clarification_question: str | None = None,
) -> DateResolutionStatus:
    return DateResolutionStatus(
        status=status,
        original_text=original_text,
        resolution_method="deterministic",
        resolved_date="2026-06-14" if status == STATUS_RESOLVED else None,
        alternative_date=None,
        clarification_required=status in (STATUS_AMBIGUOUS, STATUS_RESOLVED_WITH_CONFIRMATION),
        clarification_reason=None,
        clarification_question=clarification_question,
    )


class _FakeAvailabilityDecision:
    """Minimal stand-in for AvailabilityDecision (ORCH-002)."""

    def __init__(self, availability_status: str) -> None:
        self.availability_status = availability_status


class _FakeMissingInfo:
    """Minimal stand-in for MissingInformationResult (ORCH-003)."""

    def __init__(
        self,
        missing_fields: list[str] | None = None,
        critical_missing_fields: list[str] | None = None,
        should_send_webform: bool = False,
        missing_info_reason: str = "",
    ) -> None:
        self.missing_fields = missing_fields or []
        self.critical_missing_fields = critical_missing_fields or []
        self.should_send_webform = should_send_webform
        self.missing_info_reason = missing_info_reason


# ── ALL_GOALS constant ─────────────────────────────────────────────────────────


def test_all_goals_contains_new_goals():
    assert GOAL_CONFIRM_AVAILABLE in ALL_GOALS
    assert GOAL_RESPOND_UNAVAILABLE in ALL_GOALS
    assert GOAL_ACKNOWLEDGE_AND_CHECK_AVAILABILITY in ALL_GOALS
    assert GOAL_UNABLE_TO_PROCESS in ALL_GOALS
    # deprecated alias still present for backward compat
    assert GOAL_READY_TO_CONFIRM_AVAILABILITY in ALL_GOALS


# ── ResponseGoalResult ────────────────────────────────────────────────────────


def test_result_to_dict_includes_all_keys():
    r = ResponseGoalResult(
        response_goal=GOAL_READY_TO_CONFIRM_AVAILABILITY,
        goal_reason="all good",
        blocking_fields=[],
        can_generate_draft=True,
    )
    d = r.to_dict()
    assert set(d.keys()) == {"response_goal", "goal_reason", "blocking_fields", "can_generate_draft"}


# ── Rule 1: UNABLE_TO_PROCESS ─────────────────────────────────────────────────


def test_unable_to_process_when_nothing_usable():
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(
            status=STATUS_INSUFFICIENT_INFORMATION,
            date_understood=False,
            guest_count_present=False,
            occasion_understood=False,
        ),
        date_resolution_status=_date_status(status=STATUS_UNKNOWN),
    )
    assert r.response_goal == GOAL_UNABLE_TO_PROCESS
    assert r.can_generate_draft is False
    assert "date" in r.blocking_fields


def test_unable_to_process_when_date_status_none_and_nothing_known():
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(
            status=STATUS_INSUFFICIENT_INFORMATION,
            date_understood=False,
            guest_count_present=False,
            occasion_understood=False,
        ),
        date_resolution_status=None,
    )
    assert r.response_goal == GOAL_UNABLE_TO_PROCESS
    assert r.can_generate_draft is False


# ── Rule 2: ESCALATE_TO_HUMAN ─────────────────────────────────────────────────


def test_escalate_when_insufficient_but_occasion_understood():
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(
            status=STATUS_INSUFFICIENT_INFORMATION,
            occasion_understood=True,
            guest_count_present=False,
            date_understood=False,
            missing_for_availability=["date", "guest_count"],
        ),
        date_resolution_status=_date_status(status=STATUS_UNKNOWN),
    )
    assert r.response_goal == GOAL_ESCALATE_TO_HUMAN
    assert r.can_generate_draft is False
    assert "date" in r.blocking_fields


def test_escalate_when_insufficient_but_guest_count_present():
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(
            status=STATUS_INSUFFICIENT_INFORMATION,
            guest_count_present=True,
            occasion_understood=False,
            date_understood=False,
        ),
        date_resolution_status=_date_status(status=STATUS_UNKNOWN),
    )
    assert r.response_goal == GOAL_ESCALATE_TO_HUMAN
    assert r.can_generate_draft is False


# ── Rule 3: REQUEST_DATE_CONFIRMATION ─────────────────────────────────────────


def test_date_ambiguous_triggers_date_confirmation():
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(),
        date_resolution_status=_date_status(status=STATUS_AMBIGUOUS),
    )
    assert r.response_goal == GOAL_REQUEST_DATE_CONFIRMATION
    assert r.can_generate_draft is True
    assert "date_confirmation" in r.blocking_fields


def test_date_resolved_with_confirmation_triggers_date_confirmation():
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(),
        date_resolution_status=_date_status(
            status=STATUS_RESOLVED_WITH_CONFIRMATION,
            clarification_question="Did you mean 7 June or 6 July?",
        ),
    )
    assert r.response_goal == GOAL_REQUEST_DATE_CONFIRMATION
    assert r.can_generate_draft is True
    assert "Did you mean" in r.goal_reason


def test_date_confirmation_includes_clarification_question_in_reason():
    question = "Could you confirm whether you meant 14 June or 14 July?"
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(),
        date_resolution_status=_date_status(
            status=STATUS_AMBIGUOUS,
            clarification_question=question,
        ),
    )
    assert question in r.goal_reason


# ── Rule 4: REQUEST_WEBFORM ───────────────────────────────────────────────────


def test_webform_required_by_readiness_evaluator():
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(status=STATUS_WEBFORM_REQUIRED),
        date_resolution_status=_date_status(status=STATUS_RESOLVED),
    )
    assert r.response_goal == GOAL_REQUEST_WEBFORM
    assert r.can_generate_draft is True


def test_webform_required_by_missing_info_engine():
    missing = _FakeMissingInfo(
        should_send_webform=True,
        critical_missing_fields=["date", "guest_count", "occasion"],
        missing_info_reason="Three or more critical fields missing.",
    )
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(status=STATUS_NEEDS_CLARIFICATION),
        date_resolution_status=_date_status(status=STATUS_RESOLVED),
        missing_information_result=missing,
    )
    assert r.response_goal == GOAL_REQUEST_WEBFORM
    assert r.can_generate_draft is True


# ── Rule 5: REQUEST_MISSING_INFORMATION ───────────────────────────────────────


def test_needs_clarification_produces_request_missing_info():
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(
            status=STATUS_NEEDS_CLARIFICATION,
            guest_count_present=False,
            missing_for_availability=["guest_count"],
            notes="Guest count is missing.",
        ),
        date_resolution_status=_date_status(status=STATUS_RESOLVED),
    )
    assert r.response_goal == GOAL_REQUEST_MISSING_INFORMATION
    assert r.can_generate_draft is True
    assert "guest_count" in r.blocking_fields


def test_critical_fields_from_missing_info_engine_trigger_request_missing():
    missing = _FakeMissingInfo(
        critical_missing_fields=["guest_count"],
        should_send_webform=False,
    )
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(status=STATUS_READY_FOR_AVAILABILITY),
        date_resolution_status=_date_status(status=STATUS_RESOLVED),
        missing_information_result=missing,
    )
    assert r.response_goal == GOAL_REQUEST_MISSING_INFORMATION
    assert "guest_count" in r.blocking_fields


# ── Rule 6: Availability-aware response goals (RESP-005) ──────────────────────


def test_confirm_available_when_availability_decision_available():
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(status=STATUS_READY_FOR_AVAILABILITY),
        date_resolution_status=_date_status(status=STATUS_RESOLVED),
        availability_decision=_FakeAvailabilityDecision("AVAILABLE"),
    )
    assert r.response_goal == GOAL_CONFIRM_AVAILABLE
    assert r.can_generate_draft is True
    assert r.blocking_fields == []


def test_confirm_available_when_partially_available():
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(status=STATUS_READY_FOR_AVAILABILITY),
        date_resolution_status=_date_status(status=STATUS_RESOLVED),
        availability_decision=_FakeAvailabilityDecision("PARTIALLY_AVAILABLE"),
    )
    assert r.response_goal == GOAL_CONFIRM_AVAILABLE


def test_respond_unavailable_when_availability_decision_unavailable():
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(status=STATUS_READY_FOR_AVAILABILITY),
        date_resolution_status=_date_status(status=STATUS_RESOLVED),
        availability_decision=_FakeAvailabilityDecision("UNAVAILABLE"),
    )
    assert r.response_goal == GOAL_RESPOND_UNAVAILABLE
    assert r.can_generate_draft is True
    assert r.blocking_fields == []


def test_acknowledge_and_check_when_no_availability_decision():
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(status=STATUS_READY_FOR_AVAILABILITY),
        date_resolution_status=_date_status(status=STATUS_RESOLVED),
        availability_decision=None,
    )
    assert r.response_goal == GOAL_ACKNOWLEDGE_AND_CHECK_AVAILABILITY
    assert r.can_generate_draft is True
    assert r.blocking_fields == []


def test_acknowledge_and_check_when_not_checked_status():
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(status=STATUS_READY_FOR_AVAILABILITY),
        date_resolution_status=_date_status(status=STATUS_RESOLVED),
        availability_decision=_FakeAvailabilityDecision("NOT_CHECKED"),
    )
    assert r.response_goal == GOAL_ACKNOWLEDGE_AND_CHECK_AVAILABILITY


def test_acknowledge_and_check_with_no_date_resolution():
    """date_resolution_status=None still resolves to ACKNOWLEDGE when no availability."""
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(status=STATUS_READY_FOR_AVAILABILITY),
        date_resolution_status=None,
    )
    assert r.response_goal == GOAL_ACKNOWLEDGE_AND_CHECK_AVAILABILITY


def test_acknowledge_and_check_with_empty_missing_info():
    missing = _FakeMissingInfo(
        missing_fields=[],
        critical_missing_fields=[],
        should_send_webform=False,
    )
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(status=STATUS_READY_FOR_AVAILABILITY),
        date_resolution_status=_date_status(status=STATUS_RESOLVED),
        missing_information_result=missing,
    )
    assert r.response_goal == GOAL_ACKNOWLEDGE_AND_CHECK_AVAILABILITY


# ── Goal properties ───────────────────────────────────────────────────────────


def test_can_generate_draft_false_for_escalate():
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(
            status=STATUS_INSUFFICIENT_INFORMATION,
            occasion_understood=True,
        ),
        date_resolution_status=_date_status(status=STATUS_UNKNOWN),
    )
    assert r.can_generate_draft is False


def test_can_generate_draft_false_for_unable_to_process():
    r = ResponseGoalEngine.decide(
        readiness_evaluation=_readiness(
            status=STATUS_INSUFFICIENT_INFORMATION,
            guest_count_present=False,
            occasion_understood=False,
            date_understood=False,
        ),
        date_resolution_status=None,
    )
    assert r.can_generate_draft is False


def test_customer_type_does_not_affect_goal_assignment():
    """customer_type is passed through but does not alter goal selection in isolation."""
    for ctype in ("social", "corporate", "agency", "unknown"):
        r = ResponseGoalEngine.decide(
            readiness_evaluation=_readiness(status=STATUS_READY_FOR_AVAILABILITY),
            date_resolution_status=_date_status(status=STATUS_RESOLVED),
            customer_type=ctype,
        )
        assert r.response_goal == GOAL_ACKNOWLEDGE_AND_CHECK_AVAILABILITY
