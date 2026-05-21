"""
EMAIL-004: Gmail SMTP live send tests.

Verifies that GmailSMTPProvider sends correctly when configured and
gracefully handles all failure cases. All tests mock smtplib.SMTP —
no live network calls are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.modules.email.providers import GmailSMTPProvider


def _unconfigured() -> GmailSMTPProvider:
    return GmailSMTPProvider("smtp.gmail.com", 587, "", "", "")


def _configured() -> GmailSMTPProvider:
    return GmailSMTPProvider(
        "smtp.gmail.com", 587, "test@example.com", "app-password", "test@example.com"
    )


# ─── Unconfigured — no credentials ────────────────────────────────────────────


class TestGmailSMTPUnconfigured:
    def test_is_configured_false(self):
        assert _unconfigured().is_configured is False

    def test_send_returns_false_without_credentials(self):
        assert _unconfigured().send("guest@example.com", "Subject", "Body") is False

    def test_status_configured_false(self):
        assert _unconfigured().status()["configured"] is False

    def test_from_email_hidden_when_unconfigured(self):
        assert _unconfigured().status()["from_email"] is None


# ─── Configured — mocked SMTP ─────────────────────────────────────────────────


class TestGmailSMTPLiveSend:
    def _mock_smtp(self):
        smtp_instance = MagicMock()
        return smtp_instance

    def test_send_returns_true_on_success(self):
        with patch("smtplib.SMTP") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: self._mock_smtp()
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = _configured().send("guest@example.com", "Subject", "Body")
        assert result is True

    def test_send_calls_starttls(self):
        smtp_instance = MagicMock()
        with patch("smtplib.SMTP") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: smtp_instance
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            _configured().send("guest@example.com", "Subject", "Body")
        smtp_instance.starttls.assert_called_once()

    def test_send_calls_login_with_credentials(self):
        smtp_instance = MagicMock()
        with patch("smtplib.SMTP") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: smtp_instance
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            _configured().send("guest@example.com", "Subject", "Body")
        smtp_instance.login.assert_called_once_with("test@example.com", "app-password")

    def test_send_calls_sendmail_with_recipient(self):
        smtp_instance = MagicMock()
        with patch("smtplib.SMTP") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: smtp_instance
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            _configured().send("guest@example.com", "Subject", "Body")
        call_args = smtp_instance.sendmail.call_args
        assert call_args[0][1] == "guest@example.com"

    def test_send_returns_false_on_smtp_exception(self):
        with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("refused")):
            result = _configured().send("guest@example.com", "Subject", "Body")
        assert result is False

    def test_send_returns_false_on_auth_failure(self):
        smtp_instance = MagicMock()
        smtp_instance.login.side_effect = Exception("Authentication failed")
        with patch("smtplib.SMTP") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: smtp_instance
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = _configured().send("guest@example.com", "Subject", "Body")
        assert result is False

    def test_send_uses_from_name_in_header(self):
        provider = GmailSMTPProvider(
            "smtp.gmail.com", 587, "test@example.com", "pw", "test@example.com",
            from_name="The Grand Events"
        )
        smtp_instance = MagicMock()
        captured = {}

        def capture_sendmail(sender, recipient, msg_str):
            captured["msg"] = msg_str

        smtp_instance.sendmail.side_effect = capture_sendmail
        with patch("smtplib.SMTP") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: smtp_instance
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            provider.send("guest@example.com", "Subject", "Body")
        assert "The Grand Events" in captured.get("msg", "")

    def test_send_uses_override_from_address(self):
        smtp_instance = MagicMock()
        captured = {}

        def capture_sendmail(sender, recipient, msg_str):
            captured["sender"] = sender

        smtp_instance.sendmail.side_effect = capture_sendmail
        with patch("smtplib.SMTP") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: smtp_instance
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            _configured().send(
                "guest@example.com", "Subject", "Body",
                from_address="override@example.com"
            )
        assert captured.get("sender") == "override@example.com"


# ─── Status and provider metadata ─────────────────────────────────────────────


class TestGmailSMTPProviderMeta:
    def test_is_configured_true_with_credentials(self):
        assert _configured().is_configured is True

    def test_status_dict_has_configured_true(self):
        assert _configured().status()["configured"] is True

    def test_status_dict_provider_name(self):
        assert _configured().status()["provider"] == "gmail_smtp"

    def test_from_email_visible_when_configured(self):
        assert _configured().status()["from_email"] == "test@example.com"

    def test_status_contains_host_and_port(self):
        s = _configured().status()
        assert s["host"] == "smtp.gmail.com"
        assert s["port"] == 587
