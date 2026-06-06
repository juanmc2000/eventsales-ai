"""Tests for ResponsePreparationBuilder (ORCH-006)."""

from __future__ import annotations

import pytest

from app.modules.enquiries.availability_decision_service import (
    AvailabilityDecision,
    STATUS_AVAILABLE,
    STATUS_NOT_CHECKED,
    STATUS_UNAVAILABLE,
    STATUS_PENDING_DATE_CONFIRMATION,
    STATUS_UNAVAILABLE,
)
from app.modules.enquiries.date_resolution_status import (
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_UNKNOWN,
    DateResolutionStatus,
)
from app.modules.enquiries.missing_information_engine import MissingInformationResult
from app.modules.enquiries.persona_routing_context import PersonaRoutingContext
from app.modules.enquiries.readiness_evaluator import (
    STATUS_INSUFFICIENT_INFORMATION,
    STATUS_NEEDS_CLARIFICATION,
    STATUS_READY_FOR_AVAILABILITY,
    STATUS_WEBFORM_REQUIRED,
    ReadinessEvaluation,
)
from app.modules.enquiries.response_goal_engine import (
    GOAL_ACKNOWLEDGE_AND_CHECK_AVAILABILITY,
    GOAL_CONFIRM_AVAILABLE,
    GOAL_ESCALATE_TO_HUMAN,
    GOAL_REQUEST_DATE_CONFIRMATION,
    GOAL_REQUEST_MISSING_INFORMATION,
    GOAL_REQUEST_WEBFORM,
    GOAL_UNABLE_TO_PROCESS,
)
from app.modules.enquiries.response_preparation_builder import (
    ResponsePlan,
    ResponsePreparationBuilder,
)
from app.modules.enquiries.response_priority_engine import (
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
    PRIORITY_URGENT,
    ResponsePriorityResult,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _ready_readiness() -> ReadinessEvaluation:
    return ReadinessEvaluation(
        status=STATUS_READY_FOR_AVAILABILITY,
        date_understood=True,
        guest_count_present=True,
        occasion_understood=True,
        meal_period_present=True,
        audience_identified=True,
        availability_check_possible=True,
        date_clarification_required=False,
        missing_for_availability=[],
        notes="",
    )


def _needs_clarification_readiness(missing: list[str] | None = None) -> ReadinessEvaluation:
    return ReadinessEvaluation(
        status=STATUS_NEEDS_CLARIFICATION,
        date_understood=True,
        guest_count_present=False,
        occasion_understood=True,
        meal_period_present=True,
        audience_identified=True,
        availability_check_possible=False,
        date_clarification_required=False,
        missing_for_availability=missing or ["guest_count"],
        notes="Guest count missing.",
    )


def _webform_readiness() -> ReadinessEvaluation:
    return ReadinessEvaluation(
        status=STATUS_WEBFORM_REQUIRED,
        date_understood=False,
        guest_count_present=False,
        occasion_understood=False,
        meal_period_present=False,
        audience_identified=False,
        availability_check_possible=False,
        date_clarification_required=True,
        missing_for_availability=["date", "guest_count", "occasion"],
        notes="Too many missing fields.",
    )


def _insufficient_readiness() -> ReadinessEvaluation:
    return ReadinessEvaluation(
        status=STATUS_INSUFFICIENT_INFORMATION,
        date_understood=False,
        guest_count_present=False,
        occasion_understood=False,
        meal_period_present=False,
        audience_identified=False,
        availability_check_possible=False,
        date_clarification_required=False,
        missing_for_availability=["date", "guest_count"],
        notes="Insufficient information.",
    )


def _resolved_date_status() -> DateResolutionStatus:
    return DateResolutionStatus(
        status=STATUS_RESOLVED,
        original_text="next Saturday",
        resolution_method="weekday_relative",
        resolved_date="2026-06-13",
        alternative_date=None,
        clarification_required=False,
        clarification_reason=None,
        clarification_question=None,
        candidate_dates=["2026-06-13"],
    )


def _ambiguous_date_status() -> DateResolutionStatus:
    return DateResolutionStatus(
        status=STATUS_AMBIGUOUS,
        original_text="06/07",
        resolution_method="numeric_date_disambiguation",
        resolved_date=None,
        alternative_date=None,
        clarification_required=True,
        clarification_reason="numeric_ambiguity",
        clarification_question="Did you mean 6 July or 7 June?",
        candidate_dates=[],
    )


def _available_decision() -> AvailabilityDecision:
    return AvailabilityDecision(
        availability_status=STATUS_AVAILABLE,
        selected_candidate_date="2026-06-13",
        available_options=["2026-06-13"],
        unavailable_options=[],
        availability_reason="Date confirmed available.",
    )


def _social_persona_ctx() -> PersonaRoutingContext:
    return PersonaRoutingContext(
        customer_type="social",
        tone_guidance=["warm", "friendly", "celebratory"],
        selected_persona_id="persona-001",
        selected_persona_name="Bella",
        routing_reason="Social persona selected.",
    )


def _complete_missing_info() -> MissingInformationResult:
    return MissingInformationResult(
        missing_fields=[],
        critical_missing_fields=[],
        clarification_questions=[],
        can_ask_by_email=False,
        should_send_webform=False,
        missing_info_reason="All critical information is present.",
    )


def _urgent_priority() -> ResponsePriorityResult:
    return ResponsePriorityResult(
        response_priority=PRIORITY_URGENT,
        priority_reason="Event is today.",
    )


# ── ResponsePlan dataclass ────────────────────────────────────────────────────


def test_response_plan_to_dict_has_all_keys():
    plan = ResponsePlan(
        response_goal=GOAL_CONFIRM_AVAILABLE,
        response_priority=PRIORITY_NORMAL,
        can_generate_draft=True,
        goal_reason="All good.",
    )
    d = plan.to_dict()
    assert set(d.keys()) == {
        "response_goal", "response_priority", "can_generate_draft", "goal_reason",
        "blocking_fields", "known_facts", "missing_information", "clarification_questions",
        "date_context", "availability_context", "customer_type_context", "persona_context",
        "draft_instructions",
    }


# ── Complete enquiry → READY ──────────────────────────────────────────────────


def test_complete_enquiry_is_ready():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        date_resolution_status=_resolved_date_status(),
        candidate_dates=[{"candidate_date": "2026-06-13", "availability_status": "available"}],
        customer_type="corporate",
        availability_decision=_available_decision(),
        missing_information_result=_complete_missing_info(),
        persona_routing_context=_social_persona_ctx(),
        response_priority_result=_urgent_priority(),
    )
    assert plan.response_goal == GOAL_CONFIRM_AVAILABLE
    assert plan.can_generate_draft is True


