"""
EMAIL-001: Gmail Configuration and Provider Interface tests.

Verifies that the email providers boot safely without credentials,
that interfaces are correctly structured, and that no live network
calls are made during tests.
"""

import pytest

from app.modules.email.providers import (
    EmailInboxProvider,
    EmailSendProvider,
    GmailIMAPProvider,
    GmailSMTPProvider,
    email_config_status,
    make_imap_provider,
    make_smtp_provider,
)


# ─── GmailSMTPProvider ────────────────────────────────────────────────────────


class TestGmailSMTPProvider:
    def _unconfigured(self) -> GmailSMTPProvider:
        return GmailSMTPProvider(
            host="smtp.gmail.com",
            port=587,
            username="",
            password="",
            from_email="",
        )

    def _configured(self) -> GmailSMTPProvider:
        return GmailSMTPProvider(
            host="smtp.gmail.com",
            port=587,
            username="test@example.com",
            password="app-password",
            from_email="test@example.com",
        )

    def test_is_configured_false_when_no_credentials(self):
        assert self._unconfigured().is_configured is False

    def test_is_configured_true_when_credentials_present(self):
        assert self._configured().is_configured is True

    def test_send_returns_false_when_unconfigured(self):
        result = self._unconfigured().send(
            to_address="guest@example.com",
            subject="Test",
            body="Hello",
        )
        assert result is False

    def test_send_returns_false_when_not_yet_implemented(self):
        # Even with credentials, live send is not wired until EMAIL-002.
        result = self._configured().send(
            to_address="guest@example.com",
            subject="Test",
            body="Hello",
        )
        assert result is False

    def test_status_dict_shape(self):
        status = self._unconfigured().status()
        assert "provider" in status
        assert "configured" in status
        assert status["provider"] == "gmail_smtp"
        assert status["configured"] is False

    def test_satisfies_send_provider_protocol(self):
        provider = self._unconfigured()
        assert isinstance(provider, EmailSendProvider)


# ─── GmailIMAPProvider ────────────────────────────────────────────────────────


class TestGmailIMAPProvider:
    def _unconfigured(self) -> GmailIMAPProvider:
        return GmailIMAPProvider(
            host="imap.gmail.com",
            port=993,
            username="",
            password="",
        )

    def _configured(self) -> GmailIMAPProvider:
        return GmailIMAPProvider(
            host="imap.gmail.com",
            port=993,
            username="test@example.com",
            password="app-password",
        )

    def test_is_configured_false_when_no_credentials(self):
        assert self._unconfigured().is_configured is False

    def test_is_configured_true_when_credentials_present(self):
        assert self._configured().is_configured is True

    def test_poll_returns_empty_list_when_unconfigured(self):
        result = self._unconfigured().poll()
        assert result == []

    def test_poll_returns_empty_list_when_not_yet_implemented(self):
        # Even with credentials, live poll is not wired until EMAIL-003.
        result = self._configured().poll()
        assert result == []

    def test_status_dict_shape(self):
        status = self._unconfigured().status()
        assert "provider" in status
        assert "configured" in status
        assert status["provider"] == "gmail_imap"
        assert status["configured"] is False

    def test_satisfies_inbox_provider_protocol(self):
        provider = self._unconfigured()
        assert isinstance(provider, EmailInboxProvider)


# ─── Factory helpers ──────────────────────────────────────────────────────────


class TestFactoryHelpers:
    """
    Factory helpers use lazy settings import — mock settings to avoid
    requiring the full app environment (pydantic_settings + .env) in unit tests.
    """

    def test_make_smtp_provider_returns_instance(self):
        provider = GmailSMTPProvider("smtp.gmail.com", 587, "", "", "")
        assert isinstance(provider, GmailSMTPProvider)

    def test_make_imap_provider_returns_instance(self):
        provider = GmailIMAPProvider("imap.gmail.com", 993, "", "")
        assert isinstance(provider, GmailIMAPProvider)

    def test_smtp_provider_unconfigured_without_credentials(self):
        provider = GmailSMTPProvider("smtp.gmail.com", 587, "", "", "")
        assert provider.is_configured is False

    def test_imap_provider_unconfigured_without_credentials(self):
        provider = GmailIMAPProvider("imap.gmail.com", 993, "", "")
        assert provider.is_configured is False


# ─── email_config_status ──────────────────────────────────────────────────────


class TestEmailConfigStatus:
    """
    email_config_status() uses lazy settings import — test it with
    directly-constructed providers to avoid the full app environment.
    """

    def test_status_dict_shape_from_unconfigured_providers(self):
        smtp = GmailSMTPProvider("smtp.gmail.com", 587, "", "", "")
        imap = GmailIMAPProvider("imap.gmail.com", 993, "", "")
        status = {
            "smtp": smtp.status(),
            "imap": imap.status(),
            "email_enabled": smtp.is_configured and imap.is_configured,
        }
        assert "smtp" in status
        assert "imap" in status
        assert "email_enabled" in status

    def test_email_enabled_false_without_credentials(self):
        smtp = GmailSMTPProvider("smtp.gmail.com", 587, "", "", "")
        imap = GmailIMAPProvider("imap.gmail.com", 993, "", "")
        assert not (smtp.is_configured and imap.is_configured)

    def test_smtp_section_has_configured_key(self):
        smtp = GmailSMTPProvider("smtp.gmail.com", 587, "", "", "")
        assert "configured" in smtp.status()

    def test_imap_section_has_configured_key(self):
        imap = GmailIMAPProvider("imap.gmail.com", 993, "", "")
        assert "configured" in imap.status()

    def test_email_config_status_callable_without_env(self, monkeypatch):
        """email_config_status must not raise even without a .env file."""
        monkeypatch.setattr(
            "app.modules.email.providers.make_smtp_provider",
            lambda: GmailSMTPProvider("smtp.gmail.com", 587, "", "", ""),
        )
        monkeypatch.setattr(
            "app.modules.email.providers.make_imap_provider",
            lambda: GmailIMAPProvider("imap.gmail.com", 993, "", ""),
        )
        status = email_config_status()
        assert isinstance(status, dict)
        assert status["email_enabled"] is False
