"""Pydantic schemas for the email module.

Source of truth for API contracts related to email delivery.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class SendDraftIn(BaseModel):
    """Request body for POST /api/v1/email/send-draft."""

    enquiry_id: uuid.UUID
    to_email: EmailStr


class SendDraftOut(BaseModel):
    """Response from POST /api/v1/email/send-draft."""

    event_id: uuid.UUID
    status: str
    message: str


class EmailEventOut(BaseModel):
    """Read-only representation of an EmailEvent row."""

    id: uuid.UUID
    enquiry_id: uuid.UUID | None
    direction: str
    status: str
    from_address: str
    to_address: str
    subject: str
    error: str | None
    message_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
