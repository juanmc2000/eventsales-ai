"""Tests for the PromptRegistry and PromptRenderer (AI-003)."""

import pytest

from app.modules.ai.constants import (
    ALL_PROMPT_KEYS,
    PROMPT_KEY_DRAFT_RESPONSE,
    PROMPT_KEY_ENQUIRY_EXTRACTION,
    PROMPT_KEY_MISSING_INFO_REQUEST,
    PROMPT_KEY_FOLLOW_UP_RESPONSE,
    PROMPT_KEY_AVAILABILITY_ALTERNATIVE,
    VERSION_STATUS_ACTIVE,
)
from app.modules.ai.prompt_registry import PromptRegistry, PromptDefinition
from app.modules.ai.prompt_renderer import PromptRenderer, MissingPromptVariables


# ── PromptRegistry ─────────────────────────────────────────────────────────

class TestPromptRegistry:
    def setup_method(self) -> None:
        self.registry = PromptRegistry()

    def test_all_keys_registered(self) -> None:
        keys = set(self.registry.all_keys())
        assert ALL_PROMPT_KEYS == keys

    def test_draft_response_is_registered(self) -> None:
        defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert defn.key == PROMPT_KEY_DRAFT_RESPONSE
        assert defn.status == VERSION_STATUS_ACTIVE
        assert defn.version >= 1

    def test_enquiry_extraction_is_registered(self) -> None:
        defn = self.registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert defn.key == PROMPT_KEY_ENQUIRY_EXTRACTION
        assert defn.status == VERSION_STATUS_ACTIVE

    def test_missing_info_request_is_registered(self) -> None:
        defn = self.registry.get(PROMPT_KEY_MISSING_INFO_REQUEST)
        assert defn.key == PROMPT_KEY_MISSING_INFO_REQUEST

    def test_follow_up_response_is_registered(self) -> None:
        defn = self.registry.get(PROMPT_KEY_FOLLOW_UP_RESPONSE)
        assert defn.key == PROMPT_KEY_FOLLOW_UP_RESPONSE

    def test_availability_alternative_is_registered(self) -> None:
        defn = self.registry.get(PROMPT_KEY_AVAILABILITY_ALTERNATIVE)
        assert defn.key == PROMPT_KEY_AVAILABILITY_ALTERNATIVE

    def test_unknown_key_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="Unknown prompt key"):
            self.registry.get("nonexistent_key")

    def test_all_active_definitions_have_templates(self) -> None:
        for key in self.registry.all_keys():
            defn = self.registry.get(key)
            assert defn.system_template.strip(), f"{key}: system_template is empty"
            assert defn.user_template.strip(), f"{key}: user_template is empty"

    def test_all_definitions_have_output_schema_where_expected(self) -> None:
        draft = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        assert draft.output_schema_name is not None

        extraction = self.registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert extraction.output_schema_name is not None

    def test_prompt_definitions_are_immutable(self) -> None:
        defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        with pytest.raises((AttributeError, TypeError)):
            defn.version = 999  # type: ignore[misc]

    def test_all_definitions_returns_list(self) -> None:
        defns = self.registry.all_definitions()
        assert len(defns) >= 5


# ── PromptRenderer ─────────────────────────────────────────────────────────

