"""Tests for RESP-003 — Draft Prompt V3 Response Goals.

Validates:
- Draft prompt V3 is active and contains response_goal as required variable
- response_goal appears in the rendered system prompt
- Per-goal system prompt instructions are present
- audience_type_line and clarification_questions_line are optional variables
- _build_clarification_questions_line formats questions correctly
- _enrich_context_from_response_plan populates response_goal, audience_type,
  clarification_questions from the stored EnquiryResponsePlan
- _build_draft_input_payload includes response_goal and new optional lines
- Fallback default for response_goal is READY_TO_CONFIRM_AVAILABILITY
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from unittest.mock import MagicMock, patch

import pytest

from app.modules.ai.constants import PROMPT_KEY_DRAFT_RESPONSE, VERSION_STATUS_ACTIVE
from app.modules.ai.prompt_registry import PromptRegistry
from app.modules.ai.prompt_renderer import PromptRenderer
from app.modules.ai.schemas import DraftContext
from app.modules.ai.service import (
    _build_clarification_questions_line,
    _build_draft_input_payload,
    _enrich_context_from_response_plan,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _base_context(**overrides) -> DraftContext:
    ctx = DraftContext(
        enquiry_id=uuid.uuid4(),
        guest_first_name="Alice",
        guest_last_name="Smith",
        event_type="dinner",
        event_date=None,
        party_size=None,
        guest_message=None,
        restaurant_name="The Grand",
        restaurant_description=None,
        persona_name="Eleanor",
        persona_tone="warm and formal",
        persona_style="concise",
        persona_system_prompt="You are a hospitality professional.",
        recommended_minimum_spend=None,
    )
    for k, v in overrides.items():
        ctx = replace(ctx, **{k: v})
    return ctx


def _base_payload(**overrides) -> dict:
    base = {
        "persona_system_prompt": "You are a hospitality professional.",
        "persona_name": "Eleanor",
        "restaurant_name": "The Grand",
        "persona_tone": "warm and formal",
        "persona_style": "concise",
        "guest_first_name": "Alice",
        "guest_last_name": "Smith",
        "response_goal": "READY_TO_CONFIRM_AVAILABILITY",
    }
    base.update(overrides)
    return base


# ── Prompt registry — V3 is active ────────────────────────────────────────────


class TestDraftPromptV3Registry:
    def setup_method(self) -> None:
        self.registry = PromptRegistry()

    def test_active_draft_prompt_is_v4(self) -> None:
        defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert defn.version == 4
        assert defn.status == VERSION_STATUS_ACTIVE

    def test_response_goal_is_required_variable(self) -> None:
        defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert "response_goal" in defn.required_variables

    def test_audience_type_line_is_optional_variable(self) -> None:
        defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert "audience_type_line" in defn.optional_variables

    def test_clarification_questions_line_is_optional_variable(self) -> None:
        defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert "clarification_questions_line" in defn.optional_variables

    def test_output_schema_version_is_4(self) -> None:
        defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert defn.output_schema_version == "4.0"


# ── Prompt rendering — response_goal is in system prompt ──────────────────────


class TestDraftPromptV3Rendering:
    def setup_method(self) -> None:
        self.registry = PromptRegistry()
        self.renderer = PromptRenderer()
        self.defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)

    def _render_system(self, **overrides) -> str:
        payload = _base_payload(**overrides)
        return self.renderer.render_system(self.defn, payload)

    def test_response_goal_appears_in_system_prompt(self) -> None:
        rendered = self._render_system(response_goal="READY_TO_CONFIRM_AVAILABILITY")
        assert "READY_TO_CONFIRM_AVAILABILITY" in rendered

    def test_ready_goal_instruction_in_system_prompt(self) -> None:
        rendered = self._render_system(response_goal="READY_TO_CONFIRM_AVAILABILITY")
        assert "availability" in rendered.lower()

    def test_request_missing_info_instruction_in_system_prompt(self) -> None:
        rendered = self._render_system(response_goal="REQUEST_MISSING_INFORMATION")
        assert "REQUEST_MISSING_INFORMATION" in rendered

    def test_request_date_confirmation_instruction_in_system_prompt(self) -> None:
        rendered = self._render_system(response_goal="REQUEST_DATE_CONFIRMATION")
        assert "REQUEST_DATE_CONFIRMATION" in rendered

    def test_request_webform_instruction_in_system_prompt(self) -> None:
        rendered = self._render_system(response_goal="REQUEST_WEBFORM")
        assert "REQUEST_WEBFORM" in rendered

    def test_escalate_instruction_in_system_prompt(self) -> None:
        rendered = self._render_system(response_goal="ESCALATE_TO_HUMAN")
        assert "ESCALATE_TO_HUMAN" in rendered

    def test_persona_name_in_system_prompt(self) -> None:
        rendered = self._render_system()
        assert "Eleanor" in rendered

    def test_restaurant_name_in_system_prompt(self) -> None:
        rendered = self._render_system()
        assert "The Grand" in rendered

    def test_user_prompt_renders_without_optional_lines(self) -> None:
        payload = _base_payload()
        rendered = self.renderer.render_user(self.defn, payload)
        assert "Alice" in rendered
        assert "Smith" in rendered

    def test_audience_type_line_rendered_when_provided(self) -> None:
        payload = _base_payload(audience_type_line="Audience type: corporate\n")
        rendered = self.renderer.render_user(self.defn, payload)
        assert "corporate" in rendered

    def test_clarification_questions_line_rendered_when_provided(self) -> None:
        payload = _base_payload(
            clarification_questions_line="Clarification question to ask: What date?\n"
        )
        rendered = self.renderer.render_user(self.defn, payload)
        assert "What date?" in rendered


# ── _build_clarification_questions_line ───────────────────────────────────────


class TestBuildClarificationQuestionsLine:
    def test_returns_empty_when_no_questions(self) -> None:
        ctx = _base_context()
        assert _build_clarification_questions_line(ctx) == ""

    def test_returns_empty_when_empty_list(self) -> None:
        ctx = _base_context(clarification_questions=[])
        assert _build_clarification_questions_line(ctx) == ""

    def test_single_question_uses_singular_form(self) -> None:
        ctx = _base_context(clarification_questions=["What date works for you?"])
        result = _build_clarification_questions_line(ctx)
        assert "What date works for you?" in result
        assert "Clarification question to ask:" in result

    def test_multiple_questions_uses_plural_form(self) -> None:
        ctx = _base_context(clarification_questions=["What date?", "How many guests?"])
        result = _build_clarification_questions_line(ctx)
        assert "Clarification questions to ask" in result
        assert "1." in result
        assert "2." in result
        assert "What date?" in result
        assert "How many guests?" in result

    def test_three_questions_are_numbered(self) -> None:
        ctx = _base_context(clarification_questions=["Q1", "Q2", "Q3"])
        result = _build_clarification_questions_line(ctx)
        assert "1." in result
        assert "2." in result
        assert "3." in result


# ── _build_draft_input_payload includes response_goal ─────────────────────────


class TestBuildDraftInputPayloadResponseGoal:
    def test_response_goal_in_payload_when_set(self) -> None:
        ctx = _base_context(response_goal="REQUEST_MISSING_INFORMATION")
        payload = _build_draft_input_payload(ctx)
        assert payload["response_goal"] == "REQUEST_MISSING_INFORMATION"

    def test_response_goal_defaults_to_ready_when_none(self) -> None:
        ctx = _base_context(response_goal=None)
        payload = _build_draft_input_payload(ctx)
        assert payload["response_goal"] == "READY_TO_CONFIRM_AVAILABILITY"

    def test_audience_type_line_present_in_payload(self) -> None:
        ctx = _base_context(audience_type="corporate")
        payload = _build_draft_input_payload(ctx)
        assert "audience_type_line" in payload
        assert "corporate" in payload["audience_type_line"]

    def test_audience_type_line_empty_when_not_set(self) -> None:
        ctx = _base_context(audience_type=None)
        payload = _build_draft_input_payload(ctx)
        assert payload["audience_type_line"] == ""

    def test_clarification_questions_line_present_in_payload(self) -> None:
        ctx = _base_context(clarification_questions=["When is the event?"])
        payload = _build_draft_input_payload(ctx)
        assert "clarification_questions_line" in payload
        assert "When is the event?" in payload["clarification_questions_line"]

    def test_clarification_questions_line_empty_when_not_set(self) -> None:
        ctx = _base_context(clarification_questions=None)
        payload = _build_draft_input_payload(ctx)
        assert payload["clarification_questions_line"] == ""


# ── _enrich_context_from_response_plan ────────────────────────────────────────


class TestEnrichContextFromResponsePlan:
    def _mock_plan(
        self,
        response_goal: str = "READY_TO_CONFIRM_AVAILABILITY",
        clarification_questions: list | None = None,
        customer_type: str = "corporate",
    ) -> MagicMock:
        plan = MagicMock()
        plan.response_goal = response_goal
        plan.clarification_questions = clarification_questions or []
        plan.customer_type_context = {"final_customer_type": customer_type}
        return plan

    def test_response_goal_populated_from_plan(self) -> None:
        db = MagicMock()
        plan = self._mock_plan(response_goal="REQUEST_DATE_CONFIRMATION")

        with patch(
            "app.modules.enquiries.repository.ResponsePlanRepository.get_latest",
            return_value=plan,
        ):
            ctx = _enrich_context_from_response_plan(db, uuid.uuid4(), _base_context())

        assert ctx.response_goal == "REQUEST_DATE_CONFIRMATION"

    def test_clarification_questions_populated_from_plan(self) -> None:
        db = MagicMock()
        plan = self._mock_plan(clarification_questions=["What date?", "How many guests?"])

        with patch(
            "app.modules.enquiries.repository.ResponsePlanRepository.get_latest",
            return_value=plan,
        ):
            ctx = _enrich_context_from_response_plan(db, uuid.uuid4(), _base_context())

        assert ctx.clarification_questions == ["What date?", "How many guests?"]

    def test_audience_type_populated_from_customer_type_context(self) -> None:
        db = MagicMock()
        plan = self._mock_plan(customer_type="agency")

        with patch(
            "app.modules.enquiries.repository.ResponsePlanRepository.get_latest",
            return_value=plan,
        ):
            ctx = _enrich_context_from_response_plan(db, uuid.uuid4(), _base_context())

        assert ctx.audience_type == "agency"

    def test_returns_original_context_when_no_plan(self) -> None:
        db = MagicMock()
        original = _base_context(response_goal="ESCALATE_TO_HUMAN")

        with patch(
            "app.modules.enquiries.repository.ResponsePlanRepository.get_latest",
            return_value=None,
        ):
            ctx = _enrich_context_from_response_plan(db, uuid.uuid4(), original)

        assert ctx.response_goal == "ESCALATE_TO_HUMAN"

    def test_returns_original_context_on_exception(self) -> None:
        db = MagicMock()
        original = _base_context()

        with patch(
            "app.modules.enquiries.repository.ResponsePlanRepository.get_latest",
            side_effect=RuntimeError("DB error"),
        ):
            ctx = _enrich_context_from_response_plan(db, uuid.uuid4(), original)

        assert ctx is original

    def test_existing_audience_type_preserved_when_plan_has_none(self) -> None:
        db = MagicMock()
        plan = MagicMock()
        plan.response_goal = "READY_TO_CONFIRM_AVAILABILITY"
        plan.clarification_questions = []
        plan.customer_type_context = None  # no customer type context

        original = _base_context(audience_type="social")

        with patch(
            "app.modules.enquiries.repository.ResponsePlanRepository.get_latest",
            return_value=plan,
        ):
            ctx = _enrich_context_from_response_plan(db, uuid.uuid4(), original)

        assert ctx.audience_type == "social"


# ── DraftContext new fields ────────────────────────────────────────────────────


class TestDraftContextNewFields:
    def test_response_goal_defaults_to_none(self) -> None:
        ctx = _base_context()
        assert ctx.response_goal is None

    def test_audience_type_defaults_to_none(self) -> None:
        ctx = _base_context()
        assert ctx.audience_type is None

    def test_clarification_questions_defaults_to_none(self) -> None:
        ctx = _base_context()
        assert ctx.clarification_questions is None

    def test_response_goal_can_be_set(self) -> None:
        ctx = _base_context(response_goal="REQUEST_WEBFORM")
        assert ctx.response_goal == "REQUEST_WEBFORM"

    def test_all_goals_accepted(self) -> None:
        goals = [
            "READY_TO_CONFIRM_AVAILABILITY",
            "REQUEST_MISSING_INFORMATION",
            "REQUEST_DATE_CONFIRMATION",
            "REQUEST_WEBFORM",
            "ESCALATE_TO_HUMAN",
        ]
        for goal in goals:
            ctx = _base_context(response_goal=goal)
            assert ctx.response_goal == goal
