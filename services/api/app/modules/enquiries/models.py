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


# Forward references from email and calendar modules
if TYPE_CHECKING:
    from app.modules.email.models import EmailEvent
    from app.modules.calendar.models import CalendarEvent
