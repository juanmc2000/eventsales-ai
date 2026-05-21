"""
Email provider interfaces and implementations.

All providers are disabled by default and boot safely without credentials.
Live sending and polling activate automatically when credentials are present.

Provider hierarchy:
  EmailSendProvider  (Protocol)
    └── GmailSMTPProvider

  EmailInboxProvider (Protocol)
    └── GmailIMAPProvider
"""

from __future__ import annotations

import imaplib
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
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

        sender = from_address or self._from_email
        msg = MIMEMultipart()
        msg["From"] = formataddr((self._from_name, sender))
        msg["To"] = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            with smtplib.SMTP(self._host, self._port, timeout=30) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(self._username, self._password)
                smtp.sendmail(sender, to_address, msg.as_string())
            logger.info(
                "GmailSMTPProvider: sent to=%s subject=%r", to_address, subject
            )
            return True
        except Exception as exc:
            logger.error(
                "GmailSMTPProvider: send failed to=%s: %s", to_address, exc
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

    def poll(self, mailbox: str = "INBOX", max_messages: int = 20) -> list[dict]:
        if not self.is_configured:
            logger.warning(
                "GmailIMAPProvider: poll skipped — credentials not configured "
                "(set IMAP_USERNAME, IMAP_PASSWORD in .env)"
            )
            return []

        try:
            with imaplib.IMAP4_SSL(self._host, self._port) as imap:
                imap.login(self._username, self._password)
                imap.select(mailbox, readonly=True)
                status, data = imap.search(None, "UNSEEN")
                if status != "OK" or not data or not data[0]:
                    return []

                uids = data[0].split()
                uids = uids[-max_messages:]

                messages = []
                for uid in uids:
                    fetch_status, msg_data = imap.fetch(uid, "(RFC822)")
                    if fetch_status != "OK" or not msg_data:
                        continue
                    raw_bytes = msg_data[0][1] if isinstance(msg_data[0], tuple) else None
                    if not raw_bytes:
                        continue
                    messages.append(self._parse_rfc822(raw_bytes))

                logger.info(
                    "GmailIMAPProvider: polled %d messages from %s",
                    len(messages),
                    mailbox,
                )
                return messages
        except Exception as exc:
            logger.error("GmailIMAPProvider: poll failed: %s", exc)
            return []

    @staticmethod
    def _parse_rfc822(raw_bytes: bytes) -> dict:
        """Parse raw RFC822 bytes into a flat header+body dict for InboxParser."""
        import email as _email  # noqa: PLC0415

        msg = _email.message_from_bytes(raw_bytes)
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="replace")
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="replace")

        return {
            "message_id": msg.get("Message-ID"),
            "from": msg.get("From"),
            "to": msg.get("To"),
            "subject": msg.get("Subject"),
            "date": msg.get("Date"),
            "body": body,
        }

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
