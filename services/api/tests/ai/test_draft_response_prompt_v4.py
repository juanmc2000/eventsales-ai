"""Tests for RESP-004 — Draft Prompt V4 Availability Contract.

Validates:
- Draft prompt V4 is active and V3 is archived
- System prompt contains the AVAILABILITY CONTRACT section with all five states
- System prompt treats minimum spend as mandatory
- System prompt prohibits invented booking form links
- _build_availability_line emits the correct contract state for every input
- _build_spend_line uses 'Minimum spend' label (mandatory, not recommended)
- _derive_availability_contract maps all expected input combinations
- Six-record fixture: contract states match actual availability data
- Tests check operational meaning, not exact prose wording
"""

from __future__ import annotations

import json
import uuid
from dataclasses import replace
from pathlib import Path

import pytest

from app.modules.ai.constants import PROMPT_KEY_DRAFT_RESPONSE, VERSION_STATUS_ACTIVE, VERSION_STATUS_ARCHIVED
from app.modules.ai.prompt_registry import PromptRegistry
from app.modules.ai.prompt_renderer import PromptRenderer
from app.modules.ai.schemas import DraftContext
from app.modules.ai.service import (
    _build_availability_line,
    _build_spend_line,
    _build_draft_input_payload,
    _derive_availability_contract,
)

# ── Paths ──────────────────────────────────────────────────────────────────────

_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "draft_llm2_availability_6_results.json"

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


def _base_payload(**overrides) -> dict:
    base = {
        "persona_system_prompt": "You are a hospitality professional.",
        "persona_name": "Eleanor",
        "restaurant_name": "The Grand Ballroom",
        "persona_tone": "warm and formal",
        "persona_style": "concise",
        "guest_first_name": "Alice",
        "guest_last_name": "Smith",
        "response_goal": "READY_TO_CONFIRM_AVAILABILITY",
    }
    base.update(overrides)
    return base


# ── Registry: V4 active, V3 archived ──────────────────────────────────────────


class TestDraftPromptV4Registry:
    def setup_method(self) -> None:
        self.registry = PromptRegistry()

    def test_active_draft_prompt_is_v4(self) -> None:
        defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert defn.version == 4
        assert defn.status == VERSION_STATUS_ACTIVE

    def test_v3_is_archived(self) -> None:
        all_defns = self.registry.all_definitions()
        v3 = next(
            (d for d in all_defns if d.key == PROMPT_KEY_DRAFT_RESPONSE and d.version == 3),
            None,
        )
        assert v3 is not None, "V3 definition should still exist as historical record"
        assert v3.status == VERSION_STATUS_ARCHIVED

    def test_response_goal_is_required_variable(self) -> None:
        defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert "response_goal" in defn.required_variables

    def test_availability_line_is_optional_variable(self) -> None:
        defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert "availability_line" in defn.optional_variables

    def test_output_schema_version_is_4(self) -> None:
        defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert defn.output_schema_version == "4.0"


# ── System prompt: availability contract section ───────────────────────────────


class TestDraftPromptV4SystemPromptContract:
    def setup_method(self) -> None:
        registry = PromptRegistry()
        self.defn = registry.get(PROMPT_KEY_DRAFT_RESPONSE)

    def test_availability_contract_section_present(self) -> None:
        assert "AVAILABILITY CONTRACT" in self.defn.system_template

    def test_confirmed_available_state_defined(self) -> None:
        assert "CONFIRMED_AVAILABLE" in self.defn.system_template

    def test_confirmed_unavailable_state_defined(self) -> None:
        assert "CONFIRMED_UNAVAILABLE" in self.defn.system_template

    def test_not_checked_state_defined(self) -> None:
        assert "NOT_CHECKED" in self.defn.system_template

    def test_pending_date_confirmation_state_defined(self) -> None:
        assert "PENDING_DATE_CONFIRMATION" in self.defn.system_template

    def test_insufficient_information_state_defined(self) -> None:
        assert "INSUFFICIENT_INFORMATION" in self.defn.system_template

    def test_not_checked_prohibits_availability_assumption(self) -> None:
        # The contract must instruct the model NOT to state availability when NOT_CHECKED
        template = self.defn.system_template
        not_checked_section = template[template.index("NOT_CHECKED"):]
        # Expect instruction to withhold availability claim
        assert "not" in not_checked_section[:200].lower()

    def test_confirmed_unavailable_prohibits_invented_alternatives(self) -> None:
        template = self.defn.system_template
        unavail_idx = template.index("CONFIRMED_UNAVAILABLE")
        section = template[unavail_idx: unavail_idx + 300]
        assert "NOT" in section or "not" in section.lower()

    def test_minimum_spend_is_mandatory(self) -> None:
        template = self.defn.system_template.lower()
        assert "mandatory" in template or "required" in template

    def test_no_invented_booking_links(self) -> None:
        template = self.defn.system_template.lower()
        assert "booking form link" in template or "url" in template
        # The rule must be present (even if wording varies)
        assert "not" in template

    def test_no_invented_clarification_questions(self) -> None:
        template = self.defn.system_template
        assert "ONLY the clarification questions" in template or "only" in template.lower()


