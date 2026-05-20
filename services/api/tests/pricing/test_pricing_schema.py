"""Smoke tests for pricing schemas and recommendation logic (no DB required)."""

import uuid
import pytest


def test_pricing_rule_create_schema_valid() -> None:
    from app.modules.pricing.schemas import PricingRuleCreate

    rule = PricingRuleCreate(
        name="Weekend Dinner",
        restaurant_id=uuid.uuid4(),
        day_of_week=5,
        meal_period="dinner",
        minimum_spend=3000.0,
    )
    assert rule.name == "Weekend Dinner"
    assert rule.minimum_spend == 3000.0


def test_pricing_rule_create_invalid_day_of_week() -> None:
    from pydantic import ValidationError

    from app.modules.pricing.schemas import PricingRuleCreate

    with pytest.raises(ValidationError):
        PricingRuleCreate(
            name="Bad Rule",
            restaurant_id=uuid.uuid4(),
            day_of_week=7,  # invalid — must be 0-6
            meal_period="dinner",
            minimum_spend=1000.0,
        )


def test_pricing_rule_create_negative_spend_rejected() -> None:
    from pydantic import ValidationError

    from app.modules.pricing.schemas import PricingRuleCreate

    with pytest.raises(ValidationError):
        PricingRuleCreate(
            name="Bad Rule",
            restaurant_id=uuid.uuid4(),
            meal_period="lunch",
            minimum_spend=-500.0,
        )


def test_recommendation_request_schema() -> None:
    from app.modules.pricing.schemas import PricingRecommendationRequest

    req = PricingRecommendationRequest(
        restaurant_id=uuid.uuid4(),
        day_of_week=5,
        meal_period="dinner",
        party_size=30,
    )
    assert req.day_of_week == 5
    assert req.meal_period == "dinner"


def test_pricing_recommendation_confidence_is_always_one() -> None:
    from app.modules.pricing.schemas import PricingRecommendationOut

    out = PricingRecommendationOut(
        recommended_minimum_spend=2500.0,
        applied_rules=[],
        explanation="Test",
    )
    # Deterministic rules always have confidence=1.0 (no ML)
    assert out.confidence == 1.0
