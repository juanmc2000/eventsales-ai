"""Tests for RESP-011 — Response Section Builder (updated RESP-016).

Validates:
- SectionPlan returned for every known response goal
- allowed_sections and required_sections are non-empty for all goals
- omitted_sections are non-empty for all goals
- CONFIRM_AVAILABLE excludes exact_timing unless time_confirmed=True
- RESPOND_UNAVAILABLE excludes alternative_dates unless alternatives_provided=True
- ACKNOWLEDGE_AND_CHECK_AVAILABILITY excludes hosting_language and availability_confirmation
- REQUEST_MISSING_INFORMATION includes clarification_questions only when present
- REQUEST_DATE_CONFIRMATION requires date_confirmation_question
- REQUEST_WEBFORM includes webform_redirect only when has_webform_url=True
- Unknown goal returns conservative fallback
- to_dict returns expected keys
- ResponsePreparationBuilder.build() produces section_plan in ResponsePlan
RESP-016:
- CONFIRM_AVAILABLE uses booking_next_step (not simple_next_step)
- ACKNOWLEDGE_AND_CHECK_AVAILABILITY uses availability_check_next_step
- RESPOND_UNAVAILABLE has no next-step section
- REQUEST_MISSING_INFORMATION uses clarification_next_step
"""

from __future__ import annotations

import pytest

from app.modules.enquiries.response_section_builder import (
    SECTION_ALTERNATIVE_DATES,
    SECTION_AVAILABILITY_CHECK_NEXT_STEP,
    SECTION_AVAILABILITY_CHECK_PENDING,
    SECTION_AVAILABILITY_CONFIRMATION,
    SECTION_BOOKING_NEXT_STEP,
    SECTION_CLARIFICATION_NEXT_STEP,
    SECTION_CLARIFICATION_QUESTIONS,
    SECTION_DATE_CONFIRMATION_QUESTION,
    SECTION_EXACT_TIMING,
    SECTION_HOSTING_LANGUAGE,
    SECTION_INVENTED_QUESTIONS,
    SECTION_INVENTED_SLA,
    SECTION_MINIMUM_SPEND,
    SECTION_OPENING,
    SECTION_ROOM_SUITABILITY,
    SECTION_SIGNOFF,
    SECTION_UNAVAILABILITY_ACKNOWLEDGEMENT,
    SECTION_WEBFORM_REDIRECT,
    ResponseSectionBuilder,
    SectionPlan,
)

ALL_GOALS = [
    "CONFIRM_AVAILABLE",
    "RESPOND_UNAVAILABLE",
    "ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
    "REQUEST_MISSING_INFORMATION",
    "REQUEST_DATE_CONFIRMATION",
    "REQUEST_WEBFORM",
    "ESCALATE_TO_HUMAN",
]


# ── SectionPlan dataclass ─────────────────────────────────────────────────────


class TestSectionPlanDataclass:
    def test_to_dict_has_required_keys(self) -> None:
        plan = ResponseSectionBuilder.build("CONFIRM_AVAILABLE")
        d = plan.to_dict()
        assert set(d.keys()) == {
            "response_goal",
            "allowed_sections",
            "required_sections",
            "omitted_sections",
            "section_reasoning",
        }

    def test_response_goal_attribute_matches(self) -> None:
        plan = ResponseSectionBuilder.build("RESPOND_UNAVAILABLE")
        assert plan.response_goal == "RESPOND_UNAVAILABLE"

    def test_is_section_plan_instance(self) -> None:
        plan = ResponseSectionBuilder.build("ESCALATE_TO_HUMAN")
        assert isinstance(plan, SectionPlan)


# ── All goals return non-empty plans ─────────────────────────────────────────


