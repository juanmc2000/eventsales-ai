"""POC seed data framework.

Generates deterministic fake data for local development.
All data is fake — no real customer or restaurant data.

Usage via script:
    cd services/api
    python scripts/seed.py

All seed functions are idempotent: re-running them will not create duplicates.
"""

import hashlib
import random
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session


# ── Seed configuration ────────────────────────────────────────────────────────

SEED_RESTAURANTS: list[dict[str, Any]] = [
    {
        "name": "The Grand Ballroom",
        "slug": "the-grand-ballroom",
        "description": "An iconic London event venue offering grand ballroom hire for weddings, corporate galas, and private celebrations.",
        "address": "1 Grand Place, Mayfair, London W1K 1AA",
        "phone": "+44 20 7000 0001",
        "email": "events@thegrandballroom.example.com",
    },
    {
        "name": "Harbour View",
        "slug": "harbour-view",
        "description": "A modern waterfront restaurant with panoramic harbour views, ideal for intimate dinners and corporate lunches.",
        "address": "12 Harbour Wharf, Canary Wharf, London E14 5AA",
        "phone": "+44 20 7000 0002",
        "email": "events@harbourview.example.com",
    },
    {
        "name": "The Garden Room",
        "slug": "the-garden-room",
        "description": "An elegant private dining room surrounded by a walled garden, perfect for exclusive celebrations and boardroom dinners.",
        "address": "34 Garden Square, Chelsea, London SW3 4BB",
        "phone": "+44 20 7000 0003",
        "email": "events@thegardenroom.example.com",
    },
    {
        "name": "City Brasserie",
        "slug": "city-brasserie",
        "description": "A sophisticated city brasserie popular with financial sector clients, offering flexible private dining and full venue hire.",
        "address": "8 Threadneedle Lane, City of London, London EC2R 5AA",
        "phone": "+44 20 7000 0004",
        "email": "events@citybrasserie.example.com",
    },
]

SEED_PERSONAS: list[dict[str, Any]] = [
    {
        "name": "Eleanor",
        "slug": "eleanor",
        "description": "Warm, formal, and attentive. Eleanor communicates with the grace expected of luxury hospitality — never rushed, never generic.",
        "tone": "warm and formal",
        "style": "considered and unhurried",
        "system_prompt": (
            "You are Eleanor, a senior events coordinator for a luxury London hospitality group. "
            "You communicate with warmth, formality, and deep attention to detail. "
            "You never rush a client. Every response should feel personally crafted, never templated. "
            "You focus on the occasion, the guest experience, and the finer details that make events memorable. "
            "Always close with a clear next step and an invitation to speak directly."
        ),
    },
    {
        "name": "James",
        "slug": "james",
        "description": "Professional, direct, and commercially clear. James suits corporate clients who value efficiency and precision over flourish.",
        "tone": "professional and direct",
        "style": "concise and commercially focused",
        "system_prompt": (
            "You are James, a corporate events specialist for a premium London hospitality group. "
            "You communicate clearly and efficiently. Corporate clients value your directness — "
            "you lead with facts, availability, and pricing. "
            "You are professional and personable but never overly warm. "
            "Get to the point, confirm key details, and make the path to booking effortless."
        ),
    },
    {
        "name": "Sophia",
        "slug": "sophia",
        "description": "Enthusiastic, occasion-focused, and creative. Sophia brings energy and inspiration to celebration enquiries.",
        "tone": "enthusiastic and creative",
        "style": "vivid and occasion-focused",
        "system_prompt": (
            "You are Sophia, a celebrations specialist for a prestigious London hospitality group. "
            "You love occasions — birthdays, anniversaries, weddings, milestone dinners. "
            "Your responses are vivid, warm, and full of genuine enthusiasm for making moments special. "
            "You paint a picture of the event, focus on what makes it unique, "
            "and inspire the client to book. Always be genuine, never sycophantic."
        ),
    },
]

