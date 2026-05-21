"""
Email provider interfaces and skeleton implementations.

All providers are disabled by default and boot safely without credentials.
Live SMTP/IMAP calls are intentionally not wired here — that is EMAIL-002
(SMTP send) and EMAIL-003 (IMAP inbox reader).

Provider hierarchy:
  EmailSendProvider  (Protocol)
    └── GmailSMTPProvider

  EmailInboxProvider (Protocol)
    └── GmailIMAPProvider
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ─── Send provider ────────────────────────────────────────────────────────────


@runtime_checkable
class EmailSendProvider(Protocol):
    """Interface for outbound email providers."""

    @property
    def is_configured(self) -> bool:
        """Return True only when all required credentials are present."""
        ...

    @property
    def provider_name(self) -> str:
        """Human-readable provider identifier."""
        ...

    def send(
        self,
        to_address: str,
        subject: str,
        body: str,
        from_address: str | None = None,
    ) -> bool:
        """
        Send an email. Returns True on success, False on failure.

        Implementations MUST return False (not raise) when unconfigured.
        """
        ...


class GmailSMTPProvider:
    """
    Gmail SMTP send provider (POC-only).

    Reads credentials from app settings at construction time.
    Returns is_configured=False and skips sending when credentials are absent.
    No live network calls until EMAIL-002 wires the actual send logic.
    """

    provider_name = "gmail_smtp"

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_email: str,
        from_name: str = "EventSales AI",
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_email = from_email
        self._from_name = from_name

    @property
    def is_configured(self) -> bool:
        return bool(self._username and self._password and self._from_email)

    def send(
        self,
        to_address: str,
        subject: str,
        body: str,
        from_address: str | None = None,
    ) -> bool:
        if not self.is_configured:
            logger.warning(
                "GmailSMTPProvider: send skipped — credentials not configured "
                "(set SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL in .env)"
            )
            return False
        # Live send logic wired in EMAIL-002.
        logger.info(
            "GmailSMTPProvider: send called but not yet implemented "
            "(to=%s subject=%r)", to_address, subject
        )
        return False

    def status(self) -> dict:
        return {
            "provider": self.provider_name,
            "configured": self.is_configured,
            "host": self._host,
            "port": self._port,
            "from_email": self._from_email if self.is_configured else None,
        }


# ─── Inbox provider ───────────────────────────────────────────────────────────


@runtime_checkable
class EmailInboxProvider(Protocol):
    """Interface for inbound email inbox providers."""

    @property
    def is_configured(self) -> bool:
        """Return True only when all required credentials are present."""
        ...

    @property
    def provider_name(self) -> str:
        """Human-readable provider identifier."""
        ...

    def poll(self) -> list[dict]:
        """
        Poll for new messages. Returns a list of raw message dicts.

        Implementations MUST return an empty list (not raise) when unconfigured.
        """
        ...


class GmailIMAPProvider:
    """
    Gmail IMAP inbox reader provider (POC-only).

    Reads credentials from app settings at construction time.
    Returns is_configured=False and an empty list when credentials are absent.
    No live network calls until EMAIL-003 wires the actual polling logic.
    """

    provider_name = "gmail_imap"

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password

    @property
    def is_configured(self) -> bool:
        return bool(self._username and self._password)

    def poll(self) -> list[dict]:
        if not self.is_configured:
            logger.warning(
                "GmailIMAPProvider: poll skipped — credentials not configured "
                "(set IMAP_USERNAME, IMAP_PASSWORD in .env)"
            )
            return []
        # Live poll logic wired in EMAIL-003.
        logger.info("GmailIMAPProvider: poll called but not yet implemented")
        return []

    def status(self) -> dict:
        return {
            "provider": self.provider_name,
            "configured": self.is_configured,
            "host": self._host,
            "port": self._port,
        }


# ─── Factory helpers ──────────────────────────────────────────────────────────


def make_smtp_provider() -> GmailSMTPProvider:
    """Construct a GmailSMTPProvider from application settings."""
    from app.core.config import settings

    return GmailSMTPProvider(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        from_email=settings.smtp_from_email,
        from_name=settings.smtp_from_name,
    )


def make_imap_provider() -> GmailIMAPProvider:
    """Construct a GmailIMAPProvider from application settings."""
    from app.core.config import settings

    return GmailIMAPProvider(
        host=settings.imap_host,
        port=settings.imap_port,
        username=settings.imap_username,
        password=settings.imap_password,
    )


def email_config_status() -> dict:
    """
    Return a summary of email configuration status for health checks.

    Safe to call at any time — never raises, never makes network calls.
    """
    smtp = make_smtp_provider()
    imap = make_imap_provider()
    return {
        "smtp": smtp.status(),
        "imap": imap.status(),
        "email_enabled": smtp.is_configured and imap.is_configured,
    }
