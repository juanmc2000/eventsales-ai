"""
EmailSendService — disabled SMTP send wiring.

Orchestrates draft email sending via GmailSMTPProvider.
Returns a clear 'disabled' status when credentials are not configured.
No live SMTP calls are made until credentials are set in .env.

Used by: POST /api/v1/email/send-draft
Future:  Celery task for async sending (not wired in POC).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.email.providers import GmailSMTPProvider, make_smtp_provider
from app.modules.email.schemas import SendDraftRequest, SendEmailResult

logger = logging.getLogger(__name__)


class EmailSendService:
    """
    Service layer for SMTP send operations.

    Disabled by default — returns status='disabled' when SMTP credentials
    are not present. No live network calls are made in that state.
    """

    def __init__(self, db: Session, provider: GmailSMTPProvider | None = None) -> None:
        self._db = db
        self._provider = provider or make_smtp_provider()

    def send_draft(self, request: SendDraftRequest) -> SendEmailResult:
        """
        Attempt to send a draft email via SMTP.

        Returns:
          status='disabled' — SMTP credentials not configured.
          status='sent'     — Email delivered successfully (future).
          status='error'    — Provider returned False despite being configured.
        """
        if not self._provider.is_configured:
            logger.info(
                "EmailSendService: send skipped for enquiry=%s — provider not configured",
                request.enquiry_id,
            )
            return SendEmailResult(
                status="disabled",
                reason=(
                    "SMTP credentials are not configured. "
                    "Set SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM_EMAIL in .env "
                    "to enable Gmail SMTP sending."
                ),
            )

        # Provider is configured — attempt send (live logic wired here in future).
        success = self._provider.send(
            to_address=str(request.to_address),
            subject=request.subject,
            body=request.body,
        )

        if success:
            sent_at = datetime.now(tz=timezone.utc)
            email_event_id = self._log_email_event(request, sent_at)
            return SendEmailResult(
                status="sent",
                email_event_id=email_event_id,
                sent_at=sent_at,
            )

        # Provider returned False (not yet fully implemented).
        return SendEmailResult(
            status="disabled",
            reason="SMTP send is not yet implemented for this provider.",
        )

    def _log_email_event(
        self, request: SendDraftRequest, sent_at: datetime
    ) -> uuid.UUID | None:
        """
        Log a sent email to email_events table.

        Returns the new EmailEvent id, or None if logging fails.
        Failures are non-fatal — the send result is not affected.
        """
        try:
            from app.modules.email.models import EmailEvent
            from app.core.config import settings

            event = EmailEvent(
                id=uuid.uuid4(),
                enquiry_id=request.enquiry_id,
                direction="outbound",
                status="sent",
                from_address=settings.smtp_from_email,
                to_address=str(request.to_address),
                subject=request.subject,
                body=request.body,
            )
            self._db.add(event)
            self._db.flush()
            return event.id
        except Exception as exc:
            logger.warning("EmailSendService: failed to log email event: %s", exc)
            return None

    @staticmethod
    def smtp_status() -> dict:
        """Return current SMTP provider configuration status."""
        provider = make_smtp_provider()
        return provider.status()
