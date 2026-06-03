"""Tests for DiagnosticsAggregator (ENQ-005)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.modules.enquiries.diagnostics_aggregator import (
    CRITICAL_FIELDS,
    DiagnosticsAggregator,
    ExtractionDiagnostics,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_extraction(
    *,
    extracted_json: dict | None = None,
    normalized_json: dict | None = None,
    missing_fields: list[str] | None = None,
    prompt_run_id: uuid.UUID | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.prompt_run_id = prompt_run_id or uuid.uuid4()
    row.extracted_json = extracted_json
    row.normalized_json = normalized_json
    row.missing_fields = missing_fields
    row.validation_status = None
    row.created_at = datetime(2026, 6, 3, 12, 0, 0, tzinfo=timezone.utc)
    return row


_ENQUIRY_ID = uuid.uuid4()


# ── No extraction ─────────────────────────────────────────────────────────────


class TestNoExtraction:
    def setup_method(self) -> None:
        self.agg = DiagnosticsAggregator()

    def test_returns_insufficient_information_when_no_extraction(self) -> None:
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=None)
        assert diag.readiness_status == "INSUFFICIENT_INFORMATION"

    def test_extraction_id_is_none_when_no_extraction(self) -> None:
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=None)
        assert diag.extraction_id is None

    def test_prompt_run_id_is_none_when_no_extraction(self) -> None:
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=None)
        assert diag.prompt_run_id is None

    def test_all_critical_fields_missing_when_no_extraction(self) -> None:
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=None)
        assert set(diag.missing_critical_fields) == CRITICAL_FIELDS
        assert diag.has_missing_critical_fields is True

    def test_enquiry_id_preserved_when_no_extraction(self) -> None:
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=None)
        assert diag.enquiry_id == _ENQUIRY_ID

    def test_never_raises_on_none_extraction(self) -> None:
        # Should never raise regardless of enquiry_id type
        diag = self.agg.aggregate(enquiry_id=uuid.uuid4(), extraction=None)
        assert isinstance(diag, ExtractionDiagnostics)


# ── Missing critical fields ───────────────────────────────────────────────────


class TestMissingCriticalFields:
    def setup_method(self) -> None:
        self.agg = DiagnosticsAggregator()

    def test_no_missing_fields_when_date_and_count_present(self) -> None:
        row = _make_extraction(missing_fields=[])
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.missing_critical_fields == []
        assert diag.has_missing_critical_fields is False

    def test_date_missing(self) -> None:
        row = _make_extraction(missing_fields=["date"])
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert "date" in diag.missing_critical_fields
        assert diag.has_missing_critical_fields is True

    def test_guest_count_missing(self) -> None:
        row = _make_extraction(missing_fields=["guest_count"])
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert "guest_count" in diag.missing_critical_fields
        assert diag.has_missing_critical_fields is True

    def test_non_critical_missing_fields_excluded(self) -> None:
        row = _make_extraction(missing_fields=["occasion", "meal_period"])
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.missing_critical_fields == []
        assert diag.has_missing_critical_fields is False

    def test_none_missing_fields_treated_as_empty(self) -> None:
        row = _make_extraction(missing_fields=None)
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.missing_critical_fields == []
        assert diag.has_missing_critical_fields is False


# ── Occasion normalisation ────────────────────────────────────────────────────


class TestOccasionNormalisation:
    def setup_method(self) -> None:
        self.agg = DiagnosticsAggregator()

    def test_reads_stored_occasion_canonical(self) -> None:
        row = _make_extraction(
            extracted_json={"occasion": "birthday dinner"},
            normalized_json={"occasion_canonical": "birthday"},
        )
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.occasion_raw == "birthday dinner"
        assert diag.occasion_canonical == "birthday"
        assert diag.occasion_normalised is True

    def test_occasion_normalised_false_when_no_occasion(self) -> None:
        row = _make_extraction(
            extracted_json={},
            normalized_json={},
        )
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.occasion_raw is None
        assert diag.occasion_normalised is False

    def test_occasion_raw_from_extracted_json(self) -> None:
        row = _make_extraction(
            extracted_json={"occasion": "team lunch"},
            normalized_json={},
        )
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.occasion_raw == "team lunch"

    def test_occasion_normalised_true_when_canonical_stored(self) -> None:
        row = _make_extraction(
            extracted_json={"occasion": "anniversary"},
            normalized_json={"occasion_canonical": "anniversary"},
        )
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.occasion_normalised is True


# ── Date context warnings ─────────────────────────────────────────────────────


class TestDateContextWarnings:
    def setup_method(self) -> None:
        self.agg = DiagnosticsAggregator()

    def test_reads_stored_date_context_warnings(self) -> None:
        warnings = ["month expected but not found for date_range type"]
        row = _make_extraction(
            extracted_json={},
            normalized_json={"date_context_warnings": warnings},
        )
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.date_context_warnings == warnings
        assert diag.date_ambiguity_detected is True

    def test_no_ambiguity_when_no_warnings(self) -> None:
        row = _make_extraction(
            extracted_json={},
            normalized_json={"date_context_warnings": []},
        )
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.date_context_warnings == []
        assert diag.date_ambiguity_detected is False

    def test_no_ambiguity_when_warnings_absent_from_normalized(self) -> None:
        row = _make_extraction(
            extracted_json={},
            normalized_json={},
        )
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.date_ambiguity_detected is False

    def test_multiple_warnings_all_included(self) -> None:
        warnings = ["missing month", "missing year", "missing weekdays"]
        row = _make_extraction(
            extracted_json={},
            normalized_json={"date_context_warnings": warnings},
        )
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert len(diag.date_context_warnings) == 3


# ── Date clarification ────────────────────────────────────────────────────────


class TestDateClarification:
    def setup_method(self) -> None:
        self.agg = DiagnosticsAggregator()

    def test_date_clarification_required_true(self) -> None:
        row = _make_extraction(
            extracted_json={
                "date_request": {
                    "requires_date_clarification": True,
                    "clarification_question": "Which weekend in July?",
                }
            },
            normalized_json={},
        )
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.date_clarification_required is True
        assert diag.clarification_question == "Which weekend in July?"

    def test_date_clarification_false_when_not_required(self) -> None:
        row = _make_extraction(
            extracted_json={
                "date_request": {
                    "requires_date_clarification": False,
                    "date_request_type": "exact",
                }
            },
            normalized_json={},
        )
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.date_clarification_required is False
        assert diag.clarification_question is None

    def test_no_clarification_when_no_date_request(self) -> None:
        row = _make_extraction(extracted_json={}, normalized_json={})
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.date_clarification_required is False
        assert diag.clarification_question is None


# ── Readiness outcome ─────────────────────────────────────────────────────────


class TestReadinessOutcome:
    def setup_method(self) -> None:
        self.agg = DiagnosticsAggregator()

    def test_reads_stored_readiness_evaluation(self) -> None:
        readiness = {
            "status": "READY_FOR_AVAILABILITY",
            "missing_for_availability": [],
            "notes": "All good.",
            "date_understood": True,
            "guest_count_present": True,
            "occasion_understood": True,
            "meal_period_present": True,
            "audience_identified": False,
            "date_clarification_required": False,
            "availability_check_possible": True,
        }
        row = _make_extraction(
            extracted_json={},
            normalized_json={"readiness_evaluation": readiness},
        )
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.readiness_status == "READY_FOR_AVAILABILITY"
        assert diag.readiness_missing_for_availability == []
        assert diag.readiness_notes == "All good."

    def test_needs_clarification_status_propagated(self) -> None:
        readiness = {
            "status": "NEEDS_CLARIFICATION",
            "missing_for_availability": ["date"],
            "notes": "Date not understood.",
            "date_understood": False,
            "guest_count_present": True,
            "occasion_understood": False,
            "meal_period_present": False,
            "audience_identified": False,
            "date_clarification_required": False,
            "availability_check_possible": False,
        }
        row = _make_extraction(
            extracted_json={},
            normalized_json={"readiness_evaluation": readiness},
        )
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.readiness_status == "NEEDS_CLARIFICATION"
        assert "date" in diag.readiness_missing_for_availability

    def test_falls_back_to_re_evaluation_when_no_stored_readiness(self) -> None:
        row = _make_extraction(
            extracted_json={},
            normalized_json={},
        )
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        # Falls back to EnquiryReadinessEvaluator — empty extraction → INSUFFICIENT
        assert diag.readiness_status == "INSUFFICIENT_INFORMATION"

    def test_missing_for_availability_list_propagated(self) -> None:
        readiness = {
            "status": "NEEDS_CLARIFICATION",
            "missing_for_availability": ["date", "guest_count"],
            "notes": "Both missing.",
            "date_understood": False,
            "guest_count_present": False,
            "occasion_understood": False,
            "meal_period_present": False,
            "audience_identified": False,
            "date_clarification_required": False,
            "availability_check_possible": False,
        }
        row = _make_extraction(
            extracted_json={},
            normalized_json={"readiness_evaluation": readiness},
        )
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert set(diag.readiness_missing_for_availability) == {"date", "guest_count"}


# ── Metadata ──────────────────────────────────────────────────────────────────


class TestMetadata:
    def setup_method(self) -> None:
        self.agg = DiagnosticsAggregator()

    def test_extraction_id_populated(self) -> None:
        row = _make_extraction()
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.extraction_id == row.id

    def test_prompt_run_id_populated(self) -> None:
        run_id = uuid.uuid4()
        row = _make_extraction(prompt_run_id=run_id)
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.prompt_run_id == run_id

    def test_created_at_populated(self) -> None:
        row = _make_extraction()
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.created_at == datetime(2026, 6, 3, 12, 0, 0, tzinfo=timezone.utc)

    def test_is_fallback_false_for_stored_extraction(self) -> None:
        row = _make_extraction()
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        assert diag.is_fallback is False

    def test_enquiry_id_preserved(self) -> None:
        eid = uuid.uuid4()
        row = _make_extraction()
        diag = self.agg.aggregate(enquiry_id=eid, extraction=row)
        assert diag.enquiry_id == eid


# ── to_dict ───────────────────────────────────────────────────────────────────


class TestToDict:
    def setup_method(self) -> None:
        self.agg = DiagnosticsAggregator()

    def test_to_dict_returns_dict(self) -> None:
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=None)
        result = diag.to_dict()
        assert isinstance(result, dict)

    def test_to_dict_has_all_required_keys(self) -> None:
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=None)
        result = diag.to_dict()
        required = {
            "enquiry_id",
            "extraction_id",
            "prompt_run_id",
            "missing_critical_fields",
            "has_missing_critical_fields",
            "occasion_raw",
            "occasion_canonical",
            "occasion_normalised",
            "date_context_warnings",
            "date_ambiguity_detected",
            "date_clarification_required",
            "clarification_question",
            "readiness_status",
            "readiness_missing_for_availability",
            "readiness_notes",
            "validation_status",
            "is_fallback",
            "created_at",
        }
        assert required.issubset(result.keys())

    def test_to_dict_enquiry_id_is_string(self) -> None:
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=None)
        result = diag.to_dict()
        assert isinstance(result["enquiry_id"], str)

    def test_to_dict_extraction_id_none_when_no_extraction(self) -> None:
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=None)
        result = diag.to_dict()
        assert result["extraction_id"] is None

    def test_to_dict_extraction_id_is_string_when_set(self) -> None:
        row = _make_extraction()
        diag = self.agg.aggregate(enquiry_id=_ENQUIRY_ID, extraction=row)
        result = diag.to_dict()
        assert isinstance(result["extraction_id"], str)
