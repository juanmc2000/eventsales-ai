import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


# ── Demand Events ─────────────────────────────────────────────────────────────


class DemandEventBase(BaseModel):
    restaurant_id: uuid.UUID
    event_date: date
    # breakfast / lunch / dinner / all
    meal_period: str = Field(default="all", max_length=20)
    # low / medium / high / very_high
    demand_level: str = Field(..., max_length=20)
    demand_score: float | None = Field(default=None, ge=0.0, le=1.0)
    # seeded / manual
    source: str = Field(default="manual", max_length=20)
    notes: str | None = None


class DemandEventCreate(DemandEventBase):
    pass


class DemandEventUpdate(BaseModel):
    demand_level: str | None = Field(default=None, max_length=20)
    demand_score: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: str | None = None


class DemandEventOut(DemandEventBase):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class DemandEventListOut(BaseModel):
    items: list[DemandEventOut]
    total: int


# ── Date-level demand summary ─────────────────────────────────────────────────


class DayDemandSummary(BaseModel):
    event_date: date
    # Highest demand level across all meal periods for this date
    peak_demand_level: str
    # Average demand score across meal periods (0–1)
    avg_demand_score: float | None
    # Demand by meal period
    breakfast_level: str | None
    lunch_level: str | None
    dinner_level: str | None


class CalendarRangeOut(BaseModel):
    restaurant_id: uuid.UUID
    date_from: date
    date_to: date
    days: list[DayDemandSummary]
