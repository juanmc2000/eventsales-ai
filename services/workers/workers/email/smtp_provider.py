"""Minimal Gmail SMTP send provider for the Celery worker.

Uses only Python stdlib smtplib — no extra dependencies required.
All credentials come from environment variables, never from source code.
"""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

_SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
_SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
_SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
_SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
_SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "") or _SMTP_USERNAME
_SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "EventSales AI")


def is_smtp_configured() -> bool:
    """Return True when SMTP credentials are present in the environment."""
    return bool(_SMTP_USERNAME and _SMTP_PASSWORD)


def send_email(*, to_address: str, subject: str, body: str) -> str:
    """
    Send a plain-text email via Gmail SMTP (STARTTLS).

    Returns the SMTP message-id string on success.
    Raises smtplib.SMTPException or OSError on failure.

    This function must not be called when is_smtp_configured() is False.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{_SMTP_FROM_NAME} <{_SMTP_FROM_EMAIL}>"
    msg["To"] = to_address
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT, timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.login(_SMTP_USERNAME, _SMTP_PASSWORD)
        refused = server.sendmail(_SMTP_FROM_EMAIL, [to_address], msg.as_string())
        if refused:
            logger.warning("SMTP refused recipients: %s", refused)

    # smtplib doesn't expose the Message-ID assigned by Gmail; generate a placeholder
    message_id = msg.get("Message-ID") or f"<{id(msg)}@eventsales-ai>"
    logger.info("Email sent to %s (message_id=%s)", to_address, message_id)
    return message_id