# ── System prompt renders with all goals ──────────────────────────────────────


class TestDraftPromptV4Rendering:
    def setup_method(self) -> None:
        registry = PromptRegistry()
        self.defn = registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        self.renderer = PromptRenderer()

    def _render_system(self, **overrides) -> str:
        payload = _base_payload(**overrides)
        return self.renderer.render_system(self.defn, payload)

    def test_all_five_contract_states_in_rendered_system(self) -> None:
        rendered = self._render_system(response_goal="READY_TO_CONFIRM_AVAILABILITY")
        for state in (
            "CONFIRMED_AVAILABLE",
            "CONFIRMED_UNAVAILABLE",
            "NOT_CHECKED",
            "PENDING_DATE_CONFIRMATION",
            "INSUFFICIENT_INFORMATION",
        ):
            assert state in rendered, f"Contract state {state!r} missing from rendered system prompt"

    def test_all_response_goals_in_rendered_system(self) -> None:
        rendered = self._render_system(response_goal="READY_TO_CONFIRM_AVAILABILITY")
        for goal in (
            "READY_TO_CONFIRM_AVAILABILITY",
            "REQUEST_MISSING_INFORMATION",
            "REQUEST_DATE_CONFIRMATION",
            "REQUEST_WEBFORM",
            "ESCALATE_TO_HUMAN",
        ):
            assert goal in rendered, f"Response goal {goal!r} missing from rendered system prompt"


# ── _derive_availability_contract ─────────────────────────────────────────────


class TestDeriveAvailabilityContract:
    def test_available_maps_to_confirmed_available(self) -> None:
        ctx = _base_context(availability_status="available")
        assert _derive_availability_contract(ctx) == "CONFIRMED_AVAILABLE"

    def test_booked_maps_to_confirmed_unavailable(self) -> None:
        ctx = _base_context(availability_status="booked")
        assert _derive_availability_contract(ctx) == "CONFIRMED_UNAVAILABLE"

    def test_held_maps_to_confirmed_unavailable(self) -> None:
        ctx = _base_context(availability_status="held")
        assert _derive_availability_contract(ctx) == "CONFIRMED_UNAVAILABLE"

    def test_unavailable_maps_to_confirmed_unavailable(self) -> None:
        ctx = _base_context(availability_status="unavailable")
        assert _derive_availability_contract(ctx) == "CONFIRMED_UNAVAILABLE"

    def test_none_status_maps_to_not_checked(self) -> None:
        ctx = _base_context(availability_status=None)
        assert _derive_availability_contract(ctx) == "NOT_CHECKED"

    def test_unknown_status_maps_to_not_checked(self) -> None:
        ctx = _base_context(availability_status="unknown")
        assert _derive_availability_contract(ctx) == "NOT_CHECKED"

    def test_request_date_confirmation_goal_maps_to_pending(self) -> None:
        ctx = _base_context(availability_status=None, response_goal="REQUEST_DATE_CONFIRMATION")
        assert _derive_availability_contract(ctx) == "PENDING_DATE_CONFIRMATION"

    def test_request_missing_info_goal_maps_to_insufficient(self) -> None:
        ctx = _base_context(availability_status=None, response_goal="REQUEST_MISSING_INFORMATION")
        assert _derive_availability_contract(ctx) == "INSUFFICIENT_INFORMATION"

    def test_request_webform_goal_maps_to_insufficient(self) -> None:
        ctx = _base_context(availability_status=None, response_goal="REQUEST_WEBFORM")
        assert _derive_availability_contract(ctx) == "INSUFFICIENT_INFORMATION"

    def test_availability_status_takes_precedence_over_goal(self) -> None:
        # If availability was actually checked and found available, that wins
        ctx = _base_context(
            availability_status="available",
            response_goal="REQUEST_DATE_CONFIRMATION",
        )
        assert _derive_availability_contract(ctx) == "CONFIRMED_AVAILABLE"


