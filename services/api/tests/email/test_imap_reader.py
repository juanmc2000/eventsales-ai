"""
EMAIL-003: Disabled IMAP Inbox Reader Wiring tests.

Verifies that the inbox reader boots safely without credentials,
returns an empty list, and that the parser correctly normalises
raw IMAP message dicts. No live IMAP calls are made.
"""

from __future__ import annotations

from datetime import timezone

import pytest

from app.modules.email.inbox_service import InboxParser, InboxReaderService, ParsedEmail
from app.modules.email.providers import GmailIMAPProvider


def _unconfigured_provider() -> GmailIMAPProvider:
    return GmailIMAPProvider("imap.gmail.com", 993, "", "")


def _configured_provider() -> GmailIMAPProvider:
    return GmailIMAPProvider("imap.gmail.com", 993, "test@example.com", "app-password")


# ─── InboxReaderService — disabled mode ───────────────────────────────────────


class TestInboxReaderServiceDisabled:
    def test_poll_returns_empty_list_when_unconfigured(self):
        service = InboxReaderService(provider=_unconfigured_provider())
        assert service.poll() == []

    def test_poll_returns_empty_list_when_provider_returns_nothing(self):
        service = InboxReaderService(provider=_configured_provider())
        # Configured provider still returns [] until live logic is wired (EMAIL-003 live).
        result = service.poll()
        assert result == []

    def test_status_poll_enabled_false_when_unconfigured(self):
        service = InboxReaderService(provider=_unconfigured_provider())
        status = service.status()
        assert status["poll_enabled"] is False

    def test_status_reason_mentions_credentials(self):
        service = InboxReaderService(provider=_unconfigured_provider())
        status = service.status()
        assert status["reason"] is not None
        assert "IMAP" in status["reason"] or "credentials" in status["reason"].lower()

    def test_status_poll_enabled_true_when_configured(self):
        service = InboxReaderService(provider=_configured_provider())
        status = service.status()
        assert status["poll_enabled"] is True

    def test_status_reason_none_when_configured(self):
        service = InboxReaderService(provider=_configured_provider())
        assert service.status()["reason"] is None

    def test_no_imap_call_when_unconfigured(self):
        calls = []
        provider = _unconfigured_provider()
        original_poll = provider.poll

        def tracking_poll():
            calls.append(True)
            return original_poll()

        provider.poll = tracking_poll  # type: ignore[method-assign]
        service = InboxReaderService(provider=provider)
        service.poll()
        # Provider.poll() is not called when is_configured is False.
        assert calls == []


# ─── GmailIMAPProvider unit tests ─────────────────────────────────────────────


class TestGmailIMAPProviderUnit:
    def test_is_configured_false_no_credentials(self):
        assert _unconfigured_provider().is_configured is False

    def test_is_configured_true_with_credentials(self):
        assert _configured_provider().is_configured is True

    def test_poll_returns_empty_list_unconfigured(self):
        assert _unconfigured_provider().poll() == []

    def test_poll_returns_empty_list_not_yet_wired(self):
        assert _configured_provider().poll() == []

    def test_status_dict_keys(self):
        s = _unconfigured_provider().status()
        assert "provider" in s
        assert "configured" in s
        assert s["provider"] == "gmail_imap"


# ─── InboxParser ──────────────────────────────────────────────────────────────


class TestInboxParser:
    def _parser(self) -> InboxParser:
        return InboxParser()

    def test_parse_basic_message(self):
        raw = {
            "from": "Alice Smith <alice@example.com>",
            "to": "inbox@restaurant.com",
            "subject": "Event enquiry for July",
            "body": "Hello, I would like to book a private dining room.",
            "date": "Thu, 01 May 2026 10:00:00 +0000",
        }
        parsed = self._parser().parse(raw)
        assert isinstance(parsed, ParsedEmail)
        assert parsed.from_address == "alice@example.com"
        assert parsed.to_address == "inbox@restaurant.com"
        assert parsed.subject == "Event enquiry for July"
        assert "private dining" in (parsed.body or "")

    def test_extract_email_from_display_name(self):
        raw = {"from": "Alice Smith <alice@example.com>"}
        parsed = self._parser().parse(raw)
        assert parsed.from_address == "alice@example.com"

    def test_extract_bare_email(self):
        raw = {"from": "alice@example.com"}
        parsed = self._parser().parse(raw)
        assert parsed.from_address == "alice@example.com"

    def test_subject_re_prefix_stripped(self):
        raw = {"subject": "Re: Event enquiry for July", "from": "", "to": "", "body": ""}
        parsed = self._parser().parse(raw)
        assert parsed.subject == "Event enquiry for July"

    def test_subject_fwd_prefix_stripped(self):
        raw = {"subject": "Fwd: Event enquiry for July", "from": "", "to": "", "body": ""}
        parsed = self._parser().parse(raw)
        assert parsed.subject == "Event enquiry for July"

    def test_message_id_captured(self):
        raw = {"message_id": "<abc123@mail.gmail.com>"}
        parsed = self._parser().parse(raw)
        assert parsed.message_id == "<abc123@mail.gmail.com>"

    def test_parsed_date_is_datetime(self):
        raw = {"date": "Thu, 01 May 2026 10:00:00 +0000"}
        parsed = self._parser().parse(raw)
        assert parsed.received_at is not None

    def test_parsed_date_none_for_invalid(self):
        raw = {"date": "not a date"}
        parsed = self._parser().parse(raw)
        assert parsed.received_at is None

    def test_raw_preserved(self):
        raw = {"from": "alice@example.com", "custom": "value"}
        parsed = self._parser().parse(raw)
        assert parsed.raw == raw

    def test_parse_many_returns_list(self):
        raws = [
            {"from": "alice@example.com", "subject": "A"},
            {"from": "bob@example.com", "subject": "B"},
        ]
        results = self._parser().parse_many(raws)
        assert len(results) == 2
        assert all(isinstance(r, ParsedEmail) for r in results)

    def test_parse_many_empty_list(self):
        assert self._parser().parse_many([]) == []

    def test_missing_fields_produce_none(self):
        parsed = self._parser().parse({})
        assert parsed.from_address is None
        assert parsed.subject is None
        assert parsed.received_at is None

    def test_body_defaults_to_empty_string_for_missing(self):
        parsed = self._parser().parse({})
        assert parsed.body == ""
