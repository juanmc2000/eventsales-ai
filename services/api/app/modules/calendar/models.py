import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.restaurants.models import Restaurant
    from app.modules.enquiries.models import Enquiry


class CalendarEvent(Base):
    """A confirmed or tentative event booking on the venue calendar."""

    __tablename__ = "calendar_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("restaurants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    enquiry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enquiries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # breakfast / lunch / dinner
    meal_period: Mapped[str] = mapped_column(String(20), nullable=False)
    party_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # tentative / confirmed / cancelled
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="tentative")
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

    # Relationships
    restaurant: Mapped["Restaurant"] = relationship(
        "Restaurant", back_populates="calendar_events"
    )
    enquiry: Mapped["Enquiry | None"] = relationship(
        "Enquiry", back_populates="calendar_events"
    )
