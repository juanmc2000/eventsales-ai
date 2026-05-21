import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class EnquiryBase(BaseModel):
    restaurant_id: uuid.UUID
    persona_id: uuid.UUID | None = None
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    company_name: str | None = Field(default=None, max_length=255)
    party_size: int | None = Field(default=None, ge=1)
    event_date: date | None = None
    event_type: str | None = Field(default=None, max_length=50)
    # budget_indication: free text from guest (not a pricing rule)
    budget_indication: str | None = None
    preferred_area: str | None = Field(default=None, max_length=255)
    dietary_requirements: str | None = None
    special_requests: str | None = None
    # Initial message from the guest
    message: str | None = None
    source: str = Field(default="webform", max_length=30)


class EnquiryCreate(EnquiryBase):
    # Recommended minimum spend can be pre-populated from pricing rules at creation time
    recommended_minimum_spend: float | None = Field(default=None, ge=0)


class EnquiryStatusUpdate(BaseModel):
    status: str = Field(..., max_length=30)


class EnquiryUpdate(BaseModel):
    persona_id: uuid.UUID | None = None
    party_size: int | None = Field(default=None, ge=1)
    event_date: date | None = None
    event_type: str | None = Field(default=None, max_length=50)
    budget_indication: str | None = None
    preferred_area: str | None = Field(default=None, max_length=255)
    dietary_requirements: str | None = None
    special_requests: str | None = None
    recommended_minimum_spend: float | None = Field(default=None, ge=0)
    notes: str | None = None


class EnquiryOut(EnquiryBase):
    id: uuid.UUID
    reference: str
    status: str
    recommended_minimum_spend: float | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EnquiryListOut(BaseModel):
    items: list[EnquiryOut]
    total: int


# ── Messages ──────────────────────────────────────────────────────────────────


class EnquiryMessageCreate(BaseModel):
    direction: str = Field(..., pattern=r"^(inbound|outbound)$")
    channel: str = Field(default="manual", max_length=20)
    subject: str | None = Field(default=None, max_length=500)
    body: str
    sent_at: datetime | None = None


class EnquiryMessageOut(BaseModel):
    id: uuid.UUID
    enquiry_id: uuid.UUID
    direction: str
    channel: str
    subject: str | None
    body: str
    sent_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Intake ─────────────────────────────────────────────────────────────────────


class WebformIntakeRequest(BaseModel):
    """Input schema for the test enquiry webform intake endpoint."""

    restaurant_id: uuid.UUID
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    party_size: int | None = Field(default=None, ge=1)
    event_date: date | None = None
    event_type: str | None = Field(default=None, max_length=50)
    # meal_period is used to calculate a pricing recommendation (breakfast/lunch/dinner)
    meal_period: str = Field(default="dinner", max_length=20)
    message: str | None = None
    company_name: str | None = Field(default=None, max_length=255)
    budget_indication: str | None = None
    preferred_area: str | None = Field(default=None, max_length=255)
    dietary_requirements: str | None = None
    special_requests: str | None = None


class EnquiryIntakeOut(BaseModel):
    """Response schema for the enquiry intake endpoint.

    Includes the created enquiry plus the persona and pricing context
    derived during orchestration.
    """

    enquiry_id: uuid.UUID
    reference: str
    status: str
    restaurant_id: uuid.UUID
    # Persona context
    persona_id: uuid.UUID | None = None
    persona_name: str | None = None
    # Pricing context
    recommended_minimum_spend: float
    pricing_explanation: str
    created_at: datetime

    model_config = {"from_attributes": False}
