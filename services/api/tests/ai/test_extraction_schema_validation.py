"""Tests for extraction output schema validation (TEST-008).

Validates that the OutputValidator correctly handles extraction responses
and that schema validation works end-to-end through the gateway layer.

These tests use the schemas that exist on main. When AI-010 is merged, the
EnquiryExtractionOutput will gain Sprint 7 fields (guest_count, occasion, etc.)
and the tests in test_prompt_registry.py will cover the upgraded schema.
"""

from __future__ import annotations

import json
import uuid

import pytest

from app.modules.ai.constants import (
    SCHEMA_DRAFT_EMAIL_OUTPUT,
    SCHEMA_ENQUIRY_EXTRACTION_OUTPUT,
    VALIDATION_FAILED,
    VALIDATION_PARSE_ERROR,
    VALIDATION_PASSED,
    VALIDATION_SKIPPED,
)
from app.modules.ai.validators import DraftEmailOutput, EnquiryExtractionOutput, OutputValidator


# ── EnquiryExtractionOutput schema tests ─────────────────────────────────────


class TestEnquiryExtractionOutputSchema:
    """Schema-level validation for EnquiryExtractionOutput."""

    def test_all_fields_nullable(self):
        """All fields accept null — LLM may not extract every field."""
        out = EnquiryExtractionOutput()
        assert out.event_type is None
        assert out.event_date is None
        assert out.party_size is None

    def test_party_size_coerced_from_string(self):
        """Numeric string party_size is coerced to int."""
        out = EnquiryExtractionOutput(party_size="25")
        assert out.party_size == 25

    def test_party_size_non_numeric_string_returns_none(self):
        """Non-numeric party_size becomes None rather than raising."""
        out = EnquiryExtractionOutput(party_size="twenty")
        assert out.party_size is None

    def test_party_size_none_passes(self):
        out = EnquiryExtractionOutput(party_size=None)
        assert out.party_size is None

    def test_event_date_iso_string_accepted(self):
        out = EnquiryExtractionOutput(event_date="2026-08-15")
        assert out.event_date == "2026-08-15"

    def test_event_type_accepted(self):
        out = EnquiryExtractionOutput(event_type="corporate_dinner")
        assert out.event_type == "corporate_dinner"

    def test_full_valid_extraction(self):
        out = EnquiryExtractionOutput(
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            event_type="private_dining",
            event_date="2026-09-01",
            party_size=15,
            notes="Anniversary dinner, vegetarian options required",
        )
        assert out.first_name == "Alice"
        assert out.party_size == 15


# ── DraftEmailOutput schema tests ─────────────────────────────────────────────


class TestDraftEmailOutputSchema:
    def test_valid_draft_output(self):
        out = DraftEmailOutput(subject="Re: Event Enquiry", body="Dear Alice, thank you.")
        assert out.subject == "Re: Event Enquiry"

    def test_empty_body_raises(self):
        with pytest.raises(Exception):
            DraftEmailOutput(subject="Subject", body="")

    def test_empty_subject_allowed(self):
        """Subject may be empty — body is the mandatory field."""
        out = DraftEmailOutput(subject="", body="Dear Guest...")
        assert out.subject == ""


# ── OutputValidator integration tests ────────────────────────────────────────


