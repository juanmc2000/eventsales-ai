"""Tests for structured output validation (AI-005).

All tests are smoke/unit — no DB or live LLM required.
"""

from __future__ import annotations

import json

import pytest

from app.modules.ai.constants import (
    SCHEMA_DRAFT_EMAIL_OUTPUT,
    SCHEMA_ENQUIRY_EXTRACTION_OUTPUT,
    VALIDATION_FAILED,
    VALIDATION_FALLBACK_INVALID,
    VALIDATION_FALLBACK_VALID,
    VALIDATION_PARSE_ERROR,
    VALIDATION_PASSED,
    VALIDATION_SKIPPED,
)
from app.modules.ai.validators import (
    DraftEmailOutput,
    EnquiryExtractionOutput,
    OutputValidator,
    ValidationResult,
    get_schema,
)


# ── DraftEmailOutput schema ────────────────────────────────────────────────

class TestDraftEmailOutput:
    def test_valid_subject_and_body(self) -> None:
        out = DraftEmailOutput(subject="Hello", body="Dear Alice, ...")
        assert out.subject == "Hello"

    def test_empty_subject_allowed(self) -> None:
        out = DraftEmailOutput(subject="", body="Some body")
        assert out.subject == ""

    def test_empty_body_rejected(self) -> None:
        with pytest.raises(Exception):
            DraftEmailOutput(subject="Hi", body="")

    def test_missing_body_rejected(self) -> None:
        with pytest.raises(Exception):
            DraftEmailOutput.model_validate({"subject": "Hi"})


# ── EnquiryExtractionOutput schema ────────────────────────────────────────

class TestEnquiryExtractionOutput:
    def test_all_nullable_fields(self) -> None:
        out = EnquiryExtractionOutput()
        assert out.first_name is None
        assert out.party_size is None

    def test_valid_full_extraction(self) -> None:
        out = EnquiryExtractionOutput(
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            party_size=10,
        )
        assert out.party_size == 10

    def test_party_size_string_coercion(self) -> None:
        out = EnquiryExtractionOutput.model_validate({"party_size": "10"})
        assert out.party_size == 10

    def test_party_size_invalid_string_becomes_none(self) -> None:
        out = EnquiryExtractionOutput.model_validate({"party_size": "many"})
        assert out.party_size is None


# ── get_schema helper ──────────────────────────────────────────────────────

class TestGetSchema:
    def test_returns_draft_email_output(self) -> None:
        cls = get_schema(SCHEMA_DRAFT_EMAIL_OUTPUT)
        assert cls is DraftEmailOutput

    def test_returns_enquiry_extraction_output(self) -> None:
        cls = get_schema(SCHEMA_ENQUIRY_EXTRACTION_OUTPUT)
        assert cls is EnquiryExtractionOutput

    def test_returns_none_for_unknown(self) -> None:
        assert get_schema("NonExistentSchema") is None


# ── OutputValidator ────────────────────────────────────────────────────────

class TestOutputValidatorSkip:
    def setup_method(self) -> None:
        self.validator = OutputValidator()

    def test_none_response_skipped(self) -> None:
        result = self.validator.validate(None, SCHEMA_DRAFT_EMAIL_OUTPUT)
        assert result.status == VALIDATION_SKIPPED

    def test_fallback_skipped(self) -> None:
        result = self.validator.validate("some text", SCHEMA_DRAFT_EMAIL_OUTPUT, is_fallback=True)
        assert result.status == VALIDATION_SKIPPED

    def test_no_schema_skipped(self) -> None:
        result = self.validator.validate('{"subject":"Hi","body":"Hello"}', None)
        assert result.status == VALIDATION_SKIPPED

    def test_unknown_schema_skipped(self) -> None:
        result = self.validator.validate('{"x":1}', "UnknownSchema")
        assert result.status == VALIDATION_SKIPPED


