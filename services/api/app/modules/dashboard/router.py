"""Dashboard aggregation endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.dashboard.schemas import DashboardSummaryOut
from app.modules.dashboard.service import DashboardService

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def get_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


@router.get("/summary", response_model=DashboardSummaryOut)
def get_dashboard_summary(
    restaurant_id: uuid.UUID | None = Query(
        default=None,
        description="Filter aggregations to a single restaurant. Omit for all-venue view.",
    ),
    recent_limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Number of recent enquiries to return.",
    ),
    follow_up_limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of pending follow-ups to return.",
    ),
    demand_days_ahead: int = Query(
        default=30,
        ge=1,
        le=180,
        description="Look-ahead window in days for demand spikes.",
    ),
    service: DashboardService = Depends(get_service),
) -> DashboardSummaryOut:
    """
    Returns a full operational dashboard summary:
    - enquiry totals (overall, by status, by restaurant, by persona)
    - recent enquiries
    - pending follow-ups
    - upcoming high-demand events
    - pricing rule summary
    - email activity placeholder
    """
    return service.get_summary(
        restaurant_id=restaurant_id,
        recent_limit=recent_limit,
        follow_up_limit=follow_up_limit,
        demand_days_ahead=demand_days_ahead,
    )
