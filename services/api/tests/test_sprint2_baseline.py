"""Sprint 2 backend test coverage baseline.

All tests in this file are smoke tests that do NOT require a live database.
They verify that:
- All Sprint 2 modules import without error
- Core schemas validate correctly
- Core service invariants hold (e.g. deterministic pricing, valid status set)
- Seed data definitions are structurally valid

These tests act as a regression guard for the Sprint 2 product foundation.
Run with: cd services/api && pytest tests/test_sprint2_baseline.py

Integration tests (requiring PostgreSQL) are in tests/integration/.
"""

import uuid
from datetime import date

import pytest


# ── Module import smoke tests ─────────────────────────────────────────────────


def test_restaurants_module_importable() -> None:
    """restaurants module imports cleanly."""
    from app.modules.restaurants import models, repository, schemas, service  # noqa: F401


def test_personas_module_importable() -> None:
    """personas module imports cleanly."""
    from app.modules.personas import models, repository, schemas, service  # noqa: F401


def test_pricing_module_importable() -> None:
    """pricing module imports cleanly."""
    from app.modules.pricing import models, repository, schemas, service  # noqa: F401


def test_calendar_module_importable() -> None:
    """calendar module imports cleanly."""
    from app.modules.calendar import repository, schemas, service  # noqa: F401


def test_enquiries_module_importable() -> None:
    """enquiries module imports cleanly."""
    from app.modules.enquiries import models, repository, schemas, service  # noqa: F401


def test_all_models_registered() -> None:
    """All POC tables are registered in Base.metadata."""
    import app.db.models  # noqa: F401

    from app.db.base import Base

    expected = {
        "restaurants", "rooms", "room_availability", "personas", "restaurant_personas", "pricing_rules",
        "enquiries", "enquiry_messages", "enquiry_extractions", "enquiry_processing_snapshots",
        "email_events",
        "calendar_events", "demand_events", "insight_snapshots",
        "ai_prompt_templates", "ai_prompt_versions", "tenant_prompt_configs",
        "ai_prompt_runs", "ai_prompt_run_reviews",
        "ai_prompt_experiments", "ai_prompt_experiment_runs",
        "ai_training_examples",
    }
    actual = set(Base.metadata.tables.keys())
    assert expected == actual


# ── Restaurant schema ─────────────────────────────────────────────────────────


def test_restaurant_create_valid() -> None:
    from app.modules.restaurants.schemas import RestaurantCreate
    r = RestaurantCreate(name="Test Venue", slug="test-venue")
    assert r.slug == "test-venue"


def test_restaurant_slug_pattern_enforced() -> None:
    from pydantic import ValidationError
    from app.modules.restaurants.schemas import RestaurantCreate
    with pytest.raises(ValidationError):
        RestaurantCreate(name="Test", slug="Test Venue!")


# ── Persona schema ────────────────────────────────────────────────────────────


def test_persona_create_valid() -> None:
    from app.modules.personas.schemas import PersonaCreate
    p = PersonaCreate(name="Eleanor", slug="eleanor", system_prompt="You are Eleanor.")
    assert p.tone == "professional"  # default


def test_persona_assignment_defaults_not_default() -> None:
    from app.modules.personas.schemas import RestaurantPersonaAssign
    assign = RestaurantPersonaAssign(persona_id=uuid.uuid4())
    assert assign.is_default is False


# ── Pricing schema and determinism ────────────────────────────────────────────


def test_pricing_rule_day_of_week_validated() -> None:
    from pydantic import ValidationError
    from app.modules.pricing.schemas import PricingRuleCreate
    with pytest.raises(ValidationError):
        PricingRuleCreate(name="Bad", restaurant_id=uuid.uuid4(), day_of_week=8, meal_period="lunch", minimum_spend=100.0)


def test_pricing_recommendation_confidence_always_one() -> None:
    from app.modules.pricing.schemas import PricingRecommendationOut
    out = PricingRecommendationOut(recommended_minimum_spend=1500.0, applied_rules=[], explanation="Test")
    assert out.confidence == 1.0, "Deterministic rules must always report confidence=1.0 (no ML)"