def test_complete_enquiry_includes_priority():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        response_priority_result=_urgent_priority(),
    )
    assert plan.response_priority == PRIORITY_URGENT


def test_complete_enquiry_no_blocking_fields():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        date_resolution_status=_resolved_date_status(),
        missing_information_result=_complete_missing_info(),
    )
    assert plan.blocking_fields == []


# ── Ambiguous date → REQUEST_DATE_CONFIRMATION ────────────────────────────────


def test_ambiguous_date_requests_confirmation():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        date_resolution_status=_ambiguous_date_status(),
    )
    assert plan.response_goal == GOAL_REQUEST_DATE_CONFIRMATION
    assert plan.can_generate_draft is True


def test_ambiguous_date_includes_clarification_question():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        date_resolution_status=_ambiguous_date_status(),
    )
    assert len(plan.clarification_questions) > 0
    assert "6 July" in plan.clarification_questions[0] or "7 June" in plan.clarification_questions[0]


def test_ambiguous_date_in_date_context():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        date_resolution_status=_ambiguous_date_status(),
    )
    assert plan.date_context["status"] == STATUS_AMBIGUOUS
    assert plan.date_context["clarification_required"] is True


# ── Missing guest count → REQUEST_MISSING_INFORMATION ────────────────────────


def test_missing_guest_count_requests_info():
    missing = MissingInformationResult(
        missing_fields=["guest_count"],
        critical_missing_fields=["guest_count"],
        clarification_questions=["How many guests will be joining you?"],
        can_ask_by_email=True,
        should_send_webform=False,
        missing_info_reason="1 critical field missing.",
    )
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_needs_clarification_readiness(),
        date_resolution_status=_resolved_date_status(),
        missing_information_result=missing,
    )
    assert plan.response_goal == GOAL_REQUEST_MISSING_INFORMATION
    assert "guest_count" in plan.blocking_fields


