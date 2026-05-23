# Sprint Status Overview

**Project:** EventSales AI
**Phase:** POC (Proof of Concept)
**Last Updated:** 2026-05-23

---

## Sprint Summary

| Sprint | Theme | Status | PRs |
|--------|-------|--------|-----|
| Sprint 1 | Architecture Foundation | ✓ Complete | #1–#20 |
| Sprint 2 | Product Foundation | ✓ Complete | #21–#50 |
| Sprint 3 | UI Shell and Core Pages | ✓ Complete | #51–#82 |
| Sprint 4 | Webform and Email Wiring | ✓ Complete | #83–#93 |
| Sprint 5A | Live Gmail Validation | ✓ Complete | #104–#111 |
| Sprint 5B | Live Gmail SMTP + IMAP | ✓ Complete | #113–#114 |
| Sprint 5C | Venue Context (Rooms/PDR) | ✓ Complete | #126–#135 |
| Sprint 5D | Freeform Webform + Audience Routing | ✓ Complete | #138–#141 |
| Sprint 5E | AI Transparency + Room Availability | ✓ Complete | #145, #148–#149 |

---

## Sprint 5A Issues

| Issue | PR | Title | Status |
|-------|----|-------|--------|
| DOC-009 | #104 | Sprint 5A plan | ✓ Merged |
| UI-012 | #105 | DraftSection component | ✓ Merged |
| EMAIL-005 | #106 | Email delivery service and router | ✓ Merged |
| WORKFLOW-005 | #107 | SMTP Celery worker task | ✓ Merged |
| WORKFLOW-006 | #108 | Inbound email → enquiry pipeline | ✓ Merged |
| UI-013 | #109 | Email Activity Timeline component | ✓ Merged |
| TEST-005 | #110 | End-to-end POC workflow tests (73 tests) | ✓ Merged |
| DOC-010 | #111 | POC demo and validation guide | ✓ Merged |

---

## Sprint 5B Issues

| Issue | PR | Title | Status |
|-------|----|-------|--------|
| EMAIL-004 | #113 | Live Gmail SMTP send (GmailSMTPProvider) | ✓ Merged |
| EMAIL-006 | #114 | Live Gmail IMAP polling (GmailIMAPProvider) | ✓ Merged |

---

## Sprint 5C Issues

| Issue | PR | Title | Status |
|-------|----|-------|--------|
| DATA-005 | #126 | Rooms/PDR database model, schemas, migration | ✓ PR open |
| API-010 | #127 | Rooms/PDR backend CRUD module | ✓ PR open |
| DATA-006 | #128 | Seed data: 7 rooms across 4 restaurants | ✓ PR open |
| API-011 | #129 | Restaurant AI context endpoint | ✓ PR open |
| AI-002 | #130 | AI draft generation uses room context | ✓ PR open |
| UI-014 | #131 | Restaurant rooms summary section | ✓ PR open |
| UI-015 | #132 | Rooms/PDR management page (`/rooms`) | ✓ PR open |
| UI-016 | #133 | Webform room selection + enquiry detail | ✓ PR open |
| TEST-006 | #134 | Venue context workflow tests | ✓ PR open |
| DOC-011 | #135 | Update POC demo guide with venue context | ✓ PR open |

---

## Sprint 5D Issues

| Issue | PR | Title | Status |
|-------|----|-------|--------|
| UI-017 | #141 | Freeform enquiry tab + two-tab webform toggle | ✓ Merged |
| DATA-007 | #141 | Audience type on RestaurantPersona + migration | ✓ Merged |
| API-012 | #141 | Intake service resolves persona by audience type | ✓ Merged |

---

## Sprint 5E Issues

| Issue | PR | Title | Status |
|-------|----|-------|--------|
| DATA-008 | #145 | room_availability table, Alembic migration, deterministic seed (5,124 rows) | ✓ Merged |
| API-013 | #148 | Room availability endpoint + AIContextOut with raw prompts in draft response | ✓ Merged |
| UI-018 | #149 | Enrich webform response panels: AI transparency + room availability card | ✓ Merged |

---

## POC Feature Coverage

