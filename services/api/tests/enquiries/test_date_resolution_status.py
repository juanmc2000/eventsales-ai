"""Tests for DateResolutionStatus model (DATE-002)."""

from datetime import date

import pytest

from app.modules.enquiries.date_resolution_status import (
    ALL_DATE_RESOLUTION_STATUSES,
    ALL_RESOLUTION_METHODS,
    METHOD_AMERICAN_NEARER,
    METHOD_BOTH_EQUALLY_PLAUSIBLE,
    METHOD_BRITISH_DEFAULT,
    METHOD_DD_MM_UNAMBIGUOUS,
    METHOD_MM_DD_UNAMBIGUOUS,
    METHOD_NEAR_HORIZON_AMERICAN,
    METHOD_NEXT_YEAR_ASSUMPTION,
    METHOD_NO_DATE_EXTRACTED,
    METHOD_RELATIVE_PERIOD_EXPANSION,
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_RESOLVED_WITH_CONFIRMATION,
    STATUS_UNKNOWN,
    DateResolutionStatus,
)
from app.modules.enquiries.numeric_date_disambiguation_service import (
    NumericDateDisambiguationService,
)

ANCHOR = date(2026, 6, 3)


# ── Constants ──────────────────────────────────────────────────────────────────


class TestConstants:
    def test_all_statuses_defined(self):
        assert ALL_DATE_RESOLUTION_STATUSES == {
            "resolved", "resolved_with_confirmation", "ambiguous", "unknown"
        }

    def test_all_resolution_methods_non_empty(self):
        assert len(ALL_RESOLUTION_METHODS) >= 10


# ── from_disambiguation_result ────────────────────────────────────────────────


