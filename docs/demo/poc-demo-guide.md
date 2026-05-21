# POC Demo and Validation Guide

**EventSales AI — Sprint 5C**
**Status:** POC (Proof of Concept) — not production-ready
**Date:** 2026-05-21

---

## Important Constraints

> **This is a POC.** All emails use a test Gmail account only — no real guest or restaurant data is sent. Draft generation uses a deterministic fallback when no Anthropic API key is present. The system is demonstrating commercial hospitality operating infrastructure, not a production product.

- Gmail SMTP/IMAP: test account only (`SMTP_USERNAME` / `IMAP_USERNAME` env vars required)
- AI drafts: FallbackProvider (deterministic) unless `ANTHROPIC_API_KEY` is set
- All seed data uses `.example.com` email domains — safe to demo
- No real customer or restaurant data at any point

---

## 1. Local Setup Checklist

### Prerequisites

- [ ] Docker and Docker Compose installed
- [ ] Python 3.11 with virtual environment at `.venv-eventsales-ai`
- [ ] Node.js 18+ and npm installed

### Environment

```bash
# Copy and configure environment
cp services/api/.env.example services/api/.env
cp services/workers/.env.example services/workers/.env
cp services/web/.env.local.example services/web/.env.local
```

Required `.env` values for full demo:
| Variable | Required For | Notes |
|---|---|---|
| `DATABASE_URL` | Everything | PostgreSQL connection string |
| `REDIS_URL` | Background jobs | Redis connection string |
| `SMTP_USERNAME` | Gmail send | Gmail address |
| `SMTP_PASSWORD` | Gmail send | Gmail App Password (16-char) |
| `IMAP_USERNAME` | Gmail inbox | Same Gmail address |
| `IMAP_PASSWORD` | Gmail inbox | Same Gmail App Password |
| `ANTHROPIC_API_KEY` | LLM drafts | Optional — fallback works without it |
| `NEXT_PUBLIC_API_URL` | Frontend | `http://localhost:8000` |

### Start Services

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Activate Python environment
source .venv-eventsales-ai/bin/activate

# Run database migrations
cd services/api
alembic upgrade head

# Seed demo data (4 restaurants, 3 personas, pricing rules, demand events)
python scripts/seed.py

# Start API server (terminal 1)
uvicorn app.main:app --reload --port 8000

# Start Celery worker (terminal 2)
celery -A workers.celery_app worker --loglevel=info -Q email

# Start frontend (terminal 3)
cd services/web
npm install
npm run dev
```

Frontend: http://localhost:3000
API docs: http://localhost:8000/docs

---

## 2. Seed Data Reset Instructions

Reset to a clean demo state at any point:

```bash
source .venv-eventsales-ai/bin/activate
cd services/api

# Drop all tables and re-run migrations
alembic downgrade base
alembic upgrade head