class TestAllGoalsReturnPlans:
    @pytest.mark.parametrize("goal", ALL_GOALS)
    def test_allowed_sections_non_empty(self, goal: str) -> None:
        plan = ResponseSectionBuilder.build(goal)
        assert len(plan.allowed_sections) > 0

    @pytest.mark.parametrize("goal", ALL_GOALS)
    def test_required_sections_non_empty(self, goal: str) -> None:
        plan = ResponseSectionBuilder.build(goal)
        assert len(plan.required_sections) > 0

    @pytest.mark.parametrize("goal", ALL_GOALS)
    def test_omitted_sections_non_empty(self, goal: str) -> None:
        plan = ResponseSectionBuilder.build(goal)
        assert len(plan.omitted_sections) > 0

    @pytest.mark.parametrize("goal", ALL_GOALS)
    def test_opening_always_required(self, goal: str) -> None:
        plan = ResponseSectionBuilder.build(goal)
        assert SECTION_OPENING in plan.required_sections

    @pytest.mark.parametrize("goal", ALL_GOALS)
    def test_signoff_always_allowed(self, goal: str) -> None:
        plan = ResponseSectionBuilder.build(goal)
        assert SECTION_SIGNOFF in plan.allowed_sections


# ── CONFIRM_AVAILABLE ─────────────────────────────────────────────────────────


class TestConfirmAvailableSections:
    def test_availability_confirmation_in_required(self) -> None:
        plan = ResponseSectionBuilder.build("CONFIRM_AVAILABLE")
        assert SECTION_AVAILABILITY_CONFIRMATION in plan.required_sections

    def test_exact_timing_omitted_when_not_confirmed(self) -> None:
        plan = ResponseSectionBuilder.build("CONFIRM_AVAILABLE", time_confirmed=False)
        assert SECTION_EXACT_TIMING in plan.omitted_sections
        assert SECTION_EXACT_TIMING not in plan.allowed_sections

    def test_exact_timing_allowed_when_confirmed(self) -> None:
        plan = ResponseSectionBuilder.build("CONFIRM_AVAILABLE", time_confirmed=True)
        assert SECTION_EXACT_TIMING in plan.allowed_sections
        assert SECTION_EXACT_TIMING not in plan.omitted_sections

    def test_minimum_spend_required_when_present(self) -> None:
        plan = ResponseSectionBuilder.build("CONFIRM_AVAILABLE", has_minimum_spend=True)
        assert SECTION_MINIMUM_SPEND in plan.required_sections
        assert SECTION_MINIMUM_SPEND in plan.allowed_sections

    def test_minimum_spend_absent_when_not_present(self) -> None:
        plan = ResponseSectionBuilder.build("CONFIRM_AVAILABLE", has_minimum_spend=False)
        assert SECTION_MINIMUM_SPEND not in plan.required_sections

    def test_room_suitability_allowed_when_context_present(self) -> None:
        plan = ResponseSectionBuilder.build("CONFIRM_AVAILABLE", has_room_context=True)
        assert SECTION_ROOM_SUITABILITY in plan.allowed_sections

    def test_alternative_dates_omitted(self) -> None:
        plan = ResponseSectionBuilder.build("CONFIRM_AVAILABLE")
        assert SECTION_ALTERNATIVE_DATES in plan.omitted_sections

    def test_invented_questions_omitted(self) -> None:
        plan = ResponseSectionBuilder.build("CONFIRM_AVAILABLE")
        assert SECTION_INVENTED_QUESTIONS in plan.omitted_sections

    def test_invented_sla_omitted(self) -> None:
        plan = ResponseSectionBuilder.build("CONFIRM_AVAILABLE")
        assert SECTION_INVENTED_SLA in plan.omitted_sections

    def test_exact_timing_reasoning_provided(self) -> None:
        plan = ResponseSectionBuilder.build("CONFIRM_AVAILABLE", time_confirmed=False)
        assert SECTION_EXACT_TIMING in plan.section_reasoning


# ── RESPOND_UNAVAILABLE ───────────────────────────────────────────────────────


