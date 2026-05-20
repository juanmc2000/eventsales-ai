"""Smoke tests for restaurant schemas and service logic (no DB required)."""

import pytest


def test_restaurant_create_schema_valid() -> None:
    from app.modules.restaurants.schemas import RestaurantCreate

    r = RestaurantCreate(name="Test Venue", slug="test-venue")
    assert r.name == "Test Venue"
    assert r.slug == "test-venue"


def test_restaurant_create_schema_invalid_slug() -> None:
    from pydantic import ValidationError

    from app.modules.restaurants.schemas import RestaurantCreate

    with pytest.raises(ValidationError):
        RestaurantCreate(name="Test", slug="Test Venue With Spaces")


def test_restaurant_update_schema_excludes_none() -> None:
    from app.modules.restaurants.schemas import RestaurantUpdate

    update = RestaurantUpdate(name="New Name")
    dumped = update.model_dump(exclude_none=True)
    assert "name" in dumped
    assert "description" not in dumped


def test_restaurant_list_out_schema() -> None:
    from app.modules.restaurants.schemas import RestaurantListOut

    result = RestaurantListOut(items=[], total=0)
    assert result.total == 0
    assert result.items == []
