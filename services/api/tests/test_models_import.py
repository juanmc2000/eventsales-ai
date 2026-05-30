"""Smoke tests: all POC models import without error and register against Base.

These tests do not require a live database — they only verify that:
- all model modules import cleanly
- all expected tables appear in Base.metadata
"""

import pytest


def test_all_models_importable() -> None:
    """All model classes can be imported from app.db.models."""
    from app.db.models import (  # noqa: F401
        CalendarEvent,
        DemandEvent,
        EmailEvent,
        Enquiry,
        EnquiryMessage,
        InsightSnapshot,
        Persona,
        PricingRule,
        Restaurant,
        RestaurantPersona,
    )


def test_all_tables_in_metadata() -> None:
    """All POC tables are registered in Base.metadata after model import."""
    import app.db.models  # noqa: F401 — triggers model registration

    from app.db.base import Base

    expected_tables = {
        "restaurants",
        "rooms",
        "room_availability",
        "personas",
        "restaurant_personas",
        "pricing_rules",
        "enquiries",
        "enquiry_messages",
        "enquiry_extractions",
        "enquiry_processing_snapshots",
        "enquiry_date_requests",
        "enquiry_candidate_dates",
        "email_events",
        "calendar_events",
        "demand_events",
        "insight_snapshots",
        "ai_prompt_templates",
        "ai_prompt_versions",
        "tenant_prompt_configs",
        "ai_prompt_runs",
        "ai_prompt_run_reviews",
        "ai_prompt_experiments",
        "ai_prompt_experiment_runs",
        "ai_training_examples",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables == actual_tables, (
        f"Missing tables: {expected_tables - actual_tables}\n"
        f"Unexpected tables: {actual_tables - expected_tables}"
    )


def test_restaurant_model_columns() -> None:
    """Restaurant model has required columns."""
    from app.modules.restaurants.models import Restaurant

    col_names = {c.name for c in Restaurant.__table__.columns}
    assert "id" in col_names
    assert "tenant_id" in col_names
    assert "slug" in col_names
    assert "is_active" in col_names


def test_enquiry_model_columns() -> None:
    """Enquiry model has required columns."""
    from app.modules.enquiries.models import Enquiry

    col_names = {c.name for c in Enquiry.__table__.columns}
    assert "reference" in col_names
    assert "status" in col_names
    assert "restaurant_id" in col_names
    assert "event_date" in col_names


def test_pricing_rule_model_columns() -> None:
    """PricingRule model has minimum_spend and is deterministic (no ml fields)."""
    from app.modules.pricing.models import PricingRule

    col_names = {c.name for c in PricingRule.__table__.columns}
    assert "minimum_spend" in col_names
    assert "day_of_week" in col_names
    assert "meal_period" in col_names
    # No ML pricing fields
    assert "predicted_price" not in col_names
    assert "ml_score" not in col_names
