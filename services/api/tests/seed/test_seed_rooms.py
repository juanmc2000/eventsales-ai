"""Tests for room seed data (no DB required).

Validates that SEED_ROOMS data satisfies acceptance criteria for DATA-006
without needing a live database.
"""

import pytest

from app.modules.shared.seed_data import SEED_ROOMS, SEED_RESTAURANTS


RESTAURANT_SLUGS = {r["slug"] for r in SEED_RESTAURANTS}


def test_every_restaurant_has_at_least_one_room() -> None:
    """Each seeded restaurant must have at least one seeded room."""
    slugs_with_rooms = {r["restaurant_slug"] for r in SEED_ROOMS}
    missing = RESTAURANT_SLUGS - slugs_with_rooms
    assert not missing, f"Restaurants with no seeded rooms: {missing}"


def test_every_restaurant_has_at_least_one_event_space() -> None:
    """Each restaurant must have a usable event/dining space (seated_capacity > 0)."""
    slugs_covered: set[str] = set()
    for room in SEED_ROOMS:
        if (room.get("seated_capacity") or 0) > 0:
            slugs_covered.add(room["restaurant_slug"])
    missing = RESTAURANT_SLUGS - slugs_covered
    assert not missing, f"Restaurants with no usable event space: {missing}"


def test_luxury_restaurants_have_private_dining() -> None:
    """Grand Ballroom and Garden Room must include at least one private dining room."""
    luxury_slugs = {"the-grand-ballroom", "the-garden-room"}
    pdr_by_restaurant: set[str] = set()
    for room in SEED_ROOMS:
        if room.get("is_private_dining") and room["restaurant_slug"] in luxury_slugs:
            pdr_by_restaurant.add(room["restaurant_slug"])
    missing = luxury_slugs - pdr_by_restaurant
    assert not missing, f"Luxury restaurants missing PDR: {missing}"


def test_all_rooms_have_required_fields() -> None:
    """Every room must have name, slug, seated_capacity, standing_capacity."""
    for room in SEED_ROOMS:
        label = f"{room.get('restaurant_slug')}/{room.get('slug')}"
        assert room.get("name"), f"{label}: missing name"
        assert room.get("slug"), f"{label}: missing slug"
        assert room.get("seated_capacity") is not None, f"{label}: missing seated_capacity"
        assert room.get("standing_capacity") is not None, f"{label}: missing standing_capacity"


def test_all_rooms_have_layouts() -> None:
    """Every room must have at least one layout option."""
    for room in SEED_ROOMS:
        label = f"{room.get('restaurant_slug')}/{room.get('slug')}"
        assert room.get("layouts"), f"{label}: missing layouts"
        assert len(room["layouts"]) >= 1, f"{label}: layouts list is empty"


def test_all_rooms_have_amenities() -> None:
    """Every room must list amenities."""
    for room in SEED_ROOMS:
        label = f"{room.get('restaurant_slug')}/{room.get('slug')}"
        assert room.get("amenities"), f"{label}: missing amenities"
        assert len(room["amenities"]) >= 1, f"{label}: amenities list is empty"


def test_all_rooms_have_suitability_notes() -> None:
    """Every room must have suitability notes."""
    for room in SEED_ROOMS:
        label = f"{room.get('restaurant_slug')}/{room.get('slug')}"
        assert room.get("suitability_notes"), f"{label}: missing suitability_notes"


def test_all_rooms_have_booking_url() -> None:
    """Every room must have a booking URL."""
    for room in SEED_ROOMS:
        label = f"{room.get('restaurant_slug')}/{room.get('slug')}"
        assert room.get("booking_url"), f"{label}: missing booking_url"


def test_asset_links_are_clearly_fake() -> None:
    """Asset links must use example.com placeholders, not real CDN URLs."""
    for room in SEED_ROOMS:
        label = f"{room.get('restaurant_slug')}/{room.get('slug')}"
        for link in room.get("asset_links") or []:
            url = link.get("url", "")
            assert "example.com" in url, f"{label}: asset_link URL must use example.com, got {url!r}"


def test_room_slugs_are_unique_per_restaurant() -> None:
    """Within each restaurant, room slugs must be unique."""
    from collections import defaultdict

    slugs_by_restaurant: dict[str, list[str]] = defaultdict(list)
    for room in SEED_ROOMS:
        slugs_by_restaurant[room["restaurant_slug"]].append(room["slug"])

    for restaurant_slug, slugs in slugs_by_restaurant.items():
        assert len(slugs) == len(set(slugs)), (
            f"Duplicate room slugs in {restaurant_slug}: {slugs}"
        )


def test_seed_rooms_data_is_importable() -> None:
    """SEED_ROOMS can be imported without errors and has the expected count."""
    assert len(SEED_ROOMS) >= 4  # at least one room per restaurant


def test_capacity_consistency() -> None:
    """max_capacity must be >= seated_capacity for all rooms."""
    for room in SEED_ROOMS:
        label = f"{room.get('restaurant_slug')}/{room.get('slug')}"
        seated = room.get("seated_capacity") or 0
        max_cap = room.get("max_capacity") or 0
        assert max_cap >= seated, f"{label}: max_capacity ({max_cap}) < seated_capacity ({seated})"
