"""Tests for enquiry extraction V5 schema contract (CUST-003).

Confirms:
- V5 is the active extraction prompt
- V4 is archived
- V5 system template contains all required audience evidence fields
- output_schema_version is 5.0
- audience_type is still present (backward compatibility)
"""

import pytest

from app.modules.ai.constants import (
    PROMPT_KEY_ENQUIRY_EXTRACTION,
    VERSION_STATUS_ACTIVE,
    VERSION_STATUS_ARCHIVED,
)
from app.modules.ai.prompt_registry import PromptRegistry, _ALL_DEFINITIONS


# ── Registry resolution ────────────────────────────────────────────────────────


class TestV5IsActive:
    def test_active_extraction_prompt_is_v5(self):
        # AI-021: V6 is now active; V5 is archived
        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert defn.version == 6, (
            f"Expected V6 to be the active extraction prompt, got V{defn.version}"
        )

    def test_active_extraction_schema_version_is_5(self):
        # AI-021: V6 uses schema_version 6.0
        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert defn.output_schema_version == "6.0"

    def test_active_extraction_status_is_active(self):
        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert defn.status == VERSION_STATUS_ACTIVE

    def test_max_tokens_is_at_least_1400(self):
        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert defn.max_tokens >= 1400


# ── V4 is archived ────────────────────────────────────────────────────────────


class TestV4IsArchived:
    def test_v4_is_archived(self):
        v4 = next(
            (d for d in _ALL_DEFINITIONS
             if d.key == PROMPT_KEY_ENQUIRY_EXTRACTION and d.version == 4),
            None,
        )
        assert v4 is not None, "V4 definition not found in registry"
        assert v4.status == VERSION_STATUS_ARCHIVED, (
            f"Expected V4 to be archived, got status={v4.status}"
        )

    def test_v4_schema_version_is_4(self):
        v4 = next(
            (d for d in _ALL_DEFINITIONS
             if d.key == PROMPT_KEY_ENQUIRY_EXTRACTION and d.version == 4),
            None,
        )
        assert v4 is not None
        assert v4.output_schema_version == "4.0"


# ── V5 system template contains required audience evidence fields ───────────────


class TestV5SystemTemplateFields:
    @pytest.fixture
    def v5_system_template(self):
        registry = PromptRegistry()
        return registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION).system_template

    def test_audience_type_present_for_backward_compat(self, v5_system_template):
        assert '"audience_type"' in v5_system_template

    def test_audience_type_from_content_present(self, v5_system_template):
        assert "audience_type_from_content" in v5_system_template

    def test_audience_confidence_present(self, v5_system_template):
        assert "audience_confidence" in v5_system_template

    def test_audience_evidence_present(self, v5_system_template):
        assert "audience_evidence" in v5_system_template

    def test_audience_conflict_notes_present(self, v5_system_template):
        assert "audience_conflict_notes" in v5_system_template

    def test_schema_version_declared_in_template(self, v5_system_template):
        # AI-021: active prompt is now V6
        assert "schema_version: 6.0" in v5_system_template

    def test_audience_evidence_rules_section_present(self, v5_system_template):
        assert "AUDIENCE EVIDENCE RULES" in v5_system_template

    def test_date_context_rules_still_present(self, v5_system_template):
        assert "DATE CONTEXT RULES" in v5_system_template


# ── V5 schema version ─────────────────────────────────────────────────────────


class TestV5SchemaVersion:
    def test_v5_output_schema_version_is_5(self):
        # AI-021: active prompt is now V6 with schema_version 6.0
        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert defn.output_schema_version == "6.0"

    def test_v5_change_notes_mention_audience_fields(self):
        # AI-021: V6 change notes reference policy question extraction
        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert "policy" in defn.change_notes.lower()
        assert "AI-021" in defn.change_notes


# ── Older versions still registered ──────────────────────────────────────────


class TestOlderVersionsRetained:
    def test_all_versions_1_to_6_present_in_registry(self):
        # AI-021: V6 added; versions 1–6 must all be registered
        extraction_versions = [
            d.version for d in _ALL_DEFINITIONS
            if d.key == PROMPT_KEY_ENQUIRY_EXTRACTION
        ]
        for v in range(1, 7):
            assert v in extraction_versions, f"V{v} missing from extraction registry"

    def test_v1_v2_v3_v4_v5_are_archived(self):
        # AI-021: V5 archived when V6 became active
        for v in range(1, 6):
            defn = next(
                (d for d in _ALL_DEFINITIONS
                 if d.key == PROMPT_KEY_ENQUIRY_EXTRACTION and d.version == v),
                None,
            )
            assert defn is not None, f"V{v} missing"
            assert defn.status == VERSION_STATUS_ARCHIVED, (
                f"V{v} expected ARCHIVED, got {defn.status}"
            )


# ── Required variables unchanged ──────────────────────────────────────────────


class TestV5RequiredVariables:
    def test_v5_required_variables_include_restaurant_and_freeform(self):
        registry = PromptRegistry()
        defn = registry.get(PROMPT_KEY_ENQUIRY_EXTRACTION)
        assert "restaurant_name" in defn.required_variables
        assert "freeform_text" in defn.required_variables