class TestRespondUnavailableSections:
    def test_unavailability_acknowledgement_required(self) -> None:
        plan = ResponseSectionBuilder.build("RESPOND_UNAVAILABLE")
        assert SECTION_UNAVAILABILITY_ACKNOWLEDGEMENT in plan.required_sections

    def test_alternative_dates_omitted_by_default(self) -> None:
        plan = ResponseSectionBuilder.build("RESPOND_UNAVAILABLE")
        assert SECTION_ALTERNATIVE_DATES in plan.omitted_sections
        assert SECTION_ALTERNATIVE_DATES not in plan.allowed_sections

    def test_alternative_dates_allowed_when_provided(self) -> None:
        plan = ResponseSectionBuilder.build("RESPOND_UNAVAILABLE", alternatives_provided=True)
        assert SECTION_ALTERNATIVE_DATES in plan.allowed_sections
        assert SECTION_ALTERNATIVE_DATES not in plan.omitted_sections

    def test_hosting_language_omitted(self) -> None:
        plan = ResponseSectionBuilder.build("RESPOND_UNAVAILABLE")
        assert SECTION_HOSTING_LANGUAGE in plan.omitted_sections

    def test_invented_questions_omitted(self) -> None:
        plan = ResponseSectionBuilder.build("RESPOND_UNAVAILABLE")
        assert SECTION_INVENTED_QUESTIONS in plan.omitted_sections

    def test_invented_sla_omitted(self) -> None:
        plan = ResponseSectionBuilder.build("RESPOND_UNAVAILABLE")
        assert SECTION_INVENTED_SLA in plan.omitted_sections

    def test_alternative_dates_reasoning_provided(self) -> None:
        plan = ResponseSectionBuilder.build("RESPOND_UNAVAILABLE")
        assert SECTION_ALTERNATIVE_DATES in plan.section_reasoning


# ── ACKNOWLEDGE_AND_CHECK_AVAILABILITY ───────────────────────────────────────


class TestAcknowledgeAndCheckSections:
    def test_availability_check_pending_required(self) -> None:
        plan = ResponseSectionBuilder.build("ACKNOWLEDGE_AND_CHECK_AVAILABILITY")
        assert SECTION_AVAILABILITY_CHECK_PENDING in plan.required_sections

    def test_hosting_language_omitted(self) -> None:
        plan = ResponseSectionBuilder.build("ACKNOWLEDGE_AND_CHECK_AVAILABILITY")
        assert SECTION_HOSTING_LANGUAGE in plan.omitted_sections

    def test_availability_confirmation_omitted(self) -> None:
        plan = ResponseSectionBuilder.build("ACKNOWLEDGE_AND_CHECK_AVAILABILITY")
        assert SECTION_AVAILABILITY_CONFIRMATION in plan.omitted_sections

    def test_exact_timing_omitted(self) -> None:
        plan = ResponseSectionBuilder.build("ACKNOWLEDGE_AND_CHECK_AVAILABILITY")
        assert SECTION_EXACT_TIMING in plan.omitted_sections

    def test_invented_questions_omitted(self) -> None:
        plan = ResponseSectionBuilder.build("ACKNOWLEDGE_AND_CHECK_AVAILABILITY")
        assert SECTION_INVENTED_QUESTIONS in plan.omitted_sections

    def test_invented_sla_omitted(self) -> None:
        plan = ResponseSectionBuilder.build("ACKNOWLEDGE_AND_CHECK_AVAILABILITY")
        assert SECTION_INVENTED_SLA in plan.omitted_sections

    def test_hosting_language_reasoning_provided(self) -> None:
        plan = ResponseSectionBuilder.build("ACKNOWLEDGE_AND_CHECK_AVAILABILITY")
        assert SECTION_HOSTING_LANGUAGE in plan.section_reasoning


# ── REQUEST_MISSING_INFORMATION ───────────────────────────────────────────────


class TestRequestMissingInformationSections:
    def test_clarification_questions_included_when_present(self) -> None:
        plan = ResponseSectionBuilder.build(
            "REQUEST_MISSING_INFORMATION", has_clarification_questions=True
        )
        assert SECTION_CLARIFICATION_QUESTIONS in plan.allowed_sections
        assert SECTION_CLARIFICATION_QUESTIONS in plan.required_sections

    def test_clarification_questions_absent_when_not_present(self) -> None:
        plan = ResponseSectionBuilder.build(
            "REQUEST_MISSING_INFORMATION", has_clarification_questions=False
        )
        assert SECTION_CLARIFICATION_QUESTIONS not in plan.allowed_sections

    def test_invented_questions_omitted(self) -> None:
        plan = ResponseSectionBuilder.build("REQUEST_MISSING_INFORMATION")
        assert SECTION_INVENTED_QUESTIONS in plan.omitted_sections


# ── REQUEST_DATE_CONFIRMATION ────────────────────────────────────────────────


