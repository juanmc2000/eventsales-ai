"""Smoke tests for Room schemas (no DB required)."""

import uuid

import pytest


def test_room_create_schema_valid() -> None:
    from app.modules.restaurants.schemas import RoomCreate

    r = RoomCreate(
        name="The Oak Room",
        slug="the-oak-room",
        restaurant_id=uuid.uuid4(),
        seated_capacity=40,
        standing_capacity=80,
    )
    assert r.name == "The Oak Room"
    assert r.slug == "the-oak-room"
    assert r.seated_capacity == 40


def test_room_create_schema_invalid_slug() -> None:
    from pydantic import ValidationError

    from app.modules.restaurants.schemas import RoomCreate

    with pytest.raises(ValidationError):
        RoomCreate(
            name="The Oak Room",
            slug="The Oak Room With Spaces",
            restaurant_id=uuid.uuid4(),
        )


def test_room_create_defaults() -> None:
    from app.modules.restaurants.schemas import RoomCreate

    r = RoomCreate(name="PDR One", slug="pdr-one", restaurant_id=uuid.uuid4())
    assert r.is_private_dining is False
    assert r.display_order == 0
    assert r.layouts is None
    assert r.amenities is None
    assert r.asset_links is None


def test_room_update_partial() -> None:
    from app.modules.restaurants.schemas import RoomUpdate

    u = RoomUpdate(seated_capacity=60)
    dumped = u.model_dump(exclude_none=True)
    assert "seated_capacity" in dumped
    assert "name" not in dumped


def test_room_out_schema_from_attributes() -> None:
    from datetime import datetime, timezone

    from app.modules.restaurants.schemas import RoomOut

    now = datetime.now(tz=timezone.utc)
    rid = uuid.uuid4()
    rest_id = uuid.uuid4()

    r = RoomOut(
        id=rid,
        tenant_id="default",
        restaurant_id=rest_id,
        name="The Oak Room",
        slug="the-oak-room",
        is_active=True,
        is_private_dining=False,
        display_order=0,
        created_at=now,
        updated_at=now,
    )
    assert r.id == rid
    assert r.tenant_id == "default"
    assert r.restaurant_id == rest_id


def test_room_list_out_schema() -> None:
    from app.modules.restaurants.schemas import RoomListOut

    result = RoomListOut(items=[], total=0)
    assert result.total == 0
    assert result.items == []


def test_room_json_fields_accept_lists() -> None:
    from app.modules.restaurants.schemas import RoomCreate

    r = RoomCreate(
        name="Boardroom",
        slug="boardroom",
        restaurant_id=uuid.uuid4(),
        layouts=["theatre", "boardroom", "cabaret"],
        amenities=["AV screen", "microphone", "natural light"],
        asset_links=[{"type": "image", "url": "https://example.com/room.jpg"}],
    )
    assert "theatre" in r.layouts
    assert "AV screen" in r.amenities
    assert r.asset_links[0]["type"] == "image"
