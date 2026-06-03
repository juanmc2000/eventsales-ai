"""Extraction Quality Diagnostics Aggregator (ENQ-005).

Aggregates per-enquiry extraction quality signals into a single diagnostic
view. All data is read from a stored EnquiryExtraction row; no LLM calls are
made.

Signals aggregated:

- missing_critical_fields   — from extraction.missing_fields column
- occasion normalisation     — raw vs canonical occasion values
- date context warnings      — from normalized_json['date_context_warnings']
- date ambiguity             — from extracted_json date_request block
- readiness outcome          — from normalized_json['readiness_evaluation']

The aggregator never raises. On missing or malformed data it falls back to
safe defaults and records a note.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


# ── Constants ─────────────────────────────────────────────────────────────────

# Critical fields that must be present for availability checking
CRITICAL_FIELDS = {"date", "guest_count"}


# ── Result dataclass ──────────────────────────────────────────────────────────


@dataclass
class ExtractionDiagnostics:
    """Aggregated extraction quality diagnostics for a single enquiry.

    Stored values from normalized_json are preferred; computed fallbacks are
    used when fields are absent (e.g. extraction pre-dates a new normalisation
    step).
    """

    enquiry_id: uuid.UUID
    extraction_id: uuid.UUID | None

    # Prompt run linkage — enables tracing back to the raw LLM call
    prompt_run_id: uuid.UUID | None

    # ── Missing critical fields ───────────────────────────────────────────────
    # Populated from the extraction.missing_fields column
    missing_critical_fields: list[str] = field(default_factory=list)
    has_missing_critical_fields: bool = False

    # ── Occasion normalisation ────────────────────────────────────────────────
    occasion_raw: str | None = None
    occasion_canonical: str | None = None
    # True when a canonical value was derived (even if it is "other")
    occasion_normalised: bool = False

    # ── Date context warnings ─────────────────────────────────────────────────
    # Populated from normalized_json['date_context_warnings'] (ENQ-003)
    date_context_warnings: list[str] = field(default_factory=list)
    date_ambiguity_detected: bool = False

    # ── Date clarification ────────────────────────────────────────────────────
    # From extracted_json.date_request.requires_date_clarification
    date_clarification_required: bool = False
    clarification_question: str | None = None

    # ── Readiness outcome ─────────────────────────────────────────────────────
    # From normalized_json['readiness_evaluation'] (ENQ-004)
    readiness_status: str = "UNKNOWN"
    readiness_missing_for_availability: list[str] = field(default_factory=list)
    readiness_notes: str = ""

    # ── Extraction metadata ───────────────────────────────────────────────────
    validation_status: str | None = None
    is_fallback: bool = False
    created_at: datetime | None = None

    def to_dict(self) -> dict:
        """Serialise to a plain dict for JSON responses."""
        return {
            "enquiry_id": str(self.enquiry_id),
            "extraction_id": str(self.extraction_id) if self.extraction_id else None,
            "prompt_run_id": str(self.prompt_run_id) if self.prompt_run_id else None,
            "missing_critical_fields": self.missing_critical_fields,
            "has_missing_critical_fields": self.has_missing_critical_fields,
            "occasion_raw": self.occasion_raw,
            "occasion_canonical": self.occasion_canonical,
            "occasion_normalised": self.occasion_normalised,
            "date_context_warnings": self.date_context_warnings,
            "date_ambiguity_detected": self.date_ambiguity_detected,
            "date_clarification_required": self.date_clarification_required,
            "clarification_question": self.clarification_question,
            "readiness_status": self.readiness_status,
            "readiness_missing_for_availability": self.readiness_missing_for_availability,
            "readiness_notes": self.readiness_notes,
            "validation_status": self.validation_status,
            "is_fallback": self.is_fallback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── Aggregator ────────────────────────────────────────────────────────────────


class DiagnosticsAggregator:
    """Build an ExtractionDiagnostics from a stored EnquiryExtraction row.

    Usage::

        agg = DiagnosticsAggregator()
        diag = agg.aggregate(enquiry_id=enquiry.id, extraction=latest_extraction)
        # diag.readiness_status → "READY_FOR_AVAILABILITY"
    """

    def aggregate(
        self,
        enquiry_id: uuid.UUID,
        extraction,  # EnquiryExtraction ORM row or None
    ) -> ExtractionDiagnostics:
        """Aggregate diagnostics from a stored extraction row.

        When extraction is None (no extraction has been run), returns a minimal
        diagnostics object with readiness_status=INSUFFICIENT_INFORMATION.
        Never raises.
        """
        if extraction is None:
            return ExtractionDiagnostics(
                enquiry_id=enquiry_id,
                extraction_id=None,
                prompt_run_id=None,
                missing_critical_fields=list(CRITICAL_FIELDS),
                has_missing_critical_fields=True,
                readiness_status="INSUFFICIENT_INFORMATION",
                readiness_notes="No extraction has been run for this enquiry.",
            )

        extracted: dict = extraction.extracted_json or {}
        normalized: dict = extraction.normalized_json or {}
        stored_missing: list = extraction.missing_fields or []

        diag = ExtractionDiagnostics(
            enquiry_id=enquiry_id,
            extraction_id=extraction.id,
            prompt_run_id=extraction.prompt_run_id,
            validation_status=getattr(extraction, "validation_status", None),
            is_fallback=False,  # extraction rows are never fallbacks
            created_at=extraction.created_at,
        )

        # ── Missing critical fields ───────────────────────────────────────────
        missing_critical = [f for f in stored_missing if f in CRITICAL_FIELDS]
        diag.missing_critical_fields = missing_critical
        diag.has_missing_critical_fields = bool(missing_critical)

        # ── Occasion normalisation ────────────────────────────────────────────
        # Prefer normalized_json['occasion_canonical'] (stored by ENQ-001).
        # Fall back to re-computing from extracted_json when absent.
        diag.occasion_raw = extracted.get("occasion") or normalized.get("occasion")
        diag.occasion_canonical = normalized.get("occasion_canonical")
        if diag.occasion_canonical is None and diag.occasion_raw:
            # ENQ-001 normaliser not applied — compute on-the-fly
            try:
                from app.modules.enquiries.occasion_normalisation_service import (  # noqa: PLC0415
                    OccasionNormalisationService,
                )
                diag.occasion_canonical = OccasionNormalisationService().normalise(
                    diag.occasion_raw
                )
            except ImportError:
                pass
        diag.occasion_normalised = diag.occasion_canonical is not None

        # ── Date context warnings ─────────────────────────────────────────────
        # Prefer stored list from normalized_json (ENQ-003).
        # Fall back to re-validating from extracted_json when absent.
        stored_warnings = normalized.get("date_context_warnings")
        if isinstance(stored_warnings, list):
            diag.date_context_warnings = stored_warnings
        elif extracted.get("date_request"):
            try:
                from app.modules.enquiries.date_context_validator import (  # noqa: PLC0415
                    DateContextValidator,
                )
                diag.date_context_warnings = DateContextValidator().validate(
                    extracted.get("date_request")
                )
            except ImportError:
                pass
        diag.date_ambiguity_detected = bool(diag.date_context_warnings)

        # ── Date clarification ────────────────────────────────────────────────
        date_request: dict = extracted.get("date_request") or {}
        diag.date_clarification_required = bool(
            date_request.get("requires_date_clarification", False)
        )
        diag.clarification_question = date_request.get("clarification_question")

        # ── Readiness outcome ─────────────────────────────────────────────────
        # Prefer stored readiness_evaluation from normalized_json (ENQ-004).
        # Fall back to re-evaluating from extracted_json when absent.
        stored_readiness = normalized.get("readiness_evaluation")
        if isinstance(stored_readiness, dict) and "status" in stored_readiness:
            diag.readiness_status = stored_readiness["status"]
            diag.readiness_missing_for_availability = stored_readiness.get(
                "missing_for_availability", []
            )
            diag.readiness_notes = stored_readiness.get("notes", "")
        else:
            try:
                from app.modules.enquiries.readiness_evaluator import (  # noqa: PLC0415
                    EnquiryReadinessEvaluator,
                )
                evaluation = EnquiryReadinessEvaluator().evaluate(extracted or None)
                diag.readiness_status = evaluation.status
                diag.readiness_missing_for_availability = evaluation.missing_for_availability
                diag.readiness_notes = evaluation.notes
            except ImportError:
                diag.readiness_status = "UNKNOWN"

        return diag
