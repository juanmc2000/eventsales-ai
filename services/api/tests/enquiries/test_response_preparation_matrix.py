"""TEST-010 — Response Preparation Test Matrix.

Deterministic matrix validating that ResponsePreparationBuilder.build()
produces the correct operational decision across 15 realistic enquiry scenarios.

Metrics covered:
  - response_goal accuracy
  - missing information accuracy
  - date clarification accuracy
  - persona routing accuracy
  - response priority accuracy

All tests are deterministic — no LLM calls, no DB connections, no SMTP.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from app.modules.enquiries.availability_decision_service import (
    AvailabilityDecision,
    STATUS_AVAILABLE,
    STATUS_UNAVAILABLE,
    STATUS_PENDING_DATE_CONFIRMATION,
)
from app.modules.enquiries.date_resolution_status import (
    DateResolutionStatus,
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_UNKNOWN,
)
from app.modules.enquiries.missing_information_engine import MissingInformationResult
from app.modules.enquiries.persona_routing_context import (
    PersonaRoutingContextBuilder,
    TONE_GUIDANCE,
)
from app.modules.enquiries.readiness_evaluator import (
    ReadinessEvaluation,
    STATUS_INSUFFICIENT_INFORMATION,
    STATUS_NEEDS_CLARIFICATION,
    STATUS_READY_FOR_AVAILABILITY,
    STATUS_WEBFORM_REQUIRED,
)
from app.modules.enquiries.response_goal_engine import (
    GOAL_CONFIRM_AVAILABLE,
    GOAL_ESCALATE_TO_HUMAN,
    GOAL_REQUEST_DATE_CONFIRMATION,
    GOAL_REQUEST_MISSING_INFORMATION,
    GOAL_REQUEST_WEBFORM,
)
from app.modules.enquiries.response_preparation_builder import ResponsePreparationBuilder
from app.modules.enquiries.response_priority_engine import (
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
    PRIORITY_URGENT,
    ResponsePriorityResult,
)

# ── Fixture helpers ────────────────────────────────────────────────────────────

_CASES_PATH = Path(__file__).parent.parent / "fixtures" / "response_preparation_cases.json"

_ANCHOR_DATE = date(2026, 6, 5)  # fixed anchor so priority calculations are stable


def _load_cases() -> dict[str, dict]:
    """Load fixture JSON as a dict keyed by scenario ID."""
    raw = json.loads(_CASES_PATH.read_text())
    return {c["id"]: c for c in raw}


_CASES = _load_cases()


def _expected(scenario_id: str) -> dict:
    return _CASES[scenario_id]["expected"]


def _ready_readiness(*, date_understood: bool = True, guest_count: bool = True,
                     occasion: bool = True, meal_period: bool = True,
                     audience: bool = True) -> ReadinessEvaluation:
    """Helper that returns a READY_FOR_AVAILABILITY readiness evaluation."""
    return ReadinessEvaluation(
        status=STATUS_READY_FOR_AVAILABILITY,
        date_understood=date_understood,
        guest_count_present=guest_count,
        occasion_understood=occasion,
        meal_period_present=meal_period,
        audience_identified=audience,
        date_clarification_required=False,
        availability_check_possible=True,
        missing_for_availability=[],
        notes="",
    )


def _resolved_date_status(resolved_date: str = "2026-07-15") -> DateResolutionStatus:
    """Helper that returns a STATUS_RESOLVED DateResolutionStatus."""
    return DateResolutionStatus(
        status=STATUS_RESOLVED,
        original_text=resolved_date,
        resolution_method="explicit_date",
        resolved_date=resolved_date,
        alternative_date=None,
        clarification_required=False,
        clarification_reason=None,
        clarification_question=None,
        candidate_dates=[resolved_date],
    )


def _available_decision(date_str: str = "2026-07-15") -> AvailabilityDecision:
    return AvailabilityDecision(
        availability_status=STATUS_AVAILABLE,
        selected_candidate_date=date_str,
        available_options=[date_str],
        unavailable_options=[],
        availability_reason="Room available on requested date.",
    )


def _no_missing() -> MissingInformationResult:
    return MissingInformationResult(
        missing_fields=[],
        critical_missing_fields=[],
        clarification_questions=[],
        can_ask_by_email=False,
        should_send_webform=False,
        missing_info_reason="",
    )


# ── Scenario 01: Complete enquiry, available date ─────────────────────────────


def test_scenario_01_complete_enquiry_available_date():
    exp = _expected("scenario_01")

    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        date_resolution_status=_resolved_date_status("2026-07-15"),
        candidate_dates=[],
        customer_type="social",
        availability_decision=_available_decision("2026-07-15"),
        missing_information_result=_no_missing(),
        response_priority_result=ResponsePriorityResult(
            response_priority=PRIORITY_NORMAL,
            priority_reason="15–90 days away.",
        ),
    )

    assert plan.response_goal == exp["response_goal"]
    assert plan.can_generate_draft is exp["can_generate_draft"]
    assert plan.response_priority == exp["response_priority"]
    assert plan.availability_context.get("availability_status") == exp["availability_status"]
    assert plan.missing_information.get("missing_fields") == [] or not plan.missing_information.get("missing_fields")


# ── Scenario 02: Complete enquiry, unavailable date ───────────────────────────


def test_scenario_02_complete_enquiry_unavailable_date():
    exp = _expected("scenario_02")

    unavailable = AvailabilityDecision(
        availability_status=STATUS_UNAVAILABLE,
        selected_candidate_date=None,
        available_options=[],
        unavailable_options=["2026-07-15"],
        availability_reason="No rooms available.",
    )

    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        date_resolution_status=_resolved_date_status("2026-07-15"),
        candidate_dates=[],
        customer_type="social",
        availability_decision=unavailable,
        missing_information_result=_no_missing(),
        response_priority_result=ResponsePriorityResult(
            response_priority=PRIORITY_NORMAL,
            priority_reason="15–90 days away.",
        ),
    )

    assert plan.response_goal == exp["response_goal"]
    assert plan.can_generate_draft is exp["can_generate_draft"]
    assert plan.availability_context.get("availability_status") == exp["availability_status"]


# ── Scenario 03: Ambiguous numeric date ───────────────────────────────────────


def test_scenario_03_ambiguous_numeric_date():
    exp = _expected("scenario_03")

    ambiguous_status = DateResolutionStatus(
        status=STATUS_AMBIGUOUS,
        original_text="07/03",
        resolution_method="numeric_ambiguous",
        resolved_date=None,
        alternative_date=None,
        clarification_required=True,
        clarification_reason="numeric_dd_mm_or_mm_dd",
        clarification_question="Did you mean 07 March or 03 July?",
        candidate_dates=[],
    )
    pending_avail = AvailabilityDecision(
        availability_status=STATUS_PENDING_DATE_CONFIRMATION,
        availability_reason="Date ambiguous; cannot check availability.",
    )

    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        date_resolution_status=ambiguous_status,
        candidate_dates=[],
        customer_type="corporate",
        availability_decision=pending_avail,
        missing_information_result=_no_missing(),
        response_priority_result=ResponsePriorityResult(
            response_priority=PRIORITY_NORMAL,
            priority_reason="No resolved date.",
        ),
    )

    assert plan.response_goal == exp["response_goal"]
    assert plan.can_generate_draft is exp["can_generate_draft"]
    assert plan.availability_context.get("availability_status") == exp["availability_status"]
    assert plan.date_context.get("status") == STATUS_AMBIGUOUS


# ── Scenario 04: Missing guest count only ────────────────────────────────────


def test_scenario_04_missing_guest_count_only():
    exp = _expected("scenario_04")

    readiness = ReadinessEvaluation(
        status=STATUS_NEEDS_CLARIFICATION,
        date_understood=True,
        guest_count_present=False,
        occasion_understood=True,
        meal_period_present=True,
        audience_identified=True,
        date_clarification_required=False,
        availability_check_possible=False,
        missing_for_availability=["guest_count"],
        notes="Guest count is required for availability check.",
    )
    missing = MissingInformationResult(
        missing_fields=["guest_count"],
        critical_missing_fields=["guest_count"],
        clarification_questions=["How many guests will be attending?"],
        can_ask_by_email=True,
        should_send_webform=False,
        missing_info_reason="1 critical field missing.",
    )

    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=readiness,
        date_resolution_status=_resolved_date_status(),
        candidate_dates=[],
        customer_type="social",
        missing_information_result=missing,
        response_priority_result=ResponsePriorityResult(
            response_priority=PRIORITY_NORMAL,
            priority_reason="15–90 days away.",
        ),
    )

    assert plan.response_goal == exp["response_goal"]
    assert plan.can_generate_draft is exp["can_generate_draft"]
    assert plan.missing_information.get("missing_fields") or plan.missing_information.get("critical_missing_fields")


# ── Scenario 05: Missing date only ───────────────────────────────────────────


def test_scenario_05_missing_date_only():
    exp = _expected("scenario_05")

    readiness = ReadinessEvaluation(
        status=STATUS_NEEDS_CLARIFICATION,
        date_understood=False,
        guest_count_present=True,
        occasion_understood=True,
        meal_period_present=True,
        audience_identified=True,
        date_clarification_required=False,
        availability_check_possible=False,
        missing_for_availability=["date"],
        notes="Event date is required.",
    )
    unknown_date = DateResolutionStatus(
        status=STATUS_UNKNOWN,
        original_text=None,
        resolution_method="no_date_extracted",
        resolved_date=None,
        alternative_date=None,
        clarification_required=False,
        clarification_reason=None,
        clarification_question="When would you like to hold your event?",
        candidate_dates=[],
    )
    missing = MissingInformationResult(
        missing_fields=["date"],
        critical_missing_fields=["date"],
        clarification_questions=["When would you like to hold your event?"],
        can_ask_by_email=True,
        should_send_webform=False,
        missing_info_reason="1 critical field missing.",
    )

    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=readiness,
        date_resolution_status=unknown_date,
        candidate_dates=[],
        customer_type="corporate",
        missing_information_result=missing,
        response_priority_result=ResponsePriorityResult(
            response_priority=PRIORITY_NORMAL,
            priority_reason="No resolved date.",
        ),
    )

    assert plan.response_goal == exp["response_goal"]
    assert plan.can_generate_draft is exp["can_generate_draft"]


# ── Scenario 06: Missing date, guest count and occasion (3+ fields) ───────────


def test_scenario_06_multiple_critical_fields_webform():
    exp = _expected("scenario_06")

    readiness = ReadinessEvaluation(
        status=STATUS_NEEDS_CLARIFICATION,
        date_understood=False,
        guest_count_present=False,
        occasion_understood=False,
        meal_period_present=True,
        audience_identified=False,
        date_clarification_required=False,
        availability_check_possible=False,
        missing_for_availability=["date", "guest_count", "occasion"],
        notes="Multiple critical fields missing.",
    )
    missing = MissingInformationResult(
        missing_fields=["date", "guest_count", "occasion"],
        critical_missing_fields=["date", "guest_count", "occasion"],
        clarification_questions=[
            "When would you like to hold your event?",
            "How many guests will be attending?",
            "What is the occasion?",
        ],
        can_ask_by_email=False,
        should_send_webform=True,
        missing_info_reason="3 or more critical fields missing.",
    )

    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=readiness,
        candidate_dates=[],
        customer_type="unknown",
        missing_information_result=missing,
        response_priority_result=ResponsePriorityResult(
            response_priority=PRIORITY_NORMAL,
            priority_reason="No resolved date.",
        ),
    )

    assert plan.response_goal == exp["response_goal"]
    assert plan.can_generate_draft is exp["can_generate_draft"]
    assert plan.missing_information.get("should_send_webform") is True


# ── Scenarios 07–10: Customer type persona routing ────────────────────────────


@pytest.mark.parametrize("customer_type,expected_tone", [
    ("social",    ["warm", "friendly", "celebratory"]),
    ("corporate", ["concise", "professional", "efficient"]),
    ("agency",    ["detailed", "operationally precise", "low-friction"]),
    ("unknown",   ["professional"]),
])
def test_scenarios_07_10_customer_type_tone_routing(customer_type: str, expected_tone: list[str]):
    persona_ctx = PersonaRoutingContextBuilder.build(
        final_customer_type=customer_type,
        final_customer_type_confidence=0.9,
        customer_type_resolution_reason="test",
        assigned_personas=[],
    )
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        date_resolution_status=_resolved_date_status(),
        candidate_dates=[],
        customer_type=customer_type,
        availability_decision=_available_decision(),
        missing_information_result=_no_missing(),
        persona_routing_context=persona_ctx,
        response_priority_result=ResponsePriorityResult(
            response_priority=PRIORITY_NORMAL,
            priority_reason="15–90 days away.",
        ),
    )

    assert plan.response_goal == GOAL_CONFIRM_AVAILABLE
    assert plan.can_generate_draft is True
    assert plan.customer_type_context.get("final_customer_type") == customer_type
    assert plan.persona_context.get("tone_guidance") == expected_tone


# ── Scenario 11: Webform recommended via missing_information engine ────────────


def test_scenario_11_webform_recommended():
    exp = _expected("scenario_11")

    readiness = ReadinessEvaluation(
        status=STATUS_NEEDS_CLARIFICATION,
        date_understood=False,
        guest_count_present=False,
        occasion_understood=False,
        meal_period_present=False,
        audience_identified=False,
        date_clarification_required=False,
        availability_check_possible=False,
        missing_for_availability=["date", "guest_count", "occasion", "meal_period"],
        notes="Structural gaps; webform needed.",
    )
    missing = MissingInformationResult(
        missing_fields=["date", "guest_count", "occasion", "meal_period"],
        critical_missing_fields=["date", "guest_count", "occasion", "meal_period"],
        clarification_questions=[],
        can_ask_by_email=False,
        should_send_webform=True,
        missing_info_reason="4 critical fields missing — direct to webform.",
    )

    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=readiness,
        candidate_dates=[],
        customer_type="unknown",
        missing_information_result=missing,
        response_priority_result=ResponsePriorityResult(
            response_priority=PRIORITY_NORMAL,
            priority_reason="No resolved date.",
        ),
    )

    assert plan.response_goal == exp["response_goal"]
    assert plan.can_generate_draft is exp["can_generate_draft"]
    assert plan.missing_information.get("should_send_webform") is True


# ── Scenario 12: Direct email clarification ───────────────────────────────────


def test_scenario_12_direct_email_clarification():
    exp = _expected("scenario_12")

    readiness = ReadinessEvaluation(
        status=STATUS_NEEDS_CLARIFICATION,
        date_understood=True,
        guest_count_present=False,
        occasion_understood=True,
        meal_period_present=True,
        audience_identified=True,
        date_clarification_required=False,
        availability_check_possible=False,
        missing_for_availability=["guest_count"],
        notes="Guest count absent.",
    )
    missing = MissingInformationResult(
        missing_fields=["guest_count"],
        critical_missing_fields=["guest_count"],
        clarification_questions=["How many guests will be attending?"],
        can_ask_by_email=True,
        should_send_webform=False,
        missing_info_reason="1 critical field; email is sufficient.",
    )

    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=readiness,
        date_resolution_status=_resolved_date_status(),
        candidate_dates=[],
        customer_type="corporate",
        missing_information_result=missing,
        response_priority_result=ResponsePriorityResult(
            response_priority=PRIORITY_NORMAL,
            priority_reason="15–90 days away.",
        ),
    )

    assert plan.response_goal == exp["response_goal"]
    assert plan.can_generate_draft is exp["can_generate_draft"]
    assert plan.missing_information.get("should_send_webform") is False or not plan.missing_information.get("should_send_webform")


# ── Scenario 13: Escalation required ─────────────────────────────────────────


def test_scenario_13_escalation_required():
    exp = _expected("scenario_13")

    # INSUFFICIENT_INFORMATION with occasion understood — Rule 1 does not fire,
    # Rule 2 fires → ESCALATE_TO_HUMAN
    readiness = ReadinessEvaluation(
        status=STATUS_INSUFFICIENT_INFORMATION,
        date_understood=False,
        guest_count_present=False,
        occasion_understood=True,
        meal_period_present=False,
        audience_identified=False,
        date_clarification_required=False,
        availability_check_possible=False,
        missing_for_availability=["date", "guest_count"],
        notes="Insufficient information for automated handling.",
    )

    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=readiness,
        candidate_dates=[],
        customer_type="unknown",
        response_priority_result=ResponsePriorityResult(
            response_priority=PRIORITY_NORMAL,
            priority_reason="No resolved date.",
        ),
    )

    assert plan.response_goal == exp["response_goal"]
    assert plan.can_generate_draft is exp["can_generate_draft"]


# ── Scenario 14: Urgent enquiry ───────────────────────────────────────────────


def test_scenario_14_urgent_enquiry():
    exp = _expected("scenario_14")

    # Anchor: 2026-06-05; event tomorrow: 2026-06-06 → 1 day away → URGENT
    urgent_priority = ResponsePriorityEngine_decide_with_anchor(
        resolved_event_date="2026-06-06",
        anchor=_ANCHOR_DATE,
    )

    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        date_resolution_status=_resolved_date_status("2026-06-06"),
        candidate_dates=[],
        customer_type="corporate",
        availability_decision=_available_decision("2026-06-06"),
        missing_information_result=_no_missing(),
        response_priority_result=urgent_priority,
    )

    assert plan.response_goal == exp["response_goal"]
    assert plan.can_generate_draft is exp["can_generate_draft"]
    assert plan.response_priority == exp["response_priority"]


# ── Scenario 15: Low-priority future enquiry ─────────────────────────────────


def test_scenario_15_low_priority_future_enquiry():
    exp = _expected("scenario_15")

    # Anchor: 2026-06-05; event 2026-09-10 → 97 days away → LOW
    low_priority = ResponsePriorityEngine_decide_with_anchor(
        resolved_event_date="2026-09-10",
        anchor=_ANCHOR_DATE,
    )

    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        date_resolution_status=_resolved_date_status("2026-09-10"),
        candidate_dates=[],
        customer_type="social",
        availability_decision=_available_decision("2026-09-10"),
        missing_information_result=_no_missing(),
        response_priority_result=low_priority,
    )

    assert plan.response_goal == exp["response_goal"]
    assert plan.can_generate_draft is exp["can_generate_draft"]
    assert plan.response_priority == exp["response_priority"]


# ── Priority helper ───────────────────────────────────────────────────────────


def ResponsePriorityEngine_decide_with_anchor(
    resolved_event_date: str,
    anchor: date,
) -> ResponsePriorityResult:
    """Thin wrapper around ResponsePriorityEngine.decide() with a fixed anchor date."""
    from app.modules.enquiries.response_priority_engine import ResponsePriorityEngine
    return ResponsePriorityEngine.decide(
        resolved_event_date=resolved_event_date,
        anchor_date=anchor,
    )


# ── Cross-scenario fixture integrity ──────────────────────────────────────────


def test_all_15_scenarios_present_in_fixture():
    """Guard: fixture file must define exactly 15 scenarios."""
    assert len(_CASES) == 15


def test_fixture_scenario_ids_are_sequential():
    """Guard: scenario IDs follow scenario_01 .. scenario_15 pattern."""
    for i in range(1, 16):
        assert f"scenario_{i:02d}" in _CASES, f"Missing scenario_{i:02d} in fixture"
