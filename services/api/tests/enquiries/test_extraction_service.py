"""Tests for EnquiryExtractionService (API-014).

All tests are unit-level — no DB or live LLM required.
The AI Gateway and DB session are mocked.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.modules.enquiries.extraction_service import (
    EXTRACTION_TRIGGER_FREEFORM_WEBFORM,
    EXTRACTION_TRIGGER_INBOUND_EMAIL,
    EXTRACTION_TRIGGER_MANUAL_REEXTRACT,
    VALID_TRIGGER_TYPES,
    EnquiryExtractionService,
    ExtractionRequest,
    ExtractionResult,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_request(**kwargs) -> ExtractionRequest:
    defaults = dict(
        enquiry_id=uuid.uuid4(),
        freeform_text="I'd like a private room for 20 guests on Christmas Eve.",
        restaurant_name="The Grand Ballroom",
    )
    defaults.update(kwargs)
    return ExtractionRequest(**defaults)


def _make_gateway_result(
    *,
    is_fallback: bool = False,
    parsed_response: dict | None = None,
    validation_status: str = "passed",
    status: str = "success",
    error_message: str | None = None,
) -> MagicMock:
    result = MagicMock()
    result.run_id = uuid.uuid4()
    result.is_fallback = is_fallback
    result.parsed_response = parsed_response
    result.validation_status = validation_status
    result.status = status
    result.error_message = error_message
    return result


def _make_extraction_row(enquiry_id: uuid.UUID) -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.enquiry_id = enquiry_id
    return row


# ── ExtractionRequest schema ────────────────────────────────────────────────

class TestExtractionRequest:
    def test_defaults(self) -> None:
        req = _make_request()
        assert req.trigger_type == EXTRACTION_TRIGGER_FREEFORM_WEBFORM
        assert req.source_message_id is None
        assert req.tenant_id is None
        assert req.api_key == ""

    def test_valid_trigger_types(self) -> None:
        expected = {
            EXTRACTION_TRIGGER_FREEFORM_WEBFORM,
            EXTRACTION_TRIGGER_INBOUND_EMAIL,
            EXTRACTION_TRIGGER_MANUAL_REEXTRACT,
        }
        assert VALID_TRIGGER_TYPES == expected


# ── EnquiryExtractionService ───────────────────────────────────────────────

class TestEnquiryExtractionService:
    def _make_service(self) -> tuple[EnquiryExtractionService, MagicMock]:
        db = MagicMock()
        service = EnquiryExtractionService(db=db)
        return service, db

    def _run_extract(
        self,
        service: EnquiryExtractionService,
        request: ExtractionRequest,
        gateway_result: MagicMock,
        extraction_row: MagicMock | None = None,
    ) -> ExtractionResult:
        """Run extract() with the gateway and EnquiryExtraction both mocked."""
        with (
            patch(
                "app.modules.enquiries.extraction_service.AIGateway"
            ) as mock_gw_cls,
            patch(
                "app.modules.enquiries.extraction_service.EnquiryExtraction"
            ) as mock_extraction_cls,
        ):
            mock_gw = MagicMock()
            mock_gw.run.return_value = gateway_result
            mock_gw_cls.return_value = mock_gw

            row = extraction_row or _make_extraction_row(request.enquiry_id)
            mock_extraction_cls.return_value = row

            return service.extract(request)

    def test_successful_extraction_returns_result(self) -> None:
        service, _ = self._make_service()
        parsed = {
            "occasion": "birthday dinner",
            "guest_count": 20,
            "event_date": "2026-12-24",
            "event_time": "19:00",
            "event_type": "birthday",
            "budget": {"amount": 2000.0, "currency": "GBP", "budget_type": "total"},
            "allergens": None,
            "special_requirements": None,
            "freeform_notes": "Private room preferred",
            "missing_fields": [],
            "confidence": {"occasion": 0.95, "guest_count": 0.90},
        }
        gw_result = _make_gateway_result(parsed_response=parsed)
        result = self._run_extract(service, _make_request(), gw_result)

        assert isinstance(result, ExtractionResult)
        assert result.is_fallback is False
        assert result.validation_status == "passed"
        assert result.parsed == parsed
        assert result.extraction_id is not None
        assert result.prompt_run_id == gw_result.run_id

    def test_extraction_id_is_set_on_success(self) -> None:
        service, _ = self._make_service()
        gw_result = _make_gateway_result(parsed_response={"missing_fields": [], "confidence": {}})
        result = self._run_extract(service, _make_request(), gw_result)
        assert result.extraction_id is not None

    def test_fallback_result_is_persisted(self) -> None:
        service, _ = self._make_service()
        gw_result = _make_gateway_result(is_fallback=True, parsed_response=None, validation_status="skipped")
        result = self._run_extract(service, _make_request(), gw_result)

        assert result.is_fallback is True
        assert result.parsed is None
        assert result.extraction_id is not None  # row still persisted

    def test_gateway_called_with_correct_prompt_key(self) -> None:
        service, _ = self._make_service()
        req = _make_request()
        gw_result = _make_gateway_result()

        with (
            patch("app.modules.enquiries.extraction_service.AIGateway") as mock_gw_cls,
            patch("app.modules.enquiries.extraction_service.EnquiryExtraction"),
        ):
            mock_gw = MagicMock()
            mock_gw.run.return_value = gw_result
            mock_gw_cls.return_value = mock_gw

            service.extract(req)

            call_args = mock_gw.run.call_args[0][0]
            assert call_args.prompt_key == "enquiry_extraction"
            assert call_args.input_payload["restaurant_name"] == req.restaurant_name
            assert call_args.input_payload["freeform_text"] == req.freeform_text

    def test_gateway_called_with_enquiry_id(self) -> None:
        service, _ = self._make_service()
        req = _make_request()
        gw_result = _make_gateway_result()

        with (
            patch("app.modules.enquiries.extraction_service.AIGateway") as mock_gw_cls,
            patch("app.modules.enquiries.extraction_service.EnquiryExtraction"),
        ):
            mock_gw = MagicMock()
            mock_gw.run.return_value = gw_result
            mock_gw_cls.return_value = mock_gw

            service.extract(req)

            call_args = mock_gw.run.call_args[0][0]
            assert call_args.enquiry_id == req.enquiry_id

    def test_validation_failure_persists_partial_row(self) -> None:
        service, _ = self._make_service()
        gw_result = _make_gateway_result(
            parsed_response={"missing_fields": ["event_date"]},
            validation_status="invalid",
        )
        result = self._run_extract(service, _make_request(), gw_result)

        # Even with validation failure, we persist and return
        assert result.extraction_id is not None
        assert result.validation_status == "invalid"
        assert result.parsed is not None

    def test_missing_fields_extracted_from_parsed(self) -> None:
        service, _ = self._make_service()
        parsed = {"missing_fields": ["event_date", "guest_count"], "confidence": {}}
        gw_result = _make_gateway_result(parsed_response=parsed)

        with (
            patch("app.modules.enquiries.extraction_service.AIGateway") as mock_gw_cls,
            patch(
                "app.modules.enquiries.extraction_service.EnquiryExtraction"
            ) as mock_extraction_cls,
        ):
            mock_gw = MagicMock()
            mock_gw.run.return_value = gw_result
            mock_gw_cls.return_value = mock_gw

            row = _make_extraction_row(uuid.uuid4())
            mock_extraction_cls.return_value = row

            service.extract(_make_request())

            kwargs = mock_extraction_cls.call_args.kwargs
            assert kwargs["missing_fields"] == ["event_date", "guest_count"]

    def test_confidence_json_stored(self) -> None:
        service, _ = self._make_service()
        parsed = {"missing_fields": [], "confidence": {"occasion": 0.95, "guest_count": 0.80}}
        gw_result = _make_gateway_result(parsed_response=parsed)

        with (
            patch("app.modules.enquiries.extraction_service.AIGateway") as mock_gw_cls,
            patch(
                "app.modules.enquiries.extraction_service.EnquiryExtraction"
            ) as mock_extraction_cls,
        ):
            mock_gw = MagicMock()
            mock_gw.run.return_value = gw_result
            mock_gw_cls.return_value = mock_gw

            row = _make_extraction_row(uuid.uuid4())
            mock_extraction_cls.return_value = row

            service.extract(_make_request())

            kwargs = mock_extraction_cls.call_args.kwargs
            assert kwargs["confidence_json"] == {"occasion": 0.95, "guest_count": 0.80}

    def test_prompt_run_id_stored(self) -> None:
        service, _ = self._make_service()
        gw_result = _make_gateway_result(parsed_response={"missing_fields": [], "confidence": {}})

        with (
            patch("app.modules.enquiries.extraction_service.AIGateway") as mock_gw_cls,
            patch(
                "app.modules.enquiries.extraction_service.EnquiryExtraction"
            ) as mock_extraction_cls,
        ):
            mock_gw = MagicMock()
            mock_gw.run.return_value = gw_result
            mock_gw_cls.return_value = mock_gw

            row = _make_extraction_row(uuid.uuid4())
            mock_extraction_cls.return_value = row

            service.extract(_make_request())

            kwargs = mock_extraction_cls.call_args.kwargs
            assert kwargs["prompt_run_id"] == gw_result.run_id

    def test_db_error_returns_none_extraction_id(self) -> None:
        service, db = self._make_service()
        gw_result = _make_gateway_result(parsed_response={"missing_fields": [], "confidence": {}})

        with (
            patch("app.modules.enquiries.extraction_service.AIGateway") as mock_gw_cls,
            patch(
                "app.modules.enquiries.extraction_service.EnquiryExtraction",
                side_effect=Exception("DB error"),
            ),
        ):
            mock_gw = MagicMock()
            mock_gw.run.return_value = gw_result
            mock_gw_cls.return_value = mock_gw

            result = service.extract(_make_request())
            assert result.extraction_id is None
            assert result.prompt_run_id == gw_result.run_id

    def test_unknown_trigger_type_does_not_raise(self) -> None:
        service, _ = self._make_service()
        req = _make_request(trigger_type="unknown_trigger")
        gw_result = _make_gateway_result()
        result = self._run_extract(service, req, gw_result)
        assert result is not None

    def test_source_message_id_passed_to_model(self) -> None:
        service, _ = self._make_service()
        msg_id = uuid.uuid4()
        req = _make_request(source_message_id=msg_id)
        gw_result = _make_gateway_result(parsed_response={"missing_fields": [], "confidence": {}})

        with (
            patch("app.modules.enquiries.extraction_service.AIGateway") as mock_gw_cls,
            patch(
                "app.modules.enquiries.extraction_service.EnquiryExtraction"
            ) as mock_extraction_cls,
        ):
            mock_gw = MagicMock()
            mock_gw.run.return_value = gw_result
            mock_gw_cls.return_value = mock_gw

            row = _make_extraction_row(req.enquiry_id)
            mock_extraction_cls.return_value = row

            service.extract(req)

            kwargs = mock_extraction_cls.call_args.kwargs
            assert kwargs["source_message_id"] == msg_id
