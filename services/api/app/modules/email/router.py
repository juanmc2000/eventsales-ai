"""Email module router.

Endpoint: POST /api/v1/email/send-draft
Returns 503 when SMTP credentials are not configured.
Actual SMTP delivery is handled by the Celery task in WORKFLOW-005.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.modules.email.constants import EmailDeliveryStatus
from app.modules.email.schemas import SendDraftIn, SendDraftOut
from app.modules.email.service import EmailDeliveryService

router = APIRouter(prefix="/api/v1/email", tags=["email"])

_SMTP_ENABLED = bool(settings.smtp_username and settings.smtp_password)


def _smtp_enabled() -> bool:
    """Re-evaluate at request time so tests can patch settings."""
    return bool(settings.smtp_username and settings.smtp_password)


@router.post("/send-draft", response_model=SendDraftOut)
def send_draft(
    data: SendDraftIn,
    db: Session = Depends(get_db),
) -> SendDraftOut:
    """
    Initiate sending of a generated draft email.

    - If SMTP credentials are absent: logs a DISABLED event and returns 503.
    - If SMTP credentials are present: logs a QUEUED event; the Celery
      task (WORKFLOW-005) handles actual delivery and updates the event
      status to SENT or FAILED.
    """
    svc = EmailDeliveryService(db)
    from_address = settings.smtp_from_email or settings.smtp_username or "noreply@example.com"
    subject = "Re: Your Event Enquiry"

    if not _smtp_enabled():
        event = svc.log_disabled(
            enquiry_id=data.enquiry_id,
            to_address=str(data.to_email),
            from_address=from_address,
            subject=subject,
        )
        raise HTTPException(
            status_code=503,
            detail={
                "status": EmailDeliveryStatus.DISABLED,
                "event_id": str(event.id),
                "message": "Gmail SMTP not configured — set credentials to activate sending",
            },
        )

    event = svc.log_send_attempt(
        enquiry_id=data.enquiry_id,
        to_address=str(data.to_email),
        from_address=from_address,
        subject=subject,
    )

    # WORKFLOW-005 enqueues the Celery task using event.id
    return SendDraftOut(
        event_id=event.id,
        status=EmailDeliveryStatus.QUEUED,
        message="Email queued for delivery via Gmail SMTP",
    )
