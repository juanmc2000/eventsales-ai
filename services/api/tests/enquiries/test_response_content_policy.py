"""Tests for RESP-010 — Response Content Policy.

Validates:
- ContentPolicy returned for every known response goal
- Allowed topics are non-empty for all goals
- Forbidden topics are non-empty for all goals
- Key allowed/forbidden topic contracts per goal
- Unknown goal returns conservative fallback
- is_allowed / is_forbidden helpers work correctly
- to_dict returns expected keys
"""

from __future__ import annotations

import pytest

from app.modules.enquiries.response_content_policy import (
    TOPIC_ACKNOWLEDGEMENT,
    TOPIC_ALTERNATIVE_DATES,
    TOPIC_ALTERNATIVE_ROOMS,
    TOPIC_APPROVED_CLARIFICATION_QUESTIONS,
    TOPIC_AVAILABILITY_CHECK_PENDING,
    TOPIC_AVAILABILITY_CONFIRMATION,
    TOPIC_AVAILABILITY_IMPLICATION,
    TOPIC_CALL_SCHEDULING,
    TOPIC_CALENDAR_CHECKING,
    TOPIC_DATE_CONFIRMATION_QUESTION,
    TOPIC_DATE_SUMMARY,
    TOPIC_EXACT_TIMING_CONFIRMATION,
    TOPIC_FAKE_LINKS,
    TOPIC_HOSTING_LANGUAGE,
    TOPIC_INVENTED_QUESTIONS,
    TOPIC_INVENTED_SLA,
    TOPIC_MENU_DISCUSSION,
    TOPIC_MINIMUM_SPEND_MANDATORY,
    TOPIC_POLITE_CLOSING,
    TOPIC_SIGNOFF,
    TOPIC_SPECIAL_TOUCHES,
    TOPIC_UNAVAILABILITY_STATEMENT,
    TOPIC_VENUE_ROOM_SUITABILITY,
    TOPIC_WEBFORM_REQUEST,
    ContentPolicy,
    ResponseContentPolicy,
)

ALL_GOALS = ResponseContentPolicy.all_goals()


# ── ContentPolicy dataclass ───────────────────────────────────────────────────


class TestContentPolicyDataclass:
    def test_to_dict_has_required_keys(self) -> None:
        policy = ResponseContentPolicy.for_goal("CONFIRM_AVAILABLE")
        d = policy.to_dict()
        assert set(d.keys()) == {"response_goal", "allowed_topics", "forbidden_topics", "policy_notes"}

    def test_is_allowed_true_for_allowed_topic(self) -> None:
        policy = ResponseContentPolicy.for_goal("CONFIRM_AVAILABLE")
        assert policy.is_allowed(TOPIC_ACKNOWLEDGEMENT) is True

    def test_is_allowed_false_for_forbidden_topic(self) -> None:
        policy = ResponseContentPolicy.for_goal("CONFIRM_AVAILABLE")
        assert policy.is_allowed(TOPIC_MENU_DISCUSSION) is False

    def test_is_forbidden_true_for_forbidden_topic(self) -> None:
        policy = ResponseContentPolicy.for_goal("CONFIRM_AVAILABLE")
        assert policy.is_forbidden(TOPIC_EXACT_TIMING_CONFIRMATION) is True

    def test_is_forbidden_false_for_allowed_topic(self) -> None:
        policy = ResponseContentPolicy.for_goal("CONFIRM_AVAILABLE")
        assert policy.is_forbidden(TOPIC_ACKNOWLEDGEMENT) is False

    def test_response_goal_attribute_matches(self) -> None:
        policy = ResponseContentPolicy.for_goal("RESPOND_UNAVAILABLE")
        assert policy.response_goal == "RESPOND_UNAVAILABLE"


# ── All goals have non-empty policies ────────────────────────────────────────