| Feature | Sprint | Status |
|---------|--------|--------|
| Dashboard KPIs | 3 | ✓ |
| Restaurants configuration | 2–3 | ✓ |
| Personas configuration | 2–3 | ✓ |
| Pricing Rules (deterministic) | 2–3 | ✓ |
| Calendar + demand events | 2–3 | ✓ |
| Insights / reporting | 2–3 | ✓ |
| Enquiries list + detail drawer | 3 | ✓ |
| Webform intake endpoint | 4 | ✓ |
| Webform page (`/webform`) | 4 | ✓ |
| Draft generation (FallbackProvider) | 4 | ✓ |
| Draft generation (AnthropicProvider) | 4 | ✓ |
| Gmail SMTP send (wired, disabled without creds) | 4 | ✓ |
| Gmail IMAP inbox reader (wired, disabled without creds) | 4 | ✓ |
| DraftSection UI (generate + send + states) | 5A | ✓ |
| Email Activity Timeline UI | 5A | ✓ |
| Email delivery status logging | 5A | ✓ |
| SMTP Celery worker with retry | 5A | ✓ |
| Inbound email → enquiry pipeline | 5A | ✓ |
| Deterministic end-to-end tests (73) | 5A | ✓ |
| Live Gmail SMTP send (GmailSMTPProvider) | 5B | ✓ |
| Live Gmail IMAP polling (GmailIMAPProvider) | 5B | ✓ |
| Rooms/PDR model, schemas, migration | 5C | ✓ |
| Rooms/PDR CRUD API (nested under restaurants) | 5C | ✓ |
| Seed data: 7 rooms/PDRs across 4 restaurants | 5C | ✓ |
| Restaurant AI context endpoint (`/restaurants/{id}/context`) | 5C | ✓ |
| AI draft uses room context (capacity, amenities, suitability) | 5C | ✓ |
| Restaurant detail — room summary section | 5C | ✓ |
| Rooms/PDR management page (`/rooms`) | 5C | ✓ |
| Webform room selection (backend-driven dropdown) | 5C | ✓ |
| Venue context workflow tests (332 backend, 79 frontend) | 5C | ✓ |
| POC demo guide (updated with venue context) | 5C | ✓ |
| Freeform enquiry tab (natural-language → AI → SMTP auto-flow) | 5D | ✓ |
| Two-tab webform toggle (Structured / Freeform) | 5D | ✓ |
| Audience type selector (Social / Corporate / Agency) on both tabs | 5D | ✓ |
| Audience-based persona routing (Eleanor=social, James=corporate, Sophia=agency) | 5D | ✓ |
| RestaurantPersona audience column + Alembic migration | 5D | ✓ |
| Freeform smoke tests (84 frontend, 332 backend total) | 5D | ✓ |
| room_availability table (7 rooms × 366 days × 2 periods = 5,124 rows) | 5E | ✓ |
| Room availability endpoint (`GET /restaurants/{id}/rooms/{rid}/availability?date=`) | 5E | ✓ |
| AIContextOut in draft response (model, persona, prompts, room, spend) | 5E | ✓ |
| Raw system prompt + user message exposed in draft response | 5E | ✓ |
| AI Transparency Panel on webform success page (collapsible) | 5E | ✓ |
| Room Availability Card on webform success page (status pills) | 5E | ✓ |
| Tests: 353 backend, 84 frontend (437 total) | 5E | ✓ |

---

## Remaining Gaps

| Gap | Priority | Sprint |
|-----|----------|--------|
| Gmail App Password not in CI/CD | P1 | 6 |
| Celery send-draft dispatch not wired in main.py | P1 | 6 |
| Inbound email Celery beat schedule | P2 | 6 |
| Multi-tenant authentication | P1 | 6 |
| E2E browser test (Playwright) | P2 | 6 |
| Audience auto-detection from email domain + CRM lookup | P2 | 6 |
| Production email relay (SendGrid/Postmark) | P2 | Post-POC |
| Room availability — replace seed with live booking system API | P3 | Post-POC |

---

## Key Reference Documents

| Document | Purpose |
|---|---|
| `docs/product/POC_SPECIFICATION.md` | Full POC scope |
| `docs/demo/poc-demo-guide.md` | Demo walkthrough and stakeholder talking points |
| `docs/sprints/sprint-005-completion-review.md` | Sprint 5A delivery review |
| `docs/demo/poc-demo-guide.md` (updated) | Demo walkthrough including venue context and room selection |
| `docs/sprints/sprint-005c-venue-context.md` | Sprint 5C delivery review |
| `CLAUDE.md` | Developer and AI assistant instructions |
