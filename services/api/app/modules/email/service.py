"""EmailDeliveryService — logs email delivery status to PostgreSQL.

All email state transitions write to the email_events table.
Redis / Celery carry tasks but never own durable state.
"""
import uuid

from sqlalchemy.orm import Session

from app.modules.email.constants import EmailDeliveryStatus
from app.modules.email.models import EmailEvent
from app.modules.email.repository import EmailEventRepository

_DISABLED_ERROR = (
    "SMTP not configured — set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, "
    "SMTP_PASSWORD to activate email sending"
)


class EmailDeliveryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._repo = EmailEventRepository(db)

    # ── Outbound lifecycle ─────────────────────────────────────────────────────

    def log_disabled(
        self,
        *,
        to_address: str,
        from_address: str,
        subject: str,
        enquiry_id: uuid.UUID | None = None,
        body: str | None = None,
    ) -> EmailEvent:
        """Log a send attempt that was skipped because SMTP is not configured."""
        return self._repo.create(
            enquiry_id=enquiry_id,
            direction="outbound",
            status=EmailDeliveryStatus.DISABLED,
            from_address=from_address,
            to_address=to_address,
            subject=subject,
            body=body,
            error=_DISABLED_ERROR,
        )

    def log_send_attempt(
        self,
        *,
        to_address: str,
        from_address: str,
        subject: str,
        enquiry_id: uuid.UUID | None = None,
        body: str | None = None,
    ) -> EmailEvent:
        """Log the start of an SMTP send attempt (status: queued for Celery pickup)."""
        return self._repo.create(
            enquiry_id=enquiry_id,
            direction="outbound",
            status=EmailDeliveryStatus.QUEUED,
            from_address=from_address,
            to_address=to_address,
            subject=subject,
            body=body,
        )

    def log_sending(self, event_id: uuid.UUID) -> EmailEvent | None:
        """Mark a queued event as actively sending (called by Celery worker)."""
        return self._repo.update_status(event_id, EmailDeliveryStatus.SENDING)

    def log_sent(
        self,
        event_id: uuid.UUID,
        *,
        message_id: str | None = None,
    ) -> EmailEvent | None:
        """Mark a send attempt as successfully delivered by SMTP."""
        return self._repo.update_status(
            event_id,
            EmailDeliveryStatus.SENT,
            message_id=message_id,
        )

    def log_failed(self, event_id: uuid.UUID, *, error: str) -> EmailEvent | None:
        """Mark a send attempt as failed with an error message."""
        return self._repo.update_status(
            event_id,
            EmailDeliveryStatus.FAILED,
            error=error,
        )

    # ── Query helpers ──────────────────────────────────────────────────────────

    def get_latest_status(self, enquiry_id: uuid.UUID) -> str | None:
        """Return the most recent email delivery status for a given enquiry."""
        event = self._repo.get_latest_for_enquiry(enquiry_id)
        return event.status if event else None
