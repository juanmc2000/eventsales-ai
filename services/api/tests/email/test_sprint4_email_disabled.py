"""
TEST-004: Sprint 4 Email Disabled Wiring Tests.

Verifies that SMTP and IMAP providers return safe no-op results when
credentials are absent, and that the system operates normally without
live email infrastructure.
"""

from __future__ import annotations

from app.modules.email.inbox_service import InboxParser, InboxReaderService, ParsedEmail
from app.modules.email.providers import GmailIMAPProvider, GmailSMTPProvider


# ─── SMTP disabled mode ───────────────────────────────────────────────────────


class TestSMTPDisabledMode:
    def test_unconfigured_smtp_returns_false_on_send(self):
        p = GmailSMTPProvider("smtp.gmail.com", 587, "", "", "")
        assert p.send("guest@example.com", "Subject", "Body") is False

    def test_smtp_is_not_configured_without_credentials(self):
        p = GmailSMTPProvider("smtp.gmail.com", 587, "", "", "")
        assert p.is_configured is False

    def test_smtp_configured_with_full_credentials(self):
        p = GmailSMTPProvider("smtp.gmail.com", 587, "u", "p", "u@example.com")
        assert p.is_configured is True

    def test_smtp_send_returns_false_even_when_configured(self):
        # Not-yet-wired: live send returns False until EMAIL-002 completes.
        p = GmailSMTPProvider("smtp.gmail.com", 587, "u", "p", "u@example.com")
        assert p.send("guest@example.com", "Subject", "Body") is False

    def test_smtp_status_configured_false(self):
        p = GmailSMTPProvider("smtp.gmail.com", 587, "", "", "")
        assert p.status()["configured"] is False

    def test_smtp_status_from_email_hidden_when_unconfigured(self):
        p = GmailSMTPProvider("smtp.gmail.com", 587, "", "", "")
        assert p.status()["from_email"] is None


# ─── IMAP disabled mode ───────────────────────────────────────────────────────


class TestIMAPDisabledMode:
    def test_unconfigured_imap_returns_empty_list_on_poll(self):
        p = GmailIMAPProvider("imap.gmail.com", 993, "", "")
        assert p.poll() == []

    def test_imap_is_not_configured_without_credentials(self):
        p = GmailIMAPProvider("imap.gmail.com", 993, "", "")
        assert p.is_configured is False

    def test_imap_configured_with_credentials(self):
        p = GmailIMAPProvider("imap.gmail.com", 993, "u", "p")
        assert p.is_configured is True

    def test_imap_poll_returns_empty_when_not_wired(self):
        p = GmailIMAPProvider("imap.gmail.com", 993, "u", "p")
        assert p.poll() == []


# ─── InboxReaderService ───────────────────────────────────────────────────────


class TestInboxReaderServiceDisabledMode:
    def test_poll_returns_empty_when_unconfigured(self):
        service = InboxReaderService(provider=GmailIMAPProvider("imap.gmail.com", 993, "", ""))
        assert service.poll() == []

    def test_status_poll_enabled_false_when_unconfigured(self):
        service = InboxReaderService(provider=GmailIMAPProvider("imap.gmail.com", 993, "", ""))
        assert service.status()["poll_enabled"] is False

    def test_status_reason_present_when_unconfigured(self):
        service = InboxReaderService(provider=GmailIMAPProvider("imap.gmail.com", 993, "", ""))
        assert service.status()["reason"] is not None


# ─── InboxParser ──────────────────────────────────────────────────────────────


class TestInboxParserSprint4:
    def _parser(self) -> InboxParser:
        return InboxParser()

    def test_parse_webform_style_enquiry_email(self):
        raw = {
            "from": "alice@example.com",
            "to": "events@restaurant.com",
            "subject": "Event Enquiry — Birthday Party",
            "body": "Hi, I'd like to book a table for 20 people.",
            "date": "Thu, 21 May 2026 10:00:00 +0000",
        }
        parsed = self._parser().parse(raw)
        assert parsed.from_address == "alice@example.com"
        assert parsed.subject == "Event Enquiry — Birthday Party"
        assert parsed.received_at is not None

    def test_parse_reply_email_strips_re_prefix(self):
        raw = {"subject": "Re: Event Enquiry — Birthday Party"}
        parsed = self._parser().parse(raw)
        assert parsed.subject == "Event Enquiry — Birthday Party"

    def test_parse_empty_raw_produces_safe_defaults(self):
        parsed = self._parser().parse({})
        assert parsed.from_address is None
        assert parsed.body == ""

    def test_parse_many_batch(self):
        raws = [{"from": f"guest{i}@example.com"} for i in range(5)]
        results = self._parser().parse_many(raws)
        assert len(results) == 5
        assert all(isinstance(r, ParsedEmail) for r in results)
