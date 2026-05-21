"""Tests for the enquiry intake orchestration service.

All tests here are smoke/unit tests (no DB required).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# ── Schema tests ──────────────────────────────────────────────────────────────


def test_webform_intake_request_defaults() -> None:
    from app.modules.enquiries.schemas import WebformIntakeRequest

    req = WebformIntakeRequest(
        restaurant_id=uuid.uuid4(),
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
    )
    assert req.meal_period == "dinner"
    assert req.source if hasattr(req, "source") else req.meal_period == "dinner"
    assert req.phone is None
    assert req.party_size is None


def test_webform_intake_request_invalid_email() -> None:
    from pydantic import ValidationError

    from app.modules.enquiries.schemas import WebformIntakeRequest

    with pytest.raises(ValidationError):
        WebformIntakeRequest(
            restaurant_id=uuid.uuid4(),
            first_name="Jane",
            last_name="Doe",
            email="not-an-email",
        )


def test_webform_intake_request_with_all_fields() -> None:
    from app.modules.enquiries.schemas import WebformIntakeRequest

    req = WebformIntakeRequest(
        restaurant_id=uuid.uuid4(),
        first_name="John",
        last_name="Smith",
        email="john@example.com",
        phone="+44 7700 900000",
        party_size=15,
        event_date=date(2026, 12, 31),
        event_type="corporate",
        meal_period="lunch",
        message="We'd like a private room.",
        company_name="Acme Ltd",
        budget_indication="Around £2,000",
        preferred_area="Private Dining Room",
        dietary_requirements="2 vegetarian",
        special_requests="Projector needed",
    )
    assert req.party_size == 15
    assert req.meal_period == "lunch"


def test_enquiry_intake_out_schema() -> None:
    from app.modules.enquiries.schemas import EnquiryIntakeOut

    now = datetime.now(tz=timezone.utc)
    out = EnquiryIntakeOut(
        enquiry_id=uuid.uuid4(),
        reference="ENQ-2026-0001",
        status="new",
        restaurant_id=uuid.uuid4(),
        persona_id=None,
        persona_name=None,
        recommended_minimum_spend=1500.0,
        pricing_explanation="No pricing rules matched.",
        created_at=now,
    )
    assert out.status == "new"
    assert out.recommended_minimum_spend == 1500.0
    assert out.persona_id is None


# ── Orchestration service unit tests (mocked) ─────────────────────────────────


def _make_mock_enquiry(restaurant_id: uuid.UUID, persona_id: uuid.UUID | None) -> MagicMock:
    enquiry = MagicMock()
    enquiry.id = uuid.uuid4()
    enquiry.reference = "ENQ-2026-0001"
    enquiry.status = "new"
    enquiry.restaurant_id = restaurant_id
    enquiry.persona_id = persona_id
    enquiry.created_at = datetime.now(tz=timezone.utc)
    return enquiry


def _make_mock_restaurant(restaurant_id: uuid.UUID) -> MagicMock:
    r = MagicMock()
    r.id = restaurant_id
    r.name = "Test Restaurant"
    return r


def _make_mock_persona() -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.name = "Warm Host"
    return p


def _make_mock_pricing(spend: float) -> MagicMock:
    from app.modules.pricing.schemas import PricingRecommendationOut

    return PricingRecommendationOut(
        recommended_minimum_spend=spend,
        applied_rules=[],
        explanation="1 rule matched.",
        confidence=1.0,
    )


def test_intake_service_happy_path() -> None:
    from app.modules.enquiries.intake_service import EnquiryIntakeService
    from app.modules.enquiries.schemas import WebformIntakeRequest

    restaurant_id = uuid.uuid4()
    mock_db = MagicMock()
    service = EnquiryIntakeService(mock_db)

    mock_restaurant = _make_mock_restaurant(restaurant_id)
    mock_persona = _make_mock_persona()
    mock_enquiry = _make_mock_enquiry(restaurant_id, mock_persona.id)
    mock_pricing = _make_mock_pricing(1200.0)

    service._restaurant_repo.get_by_id = MagicMock(return_value=mock_restaurant)
    service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=mock_persona)
    service._pricing_service.calculate_recommendation = MagicMock(return_value=mock_pricing)
    service._enquiry_repo.create = MagicMock(return_value=mock_enquiry)
    service._enquiry_repo.add_message = MagicMock()

    request = WebformIntakeRequest(
        restaurant_id=restaurant_id,
        first_name="Alice",
        last_name="Smith",
        email="alice@example.com",
        party_size=20,
        event_date=date(2026, 8, 15),
        message="Looking forward to a great event.",
    )

    result = service.intake(request)

    assert result.reference == "ENQ-2026-0001"
    assert result.status == "new"
    assert result.restaurant_id == restaurant_id
    assert result.persona_id == mock_persona.id
    assert result.persona_name == mock_persona.name
    assert result.recommended_minimum_spend == 1200.0
    # Initial inbound message should have been created
    service._enquiry_repo.add_message.assert_called_once()
    mock_db.commit.assert_called_once()


def test_intake_service_no_default_persona() -> None:
    from app.modules.enquiries.intake_service import EnquiryIntakeService
    from app.modules.enquiries.schemas import WebformIntakeRequest

    restaurant_id = uuid.uuid4()
    mock_db = MagicMock()
    service = EnquiryIntakeService(mock_db)

    mock_restaurant = _make_mock_restaurant(restaurant_id)
    mock_enquiry = _make_mock_enquiry(restaurant_id, None)
    mock_pricing = _make_mock_pricing(0.0)

    service._restaurant_repo.get_by_id = MagicMock(return_value=mock_restaurant)
    service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=None)
    service._pricing_service.calculate_recommendation = MagicMock(return_value=mock_pricing)
    service._enquiry_repo.create = MagicMock(return_value=mock_enquiry)
    service._enquiry_repo.add_message = MagicMock()

    request = WebformIntakeRequest(
        restaurant_id=restaurant_id,
        first_name="Bob",
        last_name="Jones",
        email="bob@example.com",
    )

    result = service.intake(request)

    assert result.persona_id is None
    assert result.persona_name is None
    # No message provided, so add_message should not be called
    service._enquiry_repo.add_message.assert_not_called()


def test_intake_service_restaurant_not_found_raises() -> None:
    from app.modules.enquiries.intake_service import EnquiryIntakeService
    from app.modules.enquiries.schemas import WebformIntakeRequest

    mock_db = MagicMock()
    service = EnquiryIntakeService(mock_db)
    service._restaurant_repo.get_by_id = MagicMock(return_value=None)

    request = WebformIntakeRequest(
        restaurant_id=uuid.uuid4(),
        first_name="Carol",
        last_name="White",
        email="carol@example.com",
    )

    with pytest.raises(ValueError, match="not found"):
        service.intake(request)


def test_intake_service_uses_event_date_for_day_of_week() -> None:
    """Pricing recommendation must use the event_date weekday, not today."""
    from app.modules.enquiries.intake_service import EnquiryIntakeService
    from app.modules.enquiries.schemas import WebformIntakeRequest
    from app.modules.pricing.schemas import PricingRecommendationRequest

    restaurant_id = uuid.uuid4()
    mock_db = MagicMock()
    service = EnquiryIntakeService(mock_db)

    mock_restaurant = _make_mock_restaurant(restaurant_id)
    mock_enquiry = _make_mock_enquiry(restaurant_id, None)
    mock_pricing = _make_mock_pricing(500.0)

    service._restaurant_repo.get_by_id = MagicMock(return_value=mock_restaurant)
    service._persona_repo.get_default_persona_for_restaurant = MagicMock(return_value=None)
    service._pricing_service.calculate_recommendation = MagicMock(return_value=mock_pricing)
    service._enquiry_repo.create = MagicMock(return_value=mock_enquiry)
    service._enquiry_repo.add_message = MagicMock()

    # 2026-08-15 is a Saturday (weekday = 5)
    event_date = date(2026, 8, 15)
    assert event_date.weekday() == 5

    request = WebformIntakeRequest(
        restaurant_id=restaurant_id,
        first_name="Dan",
        last_name="Brown",
        email="dan@example.com",
        event_date=event_date,
        meal_period="dinner",
        party_size=10,
    )

    service.intake(request)

    call_args = service._pricing_service.calculate_recommendation.call_args[0][0]
    assert isinstance(call_args, PricingRecommendationRequest)
    assert call_args.day_of_week == 5
    assert call_args.meal_period == "dinner"
    assert call_args.party_size == 10