class TestAllGoalsHavePolicies:
    @pytest.mark.parametrize("goal", ALL_GOALS)
    def test_allowed_topics_non_empty(self, goal: str) -> None:
        policy = ResponseContentPolicy.for_goal(goal)
        assert len(policy.allowed_topics) > 0, f"{goal} must have at least one allowed topic"

    @pytest.mark.parametrize("goal", ALL_GOALS)
    def test_forbidden_topics_non_empty(self, goal: str) -> None:
        policy = ResponseContentPolicy.for_goal(goal)
        assert len(policy.forbidden_topics) > 0, f"{goal} must have at least one forbidden topic"

    @pytest.mark.parametrize("goal", ALL_GOALS)
    def test_policy_notes_non_empty(self, goal: str) -> None:
        policy = ResponseContentPolicy.for_goal(goal)
        assert policy.policy_notes != "", f"{goal} must have policy_notes"

    def test_seven_goals_defined(self) -> None:
        assert len(ALL_GOALS) == 7

    def test_all_expected_goals_present(self) -> None:
        expected = {
            "CONFIRM_AVAILABLE",
            "RESPOND_UNAVAILABLE",
            "ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
            "REQUEST_MISSING_INFORMATION",
            "REQUEST_DATE_CONFIRMATION",
            "REQUEST_WEBFORM",
            "ESCALATE_TO_HUMAN",
        }
        assert set(ALL_GOALS) == expected


# ── CONFIRM_AVAILABLE policy ──────────────────────────────────────────────────


class TestConfirmAvailablePolicy:
    def setup_method(self) -> None:
        self.policy = ResponseContentPolicy.for_goal("CONFIRM_AVAILABLE")

    def test_acknowledgement_allowed(self) -> None:
        assert self.policy.is_allowed(TOPIC_ACKNOWLEDGEMENT)

    def test_availability_confirmation_allowed(self) -> None:
        assert self.policy.is_allowed(TOPIC_AVAILABILITY_CONFIRMATION)

    def test_venue_room_suitability_allowed(self) -> None:
        assert self.policy.is_allowed(TOPIC_VENUE_ROOM_SUITABILITY)

    def test_minimum_spend_mandatory_allowed(self) -> None:
        assert self.policy.is_allowed(TOPIC_MINIMUM_SPEND_MANDATORY)

    def test_exact_timing_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_EXACT_TIMING_CONFIRMATION)

    def test_menu_discussion_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_MENU_DISCUSSION)

    def test_special_touches_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_SPECIAL_TOUCHES)

    def test_call_scheduling_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_CALL_SCHEDULING)

    def test_alternative_dates_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_ALTERNATIVE_DATES)

    def test_invented_questions_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_INVENTED_QUESTIONS)

    def test_invented_sla_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_INVENTED_SLA)


# ── RESPOND_UNAVAILABLE policy ────────────────────────────────────────────────


class TestRespondUnavailablePolicy:
    def setup_method(self) -> None:
        self.policy = ResponseContentPolicy.for_goal("RESPOND_UNAVAILABLE")

    def test_acknowledgement_allowed(self) -> None:
        assert self.policy.is_allowed(TOPIC_ACKNOWLEDGEMENT)

    def test_unavailability_statement_allowed(self) -> None:
        assert self.policy.is_allowed(TOPIC_UNAVAILABILITY_STATEMENT)

    def test_polite_closing_allowed(self) -> None:
        assert self.policy.is_allowed(TOPIC_POLITE_CLOSING)

    def test_alternative_dates_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_ALTERNATIVE_DATES)

    def test_alternative_rooms_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_ALTERNATIVE_ROOMS)

    def test_calendar_checking_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_CALENDAR_CHECKING)

    def test_hosting_language_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_HOSTING_LANGUAGE)

    def test_invented_sla_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_INVENTED_SLA)


# ── ACKNOWLEDGE_AND_CHECK_AVAILABILITY policy ─────────────────────────────────


class TestAcknowledgeAndCheckPolicy:
    def setup_method(self) -> None:
        self.policy = ResponseContentPolicy.for_goal("ACKNOWLEDGE_AND_CHECK_AVAILABILITY")

    def test_acknowledgement_allowed(self) -> None:
        assert self.policy.is_allowed(TOPIC_ACKNOWLEDGEMENT)

    def test_availability_check_pending_allowed(self) -> None:
        assert self.policy.is_allowed(TOPIC_AVAILABILITY_CHECK_PENDING)

    def test_date_summary_allowed(self) -> None:
        assert self.policy.is_allowed(TOPIC_DATE_SUMMARY)

    def test_hosting_language_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_HOSTING_LANGUAGE)

    def test_availability_implication_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_AVAILABILITY_IMPLICATION)

    def test_availability_confirmation_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_AVAILABILITY_CONFIRMATION)

    def test_exact_timing_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_EXACT_TIMING_CONFIRMATION)

    def test_menu_discussion_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_MENU_DISCUSSION)

    def test_call_scheduling_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_CALL_SCHEDULING)

    def test_invented_questions_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_INVENTED_QUESTIONS)

    def test_invented_sla_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_INVENTED_SLA)

    # RESP-052: room suitability must be forbidden for ACKNOWLEDGE
    def test_venue_room_suitability_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_VENUE_ROOM_SUITABILITY)

    def test_policy_notes_mention_room_names(self) -> None:
        assert "room" in self.policy.policy_notes.lower()


