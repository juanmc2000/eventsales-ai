"""POC workflow tests — enquiry creation, persona assignment, pricing.

TEST-005: End-to-End POC Workflow Tests

All tests are smoke/unit tests (no live DB required). They cover the
backend loop: webform intake → enquiry creation → persona/pricing attachment.
"""
import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

# Load all SQLAlchemy models so mapper relationships are fully configured
import app.db.models  # noqa: F401


# ── Helpers ───────────────────────────────────────────────────────────────────


def _mock_enquiry(reference: str = "ENQ-2026-0001") -> MagicMock:
    e = MagicMock()
    e.id = uuid.uuid4()
    e.reference = reference
    e.status = "new"
    e.source = "webform"
    e.restaurant_id = uuid.uuid4()
    e.persona_id = None
    e.first_name = "Alice"
    e.last_name = "Smith"
    e.email = "alice@example.com"
    return e


def _mock_db() -> MagicMock:
    db = MagicMock()
    db.flush = MagicMock()
    db.add = MagicMock()
    db.query.return_value.count.return_value = 0
    return db


# ── Schema: webform intake input validation ────────────────────────────────────


def test_enquiry_create_schema_requires_email() -> None:
    from pydantic import ValidationError
    from app.modules.enquiries.schemas import EnquiryCreate

    with pytest.raises(ValidationError):
        EnquiryCreate(
            restaurant_id=uuid.uuid4(),
            first_name="Alice",
            last_name="Smith",
            email="not-an-email",
        )


def test_enquiry_create_schema_defaults_source_to_webform() -> None:
    from app.modules.enquiries.schemas import EnquiryCreate

    e = EnquiryCreate(
        restaurant_id=uuid.uuid4(),
        first_name="Alice",
        last_name="Smith",
        email="alice@example.com",
    )
    assert e.source == "webform"


def test_enquiry_create_schema_accepts_email_source() -> None:
    from app.modules.enquiries.schemas import EnquiryCreate

    e = EnquiryCreate(
        restaurant_id=uuid.uuid4(),
        first_name="Alice",
        last_name="Smith",
        email="alice@example.com",
        source="email",
    )
    assert e.source == "email"


# ── EnquiryRepository: reference generation ───────────────────────────────────


def test_enquiry_reference_format() -> None:
    from app.modules.enquiries.repository import EnquiryRepository

    db = _mock_db()
    repo = EnquiryRepository(db)
    ref = repo.generate_reference()
    # Format: ENQ-YYYY-NNNN
    parts = ref.split("-")
    assert len(parts) == 3
    assert parts[0] == "ENQ"
    assert len(parts[1]) == 4  # year
    assert parts[2].isdigit()


def test_enquiry_reference_increments_with_count() -> None:
    from app.modules.enquiries.repository import EnquiryRepository

    db = _mock_db()
    db.query.return_value.count.return_value = 41
    repo = EnquiryRepository(db)
    ref = repo.generate_reference()
    assert ref.endswith("0042")


# ── EnquiryService: creation ──────────────────────────────────────────────────


def test_enquiry_service_creates_enquiry_from_webform() -> None:
    from app.modules.enquiries.schemas import EnquiryCreate
    from app.modules.enquiries.service import EnquiryService

    db = _mock_db()
    svc = EnquiryService(db)
    enquiry = _mock_enquiry()
    svc._repo = MagicMock()
    svc._repo.create.return_value = enquiry

    data = EnquiryCreate(
        restaurant_id=uuid.uuid4(),
        first_name="Alice",
        last_name="Smith",
        email="alice@example.com",
        event_date=date(2026, 12, 25),
        party_size=20,
        message="Looking for a private room.",
    )

    result = svc.create_enquiry(data)

    svc._repo.create.assert_called_once()
    # Source defaults to webform
    call_payload = svc._repo.create.call_args[0][0]
    assert call_payload.get("source") == "webform"
    assert result.reference == "ENQ-2026-0001"


def test_enquiry_service_creates_initial_message_when_provided() -> None:
    from app.modules.enquiries.schemas import EnquiryCreate
    from app.modules.enquiries.service import EnquiryService

    db = _mock_db()
    svc = EnquiryService(db)
    enquiry = _mock_enquiry()
    svc._repo = MagicMock()
    svc._repo.create.return_value = enquiry

    data = EnquiryCreate(
        restaurant_id=uuid.uuid4(),
        first_name="Alice",
        last_name="Smith",
        email="alice@example.com",
        message="Hello, I want to book.",
    )

    svc.create_enquiry(data)

    svc._repo.add_message.assert_called_once()
    msg_data = svc._repo.add_message.call_args[0][1]
    assert msg_data["direction"] == "inbound"
    assert "Hello, I want to book." in msg_data["body"]


# ── Persona assignment ────────────────────────────────────────────────────────


def test_persona_base_schema() -> None:
    from app.modules.personas.schemas import PersonaCreate
    from datetime import datetime

    p = PersonaCreate(
        name="The Host",
        slug="the-host",
        tone="warm",
        style="conversational",
        greeting="Hello",
        signature="Warm regards",
        system_prompt="You are a warm host.",
        instructions="Be helpful.",
        language="en",
        is_active=True,
    )
    assert p.name == "The Host"
    assert p.tone == "warm"
    assert p.slug == "the-host"


def test_persona_service_returns_none_for_missing_persona() -> None:
    from app.modules.personas.service import PersonaService

    db = MagicMock()
    svc = PersonaService(db)
    svc._repo = MagicMock()
    svc._repo.get_by_id.return_value = None

    result = svc.get_persona(uuid.uuid4())
    assert result is None


# ── Pricing: deterministic rules ──────────────────────────────────────────────


def test_pricing_rule_schema_valid() -> None:
    from app.modules.pricing.schemas import PricingRuleCreate

    rule = PricingRuleCreate(
        restaurant_id=uuid.uuid4(),
        name="Weekend Dinner Premium",
        meal_period="dinner",
        event_type="birthday",
        day_of_week=None,
        minimum_spend=1500.0,
        notes="Weekend premium",
        is_active=True,
    )
    assert rule.minimum_spend == 1500.0
    assert rule.meal_period == "dinner"


def test_pricing_rule_minimum_spend_non_negative() -> None:
    from pydantic import ValidationError
    from app.modules.pricing.schemas import PricingRuleCreate

    with pytest.raises(ValidationError):
        PricingRuleCreate(
            restaurant_id=uuid.uuid4(),
            meal_period="lunch",
            event_type="corporate",
            minimum_spend=-100.0,
        )


# ── Status lifecycle ──────────────────────────────────────────────────────────


def test_enquiry_status_update_rejects_invalid_status() -> None:
    from app.modules.enquiries.service import EnquiryService

    db = MagicMock()
    svc = EnquiryService(db)
    svc._repo = MagicMock()
    svc._repo.get_by_id.return_value = MagicMock()

    from app.modules.enquiries.schemas import EnquiryStatusUpdate

    with pytest.raises(ValueError, match="Invalid status"):
        svc.update_enquiry_status(uuid.uuid4(), EnquiryStatusUpdate(status="invented"))


def test_enquiry_status_update_accepts_valid_statuses() -> None:
    from app.modules.enquiries.schemas import EnquiryStatusUpdate

    for status in ("new", "open", "proposal_sent", "follow_up", "confirmed", "cancelled", "lost"):
        u = EnquiryStatusUpdate(status=status)
        assert u.status == status