def test_missing_guest_count_clarification_question_included():
    missing = MissingInformationResult(
        missing_fields=["guest_count"],
        critical_missing_fields=["guest_count"],
        clarification_questions=["How many guests?"],
        can_ask_by_email=True,
        should_send_webform=False,
        missing_info_reason="1 critical field missing.",
    )
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_needs_clarification_readiness(),
        date_resolution_status=_resolved_date_status(),
        missing_information_result=missing,
    )
    assert "How many guests?" in plan.clarification_questions


# ── Webform required ──────────────────────────────────────────────────────────


def test_webform_readiness_produces_request_webform():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_webform_readiness(),
    )
    assert plan.response_goal == GOAL_REQUEST_WEBFORM
    assert plan.can_generate_draft is True


def test_missing_info_webform_flag_produces_request_webform():
    missing = MissingInformationResult(
        missing_fields=["date", "guest_count", "occasion"],
        critical_missing_fields=["date", "guest_count", "occasion"],
        clarification_questions=[],
        can_ask_by_email=False,
        should_send_webform=True,
        missing_info_reason="3+ critical fields missing.",
    )
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_needs_clarification_readiness(),
        missing_information_result=missing,
    )
    assert plan.response_goal == GOAL_REQUEST_WEBFORM


# ── Insufficient info → ESCALATE_TO_HUMAN ────────────────────────────────────


def test_insufficient_info_unable_to_process():
    """Completely empty enquiry (no date, occasion, or guest count) → UNABLE_TO_PROCESS."""
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_insufficient_readiness(),
    )
    assert plan.response_goal == GOAL_UNABLE_TO_PROCESS
    assert plan.can_generate_draft is False


def test_insufficient_info_with_occasion_escalates_to_human():
    """Insufficient readiness but occasion understood → ESCALATE_TO_HUMAN (Rule 2)."""
    readiness = ReadinessEvaluation(
        status=STATUS_INSUFFICIENT_INFORMATION,
        date_understood=False,
        guest_count_present=False,
        occasion_understood=True,       # some context exists
        meal_period_present=False,
        audience_identified=False,
        availability_check_possible=False,
        date_clarification_required=False,
        missing_for_availability=["date", "guest_count"],
        notes="Insufficient information.",
    )
    plan = ResponsePreparationBuilder.build(readiness_evaluation=readiness)
    assert plan.response_goal == GOAL_ESCALATE_TO_HUMAN
    assert plan.can_generate_draft is False


# ── Persona context ───────────────────────────────────────────────────────────


def test_persona_context_included():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        persona_routing_context=_social_persona_ctx(),
    )
    assert plan.persona_context["selected_persona_name"] == "Bella"
    assert "warm" in plan.persona_context["tone_guidance"]


def test_no_persona_context_defaults_to_professional():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        persona_routing_context=None,
    )
    assert plan.persona_context["tone_guidance"] == ["professional"]


def test_draft_instructions_tone_from_persona():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        persona_routing_context=_social_persona_ctx(),
    )
    assert "warm" in plan.draft_instructions["tone_guidance"]


# ── Availability context ──────────────────────────────────────────────────────


def test_availability_context_included():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        availability_decision=_available_decision(),
    )
    assert plan.availability_context["availability_status"] == STATUS_AVAILABLE
    assert plan.availability_context["selected_candidate_date"] == "2026-06-13"


def test_no_availability_defaults_to_not_checked():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        availability_decision=None,
    )
    assert plan.availability_context["availability_status"] == STATUS_NOT_CHECKED


def test_draft_instructions_include_availability_flag():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        availability_decision=_available_decision(),
    )
    assert plan.draft_instructions["include_availability"] is True


