"""Tests for restaurant AI context service (SQLite in-memory, no external deps)."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

import app.db.models  # noqa: F401
from app.db.base import Base
from app.modules.personas.models import Persona, RestaurantPersona
from app.modules.pricing.models import PricingRule
from app.modules.restaurants.models import Restaurant, Room
from app.modules.restaurants.service import RestaurantService


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
        name="Context Test Venue",
        slug=f"context-test-{uuid.uuid4().hex[:6]}",
        description="A test venue for context API tests.",
        address="1 Test Street, London EC1A 1AA",
        is_active=True,
    )
    db.add(r)
    db.flush()
    return r


@pytest.fixture()
def persona(db: Session, restaurant: Restaurant) -> Persona:
    p = Persona(
        id=uuid.uuid4(),
        name="Eleanor",
        slug=f"eleanor-{uuid.uuid4().hex[:4]}",
        tone="warm and formal",
        style="considered",
        system_prompt="You are Eleanor.",
        is_active=True,
    )
    db.add(p)
    db.flush()
    rp = RestaurantPersona(
        id=uuid.uuid4(),
        restaurant_id=restaurant.id,
        persona_id=p.id,
        is_default=True,
    )
    db.add(rp)
    db.flush()
    return p


@pytest.fixture()
def room(db: Session, restaurant: Restaurant) -> Room:
    r = Room(
        id=uuid.uuid4(),
        tenant_id="default",
        restaurant_id=restaurant.id,
        name="The Oak Room",
        slug=f"oak-room-{uuid.uuid4().hex[:4]}",
        seated_capacity=40,
        standing_capacity=80,
        layouts=["theatre", "banquet"],
        amenities=["AV screen", "natural light"],
        suitability_notes="Corporate and celebrations.",
        is_private_dining=True,
        is_active=True,
        display_order=1,
    )
    db.add(r)
    db.flush()
    return r


@pytest.fixture()
def pricing_rule(db: Session, restaurant: Restaurant) -> PricingRule:
    pr = PricingRule(
        id=uuid.uuid4(),
        restaurant_id=restaurant.id,
        name="Dinner (All Days)",
        meal_period="dinner",
        day_of_week=None,
        minimum_spend=Decimal("2500.00"),
        minimum_covers=20,
        is_active=True,
    )
    db.add(pr)
    db.flush()
    return pr


# --- Tests ---


def test_context_returns_restaurant_fields(
    db: Session, restaurant: Restaurant
) -> None:
    svc = RestaurantService(db)
    ctx = svc.get_restaurant_context(restaurant.id)
    assert ctx is not None
    assert ctx.id == restaurant.id
    assert ctx.name == restaurant.name
    assert ctx.tenant_id == "default"
    assert ctx.address == restaurant.address


def test_context_not_found(db: Session) -> None:
    svc = RestaurantService(db)
    result = svc.get_restaurant_context(uuid.uuid4())
    assert result is None


def test_context_includes_default_persona(
    db: Session, restaurant: Restaurant, persona: Persona
) -> None:
    svc = RestaurantService(db)
    ctx = svc.get_restaurant_context(restaurant.id)
    assert ctx is not None
    assert len(ctx.personas) >= 1
    assert ctx.default_persona is not None
    assert ctx.default_persona.name == persona.name
    assert ctx.default_persona.is_default is True


def test_context_excludes_system_prompt(
    db: Session, restaurant: Restaurant, persona: Persona
) -> None:
    from app.modules.restaurants.schemas import PersonaContextOut

    svc = RestaurantService(db)
    ctx = svc.get_restaurant_context(restaurant.id)
    assert ctx is not None
    # PersonaContextOut must not have system_prompt field
    assert not hasattr(ctx.default_persona, "system_prompt")


def test_context_includes_active_rooms(
    db: Session, restaurant: Restaurant, room: Room
) -> None:
    svc = RestaurantService(db)
    ctx = svc.get_restaurant_context(restaurant.id)
    assert ctx is not None
    room_ids = [r.id for r in ctx.rooms]
    assert room.id in room_ids


def test_context_room_has_required_fields(
    db: Session, restaurant: Restaurant, room: Room
) -> None:
    svc = RestaurantService(db)
    ctx = svc.get_restaurant_context(restaurant.id)
    assert ctx is not None
    ctx_room = next(r for r in ctx.rooms if r.id == room.id)
    assert ctx_room.seated_capacity == 40
    assert ctx_room.layouts == ["theatre", "banquet"]
    assert "AV screen" in ctx_room.amenities
    assert ctx_room.suitability_notes is not None
    assert ctx_room.is_private_dining is True


def test_context_excludes_inactive_rooms(
    db: Session, restaurant: Restaurant
) -> None:
    inactive_room = Room(
        id=uuid.uuid4(),
        tenant_id="default",
        restaurant_id=restaurant.id,
        name="Inactive Room",
        slug=f"inactive-{uuid.uuid4().hex[:4]}",
        is_active=False,
        display_order=99,
    )
    db.add(inactive_room)
    db.flush()

    svc = RestaurantService(db)
    ctx = svc.get_restaurant_context(restaurant.id)
    assert ctx is not None
    room_ids = [r.id for r in ctx.rooms]
    assert inactive_room.id not in room_ids


def test_context_includes_pricing_rules(
    db: Session, restaurant: Restaurant, pricing_rule: PricingRule
) -> None:
    svc = RestaurantService(db)
    ctx = svc.get_restaurant_context(restaurant.id)
    assert ctx is not None
    rule_names = [pr.name for pr in ctx.pricing_rules]
    assert pricing_rule.name in rule_names


def test_context_pricing_rule_has_required_fields(
    db: Session, restaurant: Restaurant, pricing_rule: PricingRule
) -> None:
    svc = RestaurantService(db)
    ctx = svc.get_restaurant_context(restaurant.id)
    assert ctx is not None
    rule = next(pr for pr in ctx.pricing_rules if pr.name == pricing_rule.name)
    assert rule.meal_period == "dinner"
    assert rule.minimum_spend == Decimal("2500.00")
    assert rule.minimum_covers == 20


def test_context_no_persona_when_none_assigned(
    db: Session
) -> None:
    standalone = Restaurant(
        id=uuid.uuid4(),
        tenant_id="default",
        name="No Persona Venue",
        slug=f"no-persona-{uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db.add(standalone)
    db.flush()

    svc = RestaurantService(db)
    ctx = svc.get_restaurant_context(standalone.id)
    assert ctx is not None
    assert ctx.personas == []
    assert ctx.default_persona is None