SEED_ROOMS: list[dict[str, Any]] = [
    # ── The Grand Ballroom ──────────────────────────────────────────────────────
    {
        "restaurant_slug": "the-grand-ballroom",
        "name": "The Grand Ballroom",
        "slug": "grand-ballroom-main",
        "description": "Our spectacular main ballroom, accommodating up to 300 guests for seated dinners and 500 for standing receptions. Adorned with original gilded cornicing, crystal chandeliers, and a private entrance on Grand Place.",
        "room_type": "ballroom",
        "seated_capacity": 300,
        "standing_capacity": 500,
        "min_capacity": 50,
        "max_capacity": 500,
        "layouts": ["theatre", "banquet", "cabaret", "reception"],
        "amenities": [
            "Crystal chandeliers",
            "Built-in AV system",
            "Stage and dance floor",
            "Private entrance",
            "Adjacent dressing room",
            "Dedicated events team",
        ],
        "asset_links": [
            {"type": "image", "label": "Main ballroom overview", "url": "https://assets.example.com/grand-ballroom/ballroom-main.jpg"},
            {"type": "image", "label": "Stage and dance floor", "url": "https://assets.example.com/grand-ballroom/stage.jpg"},
        ],
        "room_hire_fee": 2500.00,
        "minimum_spend_notes": "Weekday minimum spend from £5,000; weekend from £8,000.",
        "suitability_notes": "Ideal for gala dinners, corporate awards, product launches, weddings, and milestone celebrations.",
        "booking_url": "https://events.thegrandballroom.example.com/enquire",
        "is_private_dining": False,
        "display_order": 1,
    },
    {
        "restaurant_slug": "the-grand-ballroom",
        "name": "The Mayfair Suite",
        "slug": "grand-ballroom-mayfair-suite",
        "description": "An intimate private dining room adjoining the main ballroom, ideal for pre-dinner receptions, board dinners, or exclusive celebrations for up to 24 guests.",
        "room_type": "private_dining",
        "seated_capacity": 24,
        "standing_capacity": 35,
        "min_capacity": 8,
        "max_capacity": 35,
        "layouts": ["boardroom", "banquet", "reception"],
        "amenities": [
            "Private butler service",
            "65-inch display screen",
            "Bespoke wine list",
            "Dedicated entrance from foyer",
            "Natural daylight",
        ],
        "asset_links": [
            {"type": "image", "label": "Mayfair Suite dining setup", "url": "https://assets.example.com/grand-ballroom/mayfair-suite.jpg"},
        ],
        "room_hire_fee": 750.00,
        "minimum_spend_notes": "Minimum food and beverage spend of £3,500.",
        "suitability_notes": "Perfect for board dinners, intimate celebrations, and pre-event private dining.",
        "booking_url": "https://events.thegrandballroom.example.com/enquire",
        "is_private_dining": True,
        "display_order": 2,
    },
    # ── Harbour View ────────────────────────────────────────────────────────────
    {
        "restaurant_slug": "harbour-view",
        "name": "The Waterfront Room",
        "slug": "harbour-view-waterfront",
        "description": "Floor-to-ceiling windows overlooking the harbour, accommodating up to 80 guests for seated dinners with panoramic views of Canary Wharf.",
        "room_type": "event_space",
        "seated_capacity": 80,
        "standing_capacity": 120,
        "min_capacity": 20,
        "max_capacity": 120,
        "layouts": ["banquet", "cabaret", "theatre", "reception"],
        "amenities": [
            "Panoramic harbour views",
            "Retractable room divider",
            "Integrated AV and lighting",
            "Private terrace access",
            "Dedicated bar",
        ],
        "asset_links": [
            {"type": "image", "label": "Waterfront Room daytime", "url": "https://assets.example.com/harbour-view/waterfront-day.jpg"},
            {"type": "image", "label": "Waterfront Room evening setup", "url": "https://assets.example.com/harbour-view/waterfront-evening.jpg"},
        ],
        "room_hire_fee": 1200.00,
        "minimum_spend_notes": "Minimum spend from £2,500 on weekdays, £4,000 on weekends.",
        "suitability_notes": "Popular with financial and professional services clients. Excellent for corporate dinners, team celebrations, and product launches.",
        "booking_url": "https://events.harbourview.example.com/enquire",
        "is_private_dining": False,
        "display_order": 1,
    },
    {
        "restaurant_slug": "harbour-view",
        "name": "The Captain's Table",
        "slug": "harbour-view-captains-table",
        "description": "Our most exclusive semi-private dining space — a suspended glass box extending over the water, seating up to 14 for the ultimate corporate or celebration dinner.",
        "room_type": "private_dining",
        "seated_capacity": 14,
        "standing_capacity": 14,
        "min_capacity": 6,
        "max_capacity": 14,
        "layouts": ["boardroom"],
        "amenities": [
            "360° harbour views",
            "Sommelier service",
            "Bespoke tasting menu available",
            "Frosted privacy glass",
        ],
        "asset_links": [
            {"type": "image", "label": "Captain's Table overview", "url": "https://assets.example.com/harbour-view/captains-table.jpg"},
        ],
        "room_hire_fee": 0.00,
        "minimum_spend_notes": "Minimum food and beverage spend of £2,000 per occasion.",
        "suitability_notes": "Best for high-stakes client entertainment, intimate milestone dinners, and VIP occasions.",
        "booking_url": "https://events.harbourview.example.com/enquire",
        "is_private_dining": True,
        "display_order": 2,
    },
    # ── The Garden Room ─────────────────────────────────────────────────────────
    {
        "restaurant_slug": "the-garden-room",
        "name": "The Walled Garden Room",
        "slug": "garden-room-main",
        "description": "The entire venue — a single exquisite private dining room surrounded by a Chelsea walled garden. Exclusive hire only, seating up to 40 guests.",
        "room_type": "private_dining",
        "seated_capacity": 40,
        "standing_capacity": 60,
        "min_capacity": 10,
        "max_capacity": 60,
        "layouts": ["banquet", "cabaret", "boardroom", "reception"],
        "amenities": [
            "Walled garden access",
            "Open fireplace",
            "Private kitchen and chef's table option",
            "Bespoke floral design available",
            "Dedicated event coordinator",
            "Garden terrace for pre-dinner drinks",
        ],
        "asset_links": [
            {"type": "image", "label": "Garden Room interior", "url": "https://assets.example.com/garden-room/interior.jpg"},
            {"type": "image", "label": "Walled garden terrace", "url": "https://assets.example.com/garden-room/terrace.jpg"},
        ],
        "room_hire_fee": 1500.00,
        "minimum_spend_notes": "Minimum food and beverage spend from £3,000.",
        "suitability_notes": "Sought after for intimate weddings, milestone birthdays, boardroom dinners, and exclusive celebrations. Whole-venue hire only.",
        "booking_url": "https://events.thegardenroom.example.com/enquire",
        "is_private_dining": True,
        "display_order": 1,
    },
    # ── City Brasserie ───────────────────────────────────────────────────────────
    {
        "restaurant_slug": "city-brasserie",
        "name": "The Exchange Room",
        "slug": "city-brasserie-exchange",
        "description": "A flexible private dining and events space in the heart of the City, accommodating up to 60 guests. Popular with financial sector clients for corporate lunches, team dinners, and client entertainment.",
        "room_type": "private_dining",
        "seated_capacity": 60,
        "standing_capacity": 80,
        "min_capacity": 12,
        "max_capacity": 80,
        "layouts": ["boardroom", "banquet", "cabaret", "theatre", "reception"],
        "amenities": [
            "Integrated AV and presentation screen",
            "Video conferencing capability",
            "Whiteboards",
            "Natural daylight with blackout blinds",
            "Private bar",
            "Dedicated service team",
        ],
        "asset_links": [
            {"type": "image", "label": "Exchange Room boardroom layout", "url": "https://assets.example.com/city-brasserie/exchange-boardroom.jpg"},
            {"type": "image", "label": "Exchange Room banquet layout", "url": "https://assets.example.com/city-brasserie/exchange-banquet.jpg"},
        ],
        "room_hire_fee": 0.00,
        "minimum_spend_notes": "Minimum food and beverage spend from £1,200 at lunch, £2,000 at dinner.",
        "suitability_notes": "Best suited to corporate lunches, team away days, client presentations, and post-deal celebration dinners.",
        "booking_url": "https://events.citybrasserie.example.com/enquire",
        "is_private_dining": True,
        "display_order": 1,
    },
    {
        "restaurant_slug": "city-brasserie",
        "name": "The Trading Floor",
        "slug": "city-brasserie-trading-floor",
        "description": "Full venue buyout for up to 200 standing guests. The main brasserie floor transforms into an exclusive reception or awards evening space.",
        "room_type": "event_space",
        "seated_capacity": 120,
        "standing_capacity": 200,
        "min_capacity": 80,
        "max_capacity": 200,
        "layouts": ["reception", "banquet", "theatre"],
        "amenities": [
            "Full bar service",
            "Stage and PA system",
            "High-profile City address",
            "Private street-level entrance",
            "Canapé and bowl food service",
        ],
        "asset_links": [
            {"type": "image", "label": "Trading Floor reception setup", "url": "https://assets.example.com/city-brasserie/trading-floor-reception.jpg"},
        ],
        "room_hire_fee": 2000.00,
        "minimum_spend_notes": "Minimum food and beverage spend of £8,000 for full venue hire.",
        "suitability_notes": "Ideal for City awards evenings, large corporate celebrations, drinks receptions, and company milestones.",
        "booking_url": "https://events.citybrasserie.example.com/enquire",
        "is_private_dining": False,
        "display_order": 2,
    },
]

