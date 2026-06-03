"""Tests for MissingInformationDecisionEngine (RESP-002)."""

import pytest

from app.modules.enquiries.date_resolution_status import (
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_RESOLVED_WITH_CONFIRMATION,
    STATUS_UNKNOWN,
    DateResolutionStatus,
)
from app.modules.enquiries.missing_information_decision_engine import (
    ALL_DECISIONS,
    DECISION_PROCEED,
    DECISION_REQUEST_DATE,
    DECISION_REQUEST_DATE_CONFIRMATION,
    DECISION_REQUEST_GUEST_COUNT,
    DECISION_REQUEST_MULTIPLE,
    MissingInformationDecision,
    MissingInformationDecisionEngine,
)
from app.modules.enquiries.readiness_evaluator import (
    STATUS_NEEDS_CLARIFICATION,
    STATUS_READY_FOR_AVAILABILITY,
    ReadinessEvaluation,
)
from app.modules.enquiries.numeric_date_disambiguation_service import (
    NumericDateDisambiguationService,
)
from datetime import date


ANCHOR = date(2026, 6, 3)

# ── Helpers ────────────────────────────────────────────────────────────────────


def make_readiness(guest_count_present: bool = True, **kwargs) -> ReadinessEvaluation:
    defaults = dict(
        status=STATUS_READY_FOR_AVAILABILITY,
        date_understood=True,
        guest_count_present=guest_count_present,
        occasion_understood=True,
        meal_period_present=True,
        audience_identified=True,
        date_clarification_required=False,
        availability_check_possible=guest_count_present,
        missing_for_availability=[] if guest_count_present else ["guest_count"],
        notes="",
    )
    defaults.update(kwargs)
    return ReadinessEvaluation(**defaults)


READY_READINESS = make_readiness(guest_count_present=True)
MISSING_COUNT_READINESS = make_readiness(guest_count_present=False)

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
    clarification_question=(
        "Could you confirm you meant 1 September? "
        "I've provisionally checked availability for 1 September 2026."
    ),
    candidate_dates=["2026-09-01", "2026-01-09"],
)
UNKNOWN_DATE = DateResolutionStatus.unknown()


# ── Constants ──────────────────────────────────────────────────────────────────


class TestConstants:
    def test_all_decisions_defined(self):
        assert ALL_DECISIONS == {
            "PROCEED",
            "REQUEST_DATE_CONFIRMATION",
            "REQUEST_DATE",
            "REQUEST_GUEST_COUNT",
            "REQUEST_MULTIPLE",
        }


# ── Rule 1: Ambiguous date → availability blocked ─────────────────────────────


