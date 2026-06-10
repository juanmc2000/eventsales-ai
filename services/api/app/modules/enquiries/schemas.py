import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field

from app.modules.ai.schemas import AIContextOut  # noqa: TC001 — used in DraftResponseOut


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


# ── Webform intake ─────────────────────────────────────────────────────────────


class WebformIntakeRequest(BaseModel):
    """Input schema for the enquiry webform intake endpoint."""

    restaurant_id: uuid.UUID
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    party_size: int | None = Field(default=None, ge=1)
    event_date: date | None = None
    event_type: str | None = Field(default=None, max_length=50)
    meal_period: str = Field(default="dinner", max_length=20)
    message: str | None = None
    company_name: str | None = Field(default=None, max_length=255)
    budget_indication: str | None = None
    preferred_area: str | None = Field(default=None, max_length=255)
    dietary_requirements: str | None = None
    special_requests: str | None = None
    # Audience segment for persona resolution: "social" | "corporate" | "agency" | None
    audience_type: str | None = Field(default=None, max_length=20)


class EnquiryIntakeOut(BaseModel):
    """Response schema for the enquiry intake endpoint."""

    enquiry_id: uuid.UUID
    reference: str
    status: str
    restaurant_id: uuid.UUID
    persona_id: uuid.UUID | None = None
    persona_name: str | None = None
    audience_type: str | None = None
    recommended_minimum_spend: float
    pricing_explanation: str
    created_at: datetime

    model_config = {"from_attributes": False}


# ── Freeform intake ────────────────────────────────────────────────────────────


class FreeformIntakeRequest(BaseModel):
    """Input schema for freeform webform submission (natural language)."""

    restaurant_id: uuid.UUID
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    freeform_text: str = Field(..., min_length=10, max_length=5000)
    audience_type: str | None = Field(default=None, max_length=20)


class ExtractionSummaryOut(BaseModel):
    """Summary of the extraction step included in FreeformIntakeOut."""

    extraction_id: uuid.UUID | None = None
    prompt_run_id: uuid.UUID | None = None
    is_fallback: bool
    validation_status: str | None = None
    guest_count: int | None = None
    event_date: str | None = None
    event_type: str | None = None
    # ENQ-001: occasion fields — raw LLM value preserved alongside canonical
    occasion_raw: str | None = None
    occasion_canonical: str | None = None
    missing_fields: list[str] | None = None
    # AI transparency: prompts and raw model response for the extraction LLM call
    extraction_system_prompt: str | None = None
    extraction_user_prompt: str | None = None
    extraction_raw_response: str | None = None


class FreeformIntakeOut(BaseModel):
    """Response schema for POST /enquiries/intake/freeform.

    Includes extraction summary and recommended action from deterministic
    processing, plus the generated draft body.
    """

    enquiry_id: uuid.UUID
    reference: str
    status: str
    restaurant_id: uuid.UUID
    persona_id: uuid.UUID | None = None
    persona_name: str | None = None
    audience_type: str | None = None
    created_at: datetime
    # Sprint 7 enrichments
    extraction: ExtractionSummaryOut | None = None
    recommended_action: str | None = None
    draft_subject: str | None = None
    draft_body: str | None = None
    draft_message_id: uuid.UUID | None = None
    draft_is_fallback: bool | None = None
    # AI transparency: context from the draft LLM call (model, persona, prompts)
    draft_ai_context: AIContextOut | None = None
    # ORCH-008: summary of the deterministic response preparation plan
    response_preparation_summary: dict | None = None

    model_config = {"from_attributes": False}


# ── Draft response ─────────────────────────────────────────────────────────────


class DraftResponseOut(BaseModel):
    """API response for a generated or retrieved draft enquiry response."""

    enquiry_id: uuid.UUID
    message_id: uuid.UUID
    subject: str | None = None
    body: str
    persona_name: str | None = None
    recommended_minimum_spend: float | None = None
    pricing_explanation: str | None = None
    is_fallback: bool | None = None
    model: str | None = None
    generated_at: datetime
    ai_context: AIContextOut | None = None


# ── Readiness evaluation schema (ENQ-004) ──────────────────────────────────────


class ReadinessEvaluationOut(BaseModel):
    """API response for enquiry readiness evaluation."""

    status: str
    date_understood: bool
    guest_count_present: bool
    occasion_understood: bool
    meal_period_present: bool
    audience_identified: bool
    date_clarification_required: bool
    availability_check_possible: bool
    missing_for_availability: list[str]
    notes: str


