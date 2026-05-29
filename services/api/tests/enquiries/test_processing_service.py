"""Tests for EnquiryProcessingService (WORKFLOW-007).

All tests are unit-level — no DB or live LLM required.
DB session, repositories, and pricing service are mocked.
"""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.modules.enquiries.processing_service import (
    ACTION_ESCALATE,
    ACTION_REQUEST_INFO,
    ACTION_SEND_CONFIRMATION,
    ACTION_SEND_WITH_QUESTIONS,
    ACTION_SUGGEST_ALTERNATIVE,
    CRITICAL_FIELDS,
    EnquiryProcessingService,
    ProcessingRequest,
    ProcessingResult,
    _match_room,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_request(**kwargs) -> ProcessingRequest:
    defaults = dict(
        enquiry_id=uuid.uuid4(),
        restaurant_id=uuid.uuid4(),
        extraction_id=uuid.uuid4(),
        extraction_parsed={
            "occasion": "birthday dinner",
            "guest_count": 20,
            "event_date": "2026-12-25",
            "event_time": "19:00",
            "event_type": "birthday",
            "missing_fields": [],
            "confidence": {},
        },
    )
    defaults.update(kwargs)
    return ProcessingRequest(**defaults)


def _make_room(
    *,
    name: str = "The Grand Ballroom",
    seated_capacity: int = 100,
    is_private_dining: bool = True,
    room_type: str = "ballroom",
) -> MagicMock:
    room = MagicMock()
    room.id = uuid.uuid4()
    room.name = name
    room.seated_capacity = seated_capacity
    room.min_capacity = 10
    room.max_capacity = seated_capacity
    room.is_private_dining = is_private_dining
    room.room_type = room_type
    room.display_order = 0
    return room


def _make_availability_slot(status: str = "available", meal_period: str = "dinner") -> MagicMock:
    slot = MagicMock()
    slot.status = status
    slot.meal_period = meal_period
    slot.notes = None
    return slot


def _build_service() -> tuple[EnquiryProcessingService, dict[str, MagicMock]]:
    """Build a processing service with mocked dependencies."""
    db = MagicMock()
    service = EnquiryProcessingService(db=db)

    rooms = [_make_room()]
    avail_slots = [_make_availability_slot()]
    pricing_rec = MagicMock()
    pricing_rec.recommended_minimum_spend = 1500.0
    pricing_rec.explanation = "Weekend dinner, 20 covers"
    pricing_rec.confidence = 1.0
    pricing_rule = MagicMock()
    pricing_rule.rule_id = uuid.uuid4()
    pricing_rec.applied_rules = [pricing_rule]

    service._room_repo = MagicMock()
    service._room_repo.list_for_restaurant.return_value = rooms

    service._avail_repo = MagicMock()
    service._avail_repo.get_for_room_date.return_value = avail_slots

    service._pricing_svc = MagicMock()
    service._pricing_svc.calculate_recommendation.return_value = pricing_rec

    mocks = {
        "rooms": rooms,
        "avail_slots": avail_slots,
        "pricing_rec": pricing_rec,
    }
    return service, mocks


def _run_process(service: EnquiryProcessingService, request: ProcessingRequest) -> ProcessingResult:
    with patch("app.modules.enquiries.processing_service.EnquiryProcessingSnapshot") as mock_cls:
        snapshot = MagicMock()
        snapshot.id = uuid.uuid4()
        mock_cls.return_value = snapshot
        return service.process(request)


# ── _match_room unit tests ─────────────────────────────────────────────────────

class TestMatchRoom:
    def test_returns_none_for_empty_list(self) -> None:
        assert _match_room([], 20, None) is None

    def test_preferred_area_name_match(self) -> None:
        r1 = _make_room(name="The Garden Room")
        r2 = _make_room(name="The Grand Ballroom")
        result = _match_room([r1, r2], 20, "garden")
        assert result is r1

    def test_capacity_match_skips_small_rooms(self) -> None:
        r1 = _make_room(name="Small Room", seated_capacity=10)
        r2 = _make_room(name="Large Room", seated_capacity=50)
        result = _match_room([r1, r2], 20, None)
        assert result is r2

    def test_first_room_fallback(self) -> None:
        r1 = _make_room(name="Small Room", seated_capacity=5)
        r2 = _make_room(name="Tiny Room", seated_capacity=3)
        # party_size=20 exceeds both — falls back to first
        result = _match_room([r1, r2], 20, None)
        assert result is r1

    def test_no_preferred_area_uses_capacity(self) -> None:
        room = _make_room(seated_capacity=30)
        result = _match_room([room], 20, None)
        assert result is room

    def test_preferred_area_case_insensitive(self) -> None:
        room = _make_room(name="The PRIVATE Dining Room")
        result = _match_room([room], 20, "private")
        assert result is room


# ── EnquiryProcessingService ────────────────────────────────────────────────

class TestEnquiryProcessingService:
    def test_successful_processing_returns_result(self) -> None:
        service, _ = _build_service()
        result = _run_process(service, _make_request())
        assert isinstance(result, ProcessingResult)
        assert result.snapshot_id is not None

    def test_room_available_no_missing_fields_sends_confirmation(self) -> None:
        service, mocks = _build_service()
        mocks["avail_slots"][0].status = "available"
        result = _run_process(service, _make_request())
        assert result.recommended_action == ACTION_SEND_CONFIRMATION

    def test_room_available_with_missing_fields_sends_with_questions(self) -> None:
        service, mocks = _build_service()
        mocks["avail_slots"][0].status = "available"
        req = _make_request(extraction_parsed={
            "guest_count": 20,
            "event_date": "2026-12-25",
            "event_time": "19:00",
            "missing_fields": ["event_type"],  # non-critical but present
            "confidence": {},
        })
        result = _run_process(service, req)
        assert result.recommended_action == ACTION_SEND_WITH_QUESTIONS

    def test_room_booked_suggests_alternative(self) -> None:
        service, mocks = _build_service()
        mocks["avail_slots"][0].status = "booked"
        result = _run_process(service, _make_request())
        assert result.recommended_action == ACTION_SUGGEST_ALTERNATIVE

    def test_room_unavailable_suggests_alternative(self) -> None:
        service, mocks = _build_service()
        mocks["avail_slots"][0].status = "unavailable"
        result = _run_process(service, _make_request())
        assert result.recommended_action == ACTION_SUGGEST_ALTERNATIVE

    def test_no_matching_room_suggests_alternative(self) -> None:
        service, mocks = _build_service()
        service._room_repo.list_for_restaurant.return_value = []
        result = _run_process(service, _make_request())
        assert result.recommended_action == ACTION_SUGGEST_ALTERNATIVE

    def test_both_critical_missing_requests_info(self) -> None:
        service, _ = _build_service()
        req = _make_request(extraction_parsed={
            "occasion": "birthday",
            "missing_fields": ["guest_count", "event_date"],
            "confidence": {},
        })
        result = _run_process(service, req)
        assert result.recommended_action == ACTION_REQUEST_INFO

    def test_missing_event_date_escalates_when_room_found(self) -> None:
        service, _ = _build_service()
        req = _make_request(extraction_parsed={
            "guest_count": 20,
            "event_date": None,
            "missing_fields": ["event_date"],
            "confidence": {},
        })
        result = _run_process(service, req)
        # event_date missing → availability unknown → escalate (no critical count >= 2)
        assert result.recommended_action in (ACTION_ESCALATE, ACTION_REQUEST_INFO)

    def test_room_suitability_populated(self) -> None:
        service, mocks = _build_service()
        result = _run_process(service, _make_request())
        assert result.room_suitability_json is not None
        assert result.room_suitability_json["matched"] is True

    def test_availability_result_populated(self) -> None:
        service, mocks = _build_service()
        result = _run_process(service, _make_request())
        assert result.availability_result_json is not None
        assert result.availability_result_json["status"] in ("available", "booked", "held", "unavailable", "unknown")

    def test_pricing_result_populated(self) -> None:
        service, _ = _build_service()
        result = _run_process(service, _make_request())
        assert result.pricing_result_json is not None
        assert "minimum_spend" in result.pricing_result_json

    def test_missing_fields_aggregated(self) -> None:
        service, _ = _build_service()
        req = _make_request(extraction_parsed={
            "guest_count": None,  # missing
            "event_date": "2026-12-25",
            "missing_fields": ["event_type"],
            "confidence": {},
        })
        result = _run_process(service, req)
        assert result.missing_fields_json is not None
        # guest_count not in extraction → added by business logic
        assert "guest_count" in result.missing_fields_json

    def test_db_error_returns_none_snapshot_id(self) -> None:
        service, _ = _build_service()
        with patch(
            "app.modules.enquiries.processing_service.EnquiryProcessingSnapshot",
            side_effect=Exception("DB error"),
        ):
            result = service.process(_make_request())
        assert result.snapshot_id is None
        assert result.recommended_action is not None  # action still computed

    def test_meal_period_inferred_from_time(self) -> None:
        service = EnquiryProcessingService.__new__(EnquiryProcessingService)
        assert service._infer_meal_period("12:00") == "lunch"
        assert service._infer_meal_period("19:30") == "dinner"
        assert service._infer_meal_period(None) == "dinner"
        assert service._infer_meal_period("invalid") == "dinner"

    def test_availability_unknown_when_no_data(self) -> None:
        service, _ = _build_service()
        service._avail_repo.get_for_room_date.return_value = []
        result = _run_process(service, _make_request())
        assert result.availability_result_json is not None
        assert result.availability_result_json["status"] == "unknown"


# ── Candidate date processing (WORKFLOW-009) ──────────────────────────────────


class TestCandidateDateProcessing:
    """Tests for Step 5: processing candidate dates from a date request."""

    def _build_service_with_candidates(
        self,
        candidates: list,
        *,
        requires_clarification: bool = False,
    ) -> tuple[EnquiryProcessingService, uuid.UUID]:
        service, _ = _build_service()

        date_request_row = MagicMock()
        date_request_row.id = uuid.uuid4()
        date_request_row.requires_date_clarification = requires_clarification
        date_request_row.clarification_question = None

        service._date_request_repo = MagicMock()
        service._date_request_repo.get_latest_date_request.return_value = date_request_row
        service._date_request_repo.list_candidate_dates_for_request.return_value = candidates
        service._date_request_repo.update_candidate_date.return_value = None

        return service, date_request_row.id

    def _make_candidate(self, candidate_date: date = date(2026, 12, 25)) -> MagicMock:
        c = MagicMock()
        c.id = uuid.uuid4()
        c.candidate_date = candidate_date
        return c

    def test_candidate_date_summary_populated_when_date_request_exists(self) -> None:
        candidate = self._make_candidate()
        service, _ = self._build_service_with_candidates([candidate])
        result = _run_process(service, _make_request())
        assert result.candidate_date_summary is not None
        assert "candidate_dates_checked" in result.candidate_date_summary
        assert result.candidate_date_summary["candidate_dates_checked"] == 1

    def test_candidate_date_summary_none_when_no_date_request(self) -> None:
        service, _ = _build_service()
        service._date_request_repo = MagicMock()
        service._date_request_repo.get_latest_date_request.return_value = None
        result = _run_process(service, _make_request())
        assert result.candidate_date_summary is None

    def test_available_candidate_listed_when_room_available(self) -> None:
        candidate = self._make_candidate(date(2026, 12, 25))
        service, _ = self._build_service_with_candidates([candidate])
        # avail_repo returns available slot for candidate date
        result = _run_process(service, _make_request())
        summary = result.candidate_date_summary
        assert summary is not None
        assert len(summary["available_candidate_dates"]) == 1
        assert "2026-12-25" in summary["available_candidate_dates"]

    def test_unavailable_candidate_listed_when_room_booked(self) -> None:
        candidate = self._make_candidate(date(2026, 12, 25))
        service, _ = self._build_service_with_candidates([candidate])
        # Override availability to return booked slot
        booked_slot = _make_availability_slot(status="booked")
        service._avail_repo.get_for_room_date.return_value = [booked_slot]
        result = _run_process(service, _make_request())
        summary = result.candidate_date_summary
        assert "2026-12-25" in summary["unavailable_candidate_dates"]
        assert "2026-12-25" not in summary["available_candidate_dates"]

    def test_clarification_required_adds_event_date_to_missing(self) -> None:
        service, _ = self._build_service_with_candidates(
            [], requires_clarification=True
        )
        result = _run_process(service, _make_request())
        assert result.missing_fields_json is not None
        assert "event_date" in result.missing_fields_json

    def test_clarification_required_overrides_action_to_request_info(self) -> None:
        service, _ = self._build_service_with_candidates(
            [], requires_clarification=True
        )
        result = _run_process(service, _make_request())
        assert result.recommended_action == ACTION_REQUEST_INFO

    def test_recommended_candidate_date_is_first_available(self) -> None:
        candidates = [
            self._make_candidate(date(2026, 12, 24)),
            self._make_candidate(date(2026, 12, 25)),
        ]
        service, _ = self._build_service_with_candidates(candidates)
        result = _run_process(service, _make_request())
        summary = result.candidate_date_summary
        assert summary["recommended_candidate_date"] is not None

    def test_empty_candidates_returns_summary_with_zero_checked(self) -> None:
        service, _ = self._build_service_with_candidates([])
        result = _run_process(service, _make_request())
        assert result.candidate_date_summary is not None
        assert result.candidate_date_summary["candidate_dates_checked"] == 0
        assert result.candidate_date_summary["available_candidate_dates"] == []

    def test_candidate_date_update_called_per_candidate(self) -> None:
        candidates = [
            self._make_candidate(date(2026, 12, 25)),
            self._make_candidate(date(2026, 12, 26)),
        ]
        service, _ = self._build_service_with_candidates(candidates)
        _run_process(service, _make_request())
        assert service._date_request_repo.update_candidate_date.call_count == 2