# Re-seed
python scripts/seed.py
```

This restores: 4 restaurants, 7 rooms/PDRs (across all venues), 3 personas, ~20 pricing rules, 1 year of demand events, and a set of sample enquiries in various statuses.

---

## 3. Venue Context Model

Sprint 5C introduced a two-level venue model. Understanding this hierarchy is important for the demo.

### Restaurants (venue containers)
Restaurants are the top-level venue record. Each restaurant has:
- Name, address, contact details
- One or more assigned personas (AI response personas) — personas are always **restaurant-level**, not room-level
- Pricing rules per event type and meal period
- A summary of their rooms visible on the restaurant detail page

Navigate to `/restaurants` to see the restaurants list. Clicking a restaurant opens the detail drawer, which includes the **Room Summary** section showing how many rooms are configured and a brief per-room overview.

### Rooms and PDRs (child records)
Rooms and Private Dining Rooms (PDRs) are child records of a restaurant. Each room has:
- Capacity (seated, standing, min, max)
- Room type (ballroom, private_dining, suite, etc.)
- Layouts, amenities, hire fee, suitability notes
- PDR flag (`is_private_dining`) — PDR rooms display a "PDR" badge in the UI

Navigate to `/rooms` (the **Rooms & PDRs** page) to see all rooms across all venues. You can filter by restaurant, add new rooms, edit details, and deactivate rooms.

**Talking point:** "Restaurants configure who handles enquiries (persona) and how they're priced (pricing rules). Rooms are the physical spaces — their capacity and features feed directly into the AI draft to give guests accurate context."

---

## 4. Webform Demo Flow (updated with room selection)

**What this shows:** A prospective guest submitting a private dining enquiry via the restaurant-facing webform, optionally selecting their preferred room.

1. Navigate to http://localhost:3000/webform
2. Select a restaurant from the dropdown (e.g., "The Grand Brasserie")
   - **Observe:** The "Preferred Room or Area" field immediately updates to a dropdown populated with that venue's active rooms
3. Fill in guest details:
   - First name: Alice, Last name: Smith
   - Email: alice@example.com
   - Event type: Birthday
   - Date: any future date
   - Party size: 20
4. In the **Preferred Room or Area** dropdown, select a specific room (e.g., "The Garden Room (PDR)")
5. Add a message: "Looking for an intimate private dining room for a birthday dinner."
6. Consent checkbox → Submit
7. Observe: confirmation message with enquiry reference (e.g., `ENQ-2026-0001`)

**Room selection is optional:** The form submits successfully with "No specific room" selected. The preferred area field is preserved as a plain text input if the venue has no rooms configured.

**What happens behind the scenes:**
- `POST /api/v1/enquiries/intake` creates the enquiry with `preferred_area` set to the room name
- `EnquiryIntakeService` attaches the default persona and pricing rule
- Draft generation uses `preferred_area` to match the room and include its capacity/amenities in the draft context
- Status is set to `new`

**Talking point:** "The webform loads rooms live from the backend when a venue is selected. The selected room name becomes the `preferred_area` on the enquiry, which the AI uses to personalise the draft response."

---

## 5. Enquiry Detail Demo Flow

**What this shows:** The operations team's view of a live enquiry.

1. Navigate to http://localhost:3000/enquiries
2. Click any enquiry row to open the detail drawer
3. Show: guest details, event date, party size, recommended minimum spend
4. Show: the **Preferred Room / Area** field in the Customer & Event section — if the guest selected a room during webform submission, it appears here
5. Show: message thread (inbound initial message visible)
6. Change status using the dropdown (e.g., `new` → `open`)
7. Observe: status pill updates immediately

**Talking point:** "The enquiry list gives the events team a single view of every lead — status, source, date, spend recommendation. The preferred room is captured at intake and is visible in the drawer so the operator knows exactly which space the guest has in mind."

---

## 6. Draft Generation Demo Flow (updated with room context)

**What this shows:** AI-assisted draft email generation that uses room/PDR context from the enquiry.

1. Open an enquiry that was submitted with a preferred room (or any enquiry via the webform)
2. Scroll to the **Draft Response** section
3. Click **Generate Draft**
4. Observe: a personalised draft appears with:
   - Subject referencing the restaurant name
   - Guest name in the salutation
   - Party size, event date, and minimum spend if available
   - **Room/PDR context** — if the enquiry has a `preferred_area` that matches a configured room, the draft will reference that room by name and note its capacity and suitability
   - Persona signature

**How room context works:**
The draft generation engine queries the venue's active rooms and applies a simple matching algorithm:
1. If `preferred_area` text matches a room name (case-insensitive), that room is used
2. If not, the first room whose capacity range covers the party size is used
3. If no room matches, draft generation proceeds without room context (graceful degradation)

The engine **never invents** room details — it only uses data from the configured rooms.

**With Anthropic API key configured:**
The draft is generated by Claude and will weave room context naturally into the response.

**Without Anthropic API key (FallbackProvider):**
A deterministic template draft is generated — structurally valid and persona-aware. Room name, capacity, and PDR status are included if a room was matched.

**Talking point:** "When a guest says they're interested in a private dining room, the draft response now references that specific space — its capacity, whether it's a PDR, and its suitability. The operator doesn't need to look anything up."

---

## 7. Gmail SMTP Demo Flow

**What this shows:** Sending a draft response to a guest email address via Gmail.

> **Requires:** `SMTP_USERNAME` and `SMTP_PASSWORD` set in `.env`

1. Generate a draft (see Section 5)
2. The **Draft Response** section shows: "Test email only — will send to [guest email]"
3. Click **Send Draft**
4. Observe: status changes to **Sent** with timestamp
5. Check the test Gmail sent folder — email should appear
6. The **Email Activity** timeline in the drawer shows the outbound `sent` event

**Without Gmail credentials:**
Clicking Send Draft returns a `503 SMTP not configured` response. Status shows **Not Sent (disabled)**. The Email Activity timeline records the disabled event. The demo can show this flow to explain the credential activation path.

**Talking point:** "When Gmail App Password credentials are configured, the system activates SMTP automatically — no code change required. The test-only constraint means only emails to test addresses are sent during the POC."

---

## 8. Inbound Email Demo Flow

**What this shows:** An incoming email reply from a guest being parsed into a new enquiry or message thread.

> **Requires:** `IMAP_USERNAME` and `IMAP_PASSWORD` set in `.env`, and the Celery worker running

1. Send a test email to the configured Gmail inbox from any email client
2. The IMAP reader polls every 5 minutes (or trigger manually via Celery)
3. Navigate to http://localhost:3000/enquiries
4. Observe: a new enquiry appears with `source: email`
5. Open the enquiry — the email body appears as an inbound message

**Manual trigger (for demo purposes):**
```bash
# From services/api environment
python -c "
from app.modules.email.inbox_service import InboxReaderService
from app.db.session import get_db
db = next(get_db())
svc = InboxReaderService(db)
svc.read_inbox()
"
```

**Without Gmail credentials:**
The IMAP reader is disabled; no inbox polling occurs. Show the existing seed enquiries with `source: email` as an alternative demo path.

**Talking point:** "When a guest replies to the draft email, the system reads the inbox and threads the reply into the enquiry. This closes the loop — the operator sees the full conversation in one place."

---

## 9. Known Limitations

| Limitation | Impact | Planned Resolution |
|---|---|---|
| Gmail SMTP/IMAP requires App Password | Demo requires manual credential setup | Production would use OAuth2 |
| FallbackProvider draft quality is templated | LLM drafts require `ANTHROPIC_API_KEY` | Operator configures own key |
| No multi-tenant authentication | Any browser user can see all data | Sprint 6+ auth hardening |
| IMAP polling interval is 5 minutes | Inbound email demo requires patience | Configurable in production |
| No real payment/deposit handling | Confirmed enquiries are manual | Out of POC scope |
| No production SMTP relay | Gmail rate limits apply (100/day) | Production uses SendGrid/Postmark |
| Seed data only | No real venue or guest data | Expected for POC |
| Draft send is test-only | Emails go to seed addresses only | Production removes this constraint |
| Room availability not checked | Rooms are reference data only — no booking engine | Out of POC scope |
| No room asset management | Room images/floor plans not stored | Out of POC scope |
| Personas are restaurant-level | No per-room persona configuration | Intentional — keeps model simple |
| Room matching is deterministic | No ML ranking of rooms by suitability | Intentional — no ML in POC |

---

## 10. Demo Script

### Opening (1 min)

> "EventSales AI is private dining and events operating infrastructure for hospitality groups. Today I'll show you the complete loop from a guest enquiry landing on the webform — including room selection — through to a personalised draft response being sent."

### Flow (10 min)

1. **(1 min)** Open the Dashboard — show KPI cards (enquiries this week, pipeline value, average response time, conversion rate). Mention: "This is live seeded data — in production these pull from real bookings."

2. **(2 min)** Open **Restaurants** (`/restaurants`). Click a restaurant. Show the detail drawer — highlight the **Room Summary** section showing the venue's rooms/PDRs and default persona. Explain: "Restaurants are the venue container — they own the persona and pricing rules. Rooms are the physical spaces."

3. **(1 min)** Open **Rooms & PDRs** (`/rooms`). Show the rooms list filtered by that restaurant. Point out: PDR badge, capacity columns, room type. Show the drawer for a PDR room — suitability notes, layouts, hire fee. Explain: "This is where venue managers configure their spaces. Each room feeds into the AI draft."

4. **(1 min)** Show Personas page — the AI persona assigned to this restaurant. Explain: "Personas are always restaurant-level — not room-level. One persona handles all enquiries for a restaurant, regardless of which room is requested."

5. **(2 min)** Open the Webform at `/webform`. Select a restaurant. Watch the "Preferred Room or Area" field update to a dropdown. Select a PDR room. Fill in details (Alice Smith, corporate dinner, 12 guests). Submit.

6. **(1 min)** Switch to Enquiries list — new entry at the top. Open the drawer. Show: Preferred Room / Area populated with the selected room name.

7. **(2 min)** Generate a draft. Walk through the content — room name referenced, capacity mentioned, persona signature. Explain: "The AI matched the preferred area text to the configured room and included its details in the draft."

8. **(1 min)** Click Send Draft (if credentials configured). Show Email Activity timeline — sent event with timestamp.

### Close (1 min)

> "What you've seen is the complete operational loop, now with venue context. The guest selects a room on the webform. The AI knows that room's capacity, features, and suitability. The draft response is specific to that space — no copy-paste, no lookup, no manual work for the operator."

---

## 11. Stakeholder Talking Points

**On AI and pricing:**
> "Pricing is deterministic — rules-based, not ML. The operator controls the minimum spend for each event type, meal period, and day of week. No black box."

**On data safety:**
> "The POC uses exclusively seeded test data. No real guest information. No real restaurant data. The `.example.com` email domain is enforced throughout."

**On Gmail:**
> "Gmail is used for the POC because it requires no infrastructure. Production would use a transactional email relay (SendGrid, Postmark) with full deliverability and tracking. The SMTP interface is identical."

**On the AI draft quality:**
> "In the POC, we can demonstrate both the fallback template (deterministic, no API key) and the Anthropic-powered draft (with API key). The persona system makes both feel on-brand."

**On the venue context model:**
> "We separate restaurants from rooms deliberately. The persona and pricing logic lives at the restaurant level — it doesn't change per room. What changes per room is the physical context: capacity, features, suitability. The AI combines both layers to generate a room-specific draft without any manual templating."

**On room availability:**
> "Rooms are reference data in the POC — they don't have a booking engine. We're capturing guest preference and using it for personalisation. Availability checking and conflict management are production-phase scope."

**On multi-tenancy:**
> "The data model is multi-tenant from day one — each restaurant is isolated. The POC doesn't enforce authentication yet; that's Sprint 6 scope."

---

## 12. POC Success Criteria Checklist

| Criterion | Status | Notes |
|---|---|---|
| Dashboard KPI cards render with seeded data | ✓ Done | Sprint 3 |
| Pricing Rules page shows rules per restaurant | ✓ Done | Sprint 3 |
| Personas page shows configured personas | ✓ Done | Sprint 3 |
| Calendar page shows demand events | ✓ Done | Sprint 3 |
| Insights page shows performance metrics | ✓ Done | Sprint 3 |
| Enquiries list with status filtering | ✓ Done | Sprint 3 |
| Enquiry detail drawer with message thread | ✓ Done | Sprint 3 |
| Webform intake endpoint (`POST /enquiries/intake`) | ✓ Done | Sprint 4 |
| Webform page at `/webform` | ✓ Done | Sprint 4 |
| Draft generation (FallbackProvider) | ✓ Done | Sprint 4 |
| Draft generation (AnthropicProvider) | ✓ Done | Sprint 4 (key needed) |
| Draft response UI in enquiry drawer | ✓ Done | Sprint 4 |
| Gmail SMTP send wiring | ✓ Done | Sprint 4 (disabled without creds) |
| Gmail IMAP inbox reader | ✓ Done | Sprint 4 (disabled without creds) |
| DraftSection component (generate + send) | ✓ Done | Sprint 5A (UI-012) |
| Email Activity Timeline component | ✓ Done | Sprint 5A (UI-013) |
| Email delivery status logging (EmailEvent) | ✓ Done | Sprint 5A (EMAIL-005) |
| SMTP Celery worker task with retry | ✓ Done | Sprint 5A (WORKFLOW-005) |
| Inbound email → enquiry pipeline | ✓ Done | Sprint 5A (WORKFLOW-006) |
| End-to-end POC workflow tests (deterministic) | ✓ Done | Sprint 5A (TEST-005) |
| Rooms/PDR database model and API | ✓ Done | Sprint 5C (DATA-005, API-010) |
| Seed data includes rooms/PDRs (7 rooms across 4 restaurants) | ✓ Done | Sprint 5C (DATA-006) |
| Restaurant AI context endpoint | ✓ Done | Sprint 5C (API-011) |
| AI draft uses room context (capacity, amenities, suitability) | ✓ Done | Sprint 5C (AI-002) |
| Restaurant detail drawer shows room summary | ✓ Done | Sprint 5C (UI-014) |
| Rooms/PDR management page (`/rooms`) | ✓ Done | Sprint 5C (UI-015) |
| Webform room selection from backend dropdown | ✓ Done | Sprint 5C (UI-016) |
| Venue context workflow tests (332 backend, 79 frontend) | ✓ Done | Sprint 5C (TEST-006) |
| **Full demo loop completable without live credentials** | ✓ **Yes** | Fallback + seed data |
| **Full demo loop completable with Gmail credentials** | ✓ **Yes** | SMTP + IMAP active |
| **Room/PDR context visible in webform and draft generation** | ✓ **Yes** | Sprint 5C |

**POC verdict:** The complete operational loop — webform intake (with room selection) → enquiry creation → persona/pricing attachment → room-context draft generation → email send → inbound reply threading — is implemented and demonstrable. The system requires Gmail App Password credentials for live email and optionally an Anthropic API key for LLM-quality drafts; all other flows operate fully with seeded data and deterministic fallbacks.
