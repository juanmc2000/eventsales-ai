# Sprint 3 — UI Shell and Core Pages

## Sprint Goal

Deliver the first user-visible product experience: scaffold the Next.js frontend, establish the shared design system shell, and build all core operational pages — Dashboard, Restaurants, Personas, Pricing Rules, Calendar, Insights, and Enquiries (list + detail drawer) — fully connected to the Sprint 2 backend APIs and validated with a frontend smoke test baseline.

---

## Sprint Non-Goals

- Gmail SMTP / IMAP integration (deferred to Sprint 4)
- Webform intake path (deferred to Sprint 4)
- AI-generated draft responses (deferred to Sprint 4)
- Production authentication hardening
- Third-party CRM integrations (Salesforce, TripleSeat, Cvent, etc.)
- Microservices extraction
- Real customer or restaurant data
- Payment or deposit handling

---

## Ordered Issue List

| Order | Issue ID | Title | Type |
|-------|----------|-------|------|
| 1 | DEVOPS-003 | Scaffold Next.js Frontend Application | DevOps |
| 2 | UI-001 | Create Shared Frontend Application Shell | Frontend |
| 3 | UI-002 | Create Shared Design System Primitives | Frontend |
| 4 | API-007 | Add Dashboard Summary Backend API | Backend |
| 5 | DASH-001 | Build Dashboard Page | Frontend |
| 6 | UI-003 | Build Restaurant Management Page | Frontend |
| 7 | UI-004 | Build Persona Management Page | Frontend |
| 8 | UI-005 | Build Pricing Rules Page | Frontend |
| 9 | UI-006 | Build Commercial Calendar Page | Frontend |
| 10 | UI-007 | Build Insights Analytics Page | Frontend |
| 11 | UI-008 | Build Enquiry Management Page | Frontend |
| 12 | UI-009 | Build Enquiry Detail Drawer/Page | Frontend |
| 13 | TEST-003 | Add Frontend Smoke Test Baseline | Testing |

---

## Design System Constraints

Sprint 3 introduces the UI/UX Reference Pack as a delivery constraint for all frontend work. Every page must comply with the following non-negotiable rules:

### Shell
- Fixed **dark left sidebar** (`--nav-bg: #070A1F`) visible on all pages
- Fixed **dark topbar** (`--topbar-bg: #080B24`) visible on all pages
- **Light main workspace** (`--page-bg: #F8F7FC`) with white rounded cards

### Colour Tokens
- Use only approved tokens from `design/docs/UI_DESIGN_SYSTEM.md`
- KPI card accent sequence: purple → pink → orange → teal
- Never invent new brand colours

### Components
- All tables follow the shared table rules in `design/docs/UI_COMPONENT_RULES.md`
- Status pills use approved language only
- Cards have consistent border-radius and shadow
- AI suggestion cards always include recommendation + rationale + confidence

### Reference Images
- Each page must be validated against its reference image in `design/reference_images/`
- Final composite layout validated against `10_Composite_Overview.png`

---

## Architecture Guardrails

All Sprint 3 work must preserve Sprint 1 and Sprint 2 architecture decisions:

| Guardrail | Rule |
|-----------|------|
| Modular monolith | Frontend calls existing FastAPI APIs — no new backend services |
| PostgreSQL source of truth | No client-side state stores for durable data |
| Module boundaries | New frontend components live in `services/web/components/<domain>/` |
| API contract | Frontend uses only endpoints already defined in Sprint 2 |
| No ML pricing | Pricing recommendations are deterministic rule output only |
| No live integrations | No Salesforce, TripleSeat, Cvent, Stripe, or Adyen |
| Fake data only | All pages render seeded test data — no real customer or restaurant data |

---

## Page Delivery Summary

### DEVOPS-003 — Next.js Frontend Scaffold
Sets up the Next.js application with TypeScript, TailwindCSS, App Router, shared layout, API client foundation, environment configuration, frontend Dockerfile, and docker-compose service. Creates placeholder routes for all navigation destinations.

