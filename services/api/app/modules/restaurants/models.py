import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Text, func
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
