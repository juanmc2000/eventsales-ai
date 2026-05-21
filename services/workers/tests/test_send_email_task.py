"""Unit tests for the send_draft_email Celery task and supporting services.

All tests are isolated — no live SMTP, no live PostgreSQL, no live Redis.
"""
import sys
import os
from unittest.mock import MagicMock, patch, call
import uuid

import pytest

# Ensure workers package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── smtp_provider tests ────────────────────────────────────────────────────────


def test_is_smtp_configured_returns_false_when_env_empty(monkeypatch) -> None:
    monkeypatch.setenv("SMTP_USERNAME", "")
    monkeypatch.setenv("SMTP_PASSWORD", "")
    # Force module to re-read env
    import importlib
    import workers.email.smtp_provider as mod
    importlib.reload(mod)
    assert mod.is_smtp_configured() is False


def test_is_smtp_configured_returns_true_when_env_set(monkeypatch) -> None:
    monkeypatch.setenv("SMTP_USERNAME", "test@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    import importlib
    import workers.email.smtp_provider as mod
    importlib.reload(mod)
    assert mod.is_smtp_configured() is True


def test_send_email_calls_smtp_and_returns_message_id(monkeypatch) -> None:
    monkeypatch.setenv("SMTP_USERNAME", "sender@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "sender@gmail.com")

    import importlib
    import workers.email.smtp_provider as mod
    importlib.reload(mod)

    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        msg_id = mod.send_email(
            to_address="guest@example.com",
            subject="Re: Enquiry",
            body="Hello, thank you for your enquiry.",
        )

    # Verify SMTP interactions happened
    mock_server.ehlo.assert_called_once()
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("sender@gmail.com", "secret")
    mock_server.sendmail.assert_called_once()
    assert msg_id  # non-empty message id


# ── EmailWorkerService tests ───────────────────────────────────────────────────


def _make_db_row(status: str, event_id: str | None = None) -> MagicMock:
    row = MagicMock()
    row.id = event_id or str(uuid.uuid4())
    row.status = status
    row.to_address = "guest@example.com"
    row.subject = "Re: Enquiry"
    row.body = "Draft body"
    return row


def _mock_db_session_with_row(row):
    """Return a context manager mock that yields a DB session with one fetchone result."""
    session = MagicMock()
    session.execute.return_value.fetchone.return_value = row
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=session)
    cm.__exit__ = MagicMock(return_value=False)
    return cm, session


def test_worker_service_skips_already_sent_event() -> None:
    from workers.email.worker_service import EmailWorkerService

    svc = EmailWorkerService()
    row = _make_db_row("sent")
    cm, session = _mock_db_session_with_row(row)

    with patch("workers.email.worker_service.get_db_session", return_value=cm):
        svc.execute(event_id=str(uuid.uuid4()))

    # No UPDATE calls issued
    update_calls = [c for c in session.execute.call_args_list if "UPDATE" in str(c)]
    assert len(update_calls) == 0


def test_worker_service_marks_disabled_when_smtp_not_configured() -> None:
    from workers.email.worker_service import EmailWorkerService

    svc = EmailWorkerService()
    row = _make_db_row("queued")
    cm, session = _mock_db_session_with_row(row)

    with patch("workers.email.worker_service.get_db_session", return_value=cm), \
         patch("workers.email.worker_service.is_smtp_configured", return_value=False):
        svc.execute(event_id=str(uuid.uuid4()))

    # Should have issued a DISABLED UPDATE
    all_calls_str = str(session.execute.call_args_list)
    assert "disabled" in all_calls_str.lower()


def test_worker_service_updates_to_sent_on_success() -> None:
    from workers.email.worker_service import EmailWorkerService

    svc = EmailWorkerService()
    event_id = str(uuid.uuid4())
    row = _make_db_row("queued", event_id)

    fetch_cm, fetch_session = _mock_db_session_with_row(row)
    update_cm, update_session = _mock_db_session_with_row(None)

    # First call: fetch event and mark SENDING; second call: update to SENT
    sessions = iter([fetch_cm, update_cm])

    def get_next_session():
        return next(sessions)

    with patch("workers.email.worker_service.get_db_session", side_effect=get_next_session), \
         patch("workers.email.worker_service.is_smtp_configured", return_value=True), \
         patch("workers.email.worker_service.send_email", return_value="<msg123@gmail.com>"):
        svc.execute(event_id=event_id)

    # The final update session should have received a SENT status
    all_calls_str = str(update_session.execute.call_args_list)
    assert "sent" in all_calls_str.lower()


def test_worker_service_updates_to_failed_on_smtp_error() -> None:
    from workers.email.worker_service import EmailWorkerService

    svc = EmailWorkerService()
    event_id = str(uuid.uuid4())
    row = _make_db_row("queued", event_id)

    fetch_cm, fetch_session = _mock_db_session_with_row(row)
    update_cm, update_session = _mock_db_session_with_row(None)

    sessions = iter([fetch_cm, update_cm])

    def get_next_session():
        return next(sessions)

    with patch("workers.email.worker_service.get_db_session", side_effect=get_next_session), \
         patch("workers.email.worker_service.is_smtp_configured", return_value=True), \
         patch("workers.email.worker_service.send_email", side_effect=Exception("SMTP error")):
        with pytest.raises(Exception, match="SMTP error"):
            svc.execute(event_id=event_id)

    # Final update should contain "failed"
    all_calls_str = str(update_session.execute.call_args_list)
    assert "failed" in all_calls_str.lower()


def test_worker_service_skips_missing_event() -> None:
    from workers.email.worker_service import EmailWorkerService

    svc = EmailWorkerService()
    # Row not found
    fetch_cm, fetch_session = _mock_db_session_with_row(None)

    with patch("workers.email.worker_service.get_db_session", return_value=fetch_cm):
        svc.execute(event_id=str(uuid.uuid4()))  # should not raise

    # Only one DB call (fetch), no UPDATEs
    assert fetch_session.execute.call_count == 1


# ── Task-level tests ───────────────────────────────────────────────────────────


def test_send_draft_email_task_returns_sent_on_success() -> None:
    from workers.email.tasks import send_draft_email

    event_id = str(uuid.uuid4())
    mock_svc = MagicMock()

    with patch("workers.email.tasks.EmailWorkerService", return_value=mock_svc):
        result = send_draft_email(event_id)  # call directly (not via Celery)

    mock_svc.execute.assert_called_once_with(event_id=event_id)
    assert result["status"] == "sent"
    assert result["event_id"] == event_id


def test_send_draft_email_task_returns_failed_on_non_retryable_error() -> None:
    from workers.email.tasks import send_draft_email

    event_id = str(uuid.uuid4())
    mock_svc = MagicMock()
    mock_svc.execute.side_effect = ValueError("Authentication failed")

    with patch("workers.email.tasks.EmailWorkerService", return_value=mock_svc):
        result = send_draft_email(event_id)

    assert result["status"] == "failed"
