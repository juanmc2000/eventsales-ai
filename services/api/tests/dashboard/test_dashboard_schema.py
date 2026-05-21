"""Smoke tests for dashboard schemas and service logic (no DB required)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone


def test_dashboard_summary_schema_imports() -> None:
    """Dashboard schemas import without error."""
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
    assert DashboardSummaryOut is not None


def test_enquiry_status_count_schema() -> None:
    from app.modules.dashboard.schemas import EnquiryStatusCount

    obj = EnquiryStatusCount(status="new", count=5)
    assert obj.status == "new"
    assert obj.count == 5


def test_enquiry_totals_schema() -> None:
    from app.modules.dashboard.schemas import EnquiryTotals

    totals = EnquiryTotals(
        total=42,
        by_status=[],
        by_restaurant=[],
        by_persona=[],
    )
    assert totals.total == 42
    assert totals.by_status == []


def test_pricing_summary_schema() -> None:
    from app.modules.dashboard.schemas import PricingSummary

    summary = PricingSummary(
        active_rule_count=5,
        average_minimum_spend=250.0,
        max_minimum_spend=500.0,
        min_minimum_spend=100.0,
    )
    assert summary.active_rule_count == 5
    assert summary.average_minimum_spend == 250.0


def test_pricing_summary_schema_nullable_spend() -> None:
    from app.modules.dashboard.schemas import PricingSummary

    summary = PricingSummary(
        active_rule_count=0,
        average_minimum_spend=None,
        max_minimum_spend=None,
        min_minimum_spend=None,
    )
    assert summary.active_rule_count == 0
    assert summary.average_minimum_spend is None


def test_recent_enquiry_item_schema() -> None:
    from app.modules.dashboard.schemas import RecentEnquiryItem

    now = datetime.now(tz=timezone.utc)
    rid = uuid.uuid4()
    eid = uuid.uuid4()

    item = RecentEnquiryItem(
        id=eid,
        reference="ENQ-2026-0001",
        status="new",
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        restaurant_id=rid,
        event_date=date(2026, 8, 15),
        created_at=now,
    )
    assert item.reference == "ENQ-2026-0001"
    assert item.event_date == date(2026, 8, 15)


def test_demand_spike_item_schema() -> None:
    from app.modules.dashboard.schemas import DemandSpikeItem

    item = DemandSpikeItem(
        id=uuid.uuid4(),
        restaurant_id=uuid.uuid4(),
        restaurant_name="The Grand",
        event_date=date(2026, 6, 1),
        meal_period="dinner",
        demand_level="very_high",
        demand_score=0.92,
    )
    assert item.demand_level == "very_high"
    assert item.demand_score == 0.92


def test_dashboard_summary_schema_full() -> None:
    from app.modules.dashboard.schemas import (
        DashboardSummaryOut,
        EnquiryTotals,
        PricingSummary,
    )

    summary = DashboardSummaryOut(
        enquiry_totals=EnquiryTotals(
            total=0,
            by_status=[],
            by_restaurant=[],
            by_persona=[],
        ),
        recent_enquiries=[],
        pending_follow_ups=[],
        upcoming_demand_spikes=[],
        pricing_summary=PricingSummary(
            active_rule_count=0,
            average_minimum_spend=None,
            max_minimum_spend=None,
            min_minimum_spend=None,
        ),
        email_activity=[],
    )
    assert summary.enquiry_totals.total == 0
    assert summary.email_activity == []


def test_dashboard_service_imports() -> None:
    """DashboardService can be imported without error."""
    from app.modules.dashboard.service import DashboardService

    assert DashboardService is not None


def test_dashboard_router_imports() -> None:
    """Dashboard router registers without error."""
    from app.modules.dashboard.router import router

    route_paths = [r.path for r in router.routes]
    assert "/api/v1/dashboard/summary" in route_paths


def test_main_includes_dashboard_router() -> None:
    """main.py includes the dashboard router."""
    from app.main import app

    all_paths = [r.path for r in app.routes]
    assert "/api/v1/dashboard/summary" in all_paths