### UI-001 — Application Shell
Implements the fixed dark left sidebar and dark topbar as persistent layout components wrapping all pages. Establishes the navigation taxonomy: Main (Home, Enquiries, Calendar), Configuration (Restaurants, Personas, Pricing Rules), Insights (Dashboard, Reports), Admin.

### UI-002 — Design System Primitives
Creates shared component primitives: KPI cards (purple/pink/orange/teal sequence), status pills, data tables, form inputs, modal/drawer shells, and typography tokens. These are referenced by all subsequent page components.

### API-007 — Dashboard Summary Backend API
Adds `GET /api/v1/dashboard/summary` returning aggregated KPIs: enquiry counts by status, total revenue opportunity, conversion rate, and upcoming events. Reads from seeded PostgreSQL data.

### DASH-001 — Dashboard Page
Renders the KPI summary cards from API-007 alongside recent enquiry activity and upcoming calendar events. Matches the composite overview reference image layout.

### UI-003 — Restaurant Management Page
Table view of all restaurants with name, cuisine type, and status. Detail view shows restaurant profile, assigned personas, and pricing rule summary.

### UI-004 — Persona Management Page
Table view of all personas with name, tone, and style summary. Detail view shows full persona definition used for draft generation.

### UI-005 — Pricing Rules Page
Table view of pricing rules per restaurant, grouped by meal period and event type, showing minimum spend thresholds. Supports filtering by restaurant.

### UI-006 — Commercial Calendar Page
Monthly/weekly calendar view of demand events and confirmed bookings. Colour-coded by event type. Reads from `demand_events` and `calendar_events`.

### UI-007 — Insights Analytics Page
Charts and KPI cards for revenue pipeline, enquiry conversion, and demand signal trends. Reads from `insight_snapshots` and `demand_events`.

### UI-008 — Enquiry Management Page
Filterable, sortable table of all enquiries with status pills, guest name, restaurant, event date, party size, and recommended minimum spend. Supports filtering by restaurant and status.

### UI-009 — Enquiry Detail Drawer
Side drawer rendering full enquiry detail: guest information, event details, pricing recommendation, conversation thread (enquiry messages), and persona assignment. Includes a placeholder for the draft response section (activated in Sprint 4).

### TEST-003 — Frontend Smoke Test Baseline
Vitest + @testing-library/react smoke tests confirming: shell renders without crashing, navigation links are present, key pages render with mocked API responses, and the enquiry detail drawer renders core fields.

---

## Architecture Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Design drift from reference images | Medium | Validate each page against reference image before marking done |
| API contract mismatch between Sprint 2 and Sprint 3 | Low | Frontend types mirror backend schemas in `services/web/lib/types/` |
| Component bloat from one-off abstractions | Medium | Shared primitives in UI-002 only — no speculative components |
| Vitest setup incompatibility with Next.js App Router | Low | Use `jsdom` environment; mock `next/navigation` per test |
| Cross-module import cycles in frontend | Low | Each domain folder imports only from `lib/` — never from sibling domains |

---

## Success Criteria

- [ ] `npm run dev` starts the frontend without errors
- [ ] All 8 navigation destinations render without a blank screen
- [ ] Dashboard KPI cards display data from `/api/v1/dashboard/summary`
- [ ] Enquiry list page renders enquiries from the seeded dataset
- [ ] Enquiry detail drawer opens and displays guest name, event details, and pricing recommendation
- [ ] Restaurant, Persona, and Pricing Rules pages render their respective data tables
- [ ] Calendar page renders at least one demand event
- [ ] Insights page renders at least one chart or KPI card
- [ ] Sidebar and topbar match the design system shell rules on every page
- [ ] TEST-003 frontend smoke tests pass with `npm test`
- [ ] No approved colour tokens have been violated

---

## Definition of Done

- All 13 Sprint 3 issues are merged to `main`
- Every page validated against its reference image in `design/reference_images/`
- Frontend type definitions in `services/web/lib/types/` mirror backend schemas
- No ML pricing introduced
- No production integrations present
- TEST-003 smoke test suite passes
- No POC guardrails violated
