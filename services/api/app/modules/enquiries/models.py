import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
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


# Forward references from email and calendar modules
if TYPE_CHECKING:
    from app.modules.email.models import EmailEvent
    from app.modules.calendar.models import CalendarEvent