class TestOutputValidatorWithExtractionSchema:
    """Tests that OutputValidator correctly handles EnquiryExtractionOutput."""

    def setup_method(self) -> None:
        self.validator = OutputValidator()

    def test_valid_extraction_json_passes(self):
        payload = json.dumps({
            "first_name": "Alice",
            "event_type": "corporate_dinner",
            "event_date": "2026-08-15",
            "party_size": 20,
        })
        result = self.validator.validate(payload, SCHEMA_ENQUIRY_EXTRACTION_OUTPUT)
        assert result.status == VALIDATION_PASSED
        assert result.parsed is not None
        assert result.parsed["party_size"] == 20

    def test_extraction_with_all_nulls_passes(self):
        """All-null extraction is valid — LLM can return any subset of fields."""
        payload = json.dumps({
            "first_name": None,
            "last_name": None,
            "email": None,
            "event_type": None,
            "event_date": None,
            "party_size": None,
        })
        result = self.validator.validate(payload, SCHEMA_ENQUIRY_EXTRACTION_OUTPUT)
        assert result.status == VALIDATION_PASSED

    def test_extraction_with_string_party_size_passes(self):
        """String party_size is coerced by the schema validator."""
        payload = json.dumps({
            "party_size": "15",
        })
        result = self.validator.validate(payload, SCHEMA_ENQUIRY_EXTRACTION_OUTPUT)
        assert result.status == VALIDATION_PASSED
        assert result.parsed["party_size"] == "15"  # raw JSON value before schema coerce

    def test_non_json_extraction_returns_parse_error(self):
        result = self.validator.validate(
            "Dear Alice, I could not extract structured data.",
            SCHEMA_ENQUIRY_EXTRACTION_OUTPUT,
        )
        assert result.status == VALIDATION_PARSE_ERROR
        assert result.errors is not None

    def test_extraction_json_array_is_parse_error(self):
        """Root-level JSON array (not object) returns parse_error."""
        result = self.validator.validate(
            '["alice", "smith"]',
            SCHEMA_ENQUIRY_EXTRACTION_OUTPUT,
        )
        assert result.status == VALIDATION_PARSE_ERROR

    def test_no_schema_returns_skipped(self):
        result = self.validator.validate(
            '{"any": "json"}',
            schema_name=None,
        )
        assert result.status == VALIDATION_SKIPPED

    def test_unknown_schema_name_returns_skipped(self):
        result = self.validator.validate(
            '{"any": "json"}',
            schema_name="NonExistentSchema",
        )
        assert result.status == VALIDATION_SKIPPED

    def test_fallback_run_always_skipped(self):
        """Fallback runs are never validated regardless of schema."""
        result = self.validator.validate(
            '{"first_name": "Alice"}',
            SCHEMA_ENQUIRY_EXTRACTION_OUTPUT,
            is_fallback=True,
        )
        assert result.status == VALIDATION_SKIPPED

    def test_none_response_returns_skipped(self):
        result = self.validator.validate(None, SCHEMA_ENQUIRY_EXTRACTION_OUTPUT)
        assert result.status == VALIDATION_SKIPPED


# ── Extraction vs draft schema separation ─────────────────────────────────────


class TestExtractionAndDraftSchemaSeparation:
    """Validates that extraction and draft schemas are distinct and correct."""

    def test_extraction_schema_is_registered(self):
        from app.modules.ai.validators import get_schema
        schema = get_schema(SCHEMA_ENQUIRY_EXTRACTION_OUTPUT)
        assert schema is not None
        assert schema is EnquiryExtractionOutput

    def test_draft_schema_is_registered(self):
        from app.modules.ai.validators import get_schema
        schema = get_schema(SCHEMA_DRAFT_EMAIL_OUTPUT)
        assert schema is not None
        assert schema is DraftEmailOutput

    def test_draft_schema_is_not_extraction_schema(self):
        from app.modules.ai.validators import get_schema
        assert get_schema(SCHEMA_DRAFT_EMAIL_OUTPUT) is not get_schema(SCHEMA_ENQUIRY_EXTRACTION_OUTPUT)

    def test_extraction_schema_accepts_no_draft_fields(self):
        """Extraction schema does not validate draft-specific fields (subject/body)."""
        from app.modules.ai.validators import get_schema
        extraction_cls = get_schema(SCHEMA_ENQUIRY_EXTRACTION_OUTPUT)
        # Extra fields are allowed by default in Pydantic v2 (ignored)
        # This test confirms extraction schema doesn't REQUIRE draft fields
        obj = extraction_cls.model_validate({"subject": "ignored", "body": "ignored"})
        assert not hasattr(obj, "subject") or getattr(obj, "subject", "NOT_THERE") == "NOT_THERE"

    def test_draft_schema_requires_body(self):
        """DraftEmailOutput requires a non-empty body."""
        validator = OutputValidator()
        result = validator.validate(
            json.dumps({"subject": "Re: Enquiry", "body": ""}),
            SCHEMA_DRAFT_EMAIL_OUTPUT,
        )
        assert result.status == VALIDATION_FAILED
