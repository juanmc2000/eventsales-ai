"""
Email provider interfaces and skeleton implementations.

All providers are disabled by default and boot safely without credentials.
Live SMTP/IMAP calls are intentionally not wired here — that is EMAIL-002
(SMTP send) and EMAIL-003 (IMAP inbox reader).
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class EmailSendProvider(Protocol):
    @property
    def is_configured(self) -> bool: ...
    @property
    def provider_name(self) -> str: ...
    def send(self, to_address: str, subject: str, body: str, from_address: str | None = None) -> bool: ...


class GmailSMTPProvider:
    provider_name = "gmail_smtp"

    def __init__(self, host: str, port: int, username: str, password: str, from_email: str, from_name: str = "EventSales AI") -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_email = from_email
        self._from_name = from_name

    @property
    def is_configured(self) -> bool:
        return bool(self._username and self._password and self._from_email)

    def send(self, to_address: str, subject: str, body: str, from_address: str | None = None) -> bool:
        if not self.is_configured:
            logger.warning("GmailSMTPProvider: send skipped — credentials not configured")
            return False
        logger.info("GmailSMTPProvider: send not yet implemented (to=%s)", to_address)
        return False

    def status(self) -> dict:
        return {"provider": self.provider_name, "configured": self.is_configured, "host": self._host, "port": self._port, "from_email": self._from_email if self.is_configured else None}


@runtime_checkable
class EmailInboxProvider(Protocol):
    @property
    def is_configured(self) -> bool: ...
    @property
    def provider_name(self) -> str: ...
    def poll(self) -> list[dict]: ...


class GmailIMAPProvider:
    provider_name = "gmail_imap"

    def __init__(self, host: str, port: int, username: str, password: str) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password

    @property
    def is_configured(self) -> bool:
        return bool(self._username and self._password)

    def poll(self) -> list[dict]:
        if not self.is_configured:
            logger.warning("GmailIMAPProvider: poll skipped — credentials not configured")
            return []
        logger.info("GmailIMAPProvider: poll not yet implemented")
        return []

    def status(self) -> dict:
        return {"provider": self.provider_name, "configured": self.is_configured, "host": self._host, "port": self._port}


def make_smtp_provider() -> GmailSMTPProvider:
    from app.core.config import settings
    return GmailSMTPProvider(settings.smtp_host, settings.smtp_port, settings.smtp_username, settings.smtp_password, settings.smtp_from_email, settings.smtp_from_name)


def make_imap_provider() -> GmailIMAPProvider:
    from app.core.config import settings
    return GmailIMAPProvider(settings.imap_host, settings.imap_port, settings.imap_username, settings.imap_password)


def email_config_status() -> dict:
    smtp = make_smtp_provider()
    imap = make_imap_provider()
    return {"smtp": smtp.status(), "imap": imap.status(), "email_enabled": smtp.is_configured and imap.is_configured}
