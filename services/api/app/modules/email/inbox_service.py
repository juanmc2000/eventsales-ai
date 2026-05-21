"""
InboxReaderService — disabled IMAP inbox reader wiring.

Provides the service boundary for Gmail IMAP inbox polling.
Returns an empty list when credentials are not configured.
No live IMAP calls are made until credentials are set in .env.

Used by: future Celery scheduled task (not wired in Sprint 4).
Future:  Poll inbox, parse inbound emails, match to enquiries.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

from app.modules.email.providers import GmailIMAPProvider, make_imap_provider

logger = logging.getLogger(__name__)


# ─── Parsed email DTO ─────────────────────────────────────────────────────────


@dataclass
class ParsedEmail:
    """
    A normalised inbound email message.

    Populated by InboxParser from raw IMAP message dicts.
    All fields are optional — real messages may be missing headers.
    """

    message_id: str | None = None
    from_address: str | None = None
    to_address: str | None = None
    subject: str | None = None
    body: str | None = None
    received_at: datetime | None = None
    raw: dict = field(default_factory=dict)


# ─── Parser ───────────────────────────────────────────────────────────────────


class InboxParser:
    """
    Simple parser that converts raw IMAP message dicts into ParsedEmail objects.

    Kept minimal for POC — no attachment processing, no MIME decoding.
    """

    # Matches "Name <email@example.com>" or bare "email@example.com"
    _EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")

    def parse(self, raw: dict) -> ParsedEmail:
        """Parse a raw IMAP message dict into a ParsedEmail."""
        return ParsedEmail(
            message_id=self._get(raw, "message_id") or self._get(raw, "Message-ID"),
            from_address=self._extract_email(self._get(raw, "from") or self._get(raw, "From")),
            to_address=self._extract_email(self._get(raw, "to") or self._get(raw, "To")),
            subject=self._clean_subject(self._get(raw, "subject") or self._get(raw, "Subject")),
            body=self._get(raw, "body") or self._get(raw, "text") or "",
            received_at=self._parse_date(self._get(raw, "date") or self._get(raw, "Date")),
            raw=raw,
        )

    def parse_many(self, raws: list[dict]) -> list[ParsedEmail]:
        """Parse a list of raw messages."""
        return [self.parse(r) for r in raws]

    @staticmethod
    def _get(d: dict, key: str) -> str | None:
        value = d.get(key)
        return str(value).strip() if value is not None else None

    def _extract_email(self, value: str | None) -> str | None:
        if not value:
            return None
        match = self._EMAIL_RE.search(value)
        return match.group(0).lower() if match else value.strip().lower() or None

    @staticmethod
    def _clean_subject(value: str | None) -> str | None:
        if not value:
            return None
        # Strip common reply/forward prefixes for normalisation.
        cleaned = re.sub(r"^(Re:|Fwd?:)\s*", "", value, flags=re.IGNORECASE).strip()
        return cleaned or None

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        from email.utils import parsedate_to_datetime

        try:
            return parsedate_to_datetime(value)
        except Exception:
            return None


# ─── InboxReaderService ───────────────────────────────────────────────────────


class InboxReaderService:
    """
    Service layer for IMAP inbox polling.

    Disabled by default — returns an empty list when IMAP credentials are
    not configured. No live network calls are made in that state.
    """

    def __init__(
        self,
        provider: GmailIMAPProvider | None = None,
        parser: InboxParser | None = None,
    ) -> None:
        self._provider = provider or make_imap_provider()
        self._parser = parser or InboxParser()

    def poll(self) -> list[ParsedEmail]:
        """
        Poll the inbox for new messages.

        Returns an empty list when credentials are not configured or
        the live polling logic is not yet wired.
        """
        if not self._provider.is_configured:
            logger.info(
                "InboxReaderService: poll skipped — IMAP provider not configured "
                "(set IMAP_USERNAME, IMAP_PASSWORD in .env)"
            )
            return []

        raw_messages = self._provider.poll()
        if not raw_messages:
            return []

        return self._parser.parse_many(raw_messages)

    def status(self) -> dict:
        """Return IMAP provider configuration status."""
        return {
            **self._provider.status(),
            "poll_enabled": self._provider.is_configured,
            "reason": (
                None
                if self._provider.is_configured
                else "IMAP credentials not configured. Set IMAP_USERNAME and IMAP_PASSWORD in .env."
            ),
        }
