"""Tests for ResponsePreparationService (RESP-001)."""

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
    EnquiryReadinessEvaluator,
    ReadinessEvaluation,
)
from app.modules.enquiries.response_preparation_service import (
    ALL_RESPONSE_GOALS,
    RESPONSE_GOAL_ESCALATE_TO_HUMAN,
    RESPONSE_GOAL_READY_FOR_RESPONSE,
    RESPONSE_GOAL_REQUEST_DATE_CONFIRMATION,
    RESPONSE_GOAL_REQUEST_MISSING_INFORMATION,
    RESPONSE_GOAL_REQUEST_WEBFORM,
    ResponseContext,
    ResponsePreparationService,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


def make_evaluation(
    status: str,
    date_understood: bool = True,
    guest_count_present: bool = True,
    occasion_understood: bool = True,
    meal_period_present: bool = True,
    audience_identified: bool = True,
    date_clarification_required: bool = False,
    availability_check_possible: bool = True,
    missing_for_availability: list | None = None,
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


READY_EVAL = make_evaluation(STATUS_READY_FOR_AVAILABILITY)
NEEDS_CLARIFICATION_DATE_EVAL = make_evaluation(
    STATUS_NEEDS_CLARIFICATION,
    date_understood=False,
    date_clarification_required=True,
    availability_check_possible=False,
    missing_for_availability=["date"],
    notes="Date requires clarification.",
)
NEEDS_CLARIFICATION_COUNT_EVAL = make_evaluation(
    STATUS_NEEDS_CLARIFICATION,
    guest_count_present=False,
    availability_check_possible=False,
    missing_for_availability=["guest_count"],
    notes="Guest count missing.",
)
WEBFORM_EVAL = make_evaluation(
    STATUS_WEBFORM_REQUIRED,
    date_understood=False,
    guest_count_present=False,
    availability_check_possible=False,
    missing_for_availability=["date", "guest_count"],
    notes="Webform required.",
)
INSUFFICIENT_EVAL = make_evaluation(
    STATUS_INSUFFICIENT_INFORMATION,
    date_understood=False,
    guest_count_present=False,
    occasion_understood=False,
    meal_period_present=False,
    audience_identified=False,
    availability_check_possible=False,
    missing_for_availability=["extraction", "date", "guest_count"],
    notes="No critical information extracted.",
)

RESOLVED_DATE = DateResolutionStatus.resolved("next Friday", "2026-06-07", "weekday_relative")
AMBIGUOUS_DATE = DateResolutionStatus(
    status=STATUS_AMBIGUOUS,
    original_text="7/6",
    resolution_method="both_interpretations_equally_plausible",
    resolved_date="2026-06-07",
    alternative_date="2026-07-06",
    clarification_required=True,
    clarification_reason="both_interpretations_equally_plausible",
    clarification_question="Could you confirm whether you meant 7 June or 6 July?",
    candidate_dates=["2026-06-07", "2026-07-06"],
)
CONFIRMED_DATE = DateResolutionStatus(
    status=STATUS_RESOLVED_WITH_CONFIRMATION,
    original_text="1/9",
    resolution_method="british_default",
    resolved_date="2026-09-01",
    alternative_date="2026-01-09",
    clarification_required=True,
    clarification_reason="british_default",
    clarification_question="Could you confirm you meant 1 September? I've provisionally checked availability for 1 September 2026.",
    candidate_dates=["2026-09-01", "2026-01-09"],
)
UNKNOWN_DATE = DateResolutionStatus.unknown()


# ── Constants ──────────────────────────────────────────────────────────────────


class TestConstants:
    def test_all_goals_defined(self):
        assert ALL_RESPONSE_GOALS == {
            "READY_FOR_RESPONSE",
            "REQUEST_MISSING_INFORMATION",
            "REQUEST_DATE_CONFIRMATION",
            "REQUEST_WEBFORM",
            "ESCALATE_TO_HUMAN",
        }


# ── Rule 1: Escalate to human ─────────────────────────────────────────────────


class TestRule1EscalateToHuman:
    def test_insufficient_with_no_date_escalates(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=INSUFFICIENT_EVAL,
            date_resolution_status=UNKNOWN_DATE,
            audience_type="unknown",
        )
        assert ctx.response_goal == RESPONSE_GOAL_ESCALATE_TO_HUMAN

    def test_insufficient_with_no_date_and_no_domain_info(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=INSUFFICIENT_EVAL,
            date_resolution_status=None,
            audience_type="unknown",
        )
        assert ctx.response_goal == RESPONSE_GOAL_ESCALATE_TO_HUMAN


# ── Rule 2: Ambiguous date ────────────────────────────────────────────────────


class TestRule2AmbiguousDate:
    def test_ambiguous_date_triggers_date_confirmation(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=READY_EVAL,
            date_resolution_status=AMBIGUOUS_DATE,
            audience_type="social",
        )
        assert ctx.response_goal == RESPONSE_GOAL_REQUEST_DATE_CONFIRMATION

    def test_ambiguous_date_includes_clarification_question(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=READY_EVAL,
            date_resolution_status=AMBIGUOUS_DATE,
            audience_type="social",
        )
        assert len(ctx.clarification_questions) > 0
        assert "7 June" in ctx.clarification_questions[0] or "6 July" in ctx.clarification_questions[0]

    def test_ambiguous_date_blocks_ready_goal(self):
        # Even if readiness says ready, ambiguous date blocks the response goal
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=READY_EVAL,
            date_resolution_status=AMBIGUOUS_DATE,
            audience_type="corporate",
        )
        assert ctx.response_goal != RESPONSE_GOAL_READY_FOR_RESPONSE


# ── Rule 3: Resolved with confirmation ───────────────────────────────────────


class TestRule3ResolvedWithConfirmation:
    def test_confirmed_date_triggers_date_confirmation(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=READY_EVAL,
            date_resolution_status=CONFIRMED_DATE,
            audience_type="corporate",
        )
        assert ctx.response_goal == RESPONSE_GOAL_REQUEST_DATE_CONFIRMATION

    def test_confirmed_date_includes_clarification_question(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=READY_EVAL,
            date_resolution_status=CONFIRMED_DATE,
            audience_type="corporate",
        )
        assert len(ctx.clarification_questions) > 0
        assert "September" in ctx.clarification_questions[0]


# ── Rule 4: Ready for response ────────────────────────────────────────────────


class TestRule4ReadyForResponse:
    def test_ready_eval_with_resolved_date_returns_ready(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=READY_EVAL,
            date_resolution_status=RESOLVED_DATE,
            audience_type="social",
        )
        assert ctx.response_goal == RESPONSE_GOAL_READY_FOR_RESPONSE

    def test_ready_eval_no_clarification_questions(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=READY_EVAL,
            date_resolution_status=RESOLVED_DATE,
            audience_type="corporate",
        )
        assert ctx.clarification_questions == []

    def test_ready_can_draft_response(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=READY_EVAL,
            date_resolution_status=RESOLVED_DATE,
            audience_type="social",
        )
        assert ctx.can_draft_response is True

    def test_ready_with_no_date_status_still_proceeds(self):
        # When date_resolution_status is None, no ambiguity check applies
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=READY_EVAL,
            date_resolution_status=None,
            audience_type="social",
        )
        assert ctx.response_goal == RESPONSE_GOAL_READY_FOR_RESPONSE


