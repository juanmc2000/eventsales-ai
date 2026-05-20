"""Smoke tests for calendar/demand event schemas (no DB required)."""

import uuid
from datetime import date

import pytest


def test_demand_event_create_schema_valid() -> None:
    from app.modules.calendar.schemas import DemandEventCreate

    event = DemandEventCreate(
        restaurant_id=uuid.uuid4(),
        event_date=date(2026, 12, 25),
        meal_period="dinner",
        demand_level="very_high",
        demand_score=0.95,
    )
    assert event.demand_level == "very_high"
    assert event.demand_score == 0.95


def test_demand_score_out_of_range_rejected() -> None:
    from pydantic import ValidationError

    from app.modules.calendar.schemas import DemandEventCreate

    with pytest.raises(ValidationError):
        DemandEventCreate(
            restaurant_id=uuid.uuid4(),
            event_date=date(2026, 1, 1),
            demand_level="high",
            demand_score=1.5,  # invalid — must be 0–1
        )


def test_day_demand_summary_schema() -> None:
    from app.modules.calendar.schemas import DayDemandSummary

    summary = DayDemandSummary(
        event_date=date(2026, 6, 15),
        peak_demand_level="high",
        avg_demand_score=0.72,
        breakfast_level="medium",
        lunch_level="high",
        dinner_level="high",
    )
    assert summary.peak_demand_level == "high"


def test_calendar_range_out_schema() -> None:
    from app.modules.calendar.schemas import CalendarRangeOut

    result = CalendarRangeOut(
        restaurant_id=uuid.uuid4(),
        date_from=date(2026, 6, 1),
        date_to=date(2026, 6, 30),
        days=[],
    )
    assert result.days == []
