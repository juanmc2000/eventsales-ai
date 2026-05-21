# Sprint Status Overview

**Project:** EventSales AI
**Phase:** POC (Proof of Concept)
**Last Updated:** 2026-05-21

---

## Sprint Summary

| Sprint | Theme | Status | PRs |
|--------|-------|--------|-----|
| Sprint 1 | Architecture Foundation | ✓ Complete | #1–#20 |
| Sprint 2 | Product Foundation | ✓ Complete | #21–#50 |
| Sprint 3 | UI Shell and Core Pages | ✓ Complete | #51–#82 |
| Sprint 4 | Webform and Email Wiring | ✓ Complete | #83–#93 |
| Sprint 5A | Live Gmail Validation | ✓ Complete | #104–#111 |

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

## POC Feature Coverage

| Feature | Sprint | Status |
|---------|--------|--------|
| Dashboard KPIs | 3 | ✓ |
| Restaurants, Rooms configuration | 2–3 | ✓ |
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
| POC demo guide | 5A | ✓ |

---

## Remaining Gaps

| Gap | Priority | Sprint |
|-----|----------|--------|
| Gmail App Password not in CI/CD | P1 | 5B |
| Celery send-draft dispatch not wired in main.py | P1 | 5B |
| Inbound email Celery beat schedule | P2 | 5B |
| Multi-tenant authentication | P1 | 6 |
| E2E browser test (Playwright) | P2 | 6 |
| Production email relay (SendGrid/Postmark) | P2 | Post-POC |

---

## Key Reference Documents

| Document | Purpose |
|---|---|
| `docs/product/POC_SPECIFICATION.md` | Full POC scope |
| `docs/demo/poc-demo-guide.md` | Demo walkthrough and stakeholder talking points |
| `docs/sprints/sprint-005-completion-review.md` | Sprint 5A delivery review |
| `CLAUDE.md` | Developer and AI assistant instructions |
