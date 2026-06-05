"""Tests for GET /enquiries/{id}/response-preparation/latest (ORCH-007).

All tests use mock dependencies — no live DB required.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.enquiries.repository import EnquiryRepository, ResponsePlanRepository


# ── Helpers ───────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _mock_enquiry(enquiry_id: uuid.UUID | None = None) -> MagicMock:
    e = MagicMock()
    e.id = enquiry_id or uuid.uuid4()
    return e


def _mock_plan(
    enquiry_id: uuid.UUID,
    response_goal: str = "READY_TO_CONFIRM_AVAILABILITY",
    response_priority: str = "NORMAL",
    can_generate_draft: bool = True,
) -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.enquiry_id = enquiry_id
    p.snapshot_id = None
    p.response_goal = response_goal
    p.response_priority = response_priority
    p.can_generate_draft = can_generate_draft
    p.goal_reason = "All key facts present."
    p.blocking_fields = []
    p.known_facts = {"date_understood": True, "guest_count_present": True}
    p.missing_information = {"missing_fields": [], "should_send_webform": False}
    p.clarification_questions = []
    p.date_context = {"status": "resolved"}
    p.availability_context = {"availability_status": "AVAILABLE"}
    p.customer_type_context = {"final_customer_type": "corporate"}
    p.persona_context = {"tone_guidance": ["professional"]}
    p.draft_instructions = {"tone_guidance": ["professional"], "include_availability": True}
    p.created_at = _now()
    return p


# ── 404 when enquiry not found ────────────────────────────────────────────────


def test_returns_404_when_enquiry_not_found():
    enquiry_id = uuid.uuid4()

    with patch.object(EnquiryRepository, "get_by_id", return_value=None):
        client = TestClient(app)
        response = client.get(f"/api/v1/enquiries/{enquiry_id}/response-preparation/latest")

    assert response.status_code == 404
    assert response.json()["detail"] == "Enquiry not found"


# ── Safe empty state when no plan exists ─────────────────────────────────────


def test_returns_safe_empty_state_when_no_plan():
    enquiry_id = uuid.uuid4()
    mock_enquiry = _mock_enquiry(enquiry_id)

    with (
        patch.object(EnquiryRepository, "get_by_id", return_value=mock_enquiry),
        patch.object(ResponsePlanRepository, "get_latest", return_value=None),
    ):
        client = TestClient(app)
        response = client.get(f"/api/v1/enquiries/{enquiry_id}/response-preparation/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["response_goal"] == "NOT_RUN"
    assert body["can_generate_draft"] is False
    assert body["enquiry_id"] == str(enquiry_id)


def test_empty_state_has_all_required_fields():
    enquiry_id = uuid.uuid4()
    mock_enquiry = _mock_enquiry(enquiry_id)

    with (
        patch.object(EnquiryRepository, "get_by_id", return_value=mock_enquiry),
        patch.object(ResponsePlanRepository, "get_latest", return_value=None),
    ):
        client = TestClient(app)
        response = client.get(f"/api/v1/enquiries/{enquiry_id}/response-preparation/latest")

    body = response.json()
    for field in [
        "id", "enquiry_id", "response_goal", "response_priority",
        "can_generate_draft", "goal_reason", "blocking_fields",
        "clarification_questions", "created_at",
    ]:
        assert field in body, f"Missing field: {field}"


# ── Returns stored plan ───────────────────────────────────────────────────────


def test_returns_latest_plan_when_exists():
    enquiry_id = uuid.uuid4()
    mock_enquiry = _mock_enquiry(enquiry_id)
    mock_plan = _mock_plan(enquiry_id, response_goal="READY_TO_CONFIRM_AVAILABILITY")

    with (
        patch.object(EnquiryRepository, "get_by_id", return_value=mock_enquiry),
        patch.object(ResponsePlanRepository, "get_latest", return_value=mock_plan),
    ):
        client = TestClient(app)
        response = client.get(f"/api/v1/enquiries/{enquiry_id}/response-preparation/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["response_goal"] == "READY_TO_CONFIRM_AVAILABILITY"
    assert body["can_generate_draft"] is True


def test_returns_enquiry_id_in_response():
    enquiry_id = uuid.uuid4()
    mock_enquiry = _mock_enquiry(enquiry_id)
    mock_plan = _mock_plan(enquiry_id)

    with (
        patch.object(EnquiryRepository, "get_by_id", return_value=mock_enquiry),
        patch.object(ResponsePlanRepository, "get_latest", return_value=mock_plan),
    ):
        client = TestClient(app)
        response = client.get(f"/api/v1/enquiries/{enquiry_id}/response-preparation/latest")

    assert response.json()["enquiry_id"] == str(enquiry_id)


def test_returns_correct_priority():
    enquiry_id = uuid.uuid4()
    mock_enquiry = _mock_enquiry(enquiry_id)
    mock_plan = _mock_plan(enquiry_id, response_priority="URGENT")

    with (
        patch.object(EnquiryRepository, "get_by_id", return_value=mock_enquiry),
        patch.object(ResponsePlanRepository, "get_latest", return_value=mock_plan),
    ):
        client = TestClient(app)
        response = client.get(f"/api/v1/enquiries/{enquiry_id}/response-preparation/latest")

    assert response.json()["response_priority"] == "URGENT"


def test_returns_date_context():
    enquiry_id = uuid.uuid4()
    mock_enquiry = _mock_enquiry(enquiry_id)
    mock_plan = _mock_plan(enquiry_id)

    with (
        patch.object(EnquiryRepository, "get_by_id", return_value=mock_enquiry),
        patch.object(ResponsePlanRepository, "get_latest", return_value=mock_plan),
    ):
        client = TestClient(app)
        response = client.get(f"/api/v1/enquiries/{enquiry_id}/response-preparation/latest")

    body = response.json()
    assert body["date_context"] == {"status": "resolved"}


def test_returns_availability_context():
    enquiry_id = uuid.uuid4()
    mock_enquiry = _mock_enquiry(enquiry_id)
    mock_plan = _mock_plan(enquiry_id)

    with (
        patch.object(EnquiryRepository, "get_by_id", return_value=mock_enquiry),
        patch.object(ResponsePlanRepository, "get_latest", return_value=mock_plan),
    ):
        client = TestClient(app)
        response = client.get(f"/api/v1/enquiries/{enquiry_id}/response-preparation/latest")

    body = response.json()
    assert body["availability_context"]["availability_status"] == "AVAILABLE"


def test_returns_persona_context():
    enquiry_id = uuid.uuid4()
    mock_enquiry = _mock_enquiry(enquiry_id)
    mock_plan = _mock_plan(enquiry_id)

    with (
        patch.object(EnquiryRepository, "get_by_id", return_value=mock_enquiry),
        patch.object(ResponsePlanRepository, "get_latest", return_value=mock_plan),
    ):
        client = TestClient(app)
        response = client.get(f"/api/v1/enquiries/{enquiry_id}/response-preparation/latest")

    body = response.json()
    assert body["persona_context"]["tone_guidance"] == ["professional"]


def test_endpoint_is_read_only():
    """Verify that GET is the only HTTP method wired for this endpoint."""
    enquiry_id = uuid.uuid4()
    client = TestClient(app)
    assert client.post(f"/api/v1/enquiries/{enquiry_id}/response-preparation/latest").status_code == 405
    assert client.put(f"/api/v1/enquiries/{enquiry_id}/response-preparation/latest").status_code == 405
    assert client.delete(f"/api/v1/enquiries/{enquiry_id}/response-preparation/latest").status_code == 405
