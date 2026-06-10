import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.restaurants.models import Restaurant
    from app.modules.personas.models import Persona
    from app.modules.pricing.models import PricingRule


class Enquiry(Base):
    """An inbound event enquiry from a prospective guest."""

    __tablename__ = "enquiries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("restaurants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    persona_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Human-readable reference, e.g. ENQ-2024-001
    reference: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    # Status lifecycle: new → open → proposal_sent → follow_up → confirmed / cancelled / lost
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="new", index=True
    )
    # How the enquiry arrived
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="webform")
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    party_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    # e.g. birthday / corporate / wedding / private_dining / other
    event_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Flexible JSON for POC-phase extra fields
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    @property
    def recommended_minimum_spend(self) -> float | None:
        """Expose recommended_minimum_spend stored in metadata_ as a first-class attribute.

        Used by EnquiryOut (from_attributes=True) so Pydantic can read this field
        directly from the ORM object without a custom validator.
        """
        if self.metadata_ and isinstance(self.metadata_, dict):
            raw = self.metadata_.get("recommended_minimum_spend")
            if raw is not None:
                try:
                    return float(raw)
                except (TypeError, ValueError):
                    pass
        return None

    # Relationships
    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="enquiries")
    persona: Mapped["Persona | None"] = relationship("Persona")
    messages: Mapped[list["EnquiryMessage"]] = relationship(
        "EnquiryMessage", back_populates="enquiry", cascade="all, delete-orphan"
    )
    email_events: Mapped[list["EmailEvent"]] = relationship(
        "EmailEvent", back_populates="enquiry"
    )
    calendar_events: Mapped[list["CalendarEvent"]] = relationship(
        "CalendarEvent", back_populates="enquiry"
    )
    extractions: Mapped[list["EnquiryExtraction"]] = relationship(
        "EnquiryExtraction", back_populates="enquiry", cascade="all, delete-orphan"
    )
    processing_snapshots: Mapped[list["EnquiryProcessingSnapshot"]] = relationship(
        "EnquiryProcessingSnapshot", back_populates="enquiry", cascade="all, delete-orphan"
    )
    date_requests: Mapped[list["EnquiryDateRequest"]] = relationship(
        "EnquiryDateRequest", back_populates="enquiry", cascade="all, delete-orphan"
    )
    candidate_dates: Mapped[list["EnquiryCandidateDate"]] = relationship(
        "EnquiryCandidateDate", back_populates="enquiry", cascade="all, delete-orphan"
    )
    response_plans: Mapped[list["EnquiryResponsePlan"]] = relationship(
        "EnquiryResponsePlan", back_populates="enquiry", cascade="all, delete-orphan"
    )


class EnquiryMessage(Base):
    """A single message in an enquiry conversation thread."""

    __tablename__ = "enquiry_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    enquiry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # inbound (from guest) or outbound (from system/staff)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    # email / webform / manual
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # AUTO-004: persisted review state for draft messages.
    # Stores: review_state, validation_status, validation_blockers,
    # auto_send_allowed, auto_send_blockers, generation_path.
    # Null for non-draft or pre-AUTO-004 messages.
    review_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    enquiry: Mapped["Enquiry"] = relationship("Enquiry", back_populates="messages")


class EnquiryExtraction(Base):
    """Structured facts extracted from a freeform enquiry message via LLM (Call 1).

    Rows are immutable after insert.  Re-extraction creates a new row.
    """

    __tablename__ = "enquiry_extractions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Tenant-ready: nullable in POC, required in multi-tenant production
    tenant_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    enquiry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Nullable: extraction may come from the initial webform message or a later inbound email
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiry_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Link to the AI Gateway prompt run that produced this extraction
    prompt_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_prompt_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Raw structured output from the LLM (matches EnquiryExtractionOutput schema)
    extracted_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Post-processed / normalized version (dates parsed, guest_count coerced to int, etc.)
    normalized_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Fields the model could not extract from the text
    missing_fields: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Per-field confidence values reported by the model
    confidence_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    # Relationships
    enquiry: Mapped["Enquiry"] = relationship("Enquiry", back_populates="extractions")
    source_message: Mapped["EnquiryMessage | None"] = relationship("EnquiryMessage")
    processing_snapshots: Mapped[list["EnquiryProcessingSnapshot"]] = relationship(
        "EnquiryProcessingSnapshot",
        back_populates="extraction",
        cascade="all, delete-orphan",
    )


