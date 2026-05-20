"""Smoke tests for enquiry schemas (no DB required)."""

import uuid
from datetime import date

import pytest


def test_enquiry_create_schema_valid() -> None:
    from app.modules.enquiries.schemas import EnquiryCreate

    e = EnquiryCreate(
        restaurant_id=uuid.uuid4(),
        first_name="Alice",
        last_name="Smith",
        email="alice@example.com",
        event_date=date(2026, 12, 25),
        party_size=20,
    )
    assert e.first_name == "Alice"
    assert e.source == "webform"


def test_enquiry_create_invalid_email() -> None:
    from pydantic import ValidationError

    from app.modules.enquiries.schemas import EnquiryCreate

    with pytest.raises(ValidationError):
        EnquiryCreate(
            restaurant_id=uuid.uuid4(),
            first_name="Bob",
            last_name="Jones",
            email="not-an-email",
        )


def test_enquiry_status_update_schema() -> None:
    from app.modules.enquiries.schemas import EnquiryStatusUpdate

    update = EnquiryStatusUpdate(status="confirmed")
    assert update.status == "confirmed"


def test_enquiry_message_direction_validation() -> None:
    from pydantic import ValidationError

    from app.modules.enquiries.schemas import EnquiryMessageCreate

    with pytest.raises(ValidationError):
        EnquiryMessageCreate(direction="unknown", body="Hello")


def test_enquiry_message_create_valid_directions() -> None:
    from app.modules.enquiries.schemas import EnquiryMessageCreate

    for direction in ("inbound", "outbound"):
        msg = EnquiryMessageCreate(direction=direction, body="Test body")
        assert msg.direction == direction


def test_enquiry_list_out_schema() -> None:
    from app.modules.enquiries.schemas import EnquiryListOut

    result = EnquiryListOut(items=[], total=0)
    assert result.total == 0


def test_valid_statuses_in_service() -> None:
    from app.modules.enquiries.service import VALID_STATUSES

    expected = {"new", "open", "proposal_sent", "follow_up", "confirmed", "cancelled", "lost"}
    assert VALID_STATUSES == expected
