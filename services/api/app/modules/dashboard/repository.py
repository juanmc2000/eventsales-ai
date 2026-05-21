"""Dashboard aggregation repository.

All queries are read-only aggregations against seeded data.
No ML, no external integrations.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.enquiries.models import Enquiry
from app.modules.insights.models import DemandEvent
from app.modules.pricing.models import PricingRule
from app.modules.restaurants.models import Restaurant


class DashboardRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Enquiry aggregations ────────────────────────────────────────────────

    def count_enquiries_total(
        self, restaurant_id: uuid.UUID | None = None
    ) -> int:
        stmt = select(func.count()).select_from(Enquiry)
        if restaurant_id:
            stmt = stmt.where(Enquiry.restaurant_id == restaurant_id)
        return self._db.scalar(stmt) or 0

    def count_enquiries_by_status(
        self, restaurant_id: uuid.UUID | None = None
    ) -> list[tuple[str, int]]:
        stmt = (
            select(Enquiry.status, func.count().label("cnt"))
            .group_by(Enquiry.status)
            .order_by(func.count().desc())
        )
        if restaurant_id:
            stmt = stmt.where(Enquiry.restaurant_id == restaurant_id)
        rows = self._db.execute(stmt).all()
        return [(row.status, row.cnt) for row in rows]

    def count_enquiries_by_restaurant(
        self,
    ) -> list[tuple[uuid.UUID, str, int]]:
        stmt = (
            select(
                Enquiry.restaurant_id,
                Restaurant.name.label("restaurant_name"),
                func.count().label("cnt"),
            )
            .join(Restaurant, Restaurant.id == Enquiry.restaurant_id)
            .group_by(Enquiry.restaurant_id, Restaurant.name)
            .order_by(func.count().desc())
        )
        rows = self._db.execute(stmt).all()
        return [(row.restaurant_id, row.restaurant_name, row.cnt) for row in rows]

    def count_enquiries_by_persona(
        self, restaurant_id: uuid.UUID | None = None
    ) -> list[tuple[uuid.UUID | None, str | None, int]]:
        from app.modules.personas.models import Persona

        stmt = (
            select(
                Enquiry.persona_id,
                Persona.name.label("persona_name"),
                func.count().label("cnt"),
            )
            .outerjoin(Persona, Persona.id == Enquiry.persona_id)
            .group_by(Enquiry.persona_id, Persona.name)
            .order_by(func.count().desc())
        )
        if restaurant_id:
            stmt = stmt.where(Enquiry.restaurant_id == restaurant_id)
        rows = self._db.execute(stmt).all()
        return [(row.persona_id, row.persona_name, row.cnt) for row in rows]

    def list_recent_enquiries(
        self,
        restaurant_id: uuid.UUID | None = None,
        limit: int = 10,
    ) -> list[Enquiry]:
        stmt = select(Enquiry).order_by(Enquiry.created_at.desc()).limit(limit)
        if restaurant_id:
            stmt = stmt.where(Enquiry.restaurant_id == restaurant_id)
        return list(self._db.scalars(stmt).all())

    def list_pending_follow_ups(
        self,
        restaurant_id: uuid.UUID | None = None,
        limit: int = 20,
    ) -> list[Enquiry]:
        """Enquiries that need attention — open or in follow_up status."""
        FOLLOW_UP_STATUSES = ("new", "open", "follow_up")
        stmt = (
            select(Enquiry)
            .where(Enquiry.status.in_(FOLLOW_UP_STATUSES))
            .order_by(Enquiry.created_at.asc())
            .limit(limit)
        )
        if restaurant_id:
            stmt = stmt.where(Enquiry.restaurant_id == restaurant_id)
        return list(self._db.scalars(stmt).all())

    # ── Demand spike aggregations ───────────────────────────────────────────

    def list_upcoming_demand_spikes(
        self,
        restaurant_id: uuid.UUID | None = None,
        days_ahead: int = 30,
        limit: int = 20,
    ) -> list[tuple[DemandEvent, str]]:
        """High and very_high demand events in the next N days."""
        today = date.today()
        cutoff = today + timedelta(days=days_ahead)
        HIGH_LEVELS = ("high", "very_high")
        stmt = (
            select(DemandEvent, Restaurant.name.label("restaurant_name"))
            .join(Restaurant, Restaurant.id == DemandEvent.restaurant_id)
            .where(DemandEvent.demand_level.in_(HIGH_LEVELS))
            .where(DemandEvent.event_date >= today)
            .where(DemandEvent.event_date <= cutoff)
            .order_by(DemandEvent.event_date)
            .limit(limit)
        )
        if restaurant_id:
            stmt = stmt.where(DemandEvent.restaurant_id == restaurant_id)
        rows = self._db.execute(stmt).all()
        return [(row.DemandEvent, row.restaurant_name) for row in rows]

    # ── Pricing summary ─────────────────────────────────────────────────────

    def get_pricing_summary(
        self, restaurant_id: uuid.UUID | None = None
    ) -> dict:
        stmt = select(
            func.count().label("active_count"),
            func.avg(PricingRule.minimum_spend).label("avg_spend"),
            func.max(PricingRule.minimum_spend).label("max_spend"),
            func.min(PricingRule.minimum_spend).label("min_spend"),
        ).where(PricingRule.is_active.is_(True))
        if restaurant_id:
            stmt = stmt.where(PricingRule.restaurant_id == restaurant_id)
        row = self._db.execute(stmt).one()
        return {
            "active_rule_count": row.active_count or 0,
            "average_minimum_spend": (
                float(row.avg_spend) if row.avg_spend is not None else None
            ),
            "max_minimum_spend": (
                float(row.max_spend) if row.max_spend is not None else None
            ),
            "min_minimum_spend": (
                float(row.min_spend) if row.min_spend is not None else None
            ),
        }
