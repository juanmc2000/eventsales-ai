"""
Venue context workflow tests.

TEST-006: validates the full Sprint 5C venue context chain:
  rooms model → room CRUD → restaurant context → AI draft context

Covers:
  - rooms table present in SQLAlchemy metadata (migration sanity)
  - rooms table has expected key columns
  - room CRUD via RoomService (create, list, update, deactivate, ordering)
  - restaurant context includes room data end-to-end
  - AI _match_room resolves preferred_area and capacity
"""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session, sessionmaker

import app.db.models  # noqa: F401 — registers all models
from app.db.base import Base
from app.modules.restaurants.models import Restaurant, Room
from app.modules.restaurants.schemas import RoomCreate, RoomUpdate
from app.modules.restaurants.service import RestaurantService, RoomService


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture()
def db(engine):
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def restaurant(db: Session) -> Restaurant:
    r = Restaurant(
        id=uuid.uuid4(),
        tenant_id="default",
        name="Workflow Test Venue",
        slug=f"workflow-test-{uuid.uuid4().hex[:6]}",
        address="10 Workflow Lane, London W1A 1AA",
        is_active=True,
    )
    db.add(r)
    db.flush()
    return r


# ── Migration sanity ──────────────────────────────────────────────────────────


def test_rooms_table_in_metadata() -> None:
    """The rooms table must be registered in SQLAlchemy metadata after model import."""
    assert "rooms" in Base.metadata.tables


def test_rooms_table_key_columns(engine) -> None:
    """The rooms table must have all expected key columns."""
    inspector = inspect(engine)
    col_names = {c["name"] for c in inspector.get_columns("rooms")}
    required = {
        "id",
        "tenant_id",
        "restaurant_id",
        "name",
        "slug",
        "room_type",
        "seated_capacity",
        "standing_capacity",
        "min_capacity",
        "max_capacity",
        "is_private_dining",
        "is_active",
        "display_order",
        "created_at",
        "updated_at",
    }
    missing = required - col_names
    assert not missing, f"rooms table missing columns: {missing}"


# ── Room CRUD workflow ─────────────────────────────────────────────────────────