class EnquiryProcessingSnapshot(Base):
    """Deterministic processing result linking an extraction to pricing, availability, and room data.

    Produced entirely in Python — no LLM involvement.  Rows are immutable after insert.
    Re-processing creates a new row.
    """

    __tablename__ = "enquiry_processing_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    enquiry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiry_extractions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Nullable: pricing rule may not apply if required data is missing
    pricing_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pricing_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Room availability status from room_availability table lookup
    availability_result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Room suitability assessment (room_id, room_name, capacity, matched_reason)
    room_suitability_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Pricing calculation result (minimum_spend, rule_name, explanation)
    pricing_result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Merged list of missing fields after business-logic gap detection
    missing_fields_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # One of: "send_draft" | "request_more_info" | "flag_for_review"
    recommended_action: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    # Relationships
    enquiry: Mapped["Enquiry"] = relationship(
        "Enquiry", back_populates="processing_snapshots"
    )
    extraction: Mapped["EnquiryExtraction"] = relationship(
        "EnquiryExtraction", back_populates="processing_snapshots"
    )


class EnquiryDateRequest(Base):
    """Extracted date intent from a guest enquiry (DATA-019).

    Stores what the guest said about dates as structured intent — not expanded
    candidate dates.  The date resolution service (WORKFLOW-008) reads this row
    and deterministically generates EnquiryCandidateDate rows from it.

    Rows are immutable after insert.  Re-extraction creates a new row.
    """

    __tablename__ = "enquiry_date_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    enquiry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Nullable: may be created during extraction or as a standalone step
    extraction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiry_extractions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prompt_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_prompt_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Raw date phrase as stated by the guest
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Classified date intent type (see DateRequestType in validators.py) — raw LLM value
    date_request_type: Mapped[str] = mapped_column(
        String(60), nullable=False, default="unknown", index=True
    )
    # ENQ-002: simplified 5-category normalised type (exact/range/recurring/ambiguous/unknown)
    date_request_type_normalized: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True
    )
    # Reference date used during deterministic expansion (defaults to today when absent)
    anchor_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Full date_request JSON from the LLM output
    extracted_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Whether the date is ambiguous and requires clarification from the guest
    requires_date_clarification: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    clarification_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    # LLM confidence for the date extraction (0.0–1.0)
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    # HOTFIX-001: numeric date disambiguation fields (null for non-numeric dates)
    # One of: resolved | resolved_with_confirmation | unresolved_ambiguity
    ambiguity_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # The date the system will use for availability checks (DD/MM default or Rule-5 override)
    assumed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # The alternative interpretation (null for unambiguous dates)
    alternative_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # True when the guest must confirm which interpretation was intended
    clarification_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Machine-readable reason code for why clarification is needed
    clarification_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    # Relationships
    enquiry: Mapped["Enquiry"] = relationship("Enquiry", back_populates="date_requests")
    extraction: Mapped["EnquiryExtraction | None"] = relationship("EnquiryExtraction")
    candidate_dates: Mapped[list["EnquiryCandidateDate"]] = relationship(
        "EnquiryCandidateDate",
        back_populates="date_request",
        cascade="all, delete-orphan",
    )


class EnquiryCandidateDate(Base):
    """A single deterministically generated candidate date for an enquiry (DATA-019).

    Candidate dates are always produced by backend Python logic, never trusted
    directly from LLM output.  Rows are updated in place by WORKFLOW-009
    after availability and pricing checks.
    """

    __tablename__ = "enquiry_candidate_dates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    enquiry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiry_date_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The resolved calendar date for this candidate
    candidate_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # How the candidate was produced: "explicit" (provided by LLM) or "deterministic" (backend)
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="deterministic"
    )
    # Populated by WORKFLOW-009 after availability check
    availability_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # available | booked | held | unavailable | unknown
    # Set to True after WORKFLOW-009 runs pricing check for this date
    pricing_checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Populated by WORKFLOW-009 after pricing check
    recommended_minimum_spend: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    # Optional ranking score — null in POC; populated by future ranking logic
    ranking_score: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    enquiry: Mapped["Enquiry"] = relationship("Enquiry", back_populates="candidate_dates")
    date_request: Mapped["EnquiryDateRequest"] = relationship(
        "EnquiryDateRequest", back_populates="candidate_dates"
    )


class EnquiryResponsePlan(Base):
    """Assembled response plan produced by ResponsePreparationBuilder (ORCH-006).

    One row per response-preparation run.  Rows are immutable after insert.
    Re-running preparation creates a new row; ORCH-007 reads the latest via
    ``GET /enquiries/{id}/response-preparation/latest``.
    """

    __tablename__ = "enquiry_response_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    enquiry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Nullable: snapshot may not exist when plan is built during freeform intake
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiry_processing_snapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # ── Goal + priority ───────────────────────────────────────────────────────
    response_goal: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    response_priority: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    can_generate_draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    goal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocking_fields: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # ── Context sections ──────────────────────────────────────────────────────
    known_facts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    missing_information: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    clarification_questions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    date_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    availability_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    customer_type_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    persona_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    draft_instructions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    # Relationships
    enquiry: Mapped["Enquiry"] = relationship("Enquiry", back_populates="response_plans")


# Forward references from email and calendar modules
if TYPE_CHECKING:
    from app.modules.email.models import EmailEvent
    from app.modules.calendar.models import CalendarEvent