def test_draft_instructions_no_availability_flag():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        availability_decision=None,
    )
    assert plan.draft_instructions["include_availability"] is False


# ── Customer type context ─────────────────────────────────────────────────────


def test_customer_type_context_included():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        customer_type="agency",
        customer_type_confidence=0.85,
        customer_type_reason="agency_keyword_domain",
    )
    assert plan.customer_type_context["final_customer_type"] == "agency"
    assert plan.customer_type_context["confidence"] == 0.85
    assert plan.customer_type_context["resolution_reason"] == "agency_keyword_domain"


# ── Known facts ───────────────────────────────────────────────────────────────


def test_known_facts_assembled():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        date_resolution_status=_resolved_date_status(),
    )
    assert plan.known_facts["date_understood"] is True
    assert plan.known_facts["guest_count_present"] is True
    assert plan.known_facts["readiness_status"] == STATUS_READY_FOR_AVAILABILITY


# ── Priority computed on the fly ──────────────────────────────────────────────


def test_priority_computed_from_candidate_dates():
    """When no priority result is provided the builder derives one from candidates."""
    from datetime import date, timedelta

    future_date = (date.today() + timedelta(days=5)).isoformat()
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        date_resolution_status=DateResolutionStatus(
            status=STATUS_RESOLVED,
            original_text="next Friday",
            resolution_method="weekday_relative",
            resolved_date=future_date,
            alternative_date=None,
            clarification_required=False,
            clarification_reason=None,
            clarification_question=None,
            candidate_dates=[future_date],
        ),
        response_priority_result=None,
    )
    assert plan.response_priority == PRIORITY_HIGH


# ── No date status — safe default ─────────────────────────────────────────────


def test_no_date_status_safe_defaults():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        date_resolution_status=None,
    )
    assert plan.date_context["status"] == "unknown"
    assert plan.date_context["clarification_required"] is True


# ── Missing information section ───────────────────────────────────────────────


def test_no_missing_info_result_safe_defaults():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        missing_information_result=None,
    )
    assert plan.missing_information["missing_fields"] == []
    assert plan.missing_information["should_send_webform"] is False


# ── Availability contract in availability_context (RESP-004) ──────────────────


def test_availability_contract_not_checked_when_no_decision():
    """When no AvailabilityDecision is provided, contract is NOT_CHECKED."""
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        availability_decision=None,
    )
    assert plan.availability_context.get("availability_contract") == "NOT_CHECKED"


def test_availability_contract_confirmed_available():
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        availability_decision=_available_decision(),
    )
    assert plan.availability_context.get("availability_contract") == "CONFIRMED_AVAILABLE"


def test_availability_contract_confirmed_unavailable():
    unavail = AvailabilityDecision(
        availability_status=STATUS_UNAVAILABLE,
        selected_candidate_date=None,
        available_options=[],
        unavailable_options=["2026-06-13"],
        availability_reason="Fully booked.",
    )
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        availability_decision=unavail,
    )
    assert plan.availability_context.get("availability_contract") == "CONFIRMED_UNAVAILABLE"


def test_availability_contract_pending_date_confirmation():
    from app.modules.enquiries.availability_decision_service import STATUS_PENDING_DATE_CONFIRMATION
    pending = AvailabilityDecision(
        availability_status=STATUS_PENDING_DATE_CONFIRMATION,
        selected_candidate_date=None,
        available_options=[],
        unavailable_options=[],
        availability_reason="Date is ambiguous.",
    )
    plan = ResponsePreparationBuilder.build(
        readiness_evaluation=_ready_readiness(),
        availability_decision=pending,
    )
    assert plan.availability_context.get("availability_contract") == "PENDING_DATE_CONFIRMATION"


def test_availability_contract_key_always_present():
    """availability_contract must be present regardless of input."""
    for decision in (None, _available_decision()):
        plan = ResponsePreparationBuilder.build(
            readiness_evaluation=_ready_readiness(),
            availability_decision=decision,
        )
        assert "availability_contract" in plan.availability_context, (
            f"availability_contract key missing when decision={decision!r}"
        )