# ── Rule 5: Request missing information ───────────────────────────────────────


class TestRule5RequestMissingInformation:
    def test_date_clarification_needed_returns_missing_info(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=NEEDS_CLARIFICATION_DATE_EVAL,
            date_resolution_status=RESOLVED_DATE,
            audience_type="social",
        )
        assert ctx.response_goal == RESPONSE_GOAL_REQUEST_MISSING_INFORMATION

    def test_guest_count_missing_returns_missing_info(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=NEEDS_CLARIFICATION_COUNT_EVAL,
            date_resolution_status=RESOLVED_DATE,
            audience_type="social",
        )
        assert ctx.response_goal == RESPONSE_GOAL_REQUEST_MISSING_INFORMATION

    def test_guest_count_missing_includes_question(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=NEEDS_CLARIFICATION_COUNT_EVAL,
            date_resolution_status=RESOLVED_DATE,
            audience_type="social",
        )
        assert any("guest" in q.lower() or "many" in q.lower() for q in ctx.clarification_questions)

    def test_can_draft_when_missing_info(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=NEEDS_CLARIFICATION_COUNT_EVAL,
            date_resolution_status=RESOLVED_DATE,
            audience_type="social",
        )
        assert ctx.can_draft_response is True


# ── Rule 6: Request webform ───────────────────────────────────────────────────