class TestRequestDateConfirmationSections:
    def test_date_confirmation_question_required(self) -> None:
        plan = ResponseSectionBuilder.build("REQUEST_DATE_CONFIRMATION")
        assert SECTION_DATE_CONFIRMATION_QUESTION in plan.required_sections

    def test_availability_confirmation_omitted(self) -> None:
        plan = ResponseSectionBuilder.build("REQUEST_DATE_CONFIRMATION")
        assert SECTION_AVAILABILITY_CONFIRMATION in plan.omitted_sections

    def test_invented_questions_omitted(self) -> None:
        plan = ResponseSectionBuilder.build("REQUEST_DATE_CONFIRMATION")
        assert SECTION_INVENTED_QUESTIONS in plan.omitted_sections


# ── REQUEST_WEBFORM ───────────────────────────────────────────────────────────


class TestRequestWebformSections:
    def test_webform_redirect_included_when_url_present(self) -> None:
        plan = ResponseSectionBuilder.build("REQUEST_WEBFORM", has_webform_url=True)
        assert SECTION_WEBFORM_REDIRECT in plan.allowed_sections
        assert SECTION_WEBFORM_REDIRECT in plan.required_sections

    def test_webform_redirect_absent_when_no_url(self) -> None:
        plan = ResponseSectionBuilder.build("REQUEST_WEBFORM", has_webform_url=False)
        assert SECTION_WEBFORM_REDIRECT not in plan.required_sections

    def test_invented_questions_omitted(self) -> None:
        plan = ResponseSectionBuilder.build("REQUEST_WEBFORM")
        assert SECTION_INVENTED_QUESTIONS in plan.omitted_sections


# ── Unknown goal fallback ─────────────────────────────────────────────────────


class TestUnknownGoalFallback:
    def test_unknown_goal_returns_section_plan(self) -> None:
        plan = ResponseSectionBuilder.build("UNKNOWN_GOAL_XYZ")
        assert isinstance(plan, SectionPlan)

    def test_unknown_goal_opening_required(self) -> None:
        plan = ResponseSectionBuilder.build("UNKNOWN_GOAL_XYZ")
        assert SECTION_OPENING in plan.required_sections

    def test_unknown_goal_availability_confirmation_omitted(self) -> None:
        plan = ResponseSectionBuilder.build("UNKNOWN_GOAL_XYZ")
        assert SECTION_AVAILABILITY_CONFIRMATION in plan.omitted_sections


# ── ResponsePreparationBuilder integration ────────────────────────────────────


class TestResponsePreparationBuilderIntegration:
    """Verify that ResponsePreparationBuilder.build() populates section_plan."""

    def _make_readiness(self):
        from app.modules.enquiries.readiness_evaluator import (
            ReadinessEvaluation,
            STATUS_READY_FOR_AVAILABILITY,
        )
        return ReadinessEvaluation(
            status=STATUS_READY_FOR_AVAILABILITY,
            date_understood=True,
            guest_count_present=True,
            occasion_understood=True,
            meal_period_present=True,
            audience_identified=True,
            availability_check_possible=True,
            date_clarification_required=False,
        )

    def test_section_plan_present_in_response_plan(self) -> None:
        from app.modules.enquiries.response_preparation_builder import (
            ResponsePreparationBuilder,
        )
        plan = ResponsePreparationBuilder.build(readiness_evaluation=self._make_readiness())
        assert "section_plan" in plan.to_dict()
        assert isinstance(plan.section_plan, dict)

    def test_section_plan_has_allowed_sections(self) -> None:
        from app.modules.enquiries.response_preparation_builder import (
            ResponsePreparationBuilder,
        )
        plan = ResponsePreparationBuilder.build(readiness_evaluation=self._make_readiness())
        assert "allowed_sections" in plan.section_plan
        assert isinstance(plan.section_plan["allowed_sections"], list)

    def test_section_plan_has_omitted_sections(self) -> None:
        from app.modules.enquiries.response_preparation_builder import (
            ResponsePreparationBuilder,
        )
        plan = ResponsePreparationBuilder.build(readiness_evaluation=self._make_readiness())
        assert "omitted_sections" in plan.section_plan
        assert len(plan.section_plan["omitted_sections"]) > 0


# ── RESP-016: Deterministic next-step sections ────────────────────────────────


