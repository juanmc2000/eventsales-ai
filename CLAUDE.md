# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

This project is currently in the **POC (Proof of Concept) phase**. The repository contains documentation, design specs, and scaffolding only — no application code has been written yet. The task is to build out the POC according to the specifications in `docs/product/POC_SPECIFICATION.md`.

## Intended Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy, Alembic
- **Database:** PostgreSQL (source of truth), Redis (broker/cache)
- **Background Jobs:** Celery + Redis
- **Frontend:** React / Next.js
- **Email (POC):** Gmail SMTP for sending, IMAP for reading
- **Local services:** Docker Compose
- **Python venv:** `.venv-eventsales-ai` (Python 3.11)

## Commands

Once the application is scaffolded, the expected commands are:

```bash
# Activate virtual environment
source .venv-eventsales-ai/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start all local services (PostgreSQL, Redis)
docker-compose up -d

# Run database migrations
alembic upgrade head

# Run backend dev server
uvicorn backend.app.main:app --reload

# Run Celery worker
celery -A backend.app.celery_app worker --loglevel=info

# Run frontend dev server (from frontend/)
npm run dev

# Run tests
pytest
pytest tests/path/to/test_file.py::test_name  # single test
```

## Architecture

### Modular Monolith (not microservices)

The backend is a **modular monolith** — all modules live in one deployable FastAPI application. Do not split into separate services.

Backend module structure:
```
backend/app/modules/auth/
backend/app/modules/restaurants/
backend/app/modules/personas/
backend/app/modules/pricing/
backend/app/modules/enquiries/
backend/app/modules/email/
backend/app/modules/calendar/
backend/app/modules/insights/
backend/app/modules/dashboard/
```

### Multi-Tenancy

The system is multi-tenant (one tenant = one hospitality group). All data models must be tenant-aware. Middleware enforces tenant isolation at the request level.

### Background Jobs

Celery + Redis handles all async work: sending emails, reading the inbox, processing inbound emails into enquiries, and refreshing metrics. PostgreSQL remains the source of truth — Redis is only the broker and cache.

### POC Database Tables (minimum)

`restaurants`, `personas`, `restaurant_personas`, `pricing_rules`, `enquiries`, `enquiry_messages`, `email_events`, `calendar_events`, `demand_events`, `insight_snapshots`

Optional: `rooms`, `users`, `audit_logs`, `background_jobs`

### POC Build Order

1. Repo structure, FastAPI backend, PostgreSQL, Redis, Celery, frontend scaffold, env config, seed script framework
2. Seed data: 4 test restaurants, 3 personas, pricing rules, 1 year of fake demand events + enquiries
3. Core pages: Dashboard, Pricing Rules, Personas, Calendar, Insights
4. Test enquiry webform
5. Gmail SMTP email sending + IMAP inbox reading

## UI/UX Design System

**Before building any UI page, read all files in `design/docs/` and check the corresponding image in `design/reference_images/`.**

### Non-negotiable shell (every client-facing page)
- Fixed **dark left sidebar** (`--nav-bg: #070A1F`) + **dark topbar** (`--topbar-bg: #080B24`)
- **Light main workspace** (`--page-bg: #F8F7FC`) with white rounded cards
- Accent colours: purple → pink → orange → teal (in that sequence for KPI cards)

### Colour tokens
Defined in `design/docs/UI_DESIGN_SYSTEM.md`. Never invent new brand colours — map to existing tokens.

### Admin pages
Admin pages (Environments, Users, Audit Logs, etc.) use a **darker, more utilitarian shell** — no venue imagery, no colourful KPI storytelling.

### Sidebar navigation taxonomy
- **Main:** Home, Enquiries, Calendar, Proposals, Deposits/Bookings
- **Configuration:** Restaurants, Rooms, Pricing Rules, Personas, Workflows
- **Insights:** Dashboard, Reports, Performance
- **Admin-only:** Environments, Integrations, Users, Roles, Audit Logs, System Health, Deployment

Do not invent new navigation items.

### AI suggestion cards
Always include recommendation + rationale + confidence indicator. Never show AI recommendations without rationale.

### Page consistency checklist (before completing any page)
Verify: sidebar and topbar match shell rules, approved tokens used, cards have consistent radius/shadow, typography matches design system, status pills match approved language, forms and tables follow component rules, AI suggestions include rationale.

## Key Reference Documents

| Document | Purpose |
|---|---|
| `docs/product/POC_SPECIFICATION.md` | Full POC scope, pages, seed data, integrations, build order |
| `docs/product/ENGINEERING_SPECIFICATION.md` | MVP-level engineering specs for all 8 modules |
| `docs/product/PRODUCT_REQUIREMENT_DOCUMENT.md` | Product vision and business outcomes |
| `design/docs/UI_DESIGN_SYSTEM.md` | Colour tokens, typography, layout rules |
| `design/docs/UI_COMPONENT_RULES.md` | Component rules (sidebar, topbar, tables, forms, KPI cards, etc.) |
| `design/docs/UI_PAGE_BRIEFS.md` | Per-page required content |
| `design/docs/AI_DRIFT_GUARDRAILS.md` | Absolute rules to prevent UI drift |
| `design/docs/REFERENCE_IMAGES.md` | Reference image index |
| `design/reference_images/` | Visual mockups — check the matching image before building each page |

## POC Guardrails

- No ML pricing — pricing rules are deterministic only
- No production email sending — Gmail SMTP test accounts only
- No third-party CRM integrations (Salesforce, TripleSeat, Cvent, etc.)
- No production authentication hardening required
- No premature microservices
- Use fake/seeded data only — no real customer or restaurant data
- Preserve the intended future architecture in all implementation decisions
