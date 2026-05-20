import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.calendar.schemas import (
    CalendarRangeOut,
    DemandEventCreate,
    DemandEventListOut,
    DemandEventOut,
    DemandEventUpdate,
)
from app.modules.calendar.service import CalendarService

router = APIRouter(prefix="/api/v1/demand-events", tags=["demand-events"])
calendar_router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])


def get_service(db: Session = Depends(get_db)) -> CalendarService:
    return CalendarService(db)


# ── Demand Events CRUD ────────────────────────────────────────────────────────


@router.get("", response_model=DemandEventListOut)
def list_demand_events(
    restaurant_id: uuid.UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    meal_period: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=2000),
    service: CalendarService = Depends(get_service),
) -> DemandEventListOut:
    items, total = service.list_demand_events(
        restaurant_id=restaurant_id,
        date_from=date_from,
        date_to=date_to,
        meal_period=meal_period,
        skip=skip,
        limit=limit,
    )
    return DemandEventListOut(items=items, total=total)


@router.get("/{event_id}", response_model=DemandEventOut)
def get_demand_event(
    event_id: uuid.UUID,
    service: CalendarService = Depends(get_service),
) -> DemandEventOut:
    event = service.get_demand_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Demand event not found")
    return event


@router.post("", response_model=DemandEventOut, status_code=201)
def create_demand_event(
    data: DemandEventCreate,
    service: CalendarService = Depends(get_service),
) -> DemandEventOut:
    return service.create_demand_event(data)


@router.patch("/{event_id}", response_model=DemandEventOut)
def update_demand_event(
    event_id: uuid.UUID,
    data: DemandEventUpdate,
    service: CalendarService = Depends(get_service),
) -> DemandEventOut:
    event = service.update_demand_event(event_id, data)
    if not event:
        raise HTTPException(status_code=404, detail="Demand event not found")
    return event


@router.delete("/{event_id}", status_code=204)
def delete_demand_event(
    event_id: uuid.UUID,
    service: CalendarService = Depends(get_service),
) -> None:
    deleted = service.delete_demand_event(event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Demand event not found")


# ── Calendar range summary ────────────────────────────────────────────────────


@calendar_router.get("/range", response_model=CalendarRangeOut)
def get_calendar_range(
    restaurant_id: uuid.UUID = Query(...),
    date_from: date = Query(...),
    date_to: date = Query(...),
    service: CalendarService = Depends(get_service),
) -> CalendarRangeOut:
    if date_to < date_from:
        raise HTTPException(status_code=400, detail="date_to must be >= date_from")
    return service.get_calendar_range(restaurant_id, date_from, date_to)
