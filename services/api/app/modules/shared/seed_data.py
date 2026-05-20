"""POC seed data framework.

Generates deterministic fake data for local development.
All data is fake — no real customer or restaurant data.

Usage via script:
    cd services/api
    python scripts/seed.py

All seed functions are idempotent: re-running them will not create duplicates.
"""

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


def _upsert_restaurant_persona(db: Session, restaurant_id: uuid.UUID, persona_id: uuid.UUID, is_default: bool) -> None:
    """Assign a persona to a restaurant if not already assigned."""
    from app.modules.personas.models import RestaurantPersona

    existing = (
        db.query(RestaurantPersona)
        .filter_by(restaurant_id=restaurant_id, persona_id=persona_id)
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
        )
    )
    db.flush()


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

    # 3. Restaurant-persona assignments (round-robin: each restaurant gets one default persona)
    for i, restaurant in enumerate(restaurants):
        default_persona = personas[i % len(personas)]
        _upsert_restaurant_persona(db, restaurant.id, default_persona.id, is_default=True)
        # Assign a second non-default persona for variety
        second_persona = personas[(i + 1) % len(personas)]
        _upsert_restaurant_persona(db, restaurant.id, second_persona.id, is_default=False)

    # 4. Pricing rules
    restaurant_by_slug = {r.slug: r for r in restaurants}
    for rule in SEED_PRICING_RULES:
        restaurant = restaurant_by_slug.get(rule["restaurant_slug"])
        if restaurant:
            _upsert_pricing_rule(db, restaurant.id, rule)

    # 5. Demand events (one year per restaurant)
    for restaurant in restaurants:
        _seed_demand_events(db, restaurant.id, rng)

    # 6. Enquiries
    _seed_enquiries(db, restaurants, personas, rng)

    db.commit()

    # Return summary for logging
    from app.modules.restaurants.models import Restaurant
    from app.modules.personas.models import Persona, RestaurantPersona
    from app.modules.pricing.models import PricingRule
    from app.modules.enquiries.models import Enquiry, EnquiryMessage
    from app.modules.insights.models import DemandEvent

    return {
        "restaurants": db.query(Restaurant).count(),
        "personas": db.query(Persona).count(),
        "restaurant_personas": db.query(RestaurantPersona).count(),
        "pricing_rules": db.query(PricingRule).count(),
        "demand_events": db.query(DemandEvent).count(),
        "enquiries": db.query(Enquiry).count(),
        "enquiry_messages": db.query(EnquiryMessage).count(),
    }
