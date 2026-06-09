import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.personas.models import RestaurantPersona
    from app.modules.pricing.models import PricingRule
    from app.modules.enquiries.models import Enquiry
    from app.modules.calendar.models import CalendarEvent
    from app.modules.insights.models import DemandEvent, InsightSnapshot


class Restaurant(Base):
    """A hospitality venue within a tenant group."""

    __tablename__ = "restaurants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Tenant identifier — single-value for POC; enables multi-tenancy in MVP.
    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="default", index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Flexible JSON bag for POC-phase venue settings.
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships (string references avoid circular imports)
    restaurant_personas: Mapped[list["RestaurantPersona"]] = relationship(
        "RestaurantPersona", back_populates="restaurant", cascade="all, delete-orphan"
    )
    pricing_rules: Mapped[list["PricingRule"]] = relationship(
        "PricingRule", back_populates="restaurant", cascade="all, delete-orphan"
    )
    enquiries: Mapped[list["Enquiry"]] = relationship(
        "Enquiry", back_populates="restaurant"
    )
    calendar_events: Mapped[list["CalendarEvent"]] = relationship(
        "CalendarEvent", back_populates="restaurant"
    )
    demand_events: Mapped[list["DemandEvent"]] = relationship(
        "DemandEvent", back_populates="restaurant"
    )
    insight_snapshots: Mapped[list["InsightSnapshot"]] = relationship(
        "InsightSnapshot", back_populates="restaurant"
    )
    rooms: Mapped[list["Room"]] = relationship(
        "Room", back_populates="restaurant", cascade="all, delete-orphan"
    )


class Room(Base):
    """A room or private dining room (PDR) within a restaurant venue."""

    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="default", index=True
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    room_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Capacity fields
    seated_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    standing_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Flexible JSON fields for POC
    layouts: Mapped[list | None] = mapped_column(JSON, nullable=True)
    amenities: Mapped[list | None] = mapped_column(JSON, nullable=True)
    asset_links: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Pricing/notes
    room_hire_fee: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    minimum_spend_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    suitability_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    booking_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Flags
    is_private_dining: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship
    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="rooms")
    availability: Mapped[list["RoomAvailability"]] = relationship(
        "RoomAvailability", back_populates="room", cascade="all, delete-orphan"
    )


class RoomAvailability(Base):
    """Per-room, per-date, per-meal-period availability status.

    POC-phase: populated from seed data.
    Future: replaced by live API call to the venue's booking system.
    """

    __tablename__ = "room_availability"
    __table_args__ = (
        UniqueConstraint("room_id", "date", "meal_period", name="uq_room_availability_slot"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="default", index=True
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # "lunch" | "dinner" | "breakfast"
    meal_period: Mapped[str] = mapped_column(String(20), nullable=False)
    # "available" | "booked" | "held" | "unavailable"
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    room: Mapped["Room"] = relationship("Room", back_populates="availability")


# ── Policy FAQ models (DATA-021) ───────────────────────────────────────────────

# Supported answer_policy values
ANSWER_POLICY_ALLOWED = "allowed"
ANSWER_POLICY_NOT_ALLOWED = "not_allowed"
ANSWER_POLICY_APPROVAL_REQUIRED = "approval_required"
ANSWER_POLICY_INFORMATION_ONLY = "information_only"
ANSWER_POLICY_UNKNOWN = "unknown"

ALL_ANSWER_POLICIES = {
    ANSWER_POLICY_ALLOWED,
    ANSWER_POLICY_NOT_ALLOWED,
    ANSWER_POLICY_APPROVAL_REQUIRED,
    ANSWER_POLICY_INFORMATION_ONLY,
    ANSWER_POLICY_UNKNOWN,
}


class RestaurantPolicyFAQ(Base):
    """Restaurant-level policy FAQ entry (DATA-021).

    Stores the restaurant's policy answer for a known question key.
    Used by PolicyQuestionResolver to answer guest policy questions deterministically.
    """

    __tablename__ = "restaurant_policy_faqs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="default", index=True
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Canonical question key — one of the 20 supported types (AI-020)
    question_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # One of the ANSWER_POLICY_* constants
    answer_policy: Mapped[str] = mapped_column(String(30), nullable=False)
    # Human-readable answer text for information_only / allowed / not_allowed policies
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # True when this question should always be escalated to a human
    requires_human_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class RoomPolicyFAQ(Base):
    """Room-level policy FAQ entry (DATA-021).

    Room-specific answers override restaurant-level answers in PolicyQuestionResolver.
    """

    __tablename__ = "room_policy_faqs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="default", index=True
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    answer_policy: Mapped[str] = mapped_column(String(30), nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_human_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    room: Mapped["Room"] = relationship("Room")