class TestFromDisambiguationResult:
    """Verify HOTFIX-001 output surfaces correctly through the status model."""

    def test_unambiguous_day_month_maps_to_resolved(self):
        # 25/7 — value1 > 12, unambiguous DD/MM
        result = NumericDateDisambiguationService.disambiguate(25, 7, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("25/7", result)
        assert status.status == STATUS_RESOLVED
        assert status.resolved_date == "2026-07-25"
        assert status.alternative_date is None
        assert status.clarification_required is False
        assert status.can_proceed_to_availability is True
        assert "25/7" == status.original_text

    def test_unambiguous_month_day_maps_to_resolved(self):
        # 7/25 — value2 > 12, unambiguous MM/DD
        result = NumericDateDisambiguationService.disambiguate(7, 25, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("7/25", result)
        assert status.status == STATUS_RESOLVED
        assert status.resolved_date == "2026-07-25"
        assert status.clarification_required is False

    def test_british_default_maps_to_resolved_with_confirmation(self):
        # 10/12 — both ≤ 12; both beyond 120-day horizon (Oct 12 = 131d, Dec 10 = 190d);
        # |190-131|=59 > CLOSE_CALL_DAYS=30 → british_default (RESOLVED_WITH_CONFIRMATION)
        result = NumericDateDisambiguationService.disambiguate(10, 12, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("10/12", result)
        assert status.status == STATUS_RESOLVED_WITH_CONFIRMATION
        assert status.clarification_required is True
        assert status.clarification_question is not None

    def test_close_call_maps_to_ambiguous(self):
        # 7/6 — both dates are very close together → unresolved_ambiguity
        result = NumericDateDisambiguationService.disambiguate(7, 6, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("7/6", result)
        assert status.status == STATUS_AMBIGUOUS
        assert status.can_proceed_to_availability is False
        assert status.clarification_required is True

    def test_american_preferred_by_heuristic(self):
        # 9/1 — british (Jan 9) rolls to 2027 (>120d), american (Sep 1) is 90d away (<120d)
        # Rule 4 (HOTFIX-008): american_near, british not → RESOLVED directly
        result = NumericDateDisambiguationService.disambiguate(9, 1, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("9/1", result)
        assert status.status == STATUS_RESOLVED
        assert status.resolved_date == "2026-09-01"
        assert status.resolution_method == METHOD_NEAR_HORIZON_AMERICAN

    def test_candidate_dates_populated(self):
        result = NumericDateDisambiguationService.disambiguate(1, 9, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("1/9", result)
        assert len(status.candidate_dates) >= 1
        assert status.resolved_date in status.candidate_dates

    def test_both_candidates_when_alternative_present(self):
        result = NumericDateDisambiguationService.disambiguate(7, 6, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("7/6", result)
        if status.alternative_date:
            assert status.alternative_date in status.candidate_dates

    def test_original_text_preserved(self):
        result = NumericDateDisambiguationService.disambiguate(25, 7, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("25th July", result)
        assert status.original_text == "25th July"


# ── Resolution method mapping ─────────────────────────────────────────────────


class TestResolutionMethodMapping:
    def test_resolved_maps_to_dd_mm_unambiguous(self):
        result = NumericDateDisambiguationService.disambiguate(25, 7, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("25/7", result)
        assert status.status == STATUS_RESOLVED
        assert status.resolution_method == METHOD_DD_MM_UNAMBIGUOUS

    def test_both_equally_plausible_maps_correctly(self):
        # 7/6 → close call → UNRESOLVED_AMBIGUITY with reason=both_interpretations_equally_plausible
        result = NumericDateDisambiguationService.disambiguate(7, 6, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("7/6", result)
        assert status.resolution_method == METHOD_BOTH_EQUALLY_PLAUSIBLE

    def test_american_nearer_maps_correctly(self):
        # 9/1 now resolved via Rule 4 (near_horizon_american) rather than Rule 5
        result = NumericDateDisambiguationService.disambiguate(9, 1, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("9/1", result)
        assert status.resolution_method == METHOD_NEAR_HORIZON_AMERICAN


# ── resolved() factory ────────────────────────────────────────────────────────


class TestResolvedFactory:
    def test_resolved_factory_sets_correct_status(self):
        status = DateResolutionStatus.resolved(
            original_text="next Friday",
            resolved_date="2026-06-07",
            resolution_method=METHOD_RELATIVE_PERIOD_EXPANSION,
        )
        assert status.status == STATUS_RESOLVED
        assert status.resolved_date == "2026-06-07"
        assert status.clarification_required is False
        assert status.can_proceed_to_availability is True

    def test_resolved_factory_no_alternative(self):
        status = DateResolutionStatus.resolved("July 4th", "2026-07-04")
        assert status.alternative_date is None

    def test_resolved_factory_candidate_dates_populated(self):
        status = DateResolutionStatus.resolved("July 4th", "2026-07-04")
        assert "2026-07-04" in status.candidate_dates

    def test_resolved_factory_no_clarification_question(self):
        status = DateResolutionStatus.resolved("next week", "2026-06-09")
        assert status.clarification_question is None


# ── unknown() factory ─────────────────────────────────────────────────────────


class TestUnknownFactory:
    def test_unknown_factory_sets_unknown_status(self):
        status = DateResolutionStatus.unknown()
        assert status.status == STATUS_UNKNOWN
        assert status.can_proceed_to_availability is False
        assert status.requires_guest_action is True

    def test_unknown_factory_sets_clarification_question(self):
        status = DateResolutionStatus.unknown()
        assert status.clarification_question is not None
        assert len(status.clarification_question) > 0

    def test_unknown_factory_with_original_text(self):
        status = DateResolutionStatus.unknown("sometime")
        assert status.original_text == "sometime"

    def test_unknown_factory_no_resolved_date(self):
        status = DateResolutionStatus.unknown()
        assert status.resolved_date is None

    def test_unknown_factory_resolution_method(self):
        status = DateResolutionStatus.unknown()
        assert status.resolution_method == METHOD_NO_DATE_EXTRACTED


# ── Computed properties ───────────────────────────────────────────────────────


class TestComputedProperties:
    def test_resolved_can_proceed(self):
        status = DateResolutionStatus.resolved("today", "2026-06-03")
        assert status.can_proceed_to_availability is True

    def test_resolved_with_confirmation_cannot_proceed(self):
        # 10/12 → RESOLVED_WITH_CONFIRMATION (british_default) — cannot auto-proceed
        result = NumericDateDisambiguationService.disambiguate(10, 12, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("10/12", result)
        assert status.can_proceed_to_availability is False

    def test_ambiguous_cannot_proceed(self):
        result = NumericDateDisambiguationService.disambiguate(7, 6, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("7/6", result)
        assert status.can_proceed_to_availability is False

    def test_unknown_cannot_proceed(self):
        status = DateResolutionStatus.unknown()
        assert status.can_proceed_to_availability is False

    def test_requires_guest_action_when_clarification_required(self):
        # 10/12 → RESOLVED_WITH_CONFIRMATION (british_default) — clarification required
        result = NumericDateDisambiguationService.disambiguate(10, 12, ANCHOR)
        status = DateResolutionStatus.from_disambiguation_result("10/12", result)
        assert status.requires_guest_action is True

    def test_no_guest_action_when_resolved(self):
        status = DateResolutionStatus.resolved("July 4th", "2026-07-04")
        assert status.requires_guest_action is False


# ── to_dict serialisation ─────────────────────────────────────────────────────


class TestToDict:
    def test_to_dict_has_all_required_keys(self):
        status = DateResolutionStatus.resolved("today", "2026-06-03")
        d = status.to_dict()
        required = {
            "status", "original_text", "resolution_method", "resolved_date",
            "alternative_date", "clarification_required", "clarification_reason",
            "clarification_question", "candidate_dates", "can_proceed_to_availability",
        }
        for key in required:
            assert key in d, f"Missing key: {key}"

    def test_to_dict_status_correct(self):
        status = DateResolutionStatus.resolved("today", "2026-06-03")
        assert status.to_dict()["status"] == STATUS_RESOLVED

    def test_to_dict_can_proceed_reflected(self):
        resolved = DateResolutionStatus.resolved("today", "2026-06-03")
        unknown = DateResolutionStatus.unknown()
        assert resolved.to_dict()["can_proceed_to_availability"] is True
        assert unknown.to_dict()["can_proceed_to_availability"] is False


# ── No LLM usage ──────────────────────────────────────────────────────────────


class TestNoLLMUsage:
    def test_no_llm_calls_in_module(self):
        import app.modules.enquiries.date_resolution_status as mod
        source = open(mod.__file__).read()
        assert "AIGateway" not in source
        assert "anthropic" not in source
