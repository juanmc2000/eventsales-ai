# Sprint 4 Completion Review — Webform and Email Wiring

**Sprint:** 4 — Webform and Email Wiring
**Completed:** 2026-05-21
**PRs:** #83 (DOC-007), #84 (API-008), #85 (UI-010), #86 (AI-001), #87 (API-009), #88 (UI-011), #89 (EMAIL-001), #90 (EMAIL-002), #91 (EMAIL-003), #92 (TEST-004), #93 (DOC-008)

---

## Sprint Goal

Wire the guest-facing enquiry webform, AI-assisted draft generation, and the Gmail SMTP/IMAP email infrastructure — completing the POC operational loop from webform submission through to draft email dispatch and inbox reading.

---

## Delivered

| Issue | PR | Description | Status |
|-------|----|-------------|--------|
| DOC-007 | #83 | Sprint 4 plan | ✓ Merged |
| API-008 | #84 | Webform intake endpoint (`POST /api/v1/enquiries/intake`) | ✓ Merged |
| UI-010 | #85 | Webform page (`/webform`) + `EnquiryWebform` component | ✓ Merged |
| AI-001 | #86 | FallbackProvider + AnthropicProvider, `DraftGenerationService` | ✓ Merged |
| API-009 | #87 | Draft endpoint (`POST/GET /api/v1/enquiries/{id}/draft`) | ✓ Merged |
| UI-011 | #88 | Draft response section in Enquiry Detail Drawer | ✓ Merged |
| EMAIL-001 | #89 | `GmailSMTPProvider` + `GmailIMAPProvider` interfaces | ✓ Merged |
| EMAIL-002 | #90 | Disabled SMTP send wiring (`POST /api/v1/email/send-draft`) | ✓ Merged |
| EMAIL-003 | #91 | Disabled IMAP inbox reader + `InboxParser` | ✓ Merged |
| TEST-004 | #92 | Sprint 4 tests (38 backend + 13 frontend) | ✓ Merged |
| DOC-008 | #93 | Sprint 4 completion review | ✓ Merged |

---

## Architecture Delivered

### Backend — `services/api/app/modules/`

**`ai/`**
- `provider.py` — `FallbackProvider`, `AnthropicProvider`, `make_provider()` factory
- `service.py` — `DraftGenerationService` (builds `DraftContext`, calls provider, persists result)
- `schemas.py` — `DraftContext`, `DraftGenerationResult`

**`enquiries/`**
- `intake_service.py` — `EnquiryIntakeService` (webform → persona → pricing → enquiry creation)
- `router.py` — `POST /api/v1/enquiries/intake`, `POST/GET /api/v1/enquiries/{id}/draft`

**`email/`**
- `providers.py` — `GmailSMTPProvider`, `GmailIMAPProvider` (disabled without credentials)
- `send_service.py` — `EmailSendService` (stubs send, logs to `email_events`)
- `inbox_service.py` — `InboxReaderService`, `InboxParser`, `ParsedEmail`
- `router.py` — `POST /api/v1/email/send-draft` (returns 503 without SMTP credentials)

### Frontend — `services/web/`

- `app/webform/page.tsx` — Guest-facing webform page
- `components/webform/EnquiryWebform.tsx` — Form component: restaurant selector, guest details, event details, message field; submits to intake endpoint; shows reference on success
- Enquiry Detail Drawer — Draft response section with "Coming Soon" placeholder (full DraftSection deferred to Sprint 5A)

### Tests — `services/api/tests/` + `services/web/tests/`

- 38 backend tests covering: intake schema validation, reference generation, persona attachment, pricing rule lookup, draft generation (FallbackProvider), SMTP disabled state, IMAP disabled state
- 13 frontend tests: webform page renders, form fields present, submission flow, drawer placeholder section visible

---

## Key Design Decisions

### FallbackProvider as the default path

Draft generation must work without an Anthropic API key. `FallbackProvider` produces a structurally valid, persona-aware draft using a deterministic template. `make_provider()` checks for `ANTHROPIC_API_KEY` and falls back automatically. This ensures the POC is demonstrable without external credentials.

### Credential-activated Gmail providers

Both `GmailSMTPProvider` and `GmailIMAPProvider` check for environment variables on construction. If credentials are absent, all send/read operations return a disabled result and log to `email_events`. This keeps the application runnable in any environment without credential management overhead.

### EnquiryIntakeService pipeline

Intake is handled by a dedicated service (not the base `EnquiryService`) to keep the webform-specific orchestration — persona attachment, pricing rule selection, initial message creation — isolated from the generic CRUD operations on enquiries.

### Draft stored in enquiry_messages

Drafts are persisted as outbound messages with `channel=draft` rather than in a separate table. This keeps the conversation thread coherent and avoids schema proliferation.

---

## Remaining Gaps Identified

| Gap | Deferred To |
|-----|-------------|
| Celery task for SMTP send (async delivery) | Sprint 5A (WORKFLOW-005) |
| Celery task for IMAP inbox polling | Sprint 5A (WORKFLOW-006) |
| Full DraftSection UI (generate button + send button + status states) | Sprint 5A (UI-012) |
| Email Activity Timeline in Enquiry Detail Drawer | Sprint 5A (UI-013) |
| Email delivery status constants and logging service | Sprint 5A (EMAIL-005) |
| Gmail App Password not configured in CI | Sprint 5A / ops |
| `ANTHROPIC_API_KEY` for LLM-quality drafts | Optional — FallbackProvider covers POC |

---

## Test Summary

| Suite | Count | Result |
|-------|-------|--------|
| Backend (pytest) | 38 | ✓ All pass |
| Frontend (vitest) | 13 | ✓ All pass |
| **Total** | **51** | **✓ All pass** |

All tests are deterministic — no live Anthropic API, Gmail, or database required.

---

## POC Readiness After Sprint 4

- **Webform → enquiry creation:** Complete
- **Persona and pricing attachment:** Complete
- **Draft generation (FallbackProvider):** Complete
- **Draft generation (AnthropicProvider):** Complete (API key needed)
- **Gmail SMTP send:** Wired, disabled without credentials
- **Gmail IMAP read:** Wired, disabled without credentials
- **Email activity UI:** Placeholder only (activated in Sprint 5A)
- **Async email delivery:** Deferred to Sprint 5A
