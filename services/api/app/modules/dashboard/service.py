"""Dashboard service — assembles aggregations into summary DTOs."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.schemas import (
    DashboardSummaryOut,
    DemandSpikeItem,
    EnquiryPersonaCount,
    EnquiryRestaurantCount,
    EnquiryStatusCount,
    EnquiryTotals,
    PendingFollowUpItem,
    PricingSummary,
    RecentEnquiryItem,
)


class DashboardService:
    def __init__(self, db: Session) -> None:
        self._repo = DashboardRepository(db)

    def get_summary(
        self,
        restaurant_id: uuid.UUID | None = None,
        recent_limit: int = 10,
        follow_up_limit: int = 20,
        demand_days_ahead: int = 30,
        demand_limit: int = 20,
    ) -> DashboardSummaryOut:
        # Enquiry totals
        total = self._repo.count_enquiries_total(restaurant_id=restaurant_id)
        by_status = [
            EnquiryStatusCount(status=s, count=c)
            for s, c in self._repo.count_enquiries_by_status(restaurant_id=restaurant_id)
        ]
        by_restaurant = [
            EnquiryRestaurantCount(
                restaurant_id=rid, restaurant_name=rname, count=cnt
            )
            for rid, rname, cnt in self._repo.count_enquiries_by_restaurant()
        ]
        by_persona = [
            EnquiryPersonaCount(persona_id=pid, persona_name=pname, count=cnt)
            for pid, pname, cnt in self._repo.count_enquiries_by_persona(
                restaurant_id=restaurant_id
            )
        ]

        enquiry_totals = EnquiryTotals(
            total=total,
            by_status=by_status,
            by_restaurant=by_restaurant,
            by_persona=by_persona,
        )

        # Recent enquiries
        recent_rows = self._repo.list_recent_enquiries(
            restaurant_id=restaurant_id, limit=recent_limit
        )
        recent_enquiries = [RecentEnquiryItem.model_validate(e) for e in recent_rows]

        # Pending follow-ups
        fu_rows = self._repo.list_pending_follow_ups(
            restaurant_id=restaurant_id, limit=follow_up_limit
        )
        pending_follow_ups = [PendingFollowUpItem.model_validate(e) for e in fu_rows]

        # Upcoming demand spikes
        demand_rows = self._repo.list_upcoming_demand_spikes(
            restaurant_id=restaurant_id,
            days_ahead=demand_days_ahead,
            limit=demand_limit,
        )
        upcoming_demand_spikes = [
            DemandSpikeItem(
                id=evt.id,
                restaurant_id=evt.restaurant_id,
                restaurant_name=rname,
                event_date=evt.event_date,
                meal_period=evt.meal_period,
                demand_level=evt.demand_level,
                demand_score=evt.demand_score,
            )
            for evt, rname in demand_rows
        ]

        # Pricing summary
        pricing_data = self._repo.get_pricing_summary(restaurant_id=restaurant_id)
        pricing_summary = PricingSummary(**pricing_data)

        return DashboardSummaryOut(
            enquiry_totals=enquiry_totals,
            recent_enquiries=recent_enquiries,
            pending_follow_ups=pending_follow_ups,
            upcoming_demand_spikes=upcoming_demand_spikes,
            pricing_summary=pricing_summary,
            email_activity=[],  # email module not yet integrated
        )