class TestRule6RequestWebform:
    def test_webform_required_returns_webform_goal(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=WEBFORM_EVAL,
            date_resolution_status=RESOLVED_DATE,
            audience_type="unknown",
        )
        assert ctx.response_goal == RESPONSE_GOAL_REQUEST_WEBFORM

    def test_webform_cannot_draft_response(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=WEBFORM_EVAL,
            date_resolution_status=RESOLVED_DATE,
            audience_type="unknown",
        )
        assert ctx.can_draft_response is False


# ── Response context ──────────────────────────────────────────────────────────


class TestResponseContext:
    def test_context_contains_audience_type(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=READY_EVAL,
            date_resolution_status=RESOLVED_DATE,
            audience_type="corporate",
        )
        assert ctx.audience_type == "corporate"
        assert ctx.response_context["audience_type"] == "corporate"

    def test_context_contains_readiness_status(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=READY_EVAL,
            date_resolution_status=RESOLVED_DATE,
            audience_type="social",
        )
        assert ctx.response_context["readiness_status"] == STATUS_READY_FOR_AVAILABILITY

    def test_context_contains_date_info_when_provided(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=READY_EVAL,
            date_resolution_status=RESOLVED_DATE,
            audience_type="social",
        )
        assert ctx.response_context["date_resolved"] == "2026-06-07"
        assert ctx.response_context["date_status"] == STATUS_RESOLVED

    def test_context_date_unknown_when_no_status(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=READY_EVAL,
            date_resolution_status=None,
            audience_type="social",
        )
        assert ctx.response_context["date_status"] == STATUS_UNKNOWN

    def test_context_includes_snapshot_when_provided(self):
        snapshot = {"availability": "available", "minimum_spend": 1500}
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=READY_EVAL,
            date_resolution_status=RESOLVED_DATE,
            audience_type="corporate",
            processing_snapshot_summary=snapshot,
        )
        assert ctx.response_context.get("processing_snapshot") == snapshot

    def test_decision_reasons_populated(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=READY_EVAL,
            date_resolution_status=RESOLVED_DATE,
            audience_type="social",
        )
        assert len(ctx.decision_reasons) > 0


# ── to_dict ───────────────────────────────────────────────────────────────────


class TestToDict:
    def test_to_dict_has_all_keys(self):
        ctx = ResponsePreparationService.prepare(
            readiness_evaluation=READY_EVAL,
            date_resolution_status=RESOLVED_DATE,
            audience_type="social",
        )
        d = ctx.to_dict()
        required_keys = {
            "response_goal", "clarification_questions", "response_context",
            "audience_type", "decision_reasons", "requires_clarification",
            "can_draft_response",
        }
        for key in required_keys:
            assert key in d

    def test_goal_always_in_known_set(self):
        cases = [
            (READY_EVAL, RESOLVED_DATE, "social"),
            (NEEDS_CLARIFICATION_DATE_EVAL, RESOLVED_DATE, "social"),
            (WEBFORM_EVAL, RESOLVED_DATE, "unknown"),
            (INSUFFICIENT_EVAL, UNKNOWN_DATE, "unknown"),
            (READY_EVAL, AMBIGUOUS_DATE, "social"),
        ]
        for eval_, date, audience in cases:
            ctx = ResponsePreparationService.prepare(eval_, date, audience)
            assert ctx.response_goal in ALL_RESPONSE_GOALS


# ── No LLM usage ──────────────────────────────────────────────────────────────


class TestNoLLMUsage:
    def test_no_llm_calls(self):
        import app.modules.enquiries.response_preparation_service as mod
        source = open(mod.__file__).read()
        assert "AIGateway" not in source
        assert "anthropic" not in source