class TestPromptRenderer:
    def setup_method(self) -> None:
        self.registry = PromptRegistry()
        self.renderer = PromptRenderer()

    def _draft_context(self) -> dict:
        return {
            "persona_system_prompt": "You are a professional.",
            "persona_name": "Eleanor",
            "restaurant_name": "The Grand",
            "persona_tone": "warm and formal",
            "persona_style": "concise",
            "guest_first_name": "Alice",
            "guest_last_name": "Smith",
            "response_goal": "READY_TO_CONFIRM_AVAILABILITY",
        }

    def test_render_system_draft_response(self) -> None:
        defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        rendered = self.renderer.render_system(defn, self._draft_context())
        assert "Eleanor" in rendered
        assert "The Grand" in rendered
        assert "warm and formal" in rendered

    def test_render_user_draft_response(self) -> None:
        defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        rendered = self.renderer.render_user(defn, self._draft_context())
        assert "Alice" in rendered
        assert "Smith" in rendered

    def test_render_user_optional_fields_default_empty(self) -> None:
        defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        # No optional variables provided — should render without error
        rendered = self.renderer.render_user(defn, self._draft_context())
        # Optional lines should be absent (empty strings substituted)
        assert rendered is not None

    def test_render_system_with_optional_variable_included(self) -> None:
        defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        ctx = self._draft_context()
        # System template has no optional vars but test verifies context passthrough
        rendered = self.renderer.render_system(defn, ctx)
        assert "You are a professional." in rendered

    def test_missing_required_variable_raises(self) -> None:
        defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        incomplete = {
            "persona_name": "Eleanor",
            # Missing: persona_system_prompt, restaurant_name, etc.
        }
        with pytest.raises(MissingPromptVariables) as exc_info:
            self.renderer.render_system(defn, incomplete)
        assert exc_info.value.missing  # at least one missing variable reported

    def test_missing_prompt_variables_reports_all_missing(self) -> None:
        defn = self.registry.get(PROMPT_KEY_DRAFT_RESPONSE)
        with pytest.raises(MissingPromptVariables) as exc_info:
            self.renderer.render_system(defn, {})
        # All required variables should be in the missing set
        assert defn.required_variables == exc_info.value.missing

    def test_input_hash_is_deterministic(self) -> None:
        h1 = PromptRenderer.input_hash("system text", "user text")
        h2 = PromptRenderer.input_hash("system text", "user text")
        assert h1 == h2

    def test_input_hash_differs_for_different_content(self) -> None:
        h1 = PromptRenderer.input_hash("system text A", "user text")
        h2 = PromptRenderer.input_hash("system text B", "user text")
        assert h1 != h2

    def test_input_hash_is_64_hex_chars(self) -> None:
        h = PromptRenderer.input_hash("system", "user")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_extract_variables_finds_placeholders(self) -> None:
        template = "Hello {name}, your event on {date} is confirmed."
        vars_ = PromptRenderer.extract_variables(template)
        assert vars_ == {"name", "date"}

    def test_extract_variables_ignores_positional(self) -> None:
        template = "Hello {0}, your event on {date} is confirmed."
        vars_ = PromptRenderer.extract_variables(template)
        assert vars_ == {"date"}

    def test_render_enquiry_extraction(self) -> None:
        defn = self.registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        # V2 uses freeform_text as the primary input variable
        ctx = {
            "restaurant_name": "The Grand",
            "freeform_text": "Hi, I'd like to book a private room for a birthday dinner for 20 guests on Christmas Eve.",
        }
        system = self.renderer.render_system(defn, ctx)
        user = self.renderer.render_user(defn, ctx)
        assert "The Grand" in system
        assert "birthday dinner" in user
        assert "20 guests" in user

    def test_enquiry_extraction_is_v5(self) -> None:
        # AI-021: V6 is now the active extraction prompt (V5 archived)
        defn = self.registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert defn.version == 6

    def test_enquiry_extraction_v3_prohibits_pricing(self) -> None:
        defn = self.registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert "pricing" in defn.system_template.lower()

    def test_enquiry_extraction_v3_prohibits_availability(self) -> None:
        defn = self.registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert "availability" in defn.system_template.lower()

    def test_enquiry_extraction_v3_prohibits_drafting(self) -> None:
        defn = self.registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        template = defn.system_template.lower()
        assert "customer-facing" in template or "draft" in template or "response" in template

    def test_enquiry_extraction_v3_prohibits_candidate_date_expansion(self) -> None:
        defn = self.registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        template = defn.system_template.lower()
        assert "candidate" in template or "expand" in template

    def test_enquiry_extraction_v3_requires_freeform_text_variable(self) -> None:
        defn = self.registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert "freeform_text" in defn.required_variables

    def test_enquiry_extraction_v3_very_low_temperature(self) -> None:
        defn = self.registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert float(defn.temperature) <= 0.1

    def test_enquiry_extraction_v3_contains_json_contract(self) -> None:
        defn = self.registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        # Explicit JSON structure must be in the system template
        assert "date_request" in defn.system_template
        assert "date_request_type" in defn.system_template
        assert "requires_date_clarification" in defn.system_template

    def test_enquiry_extraction_v3_contains_null_placeholder_convention(self) -> None:
        defn = self.registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        # NULL placeholder convention must be documented in the template
        assert "NULL" in defn.system_template
        assert "null" in defn.system_template.lower()

    def test_enquiry_extraction_v3_sufficient_max_tokens(self) -> None:
        defn = self.registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        # date_request object requires more tokens than the V2 600 limit
        assert defn.max_tokens >= 900

    def test_enquiry_extraction_v5_schema_version(self) -> None:
        # AI-021: V6 bumped schema version to 6.0
        defn = self.registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert defn.output_schema_version == "6.0"

    def test_enquiry_extraction_v3_contains_schema_name(self) -> None:
        defn = self.registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert "schema_name" in defn.system_template
        assert "enquiry_extraction_output" in defn.system_template
