"""
Email module Pydantic schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class SendDraftRequest(BaseModel):
    """Request body for POST /api/v1/email/send-draft."""

    enquiry_id: uuid.UUID
    to_address: EmailStr
    subject: str = Field(..., max_length=500)
    body: str


class SendEmailResult(BaseModel):
    """Response for a send-draft attempt."""

    status: Literal["sent", "disabled", "error"]
    reason: str | None = None
    email_event_id: uuid.UUID | None = None
    sent_at: datetime | None = None