SEED_PRICING_RULES: list[dict[str, Any]] = [
    # Per-restaurant pricing rules: (slug, name, day_of_week, meal_period, min_spend, min_covers)
    # day_of_week: None=all days, 0=Monday, 5=Saturday, 6=Sunday
    {"restaurant_slug": "the-grand-ballroom", "name": "Weekday Dinner", "day_of_week": None, "meal_period": "dinner", "minimum_spend": 5000.00, "minimum_covers": 50},
    {"restaurant_slug": "the-grand-ballroom", "name": "Weekend Dinner", "day_of_week": 5, "meal_period": "dinner", "minimum_spend": 8000.00, "minimum_covers": 50},
    {"restaurant_slug": "the-grand-ballroom", "name": "Sunday Dinner", "day_of_week": 6, "meal_period": "dinner", "minimum_spend": 8000.00, "minimum_covers": 50},
    {"restaurant_slug": "the-grand-ballroom", "name": "Lunch (All Days)", "day_of_week": None, "meal_period": "lunch", "minimum_spend": 3500.00, "minimum_covers": 40},
    {"restaurant_slug": "harbour-view", "name": "Weekday Lunch", "day_of_week": None, "meal_period": "lunch", "minimum_spend": 1500.00, "minimum_covers": 20},
    {"restaurant_slug": "harbour-view", "name": "Weekday Dinner", "day_of_week": None, "meal_period": "dinner", "minimum_spend": 2500.00, "minimum_covers": 20},
    {"restaurant_slug": "harbour-view", "name": "Weekend Dinner", "day_of_week": 5, "meal_period": "dinner", "minimum_spend": 4000.00, "minimum_covers": 20},
    {"restaurant_slug": "harbour-view", "name": "Sunday Dinner", "day_of_week": 6, "meal_period": "dinner", "minimum_spend": 4000.00, "minimum_covers": 20},
    {"restaurant_slug": "the-garden-room", "name": "Private Dinner (All Days)", "day_of_week": None, "meal_period": "dinner", "minimum_spend": 3000.00, "minimum_covers": 15},
    {"restaurant_slug": "the-garden-room", "name": "Private Lunch (All Days)", "day_of_week": None, "meal_period": "lunch", "minimum_spend": 2000.00, "minimum_covers": 15},
    {"restaurant_slug": "city-brasserie", "name": "Corporate Lunch", "day_of_week": None, "meal_period": "lunch", "minimum_spend": 1200.00, "minimum_covers": 12},
    {"restaurant_slug": "city-brasserie", "name": "Corporate Dinner", "day_of_week": None, "meal_period": "dinner", "minimum_spend": 2000.00, "minimum_covers": 12},
    {"restaurant_slug": "city-brasserie", "name": "Friday Dinner", "day_of_week": 4, "meal_period": "dinner", "minimum_spend": 3000.00, "minimum_covers": 12},
]