class TestRule1AmbiguousDate:
    def test_ambiguous_date_returns_date_confirmation(self):
        decision = MissingInformationDecisionEngine.decide(AMBIGUOUS_DATE, READY_READINESS)
        assert decision.decision == DECISION_REQUEST_DATE_CONFIRMATION

    def test_ambiguous_date_blocks_availability(self):
        decision = MissingInformationDecisionEngine.decide(AMBIGUOUS_DATE, READY_READINESS)
        assert decision.availability_allowed is False

    def test_ambiguous_date_includes_clarification_question(self):
        decision = MissingInformationDecisionEngine.decide(AMBIGUOUS_DATE, READY_READINESS)
        assert len(decision.questions) > 0
        assert "7 June" in decision.questions[0] or "6 July" in decision.questions[0]

    def test_ambiguous_date_requires_clarification(self):
        decision = MissingInformationDecisionEngine.decide(AMBIGUOUS_DATE, READY_READINESS)
        assert decision.requires_clarification is True

    def test_ambiguous_date_has_blocking_reason(self):
        decision = MissingInformationDecisionEngine.decide(AMBIGUOUS_DATE, READY_READINESS)
        assert len(decision.blocking_reasons) > 0

    def test_hotfix001_ambiguous_9_1_blocks_availability(self):
        # 9/1 is RESOLVED_WITH_CONFIRMATION (not AMBIGUOUS) — Rule 2 applies
        result = NumericDateDisambiguationService.disambiguate(9, 1, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("9/1", result)
        decision = MissingInformationDecisionEngine.decide(status, READY_READINESS)
        # Sep 1 is near, so american chosen — availability may proceed
        assert decision.decision == DECISION_REQUEST_DATE_CONFIRMATION
        assert decision.availability_allowed is True  # confirmation, not blocked

    def test_hotfix001_close_call_7_6_blocks_availability(self):
        # 7/6 is UNRESOLVED_AMBIGUITY → ambiguous
        result = NumericDateDisambiguationService.disambiguate(7, 6, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("7/6", result)
        decision = MissingInformationDecisionEngine.decide(status, READY_READINESS)
        assert decision.availability_allowed is False


# ── Rule 2: Resolved with confirmation ───────────────────────────────────────


class TestRule2ResolvedWithConfirmation:
    def test_confirmed_date_does_not_block_availability(self):
        decision = MissingInformationDecisionEngine.decide(CONFIRMED_DATE, READY_READINESS)
        assert decision.availability_allowed is True

    def test_confirmed_date_returns_date_confirmation_decision(self):
        decision = MissingInformationDecisionEngine.decide(CONFIRMED_DATE, READY_READINESS)
        assert decision.decision == DECISION_REQUEST_DATE_CONFIRMATION

    def test_confirmed_date_includes_clarification_question(self):
        decision = MissingInformationDecisionEngine.decide(CONFIRMED_DATE, READY_READINESS)
        assert len(decision.questions) > 0
        assert "September" in decision.questions[0]

    def test_confirmed_date_requires_clarification(self):
        decision = MissingInformationDecisionEngine.decide(CONFIRMED_DATE, READY_READINESS)
        assert decision.requires_clarification is True


# ── Rule 3: No date extracted ─────────────────────────────────────────────────


class TestRule3NoDate:
    def test_unknown_date_blocks_availability(self):
        decision = MissingInformationDecisionEngine.decide(UNKNOWN_DATE, READY_READINESS)
        assert decision.availability_allowed is False

    def test_unknown_date_returns_request_date(self):
        decision = MissingInformationDecisionEngine.decide(UNKNOWN_DATE, READY_READINESS)
        assert decision.decision == DECISION_REQUEST_DATE

    def test_none_date_status_blocks_availability(self):
        decision = MissingInformationDecisionEngine.decide(None, READY_READINESS)
        assert decision.availability_allowed is False
        assert decision.decision == DECISION_REQUEST_DATE

    def test_unknown_date_includes_question(self):
        decision = MissingInformationDecisionEngine.decide(UNKNOWN_DATE, READY_READINESS)
        assert len(decision.questions) > 0

    def test_unknown_date_has_blocking_reason(self):
        decision = MissingInformationDecisionEngine.decide(UNKNOWN_DATE, READY_READINESS)
        assert len(decision.blocking_reasons) > 0


# ── Rule 4: Guest count missing ───────────────────────────────────────────────


class TestRule4GuestCountMissing:
    def test_missing_count_with_resolved_date_blocks_availability(self):
        decision = MissingInformationDecisionEngine.decide(RESOLVED_DATE, MISSING_COUNT_READINESS)
        assert decision.availability_allowed is False

    def test_missing_count_returns_guest_count_decision(self):
        decision = MissingInformationDecisionEngine.decide(RESOLVED_DATE, MISSING_COUNT_READINESS)
        assert decision.decision == DECISION_REQUEST_GUEST_COUNT

    def test_missing_count_includes_guest_count_question(self):
        decision = MissingInformationDecisionEngine.decide(RESOLVED_DATE, MISSING_COUNT_READINESS)
        assert any("guest" in q.lower() or "many" in q.lower() for q in decision.questions)

    def test_missing_count_has_blocking_reason(self):
        decision = MissingInformationDecisionEngine.decide(RESOLVED_DATE, MISSING_COUNT_READINESS)
        assert len(decision.blocking_reasons) > 0


# ── Rule 5: All info present → proceed ────────────────────────────────────────


class TestRule5Proceed:
    def test_resolved_date_and_count_returns_proceed(self):
        decision = MissingInformationDecisionEngine.decide(RESOLVED_DATE, READY_READINESS)
        assert decision.decision == DECISION_PROCEED

    def test_proceed_allows_availability(self):
        decision = MissingInformationDecisionEngine.decide(RESOLVED_DATE, READY_READINESS)
        assert decision.availability_allowed is True

    def test_proceed_has_no_questions(self):
        decision = MissingInformationDecisionEngine.decide(RESOLVED_DATE, READY_READINESS)
        assert decision.questions == []

    def test_proceed_does_not_require_clarification(self):
        decision = MissingInformationDecisionEngine.decide(RESOLVED_DATE, READY_READINESS)
        assert decision.requires_clarification is False

    def test_no_readiness_with_resolved_date_proceeds(self):
        # When readiness is not provided, guest count check is skipped
        decision = MissingInformationDecisionEngine.decide(RESOLVED_DATE, None)
        assert decision.decision == DECISION_PROCEED
        assert decision.availability_allowed is True


# ── Multiple missing items ────────────────────────────────────────────────────


class TestMultipleMissingItems:
    def test_ambiguous_date_plus_missing_count_returns_multiple(self):
        decision = MissingInformationDecisionEngine.decide(AMBIGUOUS_DATE, MISSING_COUNT_READINESS)
        assert decision.decision == DECISION_REQUEST_MULTIPLE

    def test_multiple_includes_both_questions(self):
        decision = MissingInformationDecisionEngine.decide(AMBIGUOUS_DATE, MISSING_COUNT_READINESS)
        assert len(decision.questions) >= 2

    def test_multiple_blocks_availability(self):
        decision = MissingInformationDecisionEngine.decide(AMBIGUOUS_DATE, MISSING_COUNT_READINESS)
        assert decision.availability_allowed is False

    def test_unknown_date_plus_missing_count_returns_multiple(self):
        decision = MissingInformationDecisionEngine.decide(UNKNOWN_DATE, MISSING_COUNT_READINESS)
        assert decision.decision == DECISION_REQUEST_MULTIPLE


# ── Result shape ──────────────────────────────────────────────────────────────


class TestResultShape:
    def test_result_has_all_required_fields(self):
        decision = MissingInformationDecisionEngine.decide(RESOLVED_DATE, READY_READINESS)
        assert isinstance(decision, MissingInformationDecision)
        assert hasattr(decision, "decision")
        assert hasattr(decision, "availability_allowed")
        assert hasattr(decision, "questions")
        assert hasattr(decision, "blocking_reasons")

    def test_decision_always_in_known_set(self):
        cases = [
            (RESOLVED_DATE, READY_READINESS),
            (AMBIGUOUS_DATE, READY_READINESS),
            (CONFIRMED_DATE, READY_READINESS),
            (UNKNOWN_DATE, READY_READINESS),
            (RESOLVED_DATE, MISSING_COUNT_READINESS),
            (AMBIGUOUS_DATE, MISSING_COUNT_READINESS),
            (None, None),
        ]
        for date_status, readiness in cases:
            decision = MissingInformationDecisionEngine.decide(date_status, readiness)
            assert decision.decision in ALL_DECISIONS

    def test_to_dict_has_all_keys(self):
        decision = MissingInformationDecisionEngine.decide(RESOLVED_DATE, READY_READINESS)
        d = decision.to_dict()
        for key in ("decision", "availability_allowed", "questions", "blocking_reasons", "requires_clarification"):
            assert key in d


# ── HOTFIX-001 integration ────────────────────────────────────────────────────


class TestHotfix001Integration:
    """Verify that HOTFIX-001 disambiguation results surface correctly through the engine."""

    def test_25_7_unambiguous_proceeds(self):
        result = NumericDateDisambiguationService.disambiguate(25, 7, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("25/7", result)
        decision = MissingInformationDecisionEngine.decide(status, READY_READINESS)
        assert decision.decision == DECISION_PROCEED
        assert decision.availability_allowed is True

    def test_7_6_ambiguous_blocks(self):
        result = NumericDateDisambiguationService.disambiguate(7, 6, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("7/6", result)
        decision = MissingInformationDecisionEngine.decide(status, READY_READINESS)
        assert decision.availability_allowed is False
        assert "7 June" in decision.questions[0] or "6 July" in decision.questions[0]

    def test_1_9_confirmation_allows_availability(self):
        result = NumericDateDisambiguationService.disambiguate(1, 9, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("1/9", result)
        decision = MissingInformationDecisionEngine.decide(status, READY_READINESS)
        assert decision.availability_allowed is True
        assert decision.requires_clarification is True


# ── No LLM usage ──────────────────────────────────────────────────────────────


class TestNoLLMUsage:
    def test_no_llm_calls(self):
        import app.modules.enquiries.missing_information_decision_engine as mod
        source = open(mod.__file__).read()
        assert "AIGateway" not in source
        assert "anthropic" not in source