# ── Extraction quality diagnostics (ENQ-005) ──────────────────────────────────


class EnquiryDiagnosticsOut(BaseModel):
    """API response for per-enquiry extraction quality diagnostics."""

    enquiry_id: uuid.UUID
    extraction_id: uuid.UUID | None = None
    prompt_run_id: uuid.UUID | None = None

    # Missing critical fields
    missing_critical_fields: list[str]
    has_missing_critical_fields: bool

    # Occasion normalisation
    occasion_raw: str | None = None
    occasion_canonical: str | None = None
    occasion_normalised: bool

    # Date context warnings
    date_context_warnings: list[str]
    date_ambiguity_detected: bool

    # Date clarification
    date_clarification_required: bool
    clarification_question: str | None = None

    # Readiness outcome
    readiness_status: str
    readiness_missing_for_availability: list[str]
    readiness_notes: str

    # Extraction metadata
    validation_status: str | None = None
    is_fallback: bool
    created_at: datetime | None = None


# ── Policy question extraction schema (AI-020) ────────────────────────────────


class PolicyQuestionExtracted(BaseModel):
    """A single policy question extracted from guest message (AI-020).

    LLM1 extracts the question reference only — it does not answer it.
    The PolicyQuestionResolver (RESP-045) handles answer lookup.
    """

    # One of the 20 supported question keys, or "unknown"
    question_key: str
    # The verbatim question fragment from the guest message
    raw_question: str
    # "restaurant" | "room" | "unknown" — helps resolver pick the right FAQ scope
    scope_hint: str = "unknown"
    # LLM confidence 0.0–1.0 for the question_key mapping
    confidence: float = 0.0


# ── Date request and candidate date schemas ────────────────────────────────────


class EnquiryDateRequestOut(BaseModel):
    """API response for a stored enquiry_date_requests row."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    enquiry_id: uuid.UUID
    extraction_id: uuid.UUID | None = None
    prompt_run_id: uuid.UUID | None = None
    raw_text: str | None = None
    date_request_type: str
    # ENQ-002: simplified normalized type alongside the raw LLM classification
    date_request_type_normalized: str | None = None
    anchor_date: date | None = None
    timezone: str | None = None
    extracted_json: dict | None = None
    requires_date_clarification: bool
    clarification_question: str | None = None
    confidence: float | None = None
    created_at: datetime


class EnquiryCandidateDateOut(BaseModel):
    """API response for a stored enquiry_candidate_dates row."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    enquiry_id: uuid.UUID
    date_request_id: uuid.UUID
    candidate_date: date
    source_type: str
    availability_status: str | None = None
    pricing_checked: bool
    recommended_minimum_spend: float | None = None
    ranking_score: float | None = None
    created_at: datetime


# ── Extraction and processing schemas ──────────────────────────────────────────


class EnquiryExtractionOut(BaseModel):
    """API response for a stored enquiry extraction row."""

    id: uuid.UUID
    enquiry_id: uuid.UUID
    source_message_id: uuid.UUID | None = None
    prompt_run_id: uuid.UUID | None = None
    extracted_json: dict | None = None
    normalized_json: dict | None = None
    missing_fields: list[str] | None = None
    confidence_json: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResponsePlanOut(BaseModel):
    """API response for the latest stored response preparation plan (ORCH-007)."""

    id: uuid.UUID
    enquiry_id: uuid.UUID
    snapshot_id: uuid.UUID | None = None
    response_goal: str
    response_priority: str
    can_generate_draft: bool
    goal_reason: str | None = None
    blocking_fields: list[str] | None = None
    known_facts: dict | None = None
    missing_information: dict | None = None
    clarification_questions: list[str] | None = None
    date_context: dict | None = None
    availability_context: dict | None = None
    customer_type_context: dict | None = None
    persona_context: dict | None = None
    draft_instructions: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EnquiryProcessingSnapshotOut(BaseModel):
    """API response for a stored enquiry processing snapshot row."""

    id: uuid.UUID
    enquiry_id: uuid.UUID
    extraction_id: uuid.UUID
    pricing_rule_id: uuid.UUID | None = None
    availability_result_json: dict | None = None
    room_suitability_json: dict | None = None
    pricing_result_json: dict | None = None
    missing_fields_json: list[str] | None = None
    recommended_action: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
