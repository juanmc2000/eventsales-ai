"""Smoke tests for the seed data framework.

These tests do not require a live database.  They verify that:
- the seed data definitions are structurally valid
- the seed data constants contain the correct counts
- no real customer data is embedded
"""

import pytest


def test_seed_restaurant_count() -> None:
    """Exactly 4 test restaurants are defined."""
    from app.modules.shared.seed_data import SEED_RESTAURANTS

    assert len(SEED_RESTAURANTS) == 4


def test_seed_persona_count() -> None:
    """Exactly 3 default personas are defined."""
    from app.modules.shared.seed_data import SEED_PERSONAS

    assert len(SEED_PERSONAS) == 3


def test_seed_restaurants_have_required_fields() -> None:
    """Each restaurant definition has name, slug, and email."""
    from app.modules.shared.seed_data import SEED_RESTAURANTS

    for r in SEED_RESTAURANTS:
        assert "name" in r, f"Restaurant missing 'name': {r}"
        assert "slug" in r, f"Restaurant missing 'slug': {r}"
        assert "email" in r, f"Restaurant missing 'email': {r}"


def test_seed_personas_have_required_fields() -> None:
    """Each persona has name, slug, tone, style, and system_prompt."""
    from app.modules.shared.seed_data import SEED_PERSONAS

    for p in SEED_PERSONAS:
        assert "name" in p
        assert "slug" in p
        assert "tone" in p
        assert "style" in p
        assert "system_prompt" in p
        assert len(p["system_prompt"]) > 20, "system_prompt too short"


def test_seed_restaurant_slugs_unique() -> None:
    """All restaurant slugs are unique."""
    from app.modules.shared.seed_data import SEED_RESTAURANTS

    slugs = [r["slug"] for r in SEED_RESTAURANTS]
    assert len(slugs) == len(set(slugs)), "Duplicate restaurant slugs found"


def test_seed_persona_slugs_unique() -> None:
    """All persona slugs are unique."""
    from app.modules.shared.seed_data import SEED_PERSONAS

    slugs = [p["slug"] for p in SEED_PERSONAS]
    assert len(slugs) == len(set(slugs)), "Duplicate persona slugs found"


def test_seed_emails_are_not_real() -> None:
    """Restaurant email addresses use .example.com — not real domains."""
    from app.modules.shared.seed_data import SEED_RESTAURANTS

    for r in SEED_RESTAURANTS:
        email = r.get("email", "")
        assert "example.com" in email, (
            f"Restaurant {r['name']} email '{email}' must use .example.com domain "
            "to prevent accidental delivery to real addresses."
        )


def test_seed_pricing_rules_have_required_fields() -> None:
    """Each pricing rule references a known restaurant slug and has minimum_spend."""
    from app.modules.shared.seed_data import SEED_PRICING_RULES, SEED_RESTAURANTS

    known_slugs = {r["slug"] for r in SEED_RESTAURANTS}
    for rule in SEED_PRICING_RULES:
        assert rule["restaurant_slug"] in known_slugs, (
            f"Pricing rule references unknown restaurant slug: {rule['restaurant_slug']}"
        )
        assert "minimum_spend" in rule
        assert rule["minimum_spend"] > 0


def test_pricing_rules_deterministic_only() -> None:
    """No ML pricing fields are present in pricing rule definitions."""
    from app.modules.shared.seed_data import SEED_PRICING_RULES

    for rule in SEED_PRICING_RULES:
        assert "ml_score" not in rule
        assert "predicted_price" not in rule
        assert "model" not in rule