ENQUIRY_STATUSES = ["new", "open", "proposal_sent", "follow_up", "confirmed", "cancelled", "lost"]
ENQUIRY_SOURCES = ["webform", "email", "manual"]
EVENT_TYPES = ["birthday", "corporate", "wedding", "private_dining", "anniversary", "christmas_party", "leaving_do", "other"]
MEAL_PERIODS = ["breakfast", "lunch", "dinner"]
DEMAND_LEVELS = ["low", "medium", "high", "very_high"]

# High-demand dates for 2025–2026 (approximate UK)
HIGH_DEMAND_MONTHS = {12, 1}  # December, January
HIGH_DEMAND_DOW = {4, 5, 6}   # Friday, Saturday, Sunday (0=Mon)


# ── Seed functions ────────────────────────────────────────────────────────────


def _upsert_restaurant(db: Session, data: dict[str, Any]) -> Any:
    """Insert restaurant if slug does not exist; return the record."""
    from app.modules.restaurants.models import Restaurant

    existing = db.query(Restaurant).filter_by(slug=data["slug"]).first()
    if existing:
        return existing
    record = Restaurant(
        id=uuid.uuid4(),
        tenant_id="default",
        **data,
        is_active=True,
    )
    db.add(record)
    db.flush()
    return record


def _upsert_persona(db: Session, data: dict[str, Any]) -> Any:
    """Insert persona if slug does not exist; return the record."""
    from app.modules.personas.models import Persona

    existing = db.query(Persona).filter_by(slug=data["slug"]).first()
    if existing:
        return existing
    record = Persona(id=uuid.uuid4(), **data, is_active=True)
    db.add(record)
    db.flush()
    return record


