"""Unit tests for RoomService using a real in-memory SQLite database."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

import app.db.models  # noqa: F401 — registers all models
from app.db.base import Base
from app.modules.restaurants.models import Restaurant, Room
from app.modules.restaurants.schemas import RoomCreate, RoomUpdate
from app.modules.restaurants.service import RoomService


@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    # SQLite does not enforce FK constraints by default.
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
        name="Test Venue",
        slug=f"test-venue-{uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db.add(r)
    db.flush()
    return r


def _make_room_data(restaurant_id: uuid.UUID, **kwargs) -> RoomCreate:
    defaults = dict(
        name="The Oak Room",
        slug=f"the-oak-room-{uuid.uuid4().hex[:6]}",
        restaurant_id=restaurant_id,
        seated_capacity=40,
        standing_capacity=80,
    )
    defaults.update(kwargs)
    return RoomCreate(**defaults)


# --- Create ---


def test_create_room(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    data = _make_room_data(restaurant.id)
    room = svc.create_room(restaurant.id, data)
    assert room.id is not None
    assert room.restaurant_id == restaurant.id
    assert room.name == data.name
    assert room.tenant_id == "default"


def test_create_room_unknown_restaurant(db: Session) -> None:
    svc = RoomService(db)
    data = _make_room_data(uuid.uuid4())
    with pytest.raises(ValueError, match="Restaurant not found"):
        svc.create_room(uuid.uuid4(), data)


def test_create_room_with_json_fields(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    data = _make_room_data(
        restaurant.id,
        layouts=["theatre", "boardroom"],
        amenities=["AV screen", "natural light"],
        asset_links=[{"type": "image", "url": "https://example.com/room.jpg"}],
    )
    room = svc.create_room(restaurant.id, data)
    assert room.layouts == ["theatre", "boardroom"]
    assert "AV screen" in room.amenities


def test_create_room_private_dining(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    data = _make_room_data(restaurant.id, is_private_dining=True, room_hire_fee=Decimal("500.00"))
    room = svc.create_room(restaurant.id, data)
    assert room.is_private_dining is True
    assert room.room_hire_fee == Decimal("500.00")


# --- List ---


def test_list_rooms_active_only(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    svc.create_room(restaurant.id, _make_room_data(restaurant.id))
    svc.create_room(restaurant.id, _make_room_data(restaurant.id))
    items, total = svc.list_rooms(restaurant.id, active_only=True)
    assert len(items) >= 2
    assert total >= 2
    assert all(r.is_active for r in items)


def test_list_rooms_inactive_excluded_by_default(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    room = svc.create_room(restaurant.id, _make_room_data(restaurant.id))
    svc.deactivate_room(restaurant.id, room.id)
    items, _ = svc.list_rooms(restaurant.id, active_only=True)
    assert room.id not in [r.id for r in items]


def test_list_rooms_includes_inactive_when_requested(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    room = svc.create_room(restaurant.id, _make_room_data(restaurant.id))
    svc.deactivate_room(restaurant.id, room.id)
    items, _ = svc.list_rooms(restaurant.id, active_only=False)
    assert room.id in [r.id for r in items]


def test_list_rooms_ordered_by_display_order(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    r1 = svc.create_room(restaurant.id, _make_room_data(restaurant.id, display_order=10))
    r2 = svc.create_room(restaurant.id, _make_room_data(restaurant.id, display_order=1))
    items, _ = svc.list_rooms(restaurant.id)
    ids = [r.id for r in items]
    assert ids.index(r2.id) < ids.index(r1.id)


# --- Get ---


def test_get_room(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    created = svc.create_room(restaurant.id, _make_room_data(restaurant.id))
    fetched = svc.get_room(restaurant.id, created.id)
    assert fetched is not None
    assert fetched.id == created.id


def test_get_room_wrong_restaurant(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    created = svc.create_room(restaurant.id, _make_room_data(restaurant.id))
    result = svc.get_room(uuid.uuid4(), created.id)
    assert result is None


def test_get_room_not_found(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    result = svc.get_room(restaurant.id, uuid.uuid4())
    assert result is None


# --- Update ---


def test_update_room(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    room = svc.create_room(restaurant.id, _make_room_data(restaurant.id))
    updated = svc.update_room(restaurant.id, room.id, RoomUpdate(seated_capacity=60))
    assert updated is not None
    assert updated.seated_capacity == 60


def test_update_room_not_found(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    result = svc.update_room(restaurant.id, uuid.uuid4(), RoomUpdate(name="New"))
    assert result is None


def test_update_room_empty_payload_returns_unchanged(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    room = svc.create_room(restaurant.id, _make_room_data(restaurant.id))
    result = svc.update_room(restaurant.id, room.id, RoomUpdate())
    assert result is not None
    assert result.id == room.id


# --- Deactivate ---


def test_deactivate_room(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    room = svc.create_room(restaurant.id, _make_room_data(restaurant.id))
    assert room.is_active is True
    deactivated = svc.deactivate_room(restaurant.id, room.id)
    assert deactivated is not None
    assert deactivated.is_active is False


def test_deactivate_room_not_found(db: Session, restaurant: Restaurant) -> None:
    svc = RoomService(db)
    result = svc.deactivate_room(restaurant.id, uuid.uuid4())
    assert result is None