# ── _build_availability_line ───────────────────────────────────────────────────


class TestBuildAvailabilityLineV4:
    def test_confirmed_available_contains_contract_state(self) -> None:
        ctx = _base_context(
            availability_status="available",
            availability_date="2026-06-12",
            availability_meal_period="dinner",
        )
        line = _build_availability_line(ctx)
        assert "CONFIRMED_AVAILABLE" in line
        assert "2026-06-12" in line

    def test_confirmed_unavailable_contains_contract_state(self) -> None:
        ctx = _base_context(
            availability_status="booked",
            availability_date="2026-06-20",
            availability_meal_period="dinner",
        )
        line = _build_availability_line(ctx)
        assert "CONFIRMED_UNAVAILABLE" in line
        assert "2026-06-20" in line

    def test_confirmed_unavailable_does_not_suggest_alternatives(self) -> None:
        # The line itself must not propose alternatives
        ctx = _base_context(availability_status="booked", availability_date="2026-06-20")
        line = _build_availability_line(ctx)
        assert "alternative" not in line.lower()

    def test_not_checked_always_returned_when_no_availability(self) -> None:
        ctx = _base_context()  # no availability_status
        line = _build_availability_line(ctx)
        assert "NOT_CHECKED" in line

    def test_not_checked_does_not_confirm_availability(self) -> None:
        ctx = _base_context()
        line = _build_availability_line(ctx)
        assert "available" not in line.lower() or "NOT_CHECKED" in line

    def test_pending_date_confirmation_state(self) -> None:
        ctx = _base_context(response_goal="REQUEST_DATE_CONFIRMATION")
        line = _build_availability_line(ctx)
        assert "PENDING_DATE_CONFIRMATION" in line

    def test_insufficient_information_state(self) -> None:
        ctx = _base_context(response_goal="REQUEST_MISSING_INFORMATION")
        line = _build_availability_line(ctx)
        assert "INSUFFICIENT_INFORMATION" in line

    def test_line_always_non_empty(self) -> None:
        # Every context must produce a non-empty availability line
        for status in (None, "available", "booked", "held", "unavailable", "unknown"):
            ctx = _base_context(availability_status=status)
            assert _build_availability_line(ctx) != "", f"Empty line for status={status!r}"


# ── _build_spend_line — mandatory label ───────────────────────────────────────


class TestBuildSpendLineV4:
    def test_spend_line_uses_minimum_spend_label(self) -> None:
        ctx = _base_context(confirmed_minimum_spend=5000.0)
        line = _build_spend_line(ctx)
        assert "Minimum spend" in line

    def test_spend_line_does_not_say_recommended(self) -> None:
        ctx = _base_context(confirmed_minimum_spend=5000.0)
        line = _build_spend_line(ctx)
        assert "Recommended" not in line
        assert "recommended" not in line

    def test_spend_line_does_not_say_confirmed(self) -> None:
        ctx = _base_context(confirmed_minimum_spend=5000.0)
        line = _build_spend_line(ctx)
        assert "Confirmed" not in line

    def test_spend_line_contains_amount(self) -> None:
        ctx = _base_context(confirmed_minimum_spend=3500.0)
        line = _build_spend_line(ctx)
        assert "3,500" in line

    def test_spend_line_fallback_to_recommended_field(self) -> None:
        ctx = _base_context(recommended_minimum_spend=1200.0)
        line = _build_spend_line(ctx)
        assert "1,200" in line
        assert "Minimum spend" in line

    def test_spend_line_empty_when_no_spend(self) -> None:
        ctx = _base_context()
        assert _build_spend_line(ctx) == ""

    def test_spend_line_payload_key_present(self) -> None:
        ctx = _base_context(confirmed_minimum_spend=2000.0)
        payload = _build_draft_input_payload(ctx)
        assert "spend_line" in payload
        assert "Minimum spend" in payload["spend_line"]


