"""Tests for date request and candidate date API endpoints (API-019).

Tests cover:
- GET /enquiries/{id}/date-request/latest
- GET /enquiries/{id}/candidate-dates

All tests are unit/smoke level — no DB or live LLM required.
DB dependencies are mocked via FastAPI dependency overrides.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import app.db.models  # noqa: F401 — registers all models

from app.main import app
from app.db.session import get_db
from app.modules.enquiries.schemas import EnquiryDateRequestOut, EnquiryCandidateDateOut


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_date_request_row(
    enquiry_id: uuid.UUID,
    *,
    date_request_type: str = "month_flexible",
    requires_date_clarification: bool = False,
    clarification_question: str | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.enquiry_id = enquiry_id
    row.extraction_id = uuid.uuid4()
    row.prompt_run_id = None
    row.raw_text = "sometime in August"
    row.date_request_type = date_request_type
    row.anchor_date = date(2026, 5, 29)
    row.timezone = "Europe/London"
    row.extracted_json = {}
    row.requires_date_clarification = requires_date_clarification
    row.clarification_question = clarification_question
    row.confidence = 0.9
    row.created_at = datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc)
    return row


def _make_candidate_row(
    enquiry_id: uuid.UUID,
    date_request_id: uuid.UUID,
    *,
    candidate_date: date = date(2026, 8, 15),
    availability_status: str | None = "available",
    recommended_minimum_spend: float | None = 2500.0,
) -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.enquiry_id = enquiry_id
    row.date_request_id = date_request_id
    row.candidate_date = candidate_date
    row.source_type = "deterministic"
    row.availability_status = availability_status
    row.pricing_checked = True
    row.recommended_minimum_spend = recommended_minimum_spend
    row.ranking_score = None
    row.created_at = datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc)
    return row


def _make_db_with_enquiry(
    enquiry_id: uuid.UUID,
    *,
    has_date_request: bool = True,
    candidates: list | None = None,
    date_request_type: str = "month_flexible",
    requires_date_clarification: bool = False,
) -> MagicMock:
    """Build a mock DB whose repo methods return controlled data."""
    db = MagicMock()

    enquiry = MagicMock()
    enquiry.id = enquiry_id
    enquiry.persona_id = None

    db.get.return_value = enquiry

    date_request_row = None
    if has_date_request:
        date_request_row = _make_date_request_row(
            enquiry_id,
            date_request_type=date_request_type,
            requires_date_clarification=requires_date_clarification,
        )

    # Make db.scalars().first() return the date_request_row
    scalars_mock = MagicMock()
    scalars_mock.first.return_value = date_request_row
    if candidates is not None:
        scalars_mock.all.return_value = candidates
    else:
        scalars_mock.all.return_value = []
    db.scalars.return_value = scalars_mock

    return db


# ── Schema tests ───────────────────────────────────────────────────────────────


class TestEnquiryDateRequestOutSchema:
    def test_minimal_construction(self) -> None:
        out = EnquiryDateRequestOut(
            id=uuid.uuid4(),
            enquiry_id=uuid.uuid4(),
            date_request_type="exact",
            anchor_date=date(2026, 8, 15),
            timezone="Europe/London",
            requires_date_clarification=False,
            confidence=0.95,
            created_at=datetime.now(tz=timezone.utc),
        )
        assert out.raw_text is None
        assert out.extraction_id is None
        assert out.clarification_question is None

    def test_full_construction(self) -> None:
        out = EnquiryDateRequestOut(
            id=uuid.uuid4(),
            enquiry_id=uuid.uuid4(),
            extraction_id=uuid.uuid4(),
            prompt_run_id=uuid.uuid4(),
            raw_text="sometime in August",
            date_request_type="month_flexible",
            anchor_date=date(2026, 5, 29),
            timezone="Europe/London",
            extracted_json={"month": 8},
            requires_date_clarification=True,
            clarification_question="Which week in August?",
            confidence=0.8,
            created_at=datetime.now(tz=timezone.utc),
        )
        assert out.raw_text == "sometime in August"
        assert out.requires_date_clarification is True
        assert out.clarification_question == "Which week in August?"


class TestEnquiryCandidateDateOutSchema:
    def test_minimal_construction(self) -> None:
        out = EnquiryCandidateDateOut(
            id=uuid.uuid4(),
            enquiry_id=uuid.uuid4(),
            date_request_id=uuid.uuid4(),
            candidate_date=date(2026, 8, 15),
            source_type="deterministic",
            pricing_checked=False,
            created_at=datetime.now(tz=timezone.utc),
        )
        assert out.availability_status is None
        assert out.recommended_minimum_spend is None
        assert out.ranking_score is None

    def test_full_construction(self) -> None:
        out = EnquiryCandidateDateOut(
            id=uuid.uuid4(),
            enquiry_id=uuid.uuid4(),
            date_request_id=uuid.uuid4(),
            candidate_date=date(2026, 8, 15),
            source_type="explicit",
            availability_status="available",
            pricing_checked=True,
            recommended_minimum_spend=3000.0,
            ranking_score=0.92,
            created_at=datetime.now(tz=timezone.utc),
        )
        assert out.availability_status == "available"
        assert out.recommended_minimum_spend == 3000.0
        assert out.source_type == "explicit"


# ── GET /enquiries/{id}/date-request/latest ───────────────────────────────────


class TestGetLatestDateRequestEndpoint:
    def test_404_when_enquiry_not_found(self) -> None:
        enquiry_id = uuid.uuid4()
        db = MagicMock()
        db.get.return_value = None  # enquiry not found

        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app)
        try:
            resp = client.get(f"/api/v1/enquiries/{enquiry_id}/date-request/latest")
            assert resp.status_code == 404
            assert "not found" in resp.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_404_when_no_date_request_exists(self) -> None:
        enquiry_id = uuid.uuid4()
        db = _make_db_with_enquiry(enquiry_id, has_date_request=False)

        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app)
        try:
            resp = client.get(f"/api/v1/enquiries/{enquiry_id}/date-request/latest")
            assert resp.status_code == 404
            assert "date request" in resp.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_200_returns_date_request(self) -> None:
        enquiry_id = uuid.uuid4()
        db = _make_db_with_enquiry(enquiry_id, has_date_request=True)

        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app)
        try:
            resp = client.get(f"/api/v1/enquiries/{enquiry_id}/date-request/latest")
            assert resp.status_code == 200
            data = resp.json()
            assert data["date_request_type"] == "month_flexible"
            assert data["requires_date_clarification"] is False
        finally:
            app.dependency_overrides.clear()

    def test_200_returns_clarification_fields_when_present(self) -> None:
        enquiry_id = uuid.uuid4()
        db = _make_db_with_enquiry(
            enquiry_id,
            has_date_request=True,
            requires_date_clarification=True,
        )
        # Add clarification_question to the mock row
        scalars = db.scalars.return_value
        scalars.first.return_value.clarification_question = "Which week in August?"

        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app)
        try:
            resp = client.get(f"/api/v1/enquiries/{enquiry_id}/date-request/latest")
            assert resp.status_code == 200
            data = resp.json()
            assert data["requires_date_clarification"] is True
        finally:
            app.dependency_overrides.clear()

    def test_response_contains_enquiry_id_field(self) -> None:
        enquiry_id = uuid.uuid4()
        db = _make_db_with_enquiry(enquiry_id, has_date_request=True)

        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app)
        try:
            resp = client.get(f"/api/v1/enquiries/{enquiry_id}/date-request/latest")
            assert resp.status_code == 200
            data = resp.json()
            assert "id" in data
            assert "enquiry_id" in data
            assert "created_at" in data
        finally:
            app.dependency_overrides.clear()


# ── GET /enquiries/{id}/candidate-dates ──────────────────────────────────────


class TestListCandidateDatesEndpoint:
    def test_404_when_enquiry_not_found(self) -> None:
        enquiry_id = uuid.uuid4()
        db = MagicMock()
        db.get.return_value = None

        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app)
        try:
            resp = client.get(f"/api/v1/enquiries/{enquiry_id}/candidate-dates")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_200_returns_empty_list_when_no_candidates(self) -> None:
        enquiry_id = uuid.uuid4()
        db = _make_db_with_enquiry(enquiry_id, candidates=[])

        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app)
        try:
            resp = client.get(f"/api/v1/enquiries/{enquiry_id}/candidate-dates")
            assert resp.status_code == 200
            assert resp.json() == []
        finally:
            app.dependency_overrides.clear()

    def test_200_returns_candidate_date_list(self) -> None:
        enquiry_id = uuid.uuid4()
        dr_id = uuid.uuid4()
        candidate = _make_candidate_row(enquiry_id, dr_id, candidate_date=date(2026, 8, 15))
        db = _make_db_with_enquiry(enquiry_id, candidates=[candidate])

        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app)
        try:
            resp = client.get(f"/api/v1/enquiries/{enquiry_id}/candidate-dates")
            assert resp.status_code == 200
            items = resp.json()
            assert len(items) == 1
            assert items[0]["candidate_date"] == "2026-08-15"
        finally:
            app.dependency_overrides.clear()

    def test_candidate_date_includes_availability_status(self) -> None:
        enquiry_id = uuid.uuid4()
        dr_id = uuid.uuid4()
        candidate = _make_candidate_row(enquiry_id, dr_id, availability_status="booked")
        db = _make_db_with_enquiry(enquiry_id, candidates=[candidate])

        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app)
        try:
            resp = client.get(f"/api/v1/enquiries/{enquiry_id}/candidate-dates")
            assert resp.status_code == 200
            items = resp.json()
            assert items[0]["availability_status"] == "booked"
        finally:
            app.dependency_overrides.clear()

    def test_candidate_date_includes_pricing(self) -> None:
        enquiry_id = uuid.uuid4()
        dr_id = uuid.uuid4()
        candidate = _make_candidate_row(
            enquiry_id, dr_id, recommended_minimum_spend=3200.0
        )
        db = _make_db_with_enquiry(enquiry_id, candidates=[candidate])

        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app)
        try:
            resp = client.get(f"/api/v1/enquiries/{enquiry_id}/candidate-dates")
            assert resp.status_code == 200
            items = resp.json()
            assert items[0]["recommended_minimum_spend"] == 3200.0
        finally:
            app.dependency_overrides.clear()

    def test_candidate_date_includes_source_type(self) -> None:
        enquiry_id = uuid.uuid4()
        dr_id = uuid.uuid4()
        candidate = _make_candidate_row(enquiry_id, dr_id)
        candidate.source_type = "explicit"
        db = _make_db_with_enquiry(enquiry_id, candidates=[candidate])

        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app)
        try:
            resp = client.get(f"/api/v1/enquiries/{enquiry_id}/candidate-dates")
            assert resp.status_code == 200
            items = resp.json()
            assert items[0]["source_type"] == "explicit"
        finally:
            app.dependency_overrides.clear()

    def test_multiple_candidates_returned(self) -> None:
        enquiry_id = uuid.uuid4()
        dr_id = uuid.uuid4()
        candidates = [
            _make_candidate_row(enquiry_id, dr_id, candidate_date=date(2026, 8, d))
            for d in [1, 2, 3]
        ]
        db = _make_db_with_enquiry(enquiry_id, candidates=candidates)

        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app)
        try:
            resp = client.get(f"/api/v1/enquiries/{enquiry_id}/candidate-dates")
            assert resp.status_code == 200
            assert len(resp.json()) == 3
        finally:
            app.dependency_overrides.clear()