class TestDeterministicNextStepSections:
    """RESP-016 — simple_next_step replaced with goal-specific next-step types."""

    def test_confirm_available_uses_booking_next_step(self) -> None:
        plan = ResponseSectionBuilder.build("CONFIRM_AVAILABLE")
        assert SECTION_BOOKING_NEXT_STEP in plan.allowed_sections

    def test_confirm_available_no_simple_next_step(self) -> None:
        plan = ResponseSectionBuilder.build("CONFIRM_AVAILABLE")
        assert "simple_next_step" not in plan.allowed_sections
        assert "simple_next_step" not in plan.required_sections

    def test_booking_next_step_before_signoff(self) -> None:
        plan = ResponseSectionBuilder.build("CONFIRM_AVAILABLE")
        allowed = plan.allowed_sections
        assert allowed.index(SECTION_BOOKING_NEXT_STEP) < allowed.index(SECTION_SIGNOFF)

    def test_acknowledge_uses_availability_check_next_step(self) -> None:
        plan = ResponseSectionBuilder.build("ACKNOWLEDGE_AND_CHECK_AVAILABILITY")
        assert SECTION_AVAILABILITY_CHECK_NEXT_STEP in plan.allowed_sections

    def test_acknowledge_no_simple_next_step(self) -> None:
        plan = ResponseSectionBuilder.build("ACKNOWLEDGE_AND_CHECK_AVAILABILITY")
        assert "simple_next_step" not in plan.allowed_sections

    def test_availability_check_next_step_before_signoff(self) -> None:
        plan = ResponseSectionBuilder.build("ACKNOWLEDGE_AND_CHECK_AVAILABILITY")
        allowed = plan.allowed_sections
        assert allowed.index(SECTION_AVAILABILITY_CHECK_NEXT_STEP) < allowed.index(SECTION_SIGNOFF)

    def test_respond_unavailable_has_no_next_step_section(self) -> None:
        plan = ResponseSectionBuilder.build("RESPOND_UNAVAILABLE")
        assert SECTION_BOOKING_NEXT_STEP not in plan.allowed_sections
        assert SECTION_AVAILABILITY_CHECK_NEXT_STEP not in plan.allowed_sections
        assert SECTION_CLARIFICATION_NEXT_STEP not in plan.allowed_sections
        assert "simple_next_step" not in plan.allowed_sections

    def test_request_missing_information_uses_clarification_next_step(self) -> None:
        plan = ResponseSectionBuilder.build("REQUEST_MISSING_INFORMATION")
        assert SECTION_CLARIFICATION_NEXT_STEP in plan.allowed_sections

    def test_request_missing_information_no_simple_next_step(self) -> None:
        plan = ResponseSectionBuilder.build("REQUEST_MISSING_INFORMATION")
        assert "simple_next_step" not in plan.allowed_sections

    def test_clarification_next_step_before_signoff(self) -> None:
        plan = ResponseSectionBuilder.build("REQUEST_MISSING_INFORMATION")
        allowed = plan.allowed_sections
        assert allowed.index(SECTION_CLARIFICATION_NEXT_STEP) < allowed.index(SECTION_SIGNOFF)

    def test_no_next_step_sections_cross_contaminate(self) -> None:
        """booking_next_step must not appear in non-CONFIRM_AVAILABLE plans."""
        for goal in ["RESPOND_UNAVAILABLE", "ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
                     "REQUEST_MISSING_INFORMATION", "REQUEST_DATE_CONFIRMATION",
                     "REQUEST_WEBFORM", "ESCALATE_TO_HUMAN"]:
            plan = ResponseSectionBuilder.build(goal)
            assert SECTION_BOOKING_NEXT_STEP not in plan.allowed_sections, goal

    def test_availability_check_next_step_only_in_acknowledge(self) -> None:
        for goal in ["CONFIRM_AVAILABLE", "RESPOND_UNAVAILABLE",
                     "REQUEST_MISSING_INFORMATION", "REQUEST_DATE_CONFIRMATION",
                     "REQUEST_WEBFORM", "ESCALATE_TO_HUMAN"]:
            plan = ResponseSectionBuilder.build(goal)
            assert SECTION_AVAILABILITY_CHECK_NEXT_STEP not in plan.allowed_sections, goal
