"""Tests for RESP-018 — Draft Prompt V6 with copy blocks and section constraints.

Validates:
- V5 is archived; V6 is the active draft_response version
- V6 has approved_copy_blocks_line as an optional variable
- V6 temperature is 0.4 or lower
- _build_approved_copy_blocks_line produces correct blocks per goal
- approved_copy_blocks_line present in _build_draft_input_payload
- Copy blocks are verbatim from FirstResponseCopyLibrary (no paraphrasing)
- Signoff always present regardless of goal
- Spend block appears only when spend is set and goal is CONFIRM_AVAILABLE
"""

from __future__ import annotations

import uuid
from dataclasses import replace

import pytest

from app.modules.ai.constants import PROMPT_KEY_DRAFT_RESPONSE, VERSION_STATUS_ARCHIVED
from app.modules.ai.first_response_copy_library import FirstResponseCopyLibrary
from app.modules.ai.prompt_registry import PromptRegistry, _ALL_DEFINITIONS
from app.modules.ai.schemas import DraftContext
from app.modules.ai.service import (
    _build_approved_copy_blocks_line,
    _build_draft_input_payload,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _base_context(**overrides) -> DraftContext:
    ctx = DraftContext(
        enquiry_id=uuid.uuid4(),
        guest_first_name="Alice",
        guest_last_name="Smith",
        event_type="birthday",
        event_date="2026-06-12",
        party_size=8,
        guest_message=None,
        restaurant_name="The Grand",
        restaurant_description=None,
        persona_name="Eleanor",
        persona_tone="warm and celebratory",
        persona_style="concise",
        persona_system_prompt="You are Eleanor.",
        recommended_minimum_spend=None,
        response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
        audience_type="social",
    )
    for k, v in overrides.items():
        ctx = replace(ctx, **{k: v})
    return ctx


# ── V5 archived, V6 active ─────────────────────────────────────────────────────


class TestV5ArchivedV6Active:
    def test_registry_returns_v6_as_active(self) -> None:
        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert defn.version == 6

    def test_v5_is_archived_in_all_definitions(self) -> None:
        v5 = next(
            (d for d in _ALL_DEFINITIONS if d.key == PROMPT_KEY_DRAFT_RESPONSE and d.version == 5),
            None,
        )
        assert v5 is not None
        assert v5.status == VERSION_STATUS_ARCHIVED

    def test_v5_change_notes_mention_resp018(self) -> None:
        v5 = next(
            (d for d in _ALL_DEFINITIONS if d.key == PROMPT_KEY_DRAFT_RESPONSE and d.version == 5),
            None,
        )
        assert v5 is not None
        assert "RESP-018" in v5.change_notes


# ── V6 definition ─────────────────────────────────────────────────────────────


class TestV6Definition:
    def _v6(self):
        return PromptRegistry().get(PROMPT_KEY_DRAFT_RESPONSE)

    def test_v6_temperature_at_most_0_4(self) -> None:
        assert self._v6().temperature <= 0.4

    def test_v6_has_approved_copy_blocks_optional_variable(self) -> None:
        assert "approved_copy_blocks_line" in self._v6().optional_variables

    def test_v6_system_template_references_approved_copy_blocks(self) -> None:
        assert "{approved_copy_blocks_line}" in self._v6().system_template

    def test_v6_schema_version_is_6(self) -> None:
        assert self._v6().output_schema_version == "6.0"

    def test_v6_mandatory_rules_forbid_menu_and_special_touches(self) -> None:
        tmpl = self._v6().system_template
        assert "menu" in tmpl.lower()
        assert "special touches" in tmpl.lower() or "special_touches" in tmpl.lower()


# ── _build_approved_copy_blocks_line ─────────────────────────────────────────


class TestBuildApprovedCopyBlocksLine:
    def test_confirm_available_contains_opening_block(self) -> None:
        ctx = _base_context(
            response_goal="CONFIRM_AVAILABLE",
            availability_meal_period="dinner",
            availability_date="2026-06-12",
        )
        line = _build_approved_copy_blocks_line(ctx)
        expected = FirstResponseCopyLibrary.render(
            "availability_confirmed",
            {"meal_period": "dinner", "event_date": "2026-06-12"},
        )
        assert expected in line

    def test_confirm_available_contains_confirm_available_next_step(self) -> None:
        # RESP-030: CONFIRM_AVAILABLE uses confirm_available_next_step block
        ctx = _base_context(response_goal="CONFIRM_AVAILABLE")
        line = _build_approved_copy_blocks_line(ctx)
        expected = FirstResponseCopyLibrary.render("confirm_available_next_step")
        assert expected in line

    def test_confirm_available_contains_spend_block_when_spend_set(self) -> None:
        ctx = _base_context(
            response_goal="CONFIRM_AVAILABLE",
            recommended_minimum_spend=2500.0,
        )
        line = _build_approved_copy_blocks_line(ctx)
        expected = FirstResponseCopyLibrary.render(
            "minimum_spend", {"spend_amount": "£2,500"}
        )
        assert expected in line

    def test_confirm_available_no_spend_block_when_no_spend(self) -> None:
        ctx = _base_context(
            response_goal="CONFIRM_AVAILABLE",
            recommended_minimum_spend=None,
        )
        line = _build_approved_copy_blocks_line(ctx)
        assert "minimum_spend" not in line
        assert "mandatory minimum spend" not in line

    def test_respond_unavailable_contains_unavailable_block(self) -> None:
        ctx = _base_context(
            response_goal="RESPOND_UNAVAILABLE",
            availability_meal_period="dinner",
            availability_date="2026-06-12",
        )
        line = _build_approved_copy_blocks_line(ctx)
        expected = FirstResponseCopyLibrary.render(
            "availability_unavailable",
            {"meal_period": "dinner", "event_date": "2026-06-12"},
        )
        assert expected in line

    def test_respond_unavailable_does_not_contain_booking_next_step(self) -> None:
        ctx = _base_context(response_goal="RESPOND_UNAVAILABLE")
        line = _build_approved_copy_blocks_line(ctx)
        booking_step = FirstResponseCopyLibrary.render("booking_next_step")
        assert booking_step not in line

    def test_acknowledge_contains_not_checked_block(self) -> None:
        ctx = _base_context(
            response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
            availability_meal_period="dinner",
            availability_date="2026-06-12",
        )
        line = _build_approved_copy_blocks_line(ctx)
        expected = FirstResponseCopyLibrary.render(
            "availability_not_checked",
            {"meal_period": "dinner", "event_date": "2026-06-12"},
        )
        assert expected in line

    def test_acknowledge_contains_check_next_step(self) -> None:
        ctx = _base_context(response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY")
        line = _build_approved_copy_blocks_line(ctx)
        expected = FirstResponseCopyLibrary.render("availability_check_next_step")
        assert expected in line

    def test_request_missing_information_contains_clarification_next_step(self) -> None:
        ctx = _base_context(response_goal="REQUEST_MISSING_INFORMATION")
        line = _build_approved_copy_blocks_line(ctx)
        expected = FirstResponseCopyLibrary.render("clarification_next_step")
        assert expected in line

    def test_signoff_always_present(self) -> None:
        for goal in [
            "CONFIRM_AVAILABLE",
            "RESPOND_UNAVAILABLE",
            "ACKNOWLEDGE_AND_CHECK_AVAILABILITY",
            "REQUEST_MISSING_INFORMATION",
            "REQUEST_DATE_CONFIRMATION",
            "ESCALATE_TO_HUMAN",
        ]:
            ctx = _base_context(response_goal=goal, persona_name="Eleanor")
            line = _build_approved_copy_blocks_line(ctx)
            assert "Eleanor" in line, f"Signoff missing for goal {goal}"

    def test_persona_name_appears_in_signoff(self) -> None:
        ctx = _base_context(response_goal="CONFIRM_AVAILABLE", persona_name="James")
        line = _build_approved_copy_blocks_line(ctx)
        assert "James" in line

    def test_verbatim_instruction_present(self) -> None:
        ctx = _base_context(response_goal="CONFIRM_AVAILABLE")
        line = _build_approved_copy_blocks_line(ctx)
        assert "APPROVED COPY BLOCKS" in line
        assert "verbatim" in line.lower() or "exactly as written" in line.lower()

    def test_fallback_meal_period_used_when_not_set(self) -> None:
        ctx = _base_context(
            response_goal="CONFIRM_AVAILABLE",
            availability_meal_period=None,
            availability_date="2026-06-12",
        )
        line = _build_approved_copy_blocks_line(ctx)
        assert "dinner" in line

    def test_fallback_event_date_used_when_availability_date_not_set(self) -> None:
        ctx = _base_context(
            response_goal="CONFIRM_AVAILABLE",
            availability_date=None,
            event_date="2026-07-20",
        )
        line = _build_approved_copy_blocks_line(ctx)
        assert "2026-07-20" in line


# ── Payload integration ───────────────────────────────────────────────────────


class TestDraftInputPayloadIncludesCopyBlocks:
    def test_payload_contains_approved_copy_blocks_line_key(self) -> None:
        ctx = _base_context()
        payload = _build_draft_input_payload(ctx)
        assert "approved_copy_blocks_line" in payload

    def test_payload_copy_blocks_non_empty_for_confirm_available(self) -> None:
        ctx = _base_context(response_goal="CONFIRM_AVAILABLE")
        payload = _build_draft_input_payload(ctx)
        assert payload["approved_copy_blocks_line"] != ""

    def test_payload_copy_blocks_non_empty_for_respond_unavailable(self) -> None:
        ctx = _base_context(response_goal="RESPOND_UNAVAILABLE")
        payload = _build_draft_input_payload(ctx)
        assert payload["approved_copy_blocks_line"] != ""

    def test_payload_copy_blocks_non_empty_for_acknowledge(self) -> None:
        ctx = _base_context(response_goal="ACKNOWLEDGE_AND_CHECK_AVAILABILITY")
        payload = _build_draft_input_payload(ctx)
        assert payload["approved_copy_blocks_line"] != ""