class TestOutputValidatorValid:
    def setup_method(self) -> None:
        self.validator = OutputValidator()

    def test_valid_draft_email_json(self) -> None:
        raw = json.dumps({"subject": "Re: Enquiry", "body": "Dear Alice, thank you."})
        result = self.validator.validate(raw, SCHEMA_DRAFT_EMAIL_OUTPUT)
        assert result.status == VALIDATION_PASSED
        assert result.parsed == {"subject": "Re: Enquiry", "body": "Dear Alice, thank you."}
        assert result.errors is None

    def test_valid_enquiry_extraction_json(self) -> None:
        raw = json.dumps({
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice@example.com",
            "phone": None,
            "event_type": "birthday",
            "event_date": "2026-09-01",
            "party_size": 8,
            "notes": None,
        })
        result = self.validator.validate(raw, SCHEMA_ENQUIRY_EXTRACTION_OUTPUT)
        assert result.status == VALIDATION_PASSED
        assert result.parsed["first_name"] == "Alice"


class TestOutputValidatorInvalid:
    def setup_method(self) -> None:
        self.validator = OutputValidator()

    def test_missing_required_body_is_invalid(self) -> None:
        raw = json.dumps({"subject": "Hello"})  # body missing
        result = self.validator.validate(raw, SCHEMA_DRAFT_EMAIL_OUTPUT)
        assert result.status == VALIDATION_FAILED
        assert result.errors is not None
        assert len(result.errors) > 0

    def test_empty_body_is_invalid(self) -> None:
        raw = json.dumps({"subject": "Hi", "body": ""})
        result = self.validator.validate(raw, SCHEMA_DRAFT_EMAIL_OUTPUT)
        assert result.status == VALIDATION_FAILED

    def test_invalid_stores_parsed_dict(self) -> None:
        raw = json.dumps({"subject": "Hi"})
        result = self.validator.validate(raw, SCHEMA_DRAFT_EMAIL_OUTPUT)
        # Even invalid JSON responses: parsed dict is preserved
        assert result.parsed == {"subject": "Hi"}


class TestOutputValidatorParseError:
    def setup_method(self) -> None:
        self.validator = OutputValidator()

    def test_plain_text_is_parse_error(self) -> None:
        raw = "Dear Alice, thank you for your enquiry."
        result = self.validator.validate(raw, SCHEMA_DRAFT_EMAIL_OUTPUT)
        assert result.status == VALIDATION_PARSE_ERROR
        assert result.errors is not None

    def test_malformed_json_is_parse_error(self) -> None:
        raw = '{"subject": "Hi", "body": '  # truncated
        result = self.validator.validate(raw, SCHEMA_DRAFT_EMAIL_OUTPUT)
        assert result.status == VALIDATION_PARSE_ERROR

    def test_json_array_is_parse_error(self) -> None:
        raw = '[{"subject": "Hi"}]'
        result = self.validator.validate(raw, SCHEMA_DRAFT_EMAIL_OUTPUT)
        assert result.status == VALIDATION_PARSE_ERROR


class TestOutputValidatorFallbackPath:
    def setup_method(self) -> None:
        self.validator = OutputValidator()

    def test_fallback_true_always_skipped(self) -> None:
        raw = json.dumps({"subject": "Hi", "body": "Hello"})
        result = self.validator.validate(raw, SCHEMA_DRAFT_EMAIL_OUTPUT, is_fallback=True)
        assert result.status == VALIDATION_SKIPPED

    def test_fallback_none_response_skipped(self) -> None:
        result = self.validator.validate(None, SCHEMA_DRAFT_EMAIL_OUTPUT, is_fallback=True)
        assert result.status == VALIDATION_SKIPPED


# ── Gateway validation integration ───────────────────────────────────────

class TestGatewayWithValidation:
    """Confirm the gateway passes validation results through to AIGatewayResult."""

    def test_gateway_result_includes_validation_fields(self) -> None:
        """AIGatewayResult schema includes parsed_response and validation_errors."""
        from app.modules.ai.schemas import AIGatewayResult
        import uuid
        result = AIGatewayResult(
            run_id=uuid.uuid4(),
            prompt_key="draft_response",
            prompt_version=1,
            model_name="claude-haiku-4-5-20251001",
            model_provider="anthropic",
            rendered_system_prompt="system text",
            rendered_user_prompt="user text",
            raw_response='{"subject":"Hi","body":"Hello"}',
            is_fallback=False,
            fallback_reason=None,
            validation_status=VALIDATION_PASSED,
            latency_ms=150,
            status="success",
            parsed_response={"subject": "Hi", "body": "Hello"},
            validation_errors=None,
        )
        assert result.validation_status == VALIDATION_PASSED
        assert result.parsed_response == {"subject": "Hi", "body": "Hello"}
        assert result.validation_errors is None