# ── REQUEST_MISSING_INFORMATION policy ───────────────────────────────────────


class TestRequestMissingInformationPolicy:
    def setup_method(self) -> None:
        self.policy = ResponseContentPolicy.for_goal("REQUEST_MISSING_INFORMATION")

    def test_approved_clarification_questions_allowed(self) -> None:
        assert self.policy.is_allowed(TOPIC_APPROVED_CLARIFICATION_QUESTIONS)

    def test_invented_questions_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_INVENTED_QUESTIONS)

    def test_availability_confirmation_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_AVAILABILITY_CONFIRMATION)

    def test_hosting_language_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_HOSTING_LANGUAGE)


# ── REQUEST_DATE_CONFIRMATION policy ─────────────────────────────────────────


class TestRequestDateConfirmationPolicy:
    def setup_method(self) -> None:
        self.policy = ResponseContentPolicy.for_goal("REQUEST_DATE_CONFIRMATION")

    def test_date_confirmation_question_allowed(self) -> None:
        assert self.policy.is_allowed(TOPIC_DATE_CONFIRMATION_QUESTION)

    def test_availability_confirmation_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_AVAILABILITY_CONFIRMATION)

    def test_availability_implication_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_AVAILABILITY_IMPLICATION)

    def test_invented_questions_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_INVENTED_QUESTIONS)


# ── REQUEST_WEBFORM policy ────────────────────────────────────────────────────


class TestRequestWebformPolicy:
    def setup_method(self) -> None:
        self.policy = ResponseContentPolicy.for_goal("REQUEST_WEBFORM")

    def test_webform_request_allowed(self) -> None:
        assert self.policy.is_allowed(TOPIC_WEBFORM_REQUEST)

    def test_fake_links_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_FAKE_LINKS)

    def test_availability_confirmation_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_AVAILABILITY_CONFIRMATION)


# ── ESCALATE_TO_HUMAN policy ──────────────────────────────────────────────────


class TestEscalateToHumanPolicy:
    def setup_method(self) -> None:
        self.policy = ResponseContentPolicy.for_goal("ESCALATE_TO_HUMAN")

    def test_acknowledgement_allowed(self) -> None:
        assert self.policy.is_allowed(TOPIC_ACKNOWLEDGEMENT)

    def test_signoff_allowed(self) -> None:
        assert self.policy.is_allowed(TOPIC_SIGNOFF)

    def test_availability_confirmation_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_AVAILABILITY_CONFIRMATION)

    def test_invented_sla_forbidden(self) -> None:
        assert self.policy.is_forbidden(TOPIC_INVENTED_SLA)


# ── Unknown goal fallback ─────────────────────────────────────────────────────


class TestUnknownGoalFallback:
    def test_unknown_goal_returns_policy(self) -> None:
        policy = ResponseContentPolicy.for_goal("UNKNOWN_GOAL_XYZ")
        assert isinstance(policy, ContentPolicy)

    def test_unknown_goal_acknowledgement_allowed(self) -> None:
        policy = ResponseContentPolicy.for_goal("UNKNOWN_GOAL_XYZ")
        assert policy.is_allowed(TOPIC_ACKNOWLEDGEMENT)

    def test_unknown_goal_fake_links_forbidden(self) -> None:
        policy = ResponseContentPolicy.for_goal("UNKNOWN_GOAL_XYZ")
        assert policy.is_forbidden(TOPIC_FAKE_LINKS)

    def test_unknown_goal_availability_confirmation_forbidden(self) -> None:
        policy = ResponseContentPolicy.for_goal("UNKNOWN_GOAL_XYZ")
        assert policy.is_forbidden(TOPIC_AVAILABILITY_CONFIRMATION)

    def test_unknown_goal_notes_mention_unknown(self) -> None:
        policy = ResponseContentPolicy.for_goal("UNKNOWN_GOAL_XYZ")
        assert "unknown" in policy.policy_notes.lower() or "Unknown" in policy.policy_notes
