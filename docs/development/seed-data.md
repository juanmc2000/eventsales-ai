# Seed Data

EventSales AI uses a deterministic seed data framework to populate local development databases with realistic POC fake data.

All seed data is fake — no real customer or restaurant data is used.

---

## Prerequisites

- PostgreSQL running (`docker-compose up -d`)
- Alembic migrations applied (`alembic upgrade head`)
- Python virtual environment active: `source .venv-eventsales-ai/bin/activate`

---

## Run Seed

```bash
cd services/api
python scripts/seed.py
```

Or from the project root:

```bash
PYTHONPATH=services/api python services/api/scripts/seed.py
```

Expected output:

```
EventSales AI — POC seed data
========================================
Seed complete. Record counts:
  restaurants: 4
  personas: 3
  restaurant_personas: 8
  pricing_rules: 13
  demand_events: ~4380
  enquiries: ~56
  enquiry_messages: ~112
```

---

## What is seeded

### Restaurants (4)

| Name | Slug |
|------|------|
| The Grand Ballroom | `the-grand-ballroom` |
| Harbour View | `harbour-view` |
| The Garden Room | `the-garden-room` |
| City Brasserie | `city-brasserie` |

All restaurant email addresses use `.example.com` domains to prevent accidental delivery.

### Personas (3)

| Name | Tone |
|------|------|
| Eleanor | warm and formal |
| James | professional and direct |
| Sophia | enthusiastic and creative |

Each restaurant is assigned a default persona and a secondary persona.

### Pricing Rules

13 deterministic rules spread across the 4 restaurants — covering meal period (breakfast/lunch/dinner), day of week (weekday/weekend), and minimum spend.  No ML pricing.

### Demand Events

One year of daily demand events (breakfast, lunch, dinner) for each restaurant.  Demand levels (low/medium/high/very_high) are derived from day-of-week and month using a deterministic random seed (`seed=42`).

Higher demand is seeded for:
- Fridays, Saturdays, Sundays
- December and January

### Enquiries

Fake enquiries are created for each restaurant across all 7 status values:
`new`, `open`, `proposal_sent`, `follow_up`, `confirmed`, `cancelled`, `lost`

Each enquiry includes at least one inbound message; enquiries past `new` status include an outbound reply.

---

## Idempotency

The seed script is safe to rerun.  Each seed function checks for an existing record (by slug or reference) before inserting.

- Restaurants are matched by `slug`
- Personas are matched by `slug`
- Pricing rules are matched by `restaurant_id + name`
- Demand events are skipped if any events already exist for a restaurant
- Enquiries are matched by `reference`

---

## Customising seed data

Seed constants are defined in:

```
services/api/app/modules/shared/seed_data.py
```

Edit `SEED_RESTAURANTS`, `SEED_PERSONAS`, or `SEED_PRICING_RULES` to change the base data.

To change the random seed (and therefore demand levels and enquiry details), pass a different `seed` value to `run_seed()`.

---

## POC Constraints

- No real customer data
- No real restaurant data
- No production email addresses
- All `.example.com` domains
- Seed command is for local development only
