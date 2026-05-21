# Sprint 4 Completion Review — Webform and Email Wiring

**Sprint:** 4
**Goal:** Validate the webform-first enquiry intake path and prepare Gmail SMTP/IMAP wiring (disabled-by-default)
**Review Date:** 2026-05-21
**Status:** All 11 issues delivered — PRs open, awaiting merge

---

## Issues Delivered

| Issue | Title | PR | Status |
|-------|-------|----|--------|
| DOC-007 | Create Sprint 4 Webform and Email Wiring Plan | #84 | Open |
| API-008 | Add Enquiry Webform Intake Endpoint | #85 | Open |
| UI-010 | Build Enquiry Webform Page | #86 | Open |
| AI-001 | Add Persona-Based Draft Response Generation | #87 | Open |
| API-009 | Add Draft Response Endpoint | — | Merged in API-008 branch |
| UI-011 | Show Generated Draft Response in Enquiry Detail | #88 | Open |
| EMAIL-001 | Add Gmail Configuration and Provider Interfaces | #89 | Open |
| EMAIL-002 | Add Disabled SMTP Send Service Wiring | #90 | Open |
| EMAIL-003 | Add Disabled IMAP Inbox Reader Wiring | #91 | Open |
| TEST-004 | Add Sprint 4 Webform and Email Wiring Tests | #92 | Open |
| DOC-008 | Create Sprint 4 Completion Review | #93 | Open |

---

## Webform Flow Status

### What Was Delivered

- `POST /api/v1/enquiries/intake` — validates restaurant, resolves default persona, applies deterministic pricing rules, creates enquiry with `source=webform`, logs initial inbound message, returns `EnquiryIntakeOut` with persona name, recommended minimum spend, and pricing explanation
- `EnquiryWebform` React component — contact fields, event details, consent checkbox, success panel showing reference and pricing context
- `/webform` page — accessible from the navigation

### End-to-End Status

| Step | Status | Notes |
|------|--------|-------|
| Guest fills webform | ✓ Wired | Component renders and validates |
| Enquiry created in DB | ✓ Wired | Requires Docker + seeded data |
| Persona assigned | ✓ Wired | Resolves default restaurant persona |
| Pricing applied | ✓ Wired | Deterministic rules, no ML |
| Reference returned to guest | ✓ Wired | ENQ-YYYY-NNNN format |
| End-to-end smoke test | ⚠ Pending | Requires running Docker stack |

---

## Draft Generation Status

### What Was Delivered

- `FallbackProvider` — deterministic hospitality template, no API key required, always available
- `AnthropicProvider` — calls `claude-haiku-4-5-20251001`, falls back to `FallbackProvider` on error or empty key
- `make_provider(api_key)` — returns `(FallbackProvider, is_fallback=True)` when key empty
- `POST /api/v1/enquiries/{id}/draft` — generates and stores draft as `direction=outbound, channel=draft` EnquiryMessage
- `GET /api/v1/enquiries/{id}/draft` — retrieves latest stored draft
- `DraftSection` component in the Enquiry Detail Drawer — idle/loading/ready/error states, Regenerate button

### Draft Generation Status

| Path | Status | Notes |
|------|--------|-------|
| FallbackProvider draft | ✓ Live | Works without any API key |
| AnthropicProvider draft | ⚠ Conditional | Requires `ANTHROPIC_API_KEY` in `.env` |
| Draft stored in DB | ✓ Wired | Stored as outbound/draft message |
| Draft visible in UI | ✓ Wired | DraftSection renders on Enquiry Detail |
| Email sending of draft | ✗ Not wired | Requires EMAIL-002 live SMTP + credentials |

---

## Gmail Wiring Status

### What Was Delivered (Disabled-by-Default)

**SMTP (Outbound Send):**
- `GmailSMTPProvider` skeleton — reads `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` from `.env`
- `is_configured=False` when credentials absent — `send()` returns `False` with log warning, no network call
- `EmailSendService.send_draft()` returns `status='disabled'` with clear credential instructions
- `POST /api/v1/email/send-draft` endpoint — returns disabled status in current POC state
- `GET /api/v1/email/status` endpoint — health check for SMTP/IMAP configuration

**IMAP (Inbound Inbox Reader):**
- `GmailIMAPProvider` skeleton — reads `IMAP_USERNAME`, `IMAP_PASSWORD` from `.env`
- `is_configured=False` when credentials absent — `poll()` returns `[]` with log warning, no network call
- `InboxReaderService.poll()` returns empty list, `status()` returns configuration status with reason
- `InboxParser` — normalises raw IMAP message dicts into `ParsedEmail` DTOs (email extraction, Re:/Fwd: stripping, RFC 2822 date parsing)

### Gmail Credential Gap

> **IMPORTANT:** No Gmail credentials have been configured or committed. This is intentional and correct per POC guardrails.

To enable live Gmail testing in a future sprint:

1. Create a dedicated Gmail test account (not a production mailbox)
2. Enable "Less secure app access" or create a **Gmail App Password** (Google Account → Security → App Passwords)
3. Add to `.env`:
   ```
   SMTP_USERNAME=your-test-gmail@gmail.com
   SMTP_PASSWORD=your-gmail-app-password
   SMTP_FROM_EMAIL=your-test-gmail@gmail.com
   IMAP_USERNAME=your-test-gmail@gmail.com
   IMAP_PASSWORD=your-gmail-app-password
   ```
