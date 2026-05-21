"""
EMAIL-006: Gmail IMAP live poll tests.

Verifies that GmailIMAPProvider polls correctly when configured and
gracefully handles all failure cases. All tests mock imaplib.IMAP4_SSL —
no live network calls are made.
"""

from __future__ import annotations

import email as _stdlib_email
from datetime import timezone
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch

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
        # Mock IMAP returning empty search results (no UNSEEN messages).
        with patch("imaplib.IMAP4_SSL") as mock_cls:
            imap = MagicMock()
            mock_cls.return_value.__enter__ = lambda s: imap
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            imap.search.return_value = ("OK", [b""])
            service = InboxReaderService(provider=_configured_provider())
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

    def test_poll_returns_empty_list_on_imap_exception(self):
        with patch("imaplib.IMAP4_SSL", side_effect=ConnectionRefusedError("refused")):
            assert _configured_provider().poll() == []

    def test_status_dict_keys(self):
        s = _unconfigured_provider().status()
        assert "provider" in s
        assert "configured" in s
        assert s["provider"] == "gmail_imap"


# ─── GmailIMAPProvider — live poll (mocked IMAP) ──────────────────────────────


def _make_rfc822(subject: str, from_addr: str, to_addr: str, body: str) -> bytes:
    """Build minimal RFC822 bytes for test fixtures."""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Message-ID"] = f"<test-{subject.replace(' ', '')}@example.com>"
    msg["Date"] = "Thu, 01 May 2026 10:00:00 +0000"
    return msg.as_bytes()


def _mock_imap_with_messages(rfc822_list: list[bytes]):
    """Return a configured IMAP4_SSL mock that yields the given messages."""
    imap = MagicMock()
    imap.search.return_value = (
        "OK",
        [b" ".join(str(i + 1).encode() for i in range(len(rfc822_list)))],
    )

    def fetch_side_effect(uid, fmt):
        idx = int(uid) - 1
        if idx < 0 or idx >= len(rfc822_list):
            return ("NO", [])
        return ("OK", [(b"1 (RFC822)", rfc822_list[idx])])

    imap.fetch.side_effect = fetch_side_effect
    return imap


class TestGmailIMAPProviderLivePoll:
    def _provider(self) -> GmailIMAPProvider:
        return _configured_provider()

    def test_poll_returns_list_of_dicts_on_success(self):
        raw = _make_rfc822("Booking enquiry", "alice@example.com", "inbox@venue.com", "Hello!")
        imap = _mock_imap_with_messages([raw])
        with patch("imaplib.IMAP4_SSL") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: imap
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = self._provider().poll()
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)

    def test_poll_extracts_subject(self):
        raw = _make_rfc822("Private dining request", "alice@example.com", "inbox@venue.com", "Body")
        imap = _mock_imap_with_messages([raw])
        with patch("imaplib.IMAP4_SSL") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: imap
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = self._provider().poll()
        assert result[0]["subject"] == "Private dining request"

    def test_poll_extracts_from_address(self):
        raw = _make_rfc822("Enquiry", "alice@example.com", "inbox@venue.com", "Body")
        imap = _mock_imap_with_messages([raw])
        with patch("imaplib.IMAP4_SSL") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: imap
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = self._provider().poll()
        assert "alice@example.com" in result[0]["from"]

    def test_poll_extracts_body(self):
        raw = _make_rfc822("Enquiry", "alice@example.com", "inbox@venue.com", "I want to book a table")
        imap = _mock_imap_with_messages([raw])
        with patch("imaplib.IMAP4_SSL") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: imap
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = self._provider().poll()
        assert "I want to book a table" in result[0]["body"]

    def test_poll_calls_login_with_credentials(self):
        raw = _make_rfc822("Enquiry", "alice@example.com", "inbox@venue.com", "Body")
        imap = _mock_imap_with_messages([raw])
        with patch("imaplib.IMAP4_SSL") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: imap
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            self._provider().poll()
        imap.login.assert_called_once_with("test@example.com", "app-password")

    def test_poll_selects_inbox_readonly(self):
        raw = _make_rfc822("Enquiry", "alice@example.com", "inbox@venue.com", "Body")
        imap = _mock_imap_with_messages([raw])
        with patch("imaplib.IMAP4_SSL") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: imap
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            self._provider().poll()
        imap.select.assert_called_once_with("INBOX", readonly=True)

    def test_poll_returns_empty_on_no_unseen_messages(self):
        imap = MagicMock()
        imap.search.return_value = ("OK", [b""])
        with patch("imaplib.IMAP4_SSL") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: imap
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = self._provider().poll()
        assert result == []

    def test_poll_returns_empty_on_search_failure(self):
        imap = MagicMock()
        imap.search.return_value = ("NO", [])
        with patch("imaplib.IMAP4_SSL") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: imap
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = self._provider().poll()
        assert result == []

    def test_poll_returns_empty_on_connection_error(self):
        with patch("imaplib.IMAP4_SSL", side_effect=ConnectionRefusedError("refused")):
            result = self._provider().poll()
        assert result == []

    def test_poll_returns_empty_on_auth_failure(self):
        imap = MagicMock()
        imap.login.side_effect = Exception("Authentication failed")
        with patch("imaplib.IMAP4_SSL") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: imap
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = self._provider().poll()
        assert result == []

    def test_poll_multiple_messages(self):
        msgs = [
            _make_rfc822(f"Enquiry {i}", f"guest{i}@example.com", "inbox@venue.com", f"Body {i}")
            for i in range(3)
        ]
        imap = _mock_imap_with_messages(msgs)
        with patch("imaplib.IMAP4_SSL") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: imap
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = self._provider().poll()
        assert len(result) == 3

    def test_poll_unconfigured_makes_no_imap_call(self):
        with patch("imaplib.IMAP4_SSL") as mock_cls:
            _unconfigured_provider().poll()
        mock_cls.assert_not_called()


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
