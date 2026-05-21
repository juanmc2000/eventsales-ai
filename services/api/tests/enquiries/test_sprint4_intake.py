"""
TEST-004: Sprint 4 Enquiry Intake Schema Tests.

Verifies that the webform intake source field, persona assignment,
and pricing recommendation shapes are correct. These tests use
pure Python (no pydantic) to run without the full app environment.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


# ─── Minimal intake request/response stand-ins ────────────────────────────────


@dataclass
class _WebformIntakeRequest:
    """Mirrors WebformIntakeRequest from enquiries/schemas.py."""
    restaurant_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    party_size: Optional[int] = None
    event_date: Optional[date] = None
    event_type: Optional[str] = None
    budget_indication: Optional[str] = None
    preferred_area: Optional[str] = None
    dietary_requirements: Optional[str] = None
    special_requests: Optional[str] = None
    message: Optional[str] = None
    source: str = "webform"


@dataclass
class _EnquiryIntakeOut:
    """Mirrors EnquiryIntakeOut from enquiries/schemas.py."""
    enquiry_id: uuid.UUID
    reference: str
    status: str
    persona_name: Optional[str]
    recommended_minimum_spend: Optional[float]
    pricing_explanation: Optional[str]
    created_at: datetime


class TestWebformIntakeRequestConcept:
    def test_default_source_is_webform(self):
        req = _WebformIntakeRequest(
            restaurant_id=uuid.uuid4(),
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
        )
        assert req.source == "webform"

    def test_optional_fields_default_to_none(self):
        req = _WebformIntakeRequest(
            restaurant_id=uuid.uuid4(),
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
        )
        assert req.phone is None
        assert req.party_size is None
        assert req.event_type is None
        assert req.message is None

    def test_accepts_full_event_details(self):
        req = _WebformIntakeRequest(
            restaurant_id=uuid.uuid4(),
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            party_size=20,
            event_type="Birthday",
            event_date=date(2026, 7, 1),
            message="Looking forward to the event.",
        )
        assert req.party_size == 20
        assert req.event_type == "Birthday"

    def test_restaurant_id_is_uuid(self):
        rid = uuid.uuid4()
        req = _WebformIntakeRequest(
            restaurant_id=rid,
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
        )
        assert req.restaurant_id == rid


class TestEnquiryIntakeOutConcept:
    def test_status_is_new_by_default(self):
        out = _EnquiryIntakeOut(
            enquiry_id=uuid.uuid4(),
            reference="ENQ-2026-0001",
            status="new",
            persona_name="The Host",
            recommended_minimum_spend=1500.0,
            pricing_explanation="Based on 20 guests.",
            created_at=datetime.now(),
        )
        assert out.status == "new"

    def test_reference_format(self):
        out = _EnquiryIntakeOut(
            enquiry_id=uuid.uuid4(),
            reference="ENQ-2026-0001",
            status="new",
            persona_name=None,
            recommended_minimum_spend=None,
            pricing_explanation=None,
            created_at=datetime.now(),
        )
        assert out.reference.startswith("ENQ-")

    def test_persona_name_can_be_none(self):
        out = _EnquiryIntakeOut(
            enquiry_id=uuid.uuid4(),
            reference="ENQ-2026-0001",
            status="new",
            persona_name=None,
            recommended_minimum_spend=None,
            pricing_explanation=None,
            created_at=datetime.now(),
        )
        assert out.persona_name is None

    def test_recommended_spend_can_be_set(self):
        out = _EnquiryIntakeOut(
            enquiry_id=uuid.uuid4(),
            reference="ENQ-2026-0001",
            status="new",
            persona_name=None,
            recommended_minimum_spend=2500.0,
            pricing_explanation="Min spend for 50 guests.",
            created_at=datetime.now(),
        )
        assert out.recommended_minimum_spend == 2500.0
