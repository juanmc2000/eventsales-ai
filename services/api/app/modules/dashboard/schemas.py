"""Pydantic schemas for the dashboard summary API."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel


# ── Sub-schemas ────────────────────────────────────────────────────────────────


class EnquiryStatusCount(BaseModel):
    status: str
    count: int


class EnquiryRestaurantCount(BaseModel):
    restaurant_id: uuid.UUID
    restaurant_name: str
    count: int


class EnquiryPersonaCount(BaseModel):
    persona_id: uuid.UUID | None
    persona_name: str | None
    count: int


class RecentEnquiryItem(BaseModel):
    id: uuid.UUID
    reference: str
    status: str
    first_name: str
    last_name: str
    email: str
    restaurant_id: uuid.UUID
    event_date: date | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PendingFollowUpItem(BaseModel):
    id: uuid.UUID
    reference: str
    status: str
    first_name: str
    last_name: str
    email: str
    restaurant_id: uuid.UUID
    event_date: date | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DemandSpikeItem(BaseModel):
    id: uuid.UUID
    restaurant_id: uuid.UUID
    restaurant_name: str
    event_date: date
    meal_period: str
    demand_level: str
    demand_score: float | None


class PricingSummary(BaseModel):
    active_rule_count: int
    average_minimum_spend: float | None
    max_minimum_spend: float | None
    min_minimum_spend: float | None


class EnquiryTotals(BaseModel):
    total: int
    by_status: list[EnquiryStatusCount]
    by_restaurant: list[EnquiryRestaurantCount]
    by_persona: list[EnquiryPersonaCount]


# ── Top-level summary ──────────────────────────────────────────────────────────


class DashboardSummaryOut(BaseModel):
    """Full dashboard aggregation response."""

    enquiry_totals: EnquiryTotals
    recent_enquiries: list[RecentEnquiryItem]
    pending_follow_ups: list[PendingFollowUpItem]
    upcoming_demand_spikes: list[DemandSpikeItem]
    pricing_summary: PricingSummary
    # Placeholder — email events integration comes in a later sprint
    email_activity: list[dict]
