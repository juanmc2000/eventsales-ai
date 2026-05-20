import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from app.modules.calendar.repository import DemandEventRepository
from app.modules.calendar.schemas import (
    CalendarRangeOut,
    DayDemandSummary,
    DemandEventCreate,
    DemandEventUpdate,
)
from app.modules.insights.models import DemandEvent

DEMAND_ORDER = {"low": 0, "medium": 1, "high": 2, "very_high": 3}


class CalendarService:
    def __init__(self, db: Session) -> None:
        self._repo = DemandEventRepository(db)

    def list_demand_events(
        self,
        restaurant_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        meal_period: str | None = None,
        skip: int = 0,
        limit: int = 500,
    ) -> tuple[list[DemandEvent], int]:
        items = self._repo.list(
            restaurant_id=restaurant_id,
            date_from=date_from,
            date_to=date_to,
            meal_period=meal_period,
            skip=skip,
            limit=limit,
        )
        total = self._repo.count(
            restaurant_id=restaurant_id, date_from=date_from, date_to=date_to
        )
        return items, total

    def get_demand_event(self, event_id: uuid.UUID) -> DemandEvent | None:
        return self._repo.get_by_id(event_id)

    def create_demand_event(self, data: DemandEventCreate) -> DemandEvent:
        return self._repo.create(data.model_dump())

    def update_demand_event(self, event_id: uuid.UUID, data: DemandEventUpdate) -> DemandEvent | None:
        event = self._repo.get_by_id(event_id)
        if not event:
            return None
        updates = data.model_dump(exclude_none=True)
        if not updates:
            return event
        return self._repo.update(event, updates)

    def delete_demand_event(self, event_id: uuid.UUID) -> bool:
        event = self._repo.get_by_id(event_id)
        if not event:
            return False
        self._repo.delete(event)
        return True

    def get_calendar_range(
        self, restaurant_id: uuid.UUID, date_from: date, date_to: date
    ) -> CalendarRangeOut:
        """Return date-level demand summaries for a restaurant over a date range."""
        events = self._repo.list(
            restaurant_id=restaurant_id,
            date_from=date_from,
            date_to=date_to,
            skip=0,
            limit=100000,
        )

        # Group by date → meal_period → demand_level
        by_date: dict[date, dict[str, str]] = defaultdict(dict)
        scores_by_date: dict[date, list[float]] = defaultdict(list)

        for event in events:
            by_date[event.event_date][event.meal_period] = event.demand_level
            if event.demand_score is not None:
                scores_by_date[event.event_date].append(event.demand_score)

        days: list[DayDemandSummary] = []
        for d, periods in sorted(by_date.items()):
            all_levels = list(periods.values())
            peak = max(all_levels, key=lambda lvl: DEMAND_ORDER.get(lvl, 0))
            scores = scores_by_date.get(d, [])
            avg_score = round(sum(scores) / len(scores), 3) if scores else None

            days.append(
                DayDemandSummary(
                    event_date=d,
                    peak_demand_level=peak,
                    avg_demand_score=avg_score,
                    breakfast_level=periods.get("breakfast"),
                    lunch_level=periods.get("lunch"),
                    dinner_level=periods.get("dinner"),
                )
            )

        return CalendarRangeOut(
            restaurant_id=restaurant_id,
            date_from=date_from,
            date_to=date_to,
            days=days,
        )
