import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.restaurants.models import Restaurant


class PricingRule(Base):
    """A deterministic minimum-spend pricing rule for a restaurant.

    Rules are evaluated in order; the most specific matching rule wins.
    No ML pricing — rules are explicit and deterministic.
    """

    __tablename__ = "pricing_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # day_of_week: 0=Monday … 6=Sunday; None means rule applies every day.
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # meal_period: breakfast / lunch / dinner / all
    meal_period: Mapped[str] = mapped_column(String(20), nullable=False, default="all")
    minimum_spend: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0.00
    )
    # minimum covers for the rule to apply; None means any party size.
    minimum_covers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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
        "Restaurant", back_populates="pricing_rules"
    )
