"""Enquiry Extraction Service (API-014).

Runs the enquiry_extraction prompt through the AI Gateway and stores
the structured result in the enquiry_extractions table.

Responsibilities:
- Build gateway request with freeform_text context
- Call AIGateway.run() — the only LLM entry point
- Parse parsed_response into EnquiryExtractionOutput if validation passed
- Persist result to enquiry_extractions
- Return stored row ID and parsed output

This service must NOT:
- Make pricing decisions
- Check room availability
- Write customer-facing copy
- Call any LLM provider directly
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.modules.ai.constants import (
    TRIGGER_SOURCE_API,
    TRIGGER_TYPE_EXTRACTION,
)
from app.modules.ai.gateway import AIGateway
from app.modules.ai.schemas import AIGatewayRequest
from app.modules.enquiries.occasion_normalisation_service import OccasionNormalisationService

# EnquiryExtraction is added by DATA-015.  Use a lazy import so the service
# module is importable in test environments that run against the unpatched schema.
try:
    from app.modules.enquiries.models import EnquiryExtraction
except ImportError:  # pragma: no cover
    EnquiryExtraction = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

PROMPT_KEY_ENQUIRY_EXTRACTION = "enquiry_extraction"

# Allowed trigger types for extraction calls
EXTRACTION_TRIGGER_FREEFORM_WEBFORM = "freeform_webform_submitted"
EXTRACTION_TRIGGER_INBOUND_EMAIL = "inbound_email_received"
EXTRACTION_TRIGGER_MANUAL_REEXTRACT = "manual_reextract"

VALID_TRIGGER_TYPES = {
    EXTRACTION_TRIGGER_FREEFORM_WEBFORM,
    EXTRACTION_TRIGGER_INBOUND_EMAIL,
    EXTRACTION_TRIGGER_MANUAL_REEXTRACT,
}


@dataclass
class ExtractionRequest:
    """Input to the EnquiryExtractionService."""

    enquiry_id: uuid.UUID
    freeform_text: str
    restaurant_name: str
    trigger_type: str = EXTRACTION_TRIGGER_FREEFORM_WEBFORM
    restaurant_id: uuid.UUID | None = field(default=None)
    source_message_id: uuid.UUID | None = field(default=None)
    tenant_id: str | None = field(default=None)
    api_key: str = field(default="")


@dataclass
class ExtractionResult:
    """Output of the EnquiryExtractionService.

    extraction_id is set when the row was persisted successfully.
    is_fallback is True when no LLM call was made.
    parsed holds the validated extraction dict, or None on parse/validation error.
    rendered_system_prompt / rendered_user_prompt / raw_response are populated
    from the gateway result so callers can surface them in transparency panels.
    occasion_canonical is the deterministically normalised occasion value (ENQ-001).
    """

    extraction_id: uuid.UUID | None
    prompt_run_id: uuid.UUID | None
    is_fallback: bool
    validation_status: str
    parsed: dict | None = field(default=None)
    error_message: str | None = field(default=None)
    rendered_system_prompt: str | None = field(default=None)
    rendered_user_prompt: str | None = field(default=None)
    raw_response: str | None = field(default=None)
    # ENQ-001: canonical occasion derived deterministically from parsed.occasion
    occasion_canonical: str | None = field(default=None)


class EnquiryExtractionService:
    """Runs enquiry extraction via the AI Gateway and persists the result.

    Example::

        service = EnquiryExtractionService(db=db)
        result = service.extract(ExtractionRequest(
            enquiry_id=enquiry.id,
            freeform_text="I'd like to book a private room for 20 guests...",
            restaurant_name="The Grand Ballroom",
        ))
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        """Run extraction and persist the result.

        Always returns an ExtractionResult — never raises.
        On gateway error or validation failure, persists a partial row and
        returns an ExtractionResult with error_message set.
        """
        if request.trigger_type not in VALID_TRIGGER_TYPES:
            logger.warning(
                "Unknown extraction trigger type %r — defaulting to freeform_webform_submitted",
                request.trigger_type,
            )

        gateway = AIGateway(db=self._db, api_key=request.api_key)

        gateway_request = AIGatewayRequest(
            prompt_key=PROMPT_KEY_ENQUIRY_EXTRACTION,
            input_payload={
                "restaurant_name": request.restaurant_name,
                "freeform_text": request.freeform_text,
            },
            tenant_id=request.tenant_id,
            restaurant_id=request.restaurant_id,
            enquiry_id=request.enquiry_id,
            trigger_type=request.trigger_type,
            trigger_source=TRIGGER_SOURCE_API,
        )

        gateway_result = gateway.run(gateway_request)

        # Build the extraction row from the gateway result
        extraction = self._persist_extraction(request, gateway_result)

        # ENQ-001: derive canonical occasion from raw LLM output
        _occasion_svc = OccasionNormalisationService()
        _occasion_raw = (gateway_result.parsed_response or {}).get("occasion")
        _occasion_canonical = _occasion_svc.normalise(_occasion_raw)

        return ExtractionResult(
            extraction_id=extraction.id if extraction is not None else None,
            prompt_run_id=gateway_result.run_id,
            is_fallback=gateway_result.is_fallback,
            validation_status=gateway_result.validation_status,
            parsed=gateway_result.parsed_response,
            error_message=gateway_result.error_message,
            rendered_system_prompt=gateway_result.rendered_system_prompt,
            rendered_user_prompt=gateway_result.rendered_user_prompt,
            raw_response=gateway_result.raw_response,
            occasion_canonical=_occasion_canonical,
        )

    def _persist_extraction(
        self,
        request: ExtractionRequest,
        gateway_result,
    ) -> EnquiryExtraction | None:
        """Persist an EnquiryExtraction row and return it.

        On DB error, logs and returns None — the caller still gets a result.
        """
        parsed = gateway_result.parsed_response or {}
        missing_fields: list[str] = parsed.get("missing_fields", []) if parsed else []
        confidence_json: dict = parsed.get("confidence", {}) if parsed else {}

        # normalized_json: a copy of parsed_response with type-safe guest_count
        # and canonical occasion added by OccasionNormalisationService (ENQ-001).
        normalized: dict | None = None
        if parsed:
            normalized = dict(parsed)
            if normalized.get("guest_count") is not None:
                try:
                    normalized["guest_count"] = int(normalized["guest_count"])
                except (TypeError, ValueError):
                    normalized["guest_count"] = None
            # ENQ-001: add occasion_canonical alongside the raw occasion string
            _occasion_svc = OccasionNormalisationService()
            normalized["occasion_canonical"] = _occasion_svc.normalise(
                normalized.get("occasion")
            )

        try:
            if EnquiryExtraction is None:  # DATA-015 not yet applied
                logger.warning("EnquiryExtraction model not available — skipping persistence")
                return None
            extraction = EnquiryExtraction(
                id=uuid.uuid4(),
                tenant_id=request.tenant_id,
                enquiry_id=request.enquiry_id,
                source_message_id=request.source_message_id,
                prompt_run_id=gateway_result.run_id,
                extracted_json=parsed if parsed else None,
                normalized_json=normalized,
                missing_fields=missing_fields if missing_fields else None,
                confidence_json=confidence_json if confidence_json else None,
            )
            self._db.add(extraction)
            self._db.flush()
            return extraction
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to persist enquiry extraction for enquiry %s: %s",
                request.enquiry_id,
                exc,
            )
            return None