def test_pricing_rule_negative_spend_rejected() -> None:
    from pydantic import ValidationError
    from app.modules.pricing.schemas import PricingRuleCreate
    with pytest.raises(ValidationError):
        PricingRuleCreate(name="Bad", restaurant_id=uuid.uuid4(), meal_period="lunch", minimum_spend=-100.0)


# ── Calendar schema ───────────────────────────────────────────────────────────


def test_demand_event_score_range_enforced() -> None:
    from pydantic import ValidationError
    from app.modules.calendar.schemas import DemandEventCreate
    with pytest.raises(ValidationError):
        DemandEventCreate(restaurant_id=uuid.uuid4(), event_date=date(2026, 1, 1), demand_level="high", demand_score=2.0)


def test_calendar_range_out_empty_days() -> None:
    from app.modules.calendar.schemas import CalendarRangeOut
    result = CalendarRangeOut(restaurant_id=uuid.uuid4(), date_from=date(2026, 1, 1), date_to=date(2026, 1, 31), days=[])
    assert result.days == []


# ── Enquiry schema ────────────────────────────────────────────────────────────


def test_enquiry_create_invalid_email_rejected() -> None:
    from pydantic import ValidationError
    from app.modules.enquiries.schemas import EnquiryCreate
    with pytest.raises(ValidationError):
        EnquiryCreate(restaurant_id=uuid.uuid4(), first_name="X", last_name="Y", email="not-valid")


def test_enquiry_message_direction_validated() -> None:
    from pydantic import ValidationError
    from app.modules.enquiries.schemas import EnquiryMessageCreate
    with pytest.raises(ValidationError):
        EnquiryMessageCreate(direction="sideways", body="Hello")


def test_enquiry_valid_status_set_complete() -> None:
    from app.modules.enquiries.service import VALID_STATUSES
    lifecycle = {"new", "open", "proposal_sent", "follow_up", "confirmed", "cancelled", "lost"}
    assert VALID_STATUSES == lifecycle


# ── Seed data ─────────────────────────────────────────────────────────────────


def test_seed_four_restaurants() -> None:
    from app.modules.shared.seed_data import SEED_RESTAURANTS
    assert len(SEED_RESTAURANTS) == 4


def test_seed_three_personas() -> None:
    from app.modules.shared.seed_data import SEED_PERSONAS
    assert len(SEED_PERSONAS) == 3


def test_seed_emails_safe() -> None:
    from app.modules.shared.seed_data import SEED_RESTAURANTS
    for r in SEED_RESTAURANTS:
        assert "example.com" in r.get("email", ""), f"Unsafe email in restaurant {r['name']}"


def test_seed_no_ml_pricing_fields() -> None:
    from app.modules.shared.seed_data import SEED_PRICING_RULES
    for rule in SEED_PRICING_RULES:
        assert "ml_score" not in rule
        assert "predicted_price" not in rule


# ── Alembic migration ─────────────────────────────────────────────────────────


def test_alembic_migration_importable() -> None:
    """Initial migration script imports without error."""
    import importlib.util
    import pathlib

    migration_path = pathlib.Path(__file__).parent.parent / "alembic" / "versions" / "20260520_000001_create_core_poc_tables.py"
    spec = importlib.util.spec_from_file_location("migration_initial", migration_path)
    assert spec is not None
    migration = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(migration)
    assert hasattr(migration, "upgrade")
    assert hasattr(migration, "downgrade")
    assert migration.down_revision is None, "First migration must have no parent"


def test_alembic_env_importable() -> None:
    """alembic/env.py is syntactically valid (import test only)."""
    # env.py runs migration logic on import; we only test that the module compiles
    import py_compile
    import os
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "alembic", "env.py"
    )
    assert os.path.exists(env_path), "alembic/env.py not found"
    py_compile.compile(env_path, doraise=True)
