# Sprint Status Overview

**Project:** EventSales AI — POC
**Last Updated:** 2026-05-21

---

## Sprint Summary

| Sprint | Theme | Issues | Status |
|--------|-------|--------|--------|
| Sprint 1 | Architecture Foundation | DOC-001 → DOC-004, TEST-001 | ✓ Complete |
| Sprint 2 | Product Foundation | DOC-005 → DOC-006, DATA-002 → DATA-004, API-002 → API-006, TEST-002 | ✓ Complete |
| Sprint 3 | UI Shell and Core Pages | UI-001 → UI-009, TEST-003 | ✓ Complete |
| Sprint 4 | Webform and Email Wiring | DOC-007 → DOC-008, API-008 → API-009, UI-010 → UI-011, AI-001, EMAIL-001 → EMAIL-003, TEST-004 | PRs Open |

---

## Sprint 1 — Architecture Foundation

**Goal:** Establish repo structure, Docker Compose, FastAPI skeleton, documentation standards.

**Delivered:**
- CLAUDE.md with guardrails and build order
- POC_SPECIFICATION.md, ENGINEERING_SPECIFICATION.md, PRODUCT_REQUIREMENT_DOCUMENT.md
- Docker Compose: PostgreSQL + Redis
- FastAPI application scaffold
- Alembic migration framework baseline
- Environment variable schema (.env.example)

**Status:** ✓ Merged and stable

---

## Sprint 2 — Product Foundation

**Goal:** Core data models, seed data, all backend API modules.

**Delivered:**
- Alembic migration framework (DATA-002)
- Core POC database models: restaurants, personas, pricing_rules, enquiries, enquiry_messages, email_events, calendar/demand events, insight_snapshots (DATA-003)
- Seed data framework: 4 restaurants, 3 personas, pricing rules, 1 year of demand events, sample enquiries (DATA-004)
- Restaurant, Persona, Pricing, Calendar, Enquiry, Dashboard API modules (API-002 to API-006)
- Sprint 2 backend test coverage (TEST-002)

**Status:** ✓ Merged and stable

---

## Sprint 3 — UI Shell and Core Pages

**Goal:** React/Next.js frontend with full navigation shell and all core pages.

**Delivered:**
- Fixed dark sidebar + dark topbar shell (UI-001)
- Dashboard page with KPI cards and charts (UI-002 → UI-004)
- Calendar page (UI-005)
- Pricing Rules page (UI-006)
- Insights/Analytics page (UI-007)
- Enquiry Management page (UI-008)
- Enquiry Detail Drawer (UI-009)
- Frontend smoke test baseline (TEST-003)

**Status:** ✓ Merged and stable

---

## Sprint 4 — Webform and Email Wiring

**Goal:** Validate webform intake path, wire AI draft generation, prepare Gmail SMTP/IMAP (disabled-by-default).

**Delivered (PRs open, awaiting merge):**

| Issue | Description | PR |
|-------|-------------|-----|
| DOC-007 | Sprint 4 plan document | #84 |
| API-008 | Webform intake endpoint (`POST /api/v1/enquiries/intake`) | #85 |
| UI-010 | Webform page + `EnquiryWebform` component | #86 |
| AI-001 | FallbackProvider + AnthropicProvider, draft generation service | #87 |
| UI-011 | DraftSection component in Enquiry Detail Drawer | #88 |
| EMAIL-001 | Gmail SMTP/IMAP provider interfaces | #89 |
| EMAIL-002 | Disabled SMTP send wiring (`POST /api/v1/email/send-draft`) | #90 |
| EMAIL-003 | Disabled IMAP inbox reader + InboxParser | #91 |
| TEST-004 | Sprint 4 comprehensive test suite (38 backend + 13 frontend tests) | #92 |
| DOC-008 | Sprint 4 completion review | #93 |

**Key gaps remaining:**
- Gmail App Password not configured → live SMTP/IMAP disabled
- Inbound email → enquiry Celery task not written
- AnthropicProvider requires `ANTHROPIC_API_KEY`
- No E2E browser test

---

## POC Capability Status

| Capability | Status |
|-----------|--------|
| Database schema | ✓ Complete |
| Seed data | ✓ Complete |
| Restaurant/Persona/Pricing API | ✓ Complete |
| Demand calendar API | ✓ Complete |
| Enquiry management API + UI | ✓ Complete |
| Webform intake | ✓ Wired (Sprint 4) |
| AI draft generation (fallback) | ✓ Live — no API key needed |
| AI draft generation (LLM) | ⚠ Requires ANTHROPIC_API_KEY |
| Draft response UI | ✓ Wired (Sprint 4) |
| Gmail SMTP interface | ✓ Wired — disabled without credentials |
| Gmail IMAP interface | ✓ Wired — disabled without credentials |
| Live email send | ✗ Requires Gmail App Password |
| Inbound email processing | ✗ Not started |
| End-to-end test | ✗ Manual only |

---

## Next Sprint Options

See `docs/sprints/sprint-004-completion-review.md` for detailed Sprint 5 options:

- **Option A (Recommended):** Gmail Credential Sprint — prove live email round-trip
- **Option B:** End-to-end hardening — Playwright tests against Docker stack
- **Option C:** MVP Backlog Creation — pivot from POC to MVP planning
