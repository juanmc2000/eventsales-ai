"""Tests for RESP-013 — Draft Prompt V5 Using Response Sections.

Validates:
- V5 is the active draft prompt; V4 is archived
- V5 temperature is 0.4
- V5 optional variables include allowed_sections_line and forbidden_topics_line
- _build_allowed_sections_line produces expected output from a section_plan
- _build_forbidden_topics_line produces expected output from a section_plan
- _build_draft_input_payload includes both new lines
- Empty strings returned when section_plan is absent
"""

from __future__ import annotations

import uuid
from dataclasses import replace

import pytest

from app.modules.ai.constants import (
    PROMPT_KEY_DRAFT_RESPONSE,
    VERSION_STATUS_ACTIVE,
    VERSION_STATUS_ARCHIVED,
)
from app.modules.ai.prompt_registry import PromptRegistry, _ALL_DEFINITIONS
from app.modules.ai.schemas import DraftContext
from app.modules.ai.service import (
    _build_allowed_sections_line,
    _build_draft_input_payload,
    _build_forbidden_topics_line,
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
        restaurant_name="The Grand Ballroom",
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


_SAMPLE_SECTION_PLAN = {
    "response_goal": "CONFIRM_AVAILABLE",
    "allowed_sections": ["opening", "availability_confirmation", "minimum_spend", "signoff"],
    "required_sections": ["opening", "availability_confirmation", "signoff"],
    "omitted_sections": ["exact_timing", "menu_discussion", "invented_questions", "invented_sla"],
    "section_reasoning": {
        "exact_timing": "Time was not confirmed by the venue — state only as a preference to discuss.",
        "menu_discussion": "First response must not open menu negotiation.",
        "invented_questions": "No clarification questions were provided — ask none.",
        "invented_sla": "No SLA has been committed — do not invent one.",
    },
}


# ── Registry: V5 archived (replaced by V6), V4 archived ───────────────────────


def _get_v5():
    """Return V5 directly from the full definitions list (archived since RESP-018)."""
    return next(
        (d for d in _ALL_DEFINITIONS if d.key == PROMPT_KEY_DRAFT_RESPONSE and d.version == 5),
        None,
    )


class TestDraftPromptV5Registry:
    def setup_method(self) -> None:
        self.registry = PromptRegistry()

    def test_v5_exists_as_historical_record(self) -> None:
        v5 = _get_v5()
        assert v5 is not None

    def test_v5_is_archived_since_resp018(self) -> None:
        # V5 was archived in RESP-018 — replaced by V6 (approved copy blocks)
        v5 = _get_v5()
        assert v5.status == VERSION_STATUS_ARCHIVED

    def test_v4_is_archived(self) -> None:
        all_defns = self.registry.all_definitions()
        v4 = next(
            (d for d in all_defns if d.key == PROMPT_KEY_DRAFT_RESPONSE and d.version == 4),
            None,
        )
        assert v4 is not None, "V4 definition should still exist as historical record"
        assert v4.status == VERSION_STATUS_ARCHIVED

    def test_v5_temperature_is_0_4(self) -> None:
        v5 = _get_v5()
        assert v5.temperature == 0.4

    def test_v5_allowed_sections_line_is_optional_variable(self) -> None:
        v5 = _get_v5()
        assert "allowed_sections_line" in v5.optional_variables

    def test_v5_forbidden_topics_line_is_optional_variable(self) -> None:
        v5 = _get_v5()
        assert "forbidden_topics_line" in v5.optional_variables

    def test_v5_response_goal_is_required_variable(self) -> None:
        v5 = _get_v5()
        assert "response_goal" in v5.required_variables

    def test_v5_output_schema_version_is_5(self) -> None:
        v5 = _get_v5()
        assert v5.output_schema_version == "5.0"

    def test_v5_system_template_references_allowed_sections_line(self) -> None:
        v5 = _get_v5()
        assert "{allowed_sections_line}" in v5.system_template

    def test_v5_system_template_references_forbidden_topics_line(self) -> None:
        v5 = _get_v5()
        assert "{forbidden_topics_line}" in v5.system_template


# ── _build_allowed_sections_line ──────────────────────────────────────────────


class TestBuildAllowedSectionsLine:
    def test_returns_empty_string_when_no_section_plan(self) -> None:
        ctx = _base_context(section_plan=None)
        assert _build_allowed_sections_line(ctx) == ""

    def test_returns_empty_string_when_allowed_sections_empty(self) -> None:
        ctx = _base_context(section_plan={"allowed_sections": [], "required_sections": []})
        assert _build_allowed_sections_line(ctx) == ""

    def test_lists_allowed_sections(self) -> None:
        ctx = _base_context(section_plan=_SAMPLE_SECTION_PLAN)
        result = _build_allowed_sections_line(ctx)
        assert "opening" in result
        assert "availability_confirmation" in result
        assert "signoff" in result

    def test_marks_required_sections(self) -> None:
        ctx = _base_context(section_plan=_SAMPLE_SECTION_PLAN)
        result = _build_allowed_sections_line(ctx)
        assert "opening" in result
        # Required sections should be marked
        assert "(REQUIRED)" in result

    def test_optional_sections_not_marked_required(self) -> None:
        ctx = _base_context(section_plan=_SAMPLE_SECTION_PLAN)
        result = _build_allowed_sections_line(ctx)
        # minimum_spend is allowed but not required in the sample plan
        lines = result.splitlines()
        spend_line = next((l for l in lines if "minimum_spend" in l), None)
        assert spend_line is not None
        assert "(REQUIRED)" not in spend_line

    def test_includes_do_not_write_instruction(self) -> None:
        ctx = _base_context(section_plan=_SAMPLE_SECTION_PLAN)
        result = _build_allowed_sections_line(ctx)
        assert "Do NOT write any other section" in result

    def test_result_starts_with_header(self) -> None:
        ctx = _base_context(section_plan=_SAMPLE_SECTION_PLAN)
        result = _build_allowed_sections_line(ctx)
        assert result.startswith("RESPONSE SECTIONS")


# ── _build_forbidden_topics_line ──────────────────────────────────────────────


class TestBuildForbiddenTopicsLine:
    def test_returns_empty_string_when_no_section_plan(self) -> None:
        ctx = _base_context(section_plan=None)
        assert _build_forbidden_topics_line(ctx) == ""

    def test_returns_empty_string_when_omitted_sections_empty(self) -> None:
        ctx = _base_context(section_plan={"omitted_sections": [], "section_reasoning": {}})
        assert _build_forbidden_topics_line(ctx) == ""

    def test_lists_forbidden_sections(self) -> None:
        ctx = _base_context(section_plan=_SAMPLE_SECTION_PLAN)
        result = _build_forbidden_topics_line(ctx)
        assert "exact_timing" in result
        assert "menu_discussion" in result
        assert "invented_questions" in result
        assert "invented_sla" in result

    def test_includes_reasoning_when_present(self) -> None:
        ctx = _base_context(section_plan=_SAMPLE_SECTION_PLAN)
        result = _build_forbidden_topics_line(ctx)
        assert "Time was not confirmed" in result
        assert "menu negotiation" in result

    def test_result_starts_with_header(self) -> None:
        ctx = _base_context(section_plan=_SAMPLE_SECTION_PLAN)
        result = _build_forbidden_topics_line(ctx)
        assert result.startswith("FORBIDDEN SECTIONS")


# ── _build_draft_input_payload ────────────────────────────────────────────────


class TestDraftInputPayloadV5:
    def test_payload_includes_allowed_sections_line(self) -> None:
        ctx = _base_context(section_plan=_SAMPLE_SECTION_PLAN)
        payload = _build_draft_input_payload(ctx)
        assert "allowed_sections_line" in payload

    def test_payload_includes_forbidden_topics_line(self) -> None:
        ctx = _base_context(section_plan=_SAMPLE_SECTION_PLAN)
        payload = _build_draft_input_payload(ctx)
        assert "forbidden_topics_line" in payload

    def test_allowed_sections_line_non_empty_when_plan_present(self) -> None:
        ctx = _base_context(section_plan=_SAMPLE_SECTION_PLAN)
        payload = _build_draft_input_payload(ctx)
        assert payload["allowed_sections_line"] != ""
        assert "opening" in payload["allowed_sections_line"]

    def test_forbidden_topics_line_non_empty_when_plan_present(self) -> None:
        ctx = _base_context(section_plan=_SAMPLE_SECTION_PLAN)
        payload = _build_draft_input_payload(ctx)
        assert payload["forbidden_topics_line"] != ""
        assert "exact_timing" in payload["forbidden_topics_line"]

    def test_allowed_sections_line_empty_when_no_plan(self) -> None:
        ctx = _base_context(section_plan=None)
        payload = _build_draft_input_payload(ctx)
        assert payload["allowed_sections_line"] == ""

    def test_forbidden_topics_line_empty_when_no_plan(self) -> None:
        ctx = _base_context(section_plan=None)
        payload = _build_draft_input_payload(ctx)
        assert payload["forbidden_topics_line"] == ""

    def test_payload_still_includes_existing_required_keys(self) -> None:
        ctx = _base_context()
        payload = _build_draft_input_payload(ctx)
        for key in (
            "persona_name",
            "restaurant_name",
            "response_goal",
            "guest_first_name",
            "guest_last_name",
        ):
            assert key in payload