def test_room_create_and_list(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    payload = RoomCreate(
        name="The Cedar Room",
        slug=f"cedar-{uuid.uuid4().hex[:4]}",
        restaurant_id=restaurant.id,
        seated_capacity=60,
        standing_capacity=100,
        is_private_dining=True,
        display_order=1,
    )
    room = svc.create_room(restaurant.id, payload)
    assert room.id is not None
    assert room.name == "The Cedar Room"
    assert room.is_private_dining is True

    rooms, _ = svc.list_rooms(restaurant.id, active_only=True)
    assert any(r.id == room.id for r in rooms)


def test_room_update(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    create_payload = RoomCreate(
        name="The Walnut Room",
        slug=f"walnut-{uuid.uuid4().hex[:4]}",
        restaurant_id=restaurant.id,
        seated_capacity=20,
    )
    room = svc.create_room(restaurant.id, create_payload)

    updated = svc.update_room(restaurant.id, room.id, RoomUpdate(seated_capacity=30))
    assert updated is not None
    assert updated.seated_capacity == 30
    assert updated.name == "The Walnut Room"


def test_room_deactivate_excludes_from_active_list(
    db: Session, restaurant: Restaurant
) -> None:
    svc = RoomService(db)
    room = svc.create_room(
        restaurant.id,
        RoomCreate(
            name="Temp Room",
            slug=f"temp-{uuid.uuid4().hex[:4]}",
            restaurant_id=restaurant.id,
        ),
    )
    svc.deactivate_room(restaurant.id, room.id)
    active, _ = svc.list_rooms(restaurant.id, active_only=True)
    assert not any(r.id == room.id for r in active)


def test_room_display_order_respected(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    slug_a = f"room-a-{uuid.uuid4().hex[:4]}"
    slug_b = f"room-b-{uuid.uuid4().hex[:4]}"
    svc.create_room(
        restaurant.id,
        RoomCreate(
            name="Room B",
            slug=slug_b,
            restaurant_id=restaurant.id,
            display_order=2,
        ),
    )
    svc.create_room(
        restaurant.id,
        RoomCreate(
            name="Room A",
            slug=slug_a,
            restaurant_id=restaurant.id,
            display_order=1,
        ),
    )
    rooms, _ = svc.list_rooms(restaurant.id, active_only=True)
    names = [r.name for r in rooms]
    assert names.index("Room A") < names.index("Room B")


# ── Restaurant context workflow ───────────────────────────────────────────────


def test_context_includes_rooms(db: Session, restaurant: Restaurant) -> None:
    """Restaurant context endpoint returns rooms for the venue."""
    room = Room(
        id=uuid.uuid4(),
        tenant_id="default",
        restaurant_id=restaurant.id,
        name="The Maple PDR",
        slug=f"maple-{uuid.uuid4().hex[:4]}",
        seated_capacity=16,
        is_private_dining=True,
        is_active=True,
        display_order=1,
    )
    db.add(room)
    db.flush()

    svc = RestaurantService(db)
    ctx = svc.get_restaurant_context(restaurant.id)
    assert ctx is not None
    room_ids = [r.id for r in ctx.rooms]
    assert room.id in room_ids


def test_context_room_fields_complete(db: Session, restaurant: Restaurant) -> None:
    """Context room data includes all fields required for draft generation."""
    room = Room(
        id=uuid.uuid4(),
        tenant_id="default",
        restaurant_id=restaurant.id,
        name="The Birch Suite",
        slug=f"birch-{uuid.uuid4().hex[:4]}",
        seated_capacity=50,
        standing_capacity=80,
        min_capacity=10,
        max_capacity=80,
        layouts=["theatre", "banquet"],
        amenities=["AV screen", "piano"],
        suitability_notes="Ideal for product launches.",
        is_private_dining=False,
        is_active=True,
        display_order=2,
    )
    db.add(room)
    db.flush()

    svc = RestaurantService(db)
    ctx = svc.get_restaurant_context(restaurant.id)
    assert ctx is not None
    ctx_room = next((r for r in ctx.rooms if r.id == room.id), None)
    assert ctx_room is not None
    assert ctx_room.seated_capacity == 50
    assert ctx_room.layouts == ["theatre", "banquet"]
    assert "AV screen" in ctx_room.amenities
    assert ctx_room.suitability_notes is not None
    assert ctx_room.is_private_dining is False


def test_context_no_rooms_returns_empty_list(db: Session) -> None:
    """Context for a venue with no rooms returns an empty rooms list."""
    empty_venue = Restaurant(
        id=uuid.uuid4(),
        tenant_id="default",
        name="Empty Venue",
        slug=f"empty-{uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db.add(empty_venue)
    db.flush()

    svc = RestaurantService(db)
    ctx = svc.get_restaurant_context(empty_venue.id)
    assert ctx is not None
    assert ctx.rooms == []


# ── AI room matching workflow ─────────────────────────────────────────────────


def test_match_room_by_preferred_area_name(db: Session, restaurant: Restaurant) -> None:
    """_match_room resolves preferred_area text to the correct room."""
    from app.modules.ai.service import _match_room

    pdr = Room(
        id=uuid.uuid4(),
        tenant_id="default",
        restaurant_id=restaurant.id,
        name="Private Dining Room",
        slug=f"pdr-workflow-{uuid.uuid4().hex[:4]}",
        seated_capacity=14,
        min_capacity=6,
        max_capacity=20,
        is_private_dining=True,
        is_active=True,
        display_order=1,
    )
    main_hall = Room(
        id=uuid.uuid4(),
        tenant_id="default",
        restaurant_id=restaurant.id,
        name="Main Hall",
        slug=f"main-{uuid.uuid4().hex[:4]}",
        seated_capacity=200,
        min_capacity=50,
        max_capacity=300,
        is_private_dining=False,
        is_active=True,
        display_order=2,
    )
    db.add_all([pdr, main_hall])
    db.flush()

    matched = _match_room([pdr, main_hall], party_size=10, preferred_area="private dining")
    assert matched is not None
    assert matched.id == pdr.id


def test_match_room_falls_back_to_capacity_when_no_area(
    db: Session, restaurant: Restaurant
) -> None:
    """_match_room falls back to capacity range when preferred_area is None."""
    from app.modules.ai.service import _match_room

    small = Room(
        id=uuid.uuid4(),
        tenant_id="default",
        restaurant_id=restaurant.id,
        name="Small Room",
        slug=f"small-{uuid.uuid4().hex[:4]}",
        seated_capacity=20,
        min_capacity=5,
        max_capacity=25,
        is_active=True,
        display_order=1,
    )
    large = Room(
        id=uuid.uuid4(),
        tenant_id="default",
        restaurant_id=restaurant.id,
        name="Large Hall",
        slug=f"large-{uuid.uuid4().hex[:4]}",
        seated_capacity=200,
        min_capacity=50,
        max_capacity=300,
        is_active=True,
        display_order=2,
    )
    db.add_all([small, large])
    db.flush()

    matched = _match_room([small, large], party_size=15, preferred_area=None)
    assert matched is not None
    assert matched.id == small.id


def test_match_room_returns_none_for_empty_list() -> None:
    """_match_room returns None when room list is empty."""
    from app.modules.ai.service import _match_room

    assert _match_room([], party_size=10, preferred_area="any") is None
