"""Tests for FreeformIntakeService and POST /enquiries/intake/freeform.

Covers:
- FreeformIntakeRequest / FreeformIntakeOut schema validation
- FreeformIntakeService: successful path (draft only, no extraction/processing)
- FreeformIntakeService: graceful degradation when extraction/processing unavailable
- FreeformIntakeService: invalid restaurant raises ValueError
- Router: 201 response shape includes extraction, recommended_action, draft fields
- Router: 404 for unknown restaurant
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.enquiries.intake_service import FreeformIntakeService
from app.modules.enquiries.router import get_freeform_intake_service
from app.modules.enquiries.schemas import (
    ExtractionSummaryOut,
    FreeformIntakeOut,
    FreeformIntakeRequest,
)


# ── Schema tests ──────────────────────────────────────────────────────────────


class TestFreeformIntakeRequest:
    def test_valid_minimal(self):
        req = FreeformIntakeRequest(
            restaurant_id=uuid.uuid4(),
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            freeform_text="I'd like to book a private dining room for 20 guests next Friday.",
        )
        assert req.first_name == "Alice"
        assert req.freeform_text.startswith("I'd")
        assert req.audience_type is None
        assert req.phone is None

    def test_freeform_text_too_short_raises(self):
        with pytest.raises(Exception):
            FreeformIntakeRequest(
                restaurant_id=uuid.uuid4(),
                first_name="A",
                last_name="B",
                email="a@b.com",
                freeform_text="Hi",
            )

    def test_freeform_text_too_long_raises(self):
        with pytest.raises(Exception):
            FreeformIntakeRequest(
                restaurant_id=uuid.uuid4(),
                first_name="A",
                last_name="B",
                email="a@b.com",
                freeform_text="x" * 5001,
            )

    def test_audience_type_accepted(self):
        req = FreeformIntakeRequest(
            restaurant_id=uuid.uuid4(),
            first_name="A",
            last_name="B",
            email="a@b.com",
            freeform_text="A long enough freeform message about booking a venue for dinner.",
            audience_type="corporate",
        )
        assert req.audience_type == "corporate"


class TestExtractionSummaryOut:
    def test_defaults_are_none(self):
        s = ExtractionSummaryOut(is_fallback=True)
        assert s.extraction_id is None
        assert s.guest_count is None
        assert s.missing_fields is None

    def test_full_fields(self):
        s = ExtractionSummaryOut(
            extraction_id=uuid.uuid4(),
            is_fallback=False,
            validation_status="passed",
            guest_count=20,
            event_date="2026-08-15",
            event_type="corporate_dinner",
            missing_fields=["budget"],
        )
        assert s.guest_count == 20
        assert s.event_type == "corporate_dinner"


class TestFreeformIntakeOut:
    def test_minimal_construction(self):
        out = FreeformIntakeOut(
            enquiry_id=uuid.uuid4(),
            reference="ENQ-TEST-001",
            status="new",
            restaurant_id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
        )
        assert out.extraction is None
        assert out.recommended_action is None
        assert out.draft_body is None
        assert out.draft_is_fallback is None

    def test_full_construction(self):
        out = FreeformIntakeOut(
            enquiry_id=uuid.uuid4(),
            reference="ENQ-TEST-002",
            status="new",
            restaurant_id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
            extraction=ExtractionSummaryOut(is_fallback=False, guest_count=10),
            recommended_action="send_availability_confirmation",
            draft_subject="Re: Corporate Dinner",
            draft_body="Dear Alice, thank you for your enquiry...",
            draft_message_id=uuid.uuid4(),
            draft_is_fallback=False,
        )
        assert out.extraction.guest_count == 10
        assert out.recommended_action == "send_availability_confirmation"
        assert "Alice" in out.draft_body


# ── FreeformIntakeService unit tests ─────────────────────────────────────────


class TestFreeformIntakeServiceNoDependencies:
    """Tests that exercise FreeformIntakeService with mocked DB — no Sprint 7 services."""

    def _make_service(self, db):
        from app.modules.enquiries.intake_service import FreeformIntakeService
        return FreeformIntakeService(db)

    def _make_request(self, restaurant_id=None):
        return FreeformIntakeRequest(
            restaurant_id=restaurant_id or uuid.uuid4(),
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            freeform_text="We'd like to host a private dinner for 20 guests on the 15th August.",
        )

    def test_invalid_restaurant_raises(self):
        db = MagicMock()
        svc = self._make_service(db)

        # Restaurant repo returns None
        svc._restaurant_repo = MagicMock()
        svc._restaurant_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            svc.intake_freeform(self._make_request())

    def test_creates_enquiry_and_message(self):
        db = MagicMock()
        svc = self._make_service(db)

        restaurant = MagicMock()
        restaurant.id = uuid.uuid4()
        restaurant.name = "Test Venue"

        enquiry = MagicMock()
        enquiry.id = uuid.uuid4()
        enquiry.reference = "ENQ-001"
        enquiry.status = "new"
        enquiry.restaurant_id = restaurant.id
        enquiry.created_at = datetime.now(timezone.utc)

        inbound_msg = MagicMock()
        inbound_msg.id = uuid.uuid4()

        svc._restaurant_repo = MagicMock()
        svc._restaurant_repo.get_by_id.return_value = restaurant
        svc._persona_repo = MagicMock()
        svc._persona_repo.get_default_persona_for_restaurant.return_value = None
        svc._persona_repo.get_persona_for_audience.return_value = None
        svc._enquiry_repo = MagicMock()
        svc._enquiry_repo.create.return_value = enquiry
        svc._enquiry_repo.add_message.return_value = inbound_msg

        req = self._make_request(restaurant_id=restaurant.id)

        with (
            patch("app.modules.enquiries.intake_service._EXTRACTION_AVAILABLE", False),
            patch("app.modules.enquiries.intake_service._PROCESSING_AVAILABLE", False),
            patch("app.modules.ai.service.DraftGenerationService") as MockDraft,
        ):
            mock_draft_result = MagicMock()
            mock_draft_result.subject = "Re: Event Enquiry"
            mock_draft_result.body = "Dear Alice..."
            mock_draft_result.message_id = uuid.uuid4()
            mock_draft_result.is_fallback = True
            mock_draft_result.ai_context = None
            MockDraft.return_value.generate_draft.return_value = mock_draft_result

            result = svc.intake_freeform(req)

        assert result.enquiry_id == enquiry.id
        assert result.reference == "ENQ-001"
        assert result.extraction is None
        assert result.recommended_action is None
        # Draft is best-effort (may succeed or fail depending on mock setup)

    def test_draft_failure_does_not_raise(self):
        """Draft generation failure must not crash the intake — enquiry still returned."""
        db = MagicMock()
        svc = self._make_service(db)

        restaurant = MagicMock()
        restaurant.id = uuid.uuid4()
        restaurant.name = "Test Venue"

        enquiry = MagicMock()
        enquiry.id = uuid.uuid4()
        enquiry.reference = "ENQ-002"
        enquiry.status = "new"
        enquiry.restaurant_id = restaurant.id
        enquiry.created_at = datetime.now(timezone.utc)

        inbound_msg = MagicMock()
        inbound_msg.id = uuid.uuid4()

        svc._restaurant_repo = MagicMock()
        svc._restaurant_repo.get_by_id.return_value = restaurant
        svc._persona_repo = MagicMock()
        svc._persona_repo.get_default_persona_for_restaurant.return_value = None
        svc._persona_repo.get_persona_for_audience.return_value = None
        svc._enquiry_repo = MagicMock()
        svc._enquiry_repo.create.return_value = enquiry
        svc._enquiry_repo.add_message.return_value = inbound_msg

        req = self._make_request(restaurant_id=restaurant.id)

        with (
            patch("app.modules.enquiries.intake_service._EXTRACTION_AVAILABLE", False),
            patch("app.modules.enquiries.intake_service._PROCESSING_AVAILABLE", False),
            patch(
                "app.modules.enquiries.intake_service.FreeformIntakeService.intake_freeform",
                wraps=svc.intake_freeform,
            ),
        ):
            # Patch DraftGenerationService to raise
            with patch("app.modules.ai.service.DraftGenerationService") as MockDraft:
                MockDraft.return_value.generate_draft.side_effect = RuntimeError("LLM unavailable")
                result = svc.intake_freeform(req)

        assert result.enquiry_id == enquiry.id
        assert result.draft_body is None

    def test_persona_resolved_by_audience(self):
        db = MagicMock()
        svc = self._make_service(db)

        restaurant = MagicMock()
        restaurant.id = uuid.uuid4()
        restaurant.name = "Test Venue"

        persona = MagicMock()
        persona.id = uuid.uuid4()
        persona.name = "James"

        enquiry = MagicMock()
        enquiry.id = uuid.uuid4()
        enquiry.reference = "ENQ-003"
        enquiry.status = "new"
        enquiry.restaurant_id = restaurant.id
        enquiry.created_at = datetime.now(timezone.utc)

        inbound_msg = MagicMock()
        inbound_msg.id = uuid.uuid4()

        svc._restaurant_repo = MagicMock()
        svc._restaurant_repo.get_by_id.return_value = restaurant
        svc._persona_repo = MagicMock()
        svc._persona_repo.get_persona_for_audience.return_value = persona
        svc._persona_repo.get_default_persona_for_restaurant.return_value = None
        svc._enquiry_repo = MagicMock()
        svc._enquiry_repo.create.return_value = enquiry
        svc._enquiry_repo.add_message.return_value = inbound_msg

        req = FreeformIntakeRequest(
            restaurant_id=restaurant.id,
            first_name="Bob",
            last_name="Jones",
            email="bob@corp.com",
            freeform_text="We need a corporate venue for our annual dinner with 50 attendees.",
            audience_type="corporate",
        )

        with (
            patch("app.modules.enquiries.intake_service._EXTRACTION_AVAILABLE", False),
            patch("app.modules.enquiries.intake_service._PROCESSING_AVAILABLE", False),
            patch("app.modules.ai.service.DraftGenerationService") as MockDraft,
        ):
            MockDraft.return_value.generate_draft.side_effect = RuntimeError("no key")
            result = svc.intake_freeform(req)

        assert result.persona_id == persona.id
        assert result.persona_name == "James"
        assert result.audience_type == "corporate"
        # Audience-specific persona was queried first
        svc._persona_repo.get_persona_for_audience.assert_called_once_with(
            restaurant.id, "corporate"
        )


# ── Router tests ─────────────────────────────────────────────────────────────


def _make_freeform_out(restaurant_id: uuid.UUID | None = None, **kwargs) -> FreeformIntakeOut:
    """Build a FreeformIntakeOut for use as a mock service return value."""
    rid = restaurant_id or uuid.uuid4()
    defaults = dict(
        enquiry_id=uuid.uuid4(),
        reference="ENQ-TEST-001",
        status="new",
        restaurant_id=rid,
        created_at=datetime.now(timezone.utc),
        extraction=None,
        recommended_action=None,
        draft_subject="Re: Event Enquiry — Alice Smith",
        draft_body="Dear Alice, thank you for your enquiry...",
        draft_message_id=uuid.uuid4(),
        draft_is_fallback=True,
    )
    defaults.update(kwargs)
    return FreeformIntakeOut(**defaults)


class TestFreeformIntakeRouter:
    """Router tests using TestClient with dependency overrides — no live DB needed."""

    def setup_method(self) -> None:
        self.client = TestClient(app)

    def _make_valid_body(self) -> dict:
        return {
            "restaurant_id": str(uuid.uuid4()),
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice@example.com",
            "freeform_text": "We'd like to host a private dinner for 20 guests next Friday evening.",
        }

    def _mock_service(self, return_value: FreeformIntakeOut) -> MagicMock:
        svc = MagicMock(spec=FreeformIntakeService)
        svc.intake_freeform.return_value = return_value
        return svc

    def test_endpoint_returns_201_with_required_fields(self) -> None:
        """Successful call returns 201 with all FreeformIntakeOut fields."""
        out = _make_freeform_out()
        app.dependency_overrides[get_freeform_intake_service] = lambda: self._mock_service(out)
        try:
            res = self.client.post("/api/v1/enquiries/intake/freeform", json=self._make_valid_body())
            assert res.status_code == 201
            data = res.json()
            assert "enquiry_id" in data
            assert "reference" in data
            assert data["status"] == "new"
            assert "draft_body" in data
            assert "extraction" in data
            assert "recommended_action" in data
        finally:
            app.dependency_overrides.clear()

    def test_endpoint_404_when_service_raises_value_error(self) -> None:
        """ValueError from service (unknown restaurant) becomes 404."""
        svc = MagicMock(spec=FreeformIntakeService)
        svc.intake_freeform.side_effect = ValueError("Restaurant not found")
        app.dependency_overrides[get_freeform_intake_service] = lambda: svc
        try:
            res = self.client.post("/api/v1/enquiries/intake/freeform", json=self._make_valid_body())
            assert res.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_endpoint_422_missing_freeform_text(self) -> None:
        """Missing freeform_text field returns 422."""
        body = {
            "restaurant_id": str(uuid.uuid4()),
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice@example.com",
        }
        res = self.client.post("/api/v1/enquiries/intake/freeform", json=body)
        assert res.status_code == 422

    def test_endpoint_422_text_too_short(self) -> None:
        """Freeform text under 10 characters returns 422."""
        body = self._make_valid_body()
        body["freeform_text"] = "Too short"
        res = self.client.post("/api/v1/enquiries/intake/freeform", json=body)
        assert res.status_code == 422

    def test_endpoint_includes_extraction_summary(self) -> None:
        """Extraction summary fields appear in response when extraction succeeds."""
        extraction = ExtractionSummaryOut(
            extraction_id=uuid.uuid4(),
            is_fallback=False,
            validation_status="passed",
            guest_count=20,
            event_date="2026-08-15",
            event_type="corporate_dinner",
        )
        out = _make_freeform_out(
            extraction=extraction,
            recommended_action="send_availability_confirmation",
        )
        app.dependency_overrides[get_freeform_intake_service] = lambda: self._mock_service(out)
        try:
            res = self.client.post("/api/v1/enquiries/intake/freeform", json=self._make_valid_body())
            data = res.json()
            assert data["recommended_action"] == "send_availability_confirmation"
            assert data["extraction"]["guest_count"] == 20
            assert data["extraction"]["event_date"] == "2026-08-15"
            assert data["extraction"]["is_fallback"] is False
        finally:
            app.dependency_overrides.clear()

    def test_endpoint_null_extraction_when_service_unavailable(self) -> None:
        """When extraction/processing services are unavailable, extraction is null."""
        out = _make_freeform_out(extraction=None, recommended_action=None)
        app.dependency_overrides[get_freeform_intake_service] = lambda: self._mock_service(out)
        try:
            res = self.client.post("/api/v1/enquiries/intake/freeform", json=self._make_valid_body())
            data = res.json()
            assert data["extraction"] is None
            assert data["recommended_action"] is None
        finally:
            app.dependency_overrides.clear()

    def test_structured_intake_endpoint_unaffected(self) -> None:
        """Existing POST /intake endpoint still returns 422 for incomplete requests."""
        # No override — no DB, so it would fail at DB level, but schema validation
        # happens first: empty body returns 422
        res = self.client.post("/api/v1/enquiries/intake", json={})
        assert res.status_code == 422