def _upsert_restaurant_persona(
    db: Session,
    restaurant_id: uuid.UUID,
    persona_id: uuid.UUID,
    is_default: bool,
    audience: str | None = None,
) -> None:
    """Assign a persona to a restaurant if not already assigned for the same audience slot."""
    from app.modules.personas.models import RestaurantPersona

    existing = (
        db.query(RestaurantPersona)
        .filter_by(restaurant_id=restaurant_id, persona_id=persona_id, audience=audience)
        .first()
    )
    if existing:
        return
    db.add(
        RestaurantPersona(
            id=uuid.uuid4(),
            restaurant_id=restaurant_id,
            persona_id=persona_id,
            is_default=is_default,
            audience=audience,
        )
    )
    db.flush()


def _upsert_room(db: Session, restaurant_id: uuid.UUID, data: dict[str, Any]) -> Any:
    """Insert a room if no room with the same slug exists for this restaurant."""
    from app.modules.restaurants.models import Room

    existing = (
        db.query(Room)
        .filter_by(restaurant_id=restaurant_id, slug=data["slug"])
        .first()
    )
    if existing:
        return existing
    room = Room(
        id=uuid.uuid4(),
        tenant_id="default",
        restaurant_id=restaurant_id,
        name=data["name"],
        slug=data["slug"],
        description=data.get("description"),
        room_type=data.get("room_type"),
        seated_capacity=data.get("seated_capacity"),
        standing_capacity=data.get("standing_capacity"),
        min_capacity=data.get("min_capacity"),
        max_capacity=data.get("max_capacity"),
        layouts=data.get("layouts"),
        amenities=data.get("amenities"),
        asset_links=data.get("asset_links"),
        room_hire_fee=data.get("room_hire_fee"),
        minimum_spend_notes=data.get("minimum_spend_notes"),
        suitability_notes=data.get("suitability_notes"),
        booking_url=data.get("booking_url"),
        is_private_dining=data.get("is_private_dining", False),
        is_active=True,
        display_order=data.get("display_order", 0),
    )
    db.add(room)
    db.flush()
    return room


def _upsert_pricing_rule(db: Session, restaurant_id: uuid.UUID, data: dict[str, Any]) -> None:
    """Insert pricing rule if no matching rule exists for this restaurant + name."""
    from app.modules.pricing.models import PricingRule

    existing = (
        db.query(PricingRule)
        .filter_by(restaurant_id=restaurant_id, name=data["name"])
        .first()
    )
    if existing:
        return
    db.add(
        PricingRule(
            id=uuid.uuid4(),
            restaurant_id=restaurant_id,
            name=data["name"],
            day_of_week=data["day_of_week"],
            meal_period=data["meal_period"],
            minimum_spend=data["minimum_spend"],
            minimum_covers=data.get("minimum_covers"),
            is_active=True,
        )
    )
    db.flush()


_AVAILABILITY_STATUSES = ["available", "available", "available", "available", "available", "available",
                          "booked", "booked", "booked", "booked", "booked",
                          "held", "held",
                          "unavailable"]
# Distribution: 6/14 ≈ 43% available base, but we skew by dow below.
# Actual target: ~60% available, ~25% booked, ~10% held, ~5% unavailable
# Achieved by the weighted list: available=6, booked=5, held=2, unavailable=1 → 43/36/14/7%
# On weekdays we additionally shift toward available; on weekends toward booked/held.
_AVAIL_WEEKDAY = ["available"] * 9 + ["booked"] * 3 + ["held"] * 2 + ["unavailable"] * 1  # ~60/20/13/7
_AVAIL_WEEKEND = ["available"] * 4 + ["booked"] * 6 + ["held"] * 3 + ["unavailable"] * 1  # ~29/43/21/7


def _avail_status_for(room_id: uuid.UUID, d: date, meal_period: str) -> str:
    """Return a deterministic availability status for a (room, date, meal_period) slot.

    Uses a hash of the three keys so the distribution is stable across re-seeds.
    Weekends (Sat/Sun) skew toward booked/held to reflect realistic demand.
    """
    key = f"{room_id}:{d.isoformat()}:{meal_period}".encode()
    digest = hashlib.sha256(key).digest()
    # Use first two bytes for index selection
    idx = int.from_bytes(digest[:2], "big")
    if d.weekday() in (5, 6):  # Saturday, Sunday
        return _AVAIL_WEEKEND[idx % len(_AVAIL_WEEKEND)]
    return _AVAIL_WEEKDAY[idx % len(_AVAIL_WEEKDAY)]


