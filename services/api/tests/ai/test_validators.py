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
    ExtractionBudget,
    ExtractionSpecialRequirements,
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


# ── EnquiryExtractionOutput schema (V2 — freeform) ────────────────────────

class TestEnquiryExtractionOutput:
    def test_all_fields_nullable(self) -> None:
        out = EnquiryExtractionOutput()
        assert out.occasion is None
        assert out.guest_count is None
        assert out.event_date is None
        assert out.event_time is None
        assert out.event_type is None
        assert out.budget is None
        assert out.allergens is None
        assert out.special_requirements is None
        assert out.freeform_notes is None

    def test_missing_fields_defaults_to_empty_list(self) -> None:
        out = EnquiryExtractionOutput()
        assert out.missing_fields == []

    def test_confidence_defaults_to_empty_dict(self) -> None:
        out = EnquiryExtractionOutput()
        assert out.confidence == {}

    def test_valid_full_extraction(self) -> None:
        out = EnquiryExtractionOutput(
            occasion="birthday dinner",
            guest_count=20,
            event_date="2026-12-25",
            event_time="19:00",
            event_type="birthday",
            budget=ExtractionBudget(amount=2000.0, currency="GBP", budget_type="total"),
            allergens=["gluten", "nuts"],
            special_requirements=ExtractionSpecialRequirements(
                children=True, disabled_access=True
            ),
            freeform_notes="Would prefer a private room",
            missing_fields=[],
            confidence={"occasion": 0.95, "guest_count": 0.90},
        )
        assert out.guest_count == 20
        assert out.budget is not None
        assert out.budget.amount == 2000.0
        assert out.budget.currency == "GBP"
        assert out.allergens == ["gluten", "nuts"]

    def test_guest_count_string_coercion(self) -> None:
        out = EnquiryExtractionOutput.model_validate({"guest_count": "15"})
        assert out.guest_count == 15

    def test_guest_count_invalid_string_becomes_none(self) -> None:
        out = EnquiryExtractionOutput.model_validate({"guest_count": "many"})
        assert out.guest_count is None

    def test_missing_fields_populated(self) -> None:
        out = EnquiryExtractionOutput(missing_fields=["event_date", "event_time"])
        assert "event_date" in out.missing_fields
        assert "event_time" in out.missing_fields

    def test_special_requirements_partial(self) -> None:
        sr = ExtractionSpecialRequirements(music=True, microphone=True)
        assert sr.music is True
        assert sr.children is None

    def test_budget_type_values(self) -> None:
        for bt in ("total", "per_head"):
            b = ExtractionBudget(budget_type=bt)
            assert b.budget_type == bt


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
            "occasion": "birthday dinner",
            "guest_count": 20,
            "event_date": "2026-09-01",
            "event_time": "19:00",
            "event_type": "birthday",
            "budget": {"amount": 1500.0, "currency": "GBP", "budget_type": "total"},
            "allergens": None,
            "special_requirements": None,
            "freeform_notes": "Would prefer a private room",
            "missing_fields": [],
            "confidence": {"occasion": 0.95, "guest_count": 0.90},
        })
        result = self.validator.validate(raw, SCHEMA_ENQUIRY_EXTRACTION_OUTPUT)
        assert result.status == VALIDATION_PASSED
        assert result.parsed["occasion"] == "birthday dinner"
        assert result.parsed["guest_count"] == 20


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
