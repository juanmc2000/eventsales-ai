import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.insights.models import DemandEvent


class DemandEventRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list(
        self,
        restaurant_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        meal_period: str | None = None,
        skip: int = 0,
        limit: int = 500,
    ) -> list[DemandEvent]:
        stmt = select(DemandEvent)
        if restaurant_id:
            stmt = stmt.where(DemandEvent.restaurant_id == restaurant_id)
        if date_from:
            stmt = stmt.where(DemandEvent.event_date >= date_from)
        if date_to:
            stmt = stmt.where(DemandEvent.event_date <= date_to)
        if meal_period:
            stmt = stmt.where(DemandEvent.meal_period == meal_period)
        stmt = stmt.order_by(DemandEvent.event_date, DemandEvent.meal_period)
        stmt = stmt.offset(skip).limit(limit)
        return list(self._db.scalars(stmt).all())

    def count(
        self,
        restaurant_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        return len(self.list(restaurant_id=restaurant_id, date_from=date_from, date_to=date_to, skip=0, limit=100000))

    def get_by_id(self, event_id: uuid.UUID) -> DemandEvent | None:
        return self._db.get(DemandEvent, event_id)

    def create(self, data: dict[str, Any]) -> DemandEvent:
        record = DemandEvent(id=uuid.uuid4(), **data)
        self._db.add(record)
        self._db.flush()
        return record

    def update(self, event: DemandEvent, data: dict[str, Any]) -> DemandEvent:
        for key, value in data.items():
            setattr(event, key, value)
        self._db.flush()
        return event

    def delete(self, event: DemandEvent) -> None:
        self._db.delete(event)
        self._db.flush()