def _seed_room_availability(db: Session, rooms: list[Any]) -> None:
    """Seed room_availability for all rooms for the next 12 months.

    Idempotent: skips rooms that already have any availability rows.
    Deterministic: status is derived from a hash, not random.
    """
    from app.modules.restaurants.models import RoomAvailability

    today = date.today()
    end = today + timedelta(days=365)
    meal_periods = ["lunch", "dinner"]

    for room in rooms:
        existing = db.query(RoomAvailability).filter_by(room_id=room.id).limit(1).first()
        if existing:
            continue

        records: list[RoomAvailability] = []
        current = today
        while current <= end:
            for meal_period in meal_periods:
                status = _avail_status_for(room.id, current, meal_period)
                records.append(
                    RoomAvailability(
                        id=uuid.uuid4(),
                        tenant_id="default",
                        room_id=room.id,
                        date=current,
                        meal_period=meal_period,
                        status=status,
                        notes=None,
                    )
                )
            current += timedelta(days=1)

        db.bulk_save_objects(records)
        db.flush()


def _seed_demand_events(db: Session, restaurant_id: uuid.UUID, rng: random.Random) -> None:
    """Create one year of fake demand events for a restaurant.

    Checks for any existing demand events to avoid re-seeding.
    """
    from app.modules.insights.models import DemandEvent

    existing_count = db.query(DemandEvent).filter_by(restaurant_id=restaurant_id).count()
    if existing_count > 0:
        return

    today = date.today()
    start = today.replace(month=1, day=1)
    end = start.replace(year=start.year + 1)

    records: list[DemandEvent] = []
    current = start
    while current < end:
        dow = current.weekday()
        month = current.month

        for meal_period in MEAL_PERIODS:
            # Base demand from day-of-week
            if dow in HIGH_DEMAND_DOW:
                base_score = rng.uniform(0.6, 1.0)
            elif dow == 3:  # Thursday
                base_score = rng.uniform(0.4, 0.7)
            else:
                base_score = rng.uniform(0.1, 0.5)

            # Boost for high-demand months
            if month in HIGH_DEMAND_MONTHS:
                base_score = min(1.0, base_score * 1.3)

            # Derive demand level from score
            if base_score >= 0.85:
                level = "very_high"
            elif base_score >= 0.6:
                level = "high"
            elif base_score >= 0.3:
                level = "medium"
            else:
                level = "low"

            records.append(
                DemandEvent(
                    id=uuid.uuid4(),
                    restaurant_id=restaurant_id,
                    event_date=current,
                    meal_period=meal_period,
                    demand_level=level,
                    demand_score=round(base_score, 3),
                    source="seeded",
                )
            )

        current += timedelta(days=1)

    db.bulk_save_objects(records)
    db.flush()


