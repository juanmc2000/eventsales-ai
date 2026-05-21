"""Repository for EmailEvent persistence.

PostgreSQL is the source of truth for all email activity.
"""
import uuid

from sqlalchemy.orm import Session

from app.modules.email.models import EmailEvent


class EmailEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        direction: str,
        status: str,
        from_address: str,
        to_address: str,
        subject: str,
        enquiry_id: uuid.UUID | None = None,
        body: str | None = None,
        message_id: str | None = None,
        error: str | None = None,
    ) -> EmailEvent:
        event = EmailEvent(
            enquiry_id=enquiry_id,
            direction=direction,
            status=status,
            from_address=from_address,
            to_address=to_address,
            subject=subject,
            body=body,
            message_id=message_id,
            error=error,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def update_status(
        self,
        event_id: uuid.UUID,
        status: str,
        *,
        error: str | None = None,
        message_id: str | None = None,
    ) -> EmailEvent | None:
        event = self.db.get(EmailEvent, event_id)
        if not event:
            return None
        event.status = status
        if error is not None:
            event.error = error
        if message_id is not None:
            event.message_id = message_id
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_latest_for_enquiry(self, enquiry_id: uuid.UUID) -> EmailEvent | None:
        return (
            self.db.query(EmailEvent)
            .filter(EmailEvent.enquiry_id == enquiry_id)
            .order_by(EmailEvent.created_at.desc())
            .first()
        )
