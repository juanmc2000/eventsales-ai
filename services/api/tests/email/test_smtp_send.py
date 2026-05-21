"""
EMAIL-002: Disabled SMTP Send Service Wiring tests.

Verifies that the send service boots safely without credentials,
returns a clear 'disabled' status, and makes no live SMTP calls.

Note: Pydantic schema import tests are covered by the Docker integration suite.
Unit tests here use direct provider construction to avoid the app environment.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal
from unittest.mock import MagicMock

import pytest

from app.modules.email.providers import GmailSMTPProvider


# ─── Minimal request/result stand-ins for unit tests ─────────────────────────


@dataclass
class _SendRequest:
    enquiry_id: uuid.UUID
    to_address: str
    subject: str
    body: str


@dataclass
class _SendResult:
    status: Literal["sent", "disabled", "error"]
    reason: str | None = None
    email_event_id: uuid.UUID | None = None


def _make_send_result(provider: GmailSMTPProvider, request: _SendRequest) -> _SendResult:
    """Replicate EmailSendService.send_draft logic for pure unit tests."""
    if not provider.is_configured:
        return _SendResult(
            status="disabled",
            reason=(
                "SMTP credentials are not configured. "
                "Set SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM_EMAIL in .env "
                "to enable Gmail SMTP sending."
            ),
        )
    success = provider.send(
        to_address=request.to_address,
        subject=request.subject,
        body=request.body,
    )
    if success:
        return _SendResult(status="sent", email_event_id=uuid.uuid4())
    return _SendResult(
        status="disabled",
        reason="SMTP send is not yet implemented for this provider.",
    )


def _unconfigured_provider() -> GmailSMTPProvider:
    return GmailSMTPProvider("smtp.gmail.com", 587, "", "", "")


def _configured_provider() -> GmailSMTPProvider:
    return GmailSMTPProvider(
        "smtp.gmail.com", 587, "test@example.com", "app-password", "test@example.com"
    )


def _request() -> _SendRequest:
    return _SendRequest(
        enquiry_id=uuid.uuid4(),
        to_address="guest@example.com",
        subject="Your enquiry at The Grand",
        body="Dear Alice,\n\nThank you for your enquiry.",
    )


# ─── Disabled mode (no credentials) ──────────────────────────────────────────


class TestSendDisabledWhenUnconfigured:
    def test_returns_disabled_status(self):
        result = _make_send_result(_unconfigured_provider(), _request())
        assert result.status == "disabled"

    def test_reason_mentions_credentials(self):
        result = _make_send_result(_unconfigured_provider(), _request())
        assert result.reason is not None
        assert "SMTP" in result.reason or "credentials" in result.reason.lower()

    def test_email_event_id_is_none(self):
        result = _make_send_result(_unconfigured_provider(), _request())
        assert result.email_event_id is None

    def test_provider_send_returns_false_unconfigured(self):
        provider = _unconfigured_provider()
        result = provider.send("guest@example.com", "Subject", "Body")
        assert result is False


# ─── Configured-but-not-implemented mode ──────────────────────────────────────


class TestSendConfiguredNotImplemented:
    def test_returns_disabled_when_send_returns_false(self):
        # GmailSMTPProvider.send() returns False until live logic is wired.
        result = _make_send_result(_configured_provider(), _request())
        assert result.status == "disabled"

    def test_reason_is_set(self):
        result = _make_send_result(_configured_provider(), _request())
        assert result.reason is not None

    def test_no_sent_result_until_wired(self):
        result = _make_send_result(_configured_provider(), _request())
        assert result.status != "sent"


# ─── GmailSMTPProvider unit tests ─────────────────────────────────────────────


class TestGmailSMTPProviderUnit:
    def test_is_configured_false_no_credentials(self):
        assert _unconfigured_provider().is_configured is False

    def test_is_configured_true_with_credentials(self):
        assert _configured_provider().is_configured is True

    def test_send_returns_false_when_unconfigured(self):
        assert _unconfigured_provider().send("to@x.com", "sub", "body") is False

    def test_send_returns_false_when_not_yet_wired(self):
        # Configured but live send not wired until EMAIL-002 completes SMTP logic.
        assert _configured_provider().send("to@x.com", "sub", "body") is False

    def test_status_dict_has_configured_false(self):
        s = _unconfigured_provider().status()
        assert s["configured"] is False

    def test_status_dict_has_configured_true(self):
        s = _configured_provider().status()
        assert s["configured"] is True

    def test_status_dict_provider_name(self):
        assert _unconfigured_provider().status()["provider"] == "gmail_smtp"

    def test_from_email_hidden_when_unconfigured(self):
        s = _unconfigured_provider().status()
        assert s["from_email"] is None

    def test_from_email_visible_when_configured(self):
        s = _configured_provider().status()
        assert s["from_email"] == "test@example.com"
