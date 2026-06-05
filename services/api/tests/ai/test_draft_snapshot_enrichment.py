"""Tests for draft generation enrichment from processing snapshot (AI-011)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.modules.ai.schemas import DraftContext
from app.modules.ai.service import (
    _build_availability_line,
    _build_missing_questions_line,
    _build_spend_line,
    _enrich_context_from_snapshot,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _base_context(**kwargs) -> DraftContext:
    defaults = dict(
        enquiry_id=uuid.uuid4(),
        guest_first_name="Alice",
        guest_last_name="Smith",
        event_type="birthday",
        event_date="2026-12-25",
        party_size=20,
        guest_message="We'd love a private room.",
        restaurant_name="The Grand Ballroom",
        restaurant_description=None,
        persona_name="Eleanor",
        persona_tone="warm and formal",
        persona_style="concise",
        persona_system_prompt="You are Eleanor.",
        recommended_minimum_spend=None,
    )
    defaults.update(kwargs)
    return DraftContext(**defaults)


def _make_snapshot(**kwargs) -> MagicMock:
    snap = MagicMock()
    snap.availability_result_json = kwargs.get("availability_result_json")
    snap.pricing_result_json = kwargs.get("pricing_result_json")
    snap.room_suitability_json = kwargs.get("room_suitability_json")
    snap.missing_fields_json = kwargs.get("missing_fields_json")
    snap.recommended_action = kwargs.get("recommended_action")
    return snap


# ── _enrich_context_from_snapshot ─────────────────────────────────────────────

class TestEnrichContextFromSnapshot:
    def test_availability_status_set(self) -> None:
        ctx = _base_context()
        snap = _make_snapshot(availability_result_json={"status": "available", "date": "2026-12-25", "meal_period": "dinner"})
        result = _enrich_context_from_snapshot(ctx, snap)
        assert result.availability_status == "available"
        assert result.availability_date == "2026-12-25"
        assert result.availability_meal_period == "dinner"

    def test_confirmed_spend_set_from_pricing(self) -> None:
        ctx = _base_context()
        snap = _make_snapshot(pricing_result_json={"minimum_spend": 1500.0, "explanation": "Weekend dinner"})
        result = _enrich_context_from_snapshot(ctx, snap)
        assert result.confirmed_minimum_spend == 1500.0
        assert result.pricing_explanation == "Weekend dinner"

    def test_room_name_updated_from_suitability(self) -> None:
        ctx = _base_context(room_name="Old Room")
        snap = _make_snapshot(room_suitability_json={"matched": True, "room_name": "The Grand Ballroom"})
        result = _enrich_context_from_snapshot(ctx, snap)
        assert result.room_name == "The Grand Ballroom"

    def test_room_name_preserved_when_suitability_not_matched(self) -> None:
        ctx = _base_context(room_name="Original Room")
        snap = _make_snapshot(room_suitability_json={"matched": False})
        result = _enrich_context_from_snapshot(ctx, snap)
        assert result.room_name == "Original Room"

    def test_missing_questions_set(self) -> None:
        ctx = _base_context()
        snap = _make_snapshot(missing_fields_json=["event_date", "guest_count"])
        result = _enrich_context_from_snapshot(ctx, snap)
        assert result.missing_questions == ["event_date", "guest_count"]

    def test_recommended_action_set(self) -> None:
        ctx = _base_context()
        snap = _make_snapshot(recommended_action="send_availability_confirmation")
        result = _enrich_context_from_snapshot(ctx, snap)
        assert result.recommended_action == "send_availability_confirmation"

    def test_original_context_not_mutated(self) -> None:
        ctx = _base_context()
        original_room_name = ctx.room_name
        snap = _make_snapshot(room_suitability_json={"matched": True, "room_name": "New Room"})
        _enrich_context_from_snapshot(ctx, snap)
        assert ctx.room_name == original_room_name  # original unchanged

    def test_null_snapshot_fields_do_not_override(self) -> None:
        ctx = _base_context(room_name="Existing Room")
        snap = _make_snapshot()  # all fields None
        result = _enrich_context_from_snapshot(ctx, snap)
        assert result.room_name == "Existing Room"
        assert result.availability_status is None
        assert result.confirmed_minimum_spend is None


# ── _build_availability_line ───────────────────────────────────────────────────

class TestBuildAvailabilityLine:
    def test_available_status_shows_date(self) -> None:
        ctx = _base_context(
            availability_status="available",
            availability_date="2026-12-25",
            availability_meal_period="dinner",
        )
        line = _build_availability_line(ctx)
        assert "available" in line.lower()
        assert "2026-12-25" in line

    def test_booked_status_says_not_available(self) -> None:
        ctx = _base_context(
            availability_status="booked",
            availability_date="2026-12-25",
            availability_meal_period="dinner",
        )
        line = _build_availability_line(ctx)
        assert "not available" in line.lower()

    def test_unknown_status_produces_not_checked_contract(self) -> None:
        # "unknown" DB status → NOT_CHECKED contract (cannot confirm availability)
        ctx = _base_context(availability_status="unknown")
        line = _build_availability_line(ctx)
        assert "NOT_CHECKED" in line

    def test_no_availability_produces_not_checked_contract(self) -> None:
        # No availability data → NOT_CHECKED contract (LLM must not assume available)
        ctx = _base_context()
        line = _build_availability_line(ctx)
        assert "NOT_CHECKED" in line


# ── _build_spend_line ─────────────────────────────────────────────────────────

class TestBuildSpendLine:
    def test_confirmed_spend_used_when_present(self) -> None:
        ctx = _base_context(confirmed_minimum_spend=2000.0)
        line = _build_spend_line(ctx)
        assert "2,000" in line or "2000" in line

    def test_fallback_to_recommended_spend(self) -> None:
        ctx = _base_context(recommended_minimum_spend=1500.0)
        line = _build_spend_line(ctx)
        assert "1,500" in line or "1500" in line

    def test_confirmed_takes_priority_over_recommended(self) -> None:
        ctx = _base_context(confirmed_minimum_spend=2000.0, recommended_minimum_spend=1000.0)
        line = _build_spend_line(ctx)
        assert "2,000" in line or "2000" in line

    def test_no_spend_returns_empty(self) -> None:
        ctx = _base_context()
        assert _build_spend_line(ctx) == ""


# ── _build_missing_questions_line ─────────────────────────────────────────────

class TestBuildMissingQuestionsLine:
    def test_missing_fields_formatted(self) -> None:
        ctx = _base_context(missing_questions=["event_date", "guest_count"])
        line = _build_missing_questions_line(ctx)
        assert "event_date" in line
        assert "guest_count" in line

    def test_no_missing_fields_returns_empty(self) -> None:
        ctx = _base_context()
        assert _build_missing_questions_line(ctx) == ""

    def test_empty_list_returns_empty(self) -> None:
        ctx = _base_context(missing_questions=[])
        assert _build_missing_questions_line(ctx) == ""


# ── DraftContext new fields ────────────────────────────────────────────────────

class TestDraftContextNewFields:
    def test_new_fields_default_to_none(self) -> None:
        ctx = _base_context()
        assert ctx.availability_status is None
        assert ctx.availability_date is None
        assert ctx.availability_meal_period is None
        assert ctx.confirmed_minimum_spend is None
        assert ctx.pricing_explanation is None
        assert ctx.missing_questions is None
        assert ctx.recommended_action is None

    def test_v2_prompt_is_active(self) -> None:
        from app.modules.ai.prompt_registry import PromptRegistry
        from app.modules.ai.constants import PROMPT_KEY_DRAFT_RESPONSE

        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert defn.version >= 2

    def test_v2_prompt_prohibits_invention(self) -> None:
        from app.modules.ai.prompt_registry import PromptRegistry
        from app.modules.ai.constants import PROMPT_KEY_DRAFT_RESPONSE

        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert "invent" in defn.system_template.lower() or "NOT invent" in defn.system_template

    def test_v2_prompt_has_availability_variable(self) -> None:
        from app.modules.ai.prompt_registry import PromptRegistry
        from app.modules.ai.constants import PROMPT_KEY_DRAFT_RESPONSE

        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert "availability_line" in defn.optional_variables

    def test_v2_prompt_has_missing_questions_variable(self) -> None:
        from app.modules.ai.prompt_registry import PromptRegistry
        from app.modules.ai.constants import PROMPT_KEY_DRAFT_RESPONSE

        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        # V3+ uses clarification_questions_line; V2 used missing_questions_line
        assert (
            "missing_questions_line" in defn.optional_variables
            or "clarification_questions_line" in defn.optional_variables
        )
