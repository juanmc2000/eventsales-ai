"""Unit tests for InboundEmailService (WORKFLOW-006).

No live database, no live Gmail. All DB interactions are mocked.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import pytest

# Load all SQLAlchemy models so mapper relationships are fully configured
import app.db.models  # noqa: F401


RECEIVED_AT = datetime(2026, 5, 21, 10, 0, 0, tzinfo=timezone.utc)


def _make_parsed(
    *,
    sender_email: str = "guest@example.com",
    sender_name: str | None = "Alice Smith",
    subject: str = "Private dining enquiry",
    body: str = "Hello, I would like to book a private room.",
    received_at: datetime = RECEIVED_AT,
    external_message_id: str | None = None,
):
    from app.modules.email.inbound_service import ParsedInboundEmail

    return ParsedInboundEmail(
        sender_email=sender_email,
        sender_name=sender_name,
        subject=subject,
        body=body,
        received_at=received_at,
        external_message_id=external_message_id,
    )


def _mock_restaurant(name: str = "The Grand") -> MagicMock:
    r = MagicMock()
    r.id = uuid.uuid4()
    r.name = name
    return r


def _mock_enquiry(reference: str = "ENQ-2026-0001") -> MagicMock:
    e = MagicMock()
    e.id = uuid.uuid4()
    e.reference = reference
    return e


def _make_service(
    *,
    restaurant: MagicMock | None = None,
    enquiry: MagicMock | None = None,
    existing_event: MagicMock | None = None,
):
    """Build an InboundEmailService with a fully mocked DB session."""
    from app.modules.email.inbound_service import InboundEmailService

    db = MagicMock()

    svc = InboundEmailService(db)

    # Mock restaurant repo
    svc._restaurant_repo = MagicMock()
    svc._restaurant_repo.list.return_value = [restaurant] if restaurant else []

    # Mock enquiry repo
    svc._enquiry_repo = MagicMock()
    if enquiry:
        svc._enquiry_repo.create.return_value = enquiry

    # Mock duplicate lookup
    scalars_result = MagicMock()
    scalars_result.first.return_value = existing_event
    db.scalars.return_value = scalars_result

    return svc, db


# ── ParsedInboundEmail ────────────────────────────────────────────────────────


def test_parsed_inbound_email_fields() -> None:
    parsed = _make_parsed(external_message_id="<abc@gmail.com>")
    assert parsed.sender_email == "guest@example.com"
    assert parsed.external_message_id == "<abc@gmail.com>"


# ── Duplicate guard ───────────────────────────────────────────────────────────


def test_duplicate_external_message_id_returns_duplicate_result() -> None:
    existing_event = MagicMock()
    existing_event.enquiry_id = uuid.uuid4()

    svc, db = _make_service(existing_event=existing_event)

    result = svc.process(_make_parsed(external_message_id="<dup@gmail.com>"))

    assert result.duplicate is True
    assert result.enquiry_id == existing_event.enquiry_id
    # Enquiry creation must NOT have been called
    svc._enquiry_repo.create.assert_not_called()


def test_no_duplicate_check_when_message_id_absent() -> None:
    """When external_message_id is None, duplicate guard is skipped."""
    restaurant = _mock_restaurant()
    enquiry = _mock_enquiry()
    svc, db = _make_service(restaurant=restaurant, enquiry=enquiry)

    result = svc.process(_make_parsed(external_message_id=None))

    # DB scalars (duplicate lookup) should NOT have been called
    db.scalars.assert_not_called()
    assert result.duplicate is False


# ── Restaurant inference ──────────────────────────────────────────────────────


def test_raises_when_no_active_restaurant() -> None:
    svc, db = _make_service(restaurant=None)

    with pytest.raises(ValueError, match="No active restaurants"):
        svc.process(_make_parsed())


# ── Enquiry creation ──────────────────────────────────────────────────────────


def test_creates_enquiry_with_source_email() -> None:
    restaurant = _mock_restaurant()
    enquiry = _mock_enquiry()
    svc, db = _make_service(restaurant=restaurant, enquiry=enquiry)

    result = svc.process(_make_parsed())

    svc._enquiry_repo.create.assert_called_once()
    call_data = svc._enquiry_repo.create.call_args[0][0]
    assert call_data["source"] == "email"
    assert call_data["email"] == "guest@example.com"
    assert call_data["restaurant_id"] == restaurant.id


def test_creates_enquiry_with_inbound_message() -> None:
    restaurant = _mock_restaurant()
    enquiry = _mock_enquiry()
    svc, db = _make_service(restaurant=restaurant, enquiry=enquiry)

    svc.process(_make_parsed(subject="Birthday dinner"))

    svc._enquiry_repo.add_message.assert_called_once()
    msg_data = svc._enquiry_repo.add_message.call_args[0][1]
    assert msg_data["direction"] == "inbound"
    assert msg_data["channel"] == "email"
    assert msg_data["subject"] == "Birthday dinner"


def test_returns_enquiry_reference_on_success() -> None:
    restaurant = _mock_restaurant()
    enquiry = _mock_enquiry(reference="ENQ-2026-0042")
    svc, db = _make_service(restaurant=restaurant, enquiry=enquiry)

    result = svc.process(_make_parsed())

    assert result.duplicate is False
    assert result.enquiry_reference == "ENQ-2026-0042"
    assert result.enquiry_id == enquiry.id
    assert result.action == "created"


# ── Sender name parsing ───────────────────────────────────────────────────────


def test_split_sender_name_full_name() -> None:
    from app.modules.email.inbound_service import InboundEmailService

    first, last = InboundEmailService._split_sender_name("Alice Smith")
    assert first == "Alice"
    assert last == "Smith"


def test_split_sender_name_single_word() -> None:
    from app.modules.email.inbound_service import InboundEmailService

    first, last = InboundEmailService._split_sender_name("Alice")
    assert first == "Alice"
    assert last == ""


def test_split_sender_name_none() -> None:
    from app.modules.email.inbound_service import InboundEmailService

    first, last = InboundEmailService._split_sender_name(None)
    assert first == "Unknown"
    assert last == ""


def test_split_sender_name_multiple_words() -> None:
    from app.modules.email.inbound_service import InboundEmailService

    first, last = InboundEmailService._split_sender_name("Alice Jane Smith")
    assert first == "Alice"
    assert last == "Jane Smith"


# ── Email event logging ───────────────────────────────────────────────────────


def test_email_event_is_added_to_db_session() -> None:
    restaurant = _mock_restaurant()
    enquiry = _mock_enquiry()
    svc, db = _make_service(restaurant=restaurant, enquiry=enquiry)

    svc.process(_make_parsed(external_message_id="<test@gmail.com>"))

    # db.add() should have been called with an EmailEvent instance
    from app.modules.email.models import EmailEvent

    db.add.assert_called_once()
    added_obj = db.add.call_args[0][0]
    assert isinstance(added_obj, EmailEvent)
    assert added_obj.direction == "inbound"
    assert added_obj.status == "received"
    assert added_obj.message_id == "<test@gmail.com>"