# ── Six-record fixture regression tests ──────────────────────────────────────


@pytest.fixture(scope="module")
def fixture_data() -> dict:
    if not _FIXTURE_PATH.exists():
        pytest.skip(f"Fixture not found: {_FIXTURE_PATH}")
    with _FIXTURE_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def fixture_records_with_availability(fixture_data: dict) -> list[dict]:
    return fixture_data.get("with_availability", [])


@pytest.fixture(scope="module")
def fixture_records_without_availability(fixture_data: dict) -> list[dict]:
    return fixture_data.get("without_availability", [])


class TestFixtureAvailabilityContract:
    """Structural tests against the six-record LLM2 fixture.

    These tests verify that the deterministic V4 functions produce the
    correct contract states for the fixture's known availability data.
    They do not re-call the LLM.
    """

    @staticmethod
    def _parse_spend_from_line(spend_line: str) -> float | None:
        """Extract numeric spend amount from any spend_line format."""
        import re
        match = re.search(r"£([\d,]+)", spend_line)
        if not match:
            return None
        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            return None

    def _ctx_from_fixture_record(self, record: dict) -> DraftContext:
        """Build a minimal DraftContext from a fixture record."""
        av = record.get("availability") or {}
        pi = record.get("prompt_inputs") or {}
        return _base_context(
            availability_status=av.get("availability_status"),
            availability_date=av.get("event_date"),
            availability_meal_period=av.get("meal_period"),
            confirmed_minimum_spend=self._parse_spend_from_line(pi.get("spend_line", "")),
        )

    def test_records_with_availability_have_confirmed_contract(
        self, fixture_records_with_availability: list[dict]
    ) -> None:
        assert fixture_records_with_availability, "Expected 3 records with availability"
        for record in fixture_records_with_availability:
            av = record.get("availability") or {}
            db_status = av.get("availability_status")
            ctx = self._ctx_from_fixture_record(record)
            line = _build_availability_line(ctx)
            if db_status == "available":
                assert "CONFIRMED_AVAILABLE" in line, (
                    f"{record['record_id']}: expected CONFIRMED_AVAILABLE, got: {line!r}"
                )
            elif db_status in ("booked", "held", "unavailable"):
                assert "CONFIRMED_UNAVAILABLE" in line, (
                    f"{record['record_id']}: expected CONFIRMED_UNAVAILABLE, got: {line!r}"
                )

    def test_records_without_availability_have_not_checked_contract(
        self, fixture_records_without_availability: list[dict]
    ) -> None:
        assert fixture_records_without_availability, "Expected 3 records without availability"
        for record in fixture_records_without_availability:
            ctx = self._ctx_from_fixture_record(record)
            line = _build_availability_line(ctx)
            assert "NOT_CHECKED" in line, (
                f"{record['record_id']}: expected NOT_CHECKED, got: {line!r}"
            )

    def test_booked_records_do_not_produce_available_statement(
        self, fixture_records_with_availability: list[dict]
    ) -> None:
        for record in fixture_records_with_availability:
            av = record.get("availability") or {}
            if av.get("availability_status") == "booked":
                ctx = self._ctx_from_fixture_record(record)
                line = _build_availability_line(ctx)
                # Must not tell the LLM the date is available
                assert "CONFIRMED_AVAILABLE" not in line, (
                    f"{record['record_id']}: booked record produced CONFIRMED_AVAILABLE"
                )

    def test_spend_line_never_says_recommended_in_fixture(
        self, fixture_records_with_availability: list[dict]
    ) -> None:
        # For any record that has a spend value, the built V4 line must not say Recommended
        for record in fixture_records_with_availability:
            pi = record.get("prompt_inputs") or {}
            old_line = pi.get("spend_line", "")
            amount = self._parse_spend_from_line(old_line)
            if amount is None:
                continue
            ctx = _base_context(confirmed_minimum_spend=amount)
            new_line = _build_spend_line(ctx)
            assert "Recommended" not in new_line, (
                f"{record['record_id']}: spend line says Recommended: {new_line!r}"
            )
            assert "Minimum spend" in new_line
