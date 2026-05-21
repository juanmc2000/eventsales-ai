"""
Email module API router.

Provides endpoints for sending draft emails and checking email configuration.
All send operations are disabled until SMTP credentials are configured.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.email.schemas import SendDraftRequest, SendEmailResult
from app.modules.email.send_service import EmailSendService

router = APIRouter(prefix="/api/v1/email", tags=["email"])


def get_send_service(db: Session = Depends(get_db)) -> EmailSendService:
    return EmailSendService(db)


@router.post("/send-draft", response_model=SendEmailResult)
def send_draft(
    data: SendDraftRequest,
    service: EmailSendService = Depends(get_send_service),
) -> SendEmailResult:
    """
    Attempt to send a draft email via Gmail SMTP.

    Returns status='disabled' when SMTP credentials are not configured.
    No live SMTP calls are made in that state.
    """
    return service.send_draft(data)


@router.get("/status")
def email_status() -> dict:
    """
    Return current email provider configuration status.

    Safe to call at any time — never makes network calls.
    """
    from app.modules.email.providers import email_config_status

    return email_config_status()