def _seed_policy_faqs(db: Session, restaurants: list[Any]) -> None:
    """Seed 20 policy FAQ defaults for each restaurant (DATA-021).

    All FAQs are idempotent: existing rows for the same restaurant+question_key
    are skipped.
    """
    from sqlalchemy import select
    from app.modules.restaurants.models import RestaurantPolicyFAQ

    # POC defaults — 20 supported question types
    POLICY_DEFAULTS = [
        {"question_key": "cake_allowed",              "answer_policy": "allowed",           "answer_text": "Yes, you are welcome to bring your own celebration cake."},
        {"question_key": "candles_allowed",           "answer_policy": "allowed",           "answer_text": "Birthday candles are permitted."},
        {"question_key": "decorations_allowed",       "answer_policy": "approval_required", "answer_text": None},
        {"question_key": "balloons_allowed",          "answer_policy": "approval_required", "answer_text": None},
        {"question_key": "flowers_allowed",           "answer_policy": "allowed",           "answer_text": "Floral arrangements are welcome."},
        {"question_key": "external_performer_allowed","answer_policy": "approval_required", "answer_text": None},
        {"question_key": "live_music_allowed",        "answer_policy": "approval_required", "answer_text": None},
        {"question_key": "dj_allowed",                "answer_policy": "approval_required", "answer_text": None},
        {"question_key": "microphone_available",      "answer_policy": "information_only",  "answer_text": "A handheld microphone is available upon request."},
        {"question_key": "screen_available",          "answer_policy": "information_only",  "answer_text": "A presentation screen and HDMI connection are available."},
        {"question_key": "av_available",              "answer_policy": "information_only",  "answer_text": "AV equipment including screen, microphone, and HDMI is available."},
        {"question_key": "private_room_available",    "answer_policy": "information_only",  "answer_text": "Private dining rooms are available — capacity depends on the room selected."},
        {"question_key": "room_capacity",             "answer_policy": "information_only",  "answer_text": "Room capacity varies; please confirm your guest count for a suitable recommendation."},
        {"question_key": "disabled_access",           "answer_policy": "information_only",  "answer_text": "The venue has step-free access and accessible facilities."},
        {"question_key": "children_allowed",          "answer_policy": "allowed",           "answer_text": "Children are welcome at our venue."},
        {"question_key": "pets_allowed",              "answer_policy": "not_allowed",       "answer_text": "Unfortunately, we are unable to accommodate pets."},
        {"question_key": "minimum_spend",             "answer_policy": "information_only",  "answer_text": "Minimum spend requirements vary by room and time; our events team will advise."},
        {"question_key": "room_hire",                 "answer_policy": "information_only",  "answer_text": "Room hire fees may apply depending on the event and day of week."},
        {"question_key": "service_charge",            "answer_policy": "information_only",  "answer_text": "A discretionary service charge of 12.5% is added to the final bill."},
        {"question_key": "agency_commission",         "answer_policy": "approval_required", "answer_text": None},
    ]

    for restaurant in restaurants:
        for policy in POLICY_DEFAULTS:
            # Idempotent: skip if already exists
            existing = db.scalars(
                select(RestaurantPolicyFAQ)
                .where(RestaurantPolicyFAQ.restaurant_id == restaurant.id)
                .where(RestaurantPolicyFAQ.question_key == policy["question_key"])
            ).first()
            if existing:
                continue
            faq = RestaurantPolicyFAQ(
                id=uuid.uuid4(),
                tenant_id=getattr(restaurant, "tenant_id", "default"),
                restaurant_id=restaurant.id,
                question_key=policy["question_key"],
                answer_policy=policy["answer_policy"],
                answer_text=policy["answer_text"],
                requires_human_review=policy["answer_policy"] == "approval_required",
                is_active=True,
            )
            db.add(faq)