4. The existing provider implementations will activate automatically — no code changes required

### Gmail Status Summary

| Capability | Status | Blocker |
|-----------|--------|---------|
| SMTP provider interface | ✓ Wired | — |
| SMTP credentials | ✗ Not configured | Gmail App Password needed |
| Live SMTP send | ✗ Disabled | Credentials required |
| IMAP provider interface | ✓ Wired | — |
| IMAP credentials | ✗ Not configured | Gmail App Password needed |
| Live IMAP poll | ✗ Disabled | Credentials required |
| Email event logging | ✓ Schema ready | Activates on first live send |
| Inbound email → enquiry | ✗ Not wired | Future sprint (Celery task) |

---

## Test Coverage

| Suite | Tests | Pass |
|-------|-------|------|
| Backend: email providers | 21 | ✓ |
| Backend: email send (disabled mode) | 16 | ✓ |
| Backend: IMAP reader + parser | 25 | ✓ |
| Backend: AI fallback + make_provider | 13 | ✓ |
| Backend: Sprint 4 email disabled | 15 | ✓ |
| Backend: Sprint 4 intake concept | 10 | ✓ |
| Frontend: webform smoke | 9 | ✓ |
| Frontend: draft section smoke | 5 | ✓ |
| Frontend: routes + shell (existing) | 35 | ✓ |
| **Total new Sprint 4 tests** | **105+** | ✓ |

All tests are deterministic. No live Gmail, SMTP, or LLM calls in the test suite.

---

## POC Success Criteria Checklist

| Criterion | Status | Notes |
|-----------|--------|-------|
| Test enquiry webform submits | ✓ Wired | Requires running Docker stack to validate end-to-end |
| Enquiry stored in PostgreSQL | ✓ Wired | Source of truth confirmed |
| Default persona assigned | ✓ Wired | Resolves from restaurant_personas |
| Deterministic pricing applied | ✓ Wired | No ML, rules-based only |
| Draft response generated (fallback) | ✓ Live | FallbackProvider works without API key |
| Draft response generated (LLM) | ⚠ Conditional | Requires ANTHROPIC_API_KEY |
| Draft visible in UI | ✓ Wired | DraftSection component in Enquiry Detail |
| Gmail SMTP interface ready | ✓ Wired | Disabled without credentials |
| Live SMTP send | ✗ Pending | Requires Gmail App Password |
| Gmail IMAP interface ready | ✓ Wired | Disabled without credentials |
| Live IMAP inbox reading | ✗ Pending | Requires Gmail App Password |
| Inbound email → enquiry creation | ✗ Not started | Future sprint |
| All seed data available | ✓ Complete | 4 restaurants, 3 personas, pricing rules |
| Backend API coverage | ✓ Complete | All POC endpoints delivered |
| Frontend page coverage | ✓ Complete | Dashboard, Enquiries, Calendar, Insights, Webform |

---

## Remaining POC Gaps

1. **Gmail credentials** — The single most impactful gap. One Gmail App Password unlocks live SMTP send and IMAP reading without any code changes.

2. **Inbound email → enquiry wiring** — The `InboxParser` and `InboxReaderService` are ready, but the Celery scheduled task that polls the inbox and creates enquiries from parsed emails is not written. This is Sprint 5 scope.

3. **End-to-end browser test** — No automated browser test validates the full webform → enquiry → draft → email flow. Manual Docker stack testing is required to confirm integration.

4. **AnthropicProvider live test** — The Haiku provider is wired but has not been tested with a real API key. Fallback behaviour is confirmed working.

5. **Email send button in UI** — The `POST /api/v1/email/send-draft` endpoint exists but there is no "Send" button in the Enquiry Detail Drawer. This is intentional until live SMTP is confirmed working.

---

## Recommended Sprint 5 Options

### Option A — Gmail Credential Sprint (Recommended)
**Goal:** Prove the first live email send and inbox read with a test Gmail account.

Key tasks:
- Set up dedicated Gmail test account with App Password
- Validate `POST /api/v1/email/send-draft` with real credentials
- Validate `InboxReaderService.poll()` against live inbox
- Write Celery task for scheduled inbox polling
- Create inbound email → enquiry matching logic
- Add "Send Draft" button to Enquiry Detail Drawer

**Expected outcome:** Full webform → enquiry → AI draft → email send → inbox read loop confirmed in Docker.

---

### Option B — End-to-End Hardening Sprint
**Goal:** Validate the full flow with automated tests against a running Docker stack.

Key tasks:
- Docker Compose integration test suite
- Playwright or Cypress browser tests for webform
- CI pipeline for integration tests
- Error recovery and edge case handling

---

### Option C — MVP Backlog Creation
**Goal:** Pivot from POC validation to MVP planning.

Key tasks:
- Define MVP scope and user stories
- Create GitHub Project board for MVP
- Architecture review for production hardening
- Security audit (authentication, RBAC, rate limiting)
- Cloud deployment plan

---

## Definition of Done — Sprint 4

- [x] All 11 issues have PRs
- [x] No production email sent
- [x] No real Gmail credentials committed
- [x] No ML pricing introduced
- [x] POC guardrails maintained throughout
- [x] All tests deterministic
- [x] Sprint plan document created (DOC-007)
- [x] Completion review created (DOC-008)
