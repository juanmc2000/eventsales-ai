"""Tests for email delivery status constants, service, and router.

All tests are smoke/unit tests — no live database required.
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest


# ── Constants ─────────────────────────────────────────────────────────────────


def test_all_statuses_defined() -> None:
    from app.modules.email.constants import EmailDeliveryStatus

    assert EmailDeliveryStatus.DRAFT == "draft"
    assert EmailDeliveryStatus.DISABLED == "disabled"
    assert EmailDeliveryStatus.QUEUED == "queued"
    assert EmailDeliveryStatus.SENDING == "sending"
    assert EmailDeliveryStatus.SENT == "sent"
    assert EmailDeliveryStatus.FAILED == "failed"


def test_all_tuple_contains_all_statuses() -> None:
    from app.modules.email.constants import EmailDeliveryStatus

    expected = {"draft", "disabled", "queued", "sending", "sent", "failed"}
    assert set(EmailDeliveryStatus.ALL) == expected


# ── Schemas ───────────────────────────────────────────────────────────────────


def test_send_draft_in_schema_valid() -> None:
    from app.modules.email.schemas import SendDraftIn

    payload = SendDraftIn(
        enquiry_id=uuid.uuid4(),
        to_email="guest@example.com",
    )
    assert payload.to_email == "guest@example.com"


def test_send_draft_in_schema_rejects_invalid_email() -> None:
    from pydantic import ValidationError

    from app.modules.email.schemas import SendDraftIn

    with pytest.raises(ValidationError):
        SendDraftIn(enquiry_id=uuid.uuid4(), to_email="not-an-email")


def test_send_draft_out_schema() -> None:
    from app.modules.email.schemas import SendDraftOut

    out = SendDraftOut(
        event_id=uuid.uuid4(),
        status="queued",
        message="Email queued for delivery",
    )
    assert out.status == "queued"


# ── Service ───────────────────────────────────────────────────────────────────


def _mock_email_event(status: str) -> MagicMock:
    event = MagicMock()
    event.id = uuid.uuid4()
    event.status = status
    event.enquiry_id = uuid.uuid4()
    event.direction = "outbound"
    return event


def _make_service():
    from app.modules.email.service import EmailDeliveryService

    db = MagicMock()
    svc = EmailDeliveryService(db)
    return svc


def test_log_disabled_creates_disabled_event() -> None:
    from app.modules.email.constants import EmailDeliveryStatus

    svc = _make_service()
    expected = _mock_email_event(EmailDeliveryStatus.DISABLED)
    svc._repo = MagicMock()
    svc._repo.create.return_value = expected

    result = svc.log_disabled(
        to_address="guest@example.com",
        from_address="test@gmail.com",
        subject="Re: Enquiry",
        enquiry_id=uuid.uuid4(),
    )

    svc._repo.create.assert_called_once()
    call_kwargs = svc._repo.create.call_args.kwargs
    assert call_kwargs["status"] == EmailDeliveryStatus.DISABLED
    assert call_kwargs["direction"] == "outbound"
    assert "SMTP not configured" in call_kwargs["error"]
    assert result.status == EmailDeliveryStatus.DISABLED


def test_log_send_attempt_creates_queued_event() -> None:
    from app.modules.email.constants import EmailDeliveryStatus

    svc = _make_service()
    expected = _mock_email_event(EmailDeliveryStatus.QUEUED)
    svc._repo = MagicMock()
    svc._repo.create.return_value = expected

    result = svc.log_send_attempt(
        to_address="guest@example.com",
        from_address="test@gmail.com",
        subject="Re: Enquiry",
    )

    call_kwargs = svc._repo.create.call_args.kwargs
    assert call_kwargs["status"] == EmailDeliveryStatus.QUEUED
    assert result.status == EmailDeliveryStatus.QUEUED


def test_log_sent_updates_status_to_sent() -> None:
    from app.modules.email.constants import EmailDeliveryStatus

    svc = _make_service()
    event_id = uuid.uuid4()
    expected = _mock_email_event(EmailDeliveryStatus.SENT)
    svc._repo = MagicMock()
    svc._repo.update_status.return_value = expected

    result = svc.log_sent(event_id, message_id="<msg-123@gmail.com>")

    svc._repo.update_status.assert_called_once_with(
        event_id,
        EmailDeliveryStatus.SENT,
        message_id="<msg-123@gmail.com>",
    )
    assert result.status == EmailDeliveryStatus.SENT


def test_log_failed_updates_status_to_failed() -> None:
    from app.modules.email.constants import EmailDeliveryStatus

    svc = _make_service()
    event_id = uuid.uuid4()
    expected = _mock_email_event(EmailDeliveryStatus.FAILED)
    svc._repo = MagicMock()
    svc._repo.update_status.return_value = expected

    result = svc.log_failed(event_id, error="SMTP connection refused")

    svc._repo.update_status.assert_called_once_with(
        event_id,
        EmailDeliveryStatus.FAILED,
        error="SMTP connection refused",
    )
    assert result.status == EmailDeliveryStatus.FAILED


def test_get_latest_status_returns_status_string() -> None:
    from app.modules.email.constants import EmailDeliveryStatus

    svc = _make_service()
    enquiry_id = uuid.uuid4()
    event = _mock_email_event(EmailDeliveryStatus.SENT)
    svc._repo = MagicMock()
    svc._repo.get_latest_for_enquiry.return_value = event

    status = svc.get_latest_status(enquiry_id)

    svc._repo.get_latest_for_enquiry.assert_called_once_with(enquiry_id)
    assert status == EmailDeliveryStatus.SENT


def test_get_latest_status_returns_none_when_no_events() -> None:
    svc = _make_service()
    svc._repo = MagicMock()
    svc._repo.get_latest_for_enquiry.return_value = None

    status = svc.get_latest_status(uuid.uuid4())

    assert status is None


# ── Router ────────────────────────────────────────────────────────────────────


def test_router_returns_503_when_smtp_disabled() -> None:
    """Router returns 503 and logs a DISABLED event when SMTP is not configured."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.modules.email.constants import EmailDeliveryStatus
    from app.modules.email.router import router

    app = FastAPI()
    app.include_router(router)

    enquiry_id = uuid.uuid4()
    disabled_event = _mock_email_event(EmailDeliveryStatus.DISABLED)

    mock_svc = MagicMock()
    mock_svc.log_disabled.return_value = disabled_event

    with patch("app.modules.email.router._smtp_enabled", return_value=False), \
         patch("app.modules.email.router.EmailDeliveryService", return_value=mock_svc), \
         patch("app.modules.email.router.get_db"):

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/email/send-draft",
            json={"enquiry_id": str(enquiry_id), "to_email": "guest@example.com"},
        )

    assert response.status_code == 503
    mock_svc.log_disabled.assert_called_once()


def test_router_returns_queued_when_smtp_enabled() -> None:
    """Router returns 200 with QUEUED status when SMTP credentials are present."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.modules.email.constants import EmailDeliveryStatus
    from app.modules.email.router import router

    app = FastAPI()
    app.include_router(router)

    enquiry_id = uuid.uuid4()
    queued_event = _mock_email_event(EmailDeliveryStatus.QUEUED)

    mock_svc = MagicMock()
    mock_svc.log_send_attempt.return_value = queued_event

    with patch("app.modules.email.router._smtp_enabled", return_value=True), \
         patch("app.modules.email.router.EmailDeliveryService", return_value=mock_svc), \
         patch("app.modules.email.router.get_db"):

        client = TestClient(app)
        response = client.post(
            "/api/v1/email/send-draft",
            json={"enquiry_id": str(enquiry_id), "to_email": "guest@example.com"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == EmailDeliveryStatus.QUEUED
    mock_svc.log_send_attempt.assert_called_once()