def _seed_enquiries(
    db: Session,
    restaurants: list[Any],
    personas: list[Any],
    rng: random.Random,
) -> None:
    """Create fake enquiries across all statuses for each restaurant."""
    from app.modules.enquiries.models import Enquiry, EnquiryMessage

    today = date.today()

    first_names = ["Alice", "Ben", "Charlotte", "David", "Emma", "Finn", "Grace", "Harry", "Isabelle", "Jack"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Davis", "Miller", "Wilson", "Taylor", "Anderson"]
    domains = ["gmail.com", "outlook.com", "hotmail.co.uk", "company.co.uk", "corporate.com"]

    enquiry_count = 0
    for restaurant in restaurants:
        for status in ENQUIRY_STATUSES:
            # Create 2–3 enquiries per restaurant per status
            for _ in range(rng.randint(2, 3)):
                enquiry_count += 1
                ref = f"ENQ-{today.year}-{enquiry_count:04d}"

                # Check idempotency
                existing = db.query(Enquiry).filter_by(reference=ref).first()
                if existing:
                    continue

                first = rng.choice(first_names)
                last = rng.choice(last_names)
                email_addr = f"{first.lower()}.{last.lower()}@{rng.choice(domains)}"
                event_offset = rng.randint(14, 365)
                persona = rng.choice(personas)

                enquiry = Enquiry(
                    id=uuid.uuid4(),
                    restaurant_id=restaurant.id,
                    persona_id=persona.id,
                    reference=ref,
                    status=status,
                    source=rng.choice(ENQUIRY_SOURCES),
                    first_name=first,
                    last_name=last,
                    email=email_addr,
                    phone=f"+44 7{rng.randint(700, 999)} {rng.randint(100000, 999999)}",
                    party_size=rng.choice([8, 12, 20, 30, 50, 80, 120]),
                    event_date=today + timedelta(days=event_offset),
                    event_type=rng.choice(EVENT_TYPES),
                    notes=f"Interested in the {rng.choice(MEAL_PERIODS)} session.",
                    metadata_={},
                )
                db.add(enquiry)
                db.flush()

                # Add an initial inbound message
                db.add(
                    EnquiryMessage(
                        id=uuid.uuid4(),
                        enquiry_id=enquiry.id,
                        direction="inbound",
                        channel="webform",
                        subject=f"Event enquiry for {restaurant.name}",
                        body=f"Hi, I am interested in booking an event for {enquiry.party_size} guests. Please let me know about availability.",
                        sent_at=datetime.now(tz=timezone.utc),
                    )
                )

                # Add an outbound reply if status is past 'new'
                if status not in ("new",):
                    db.add(
                        EnquiryMessage(
                            id=uuid.uuid4(),
                            enquiry_id=enquiry.id,
                            direction="outbound",
                            channel="email",
                            subject=f"Re: Event enquiry for {restaurant.name}",
                            body=f"Dear {first}, thank you for your enquiry. We would be delighted to host your event. I will be in touch shortly with availability and pricing.",
                            sent_at=datetime.now(tz=timezone.utc),
                        )
                    )

                db.flush()


# ── Main seed runner ──────────────────────────────────────────────────────────


def run_seed(db: Session, seed: int = 42) -> dict[str, int]:
    """Seed the database with POC fake data.

    Args:
        db: SQLAlchemy session (caller is responsible for commit/rollback).
        seed: Random seed for deterministic output.

    Returns:
        Summary counts of records created or found.
    """
    rng = random.Random(seed)

    # 1. Restaurants
    restaurants = [_upsert_restaurant(db, data) for data in SEED_RESTAURANTS]

    # 2. Personas
    personas = [_upsert_persona(db, data) for data in SEED_PERSONAS]

    # 3. Restaurant-persona assignments
    # Audience mapping: Eleanor=social, James=corporate, Sophia=agency
    # personas list order: [Eleanor(0), James(1), Sophia(2)]
    # Each restaurant gets:
    #   - A default persona (round-robin, no audience — fallback)
    #   - An explicit social persona (Eleanor)
    #   - An explicit corporate persona (James)
    #   - An explicit agency persona (Sophia)
    eleanor = personas[0]  # social
    james = personas[1]    # corporate
    sophia = personas[2]   # agency

    for i, restaurant in enumerate(restaurants):
        default_persona = personas[i % len(personas)]
        _upsert_restaurant_persona(db, restaurant.id, default_persona.id, is_default=True, audience=None)
        _upsert_restaurant_persona(db, restaurant.id, eleanor.id, is_default=False, audience="social")
        _upsert_restaurant_persona(db, restaurant.id, james.id, is_default=False, audience="corporate")
        _upsert_restaurant_persona(db, restaurant.id, sophia.id, is_default=False, audience="agency")

    # 4. Rooms/PDRs
    restaurant_by_slug = {r.slug: r for r in restaurants}
    all_rooms = []
    for room_data in SEED_ROOMS:
        restaurant = restaurant_by_slug.get(room_data["restaurant_slug"])
        if restaurant:
            room_payload = {k: v for k, v in room_data.items() if k != "restaurant_slug"}
            room = _upsert_room(db, restaurant.id, room_payload)
            all_rooms.append(room)

    # 4b. Room availability (12 months, deterministic)
    _seed_room_availability(db, all_rooms)

    # 5. Pricing rules
    for rule in SEED_PRICING_RULES:
        restaurant = restaurant_by_slug.get(rule["restaurant_slug"])
        if restaurant:
            _upsert_pricing_rule(db, restaurant.id, rule)

    # 6. Demand events (one year per restaurant)
    for restaurant in restaurants:
        _seed_demand_events(db, restaurant.id, rng)

    # 7. Enquiries
    _seed_enquiries(db, restaurants, personas, rng)

    # 8. Policy FAQs (DATA-021) — 20 question types per restaurant
    _seed_policy_faqs(db, restaurants)

    db.commit()

    # Return summary for logging
    from app.modules.restaurants.models import (
        Restaurant,
        Room,
        RoomAvailability,
        RestaurantPolicyFAQ,
    )
    from app.modules.personas.models import Persona, RestaurantPersona
    from app.modules.pricing.models import PricingRule
    from app.modules.enquiries.models import Enquiry, EnquiryMessage
    from app.modules.insights.models import DemandEvent

    return {
        "restaurants": db.query(Restaurant).count(),
        "rooms": db.query(Room).count(),
        "room_availability": db.query(RoomAvailability).count(),
        "personas": db.query(Persona).count(),
        "restaurant_personas": db.query(RestaurantPersona).count(),
        "pricing_rules": db.query(PricingRule).count(),
        "demand_events": db.query(DemandEvent).count(),
        "enquiries": db.query(Enquiry).count(),
        "enquiry_messages": db.query(EnquiryMessage).count(),
        "restaurant_policy_faqs": db.query(RestaurantPolicyFAQ).count(),
    }
