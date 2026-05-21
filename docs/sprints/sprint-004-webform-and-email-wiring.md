# Sprint 4 — Webform and Email Wiring

## Sprint Goal

Wire the guest-facing enquiry webform, AI-assisted draft generation, and the Gmail SMTP/IMAP email infrastructure — completing the POC operational loop from webform submission through to draft email dispatch and inbox reading. All email sending is disabled by default and activates only when Gmail credentials are present in the environment.

---

## Sprint Non-Goals

- Live email sending to real guest addresses (Gmail test account only)
- OAuth 2.0 Gmail authentication (App Password only)
- Multi-tenant authentication hardening
- Celery tasks for SMTP send and IMAP read (deferred to Sprint 5)
- Email activity UI in the Enquiry Detail Drawer (deferred to Sprint 5)
- Third-party CRM integrations
- ML-based pricing
- Payment or deposit handling

---

## Ordered Issue List

| Order | Issue ID | Title | Type |
|-------|----------|-------|------|
| 1 | DOC-007 | Create Sprint 4 Webform and Email Wiring Plan | Documentation |
| 2 | API-008 | Add Webform Intake Endpoint | Backend |
| 3 | UI-010 | Build Enquiry Webform Page | Frontend |
| 4 | AI-001 | Add AI Draft Generation Service | Backend |
| 5 | API-009 | Add Draft Response Endpoint | Backend |
| 6 | UI-011 | Add Draft Section to Enquiry Detail Drawer | Frontend |
| 7 | EMAIL-001 | Add Gmail SMTP and IMAP Provider Interfaces | Backend |
| 8 | EMAIL-002 | Add Disabled SMTP Send Wiring | Backend |
| 9 | EMAIL-003 | Add Disabled IMAP Inbox Reader Wiring | Backend |
| 10 | TEST-004 | Add Sprint 4 Webform and Email Tests | Testing |
| 11 | DOC-008 | Create Sprint 4 Completion Review | Documentation |

---

## Architecture Decisions

### Webform intake pipeline

The `EnquiryIntakeService` handles the full webform → enquiry creation flow:
1. Validate the incoming payload (Pydantic `EnquiryCreate`)
2. Generate a unique reference (`ENQ-YYYY-NNNN`)
3. Attach the restaurant's default persona
4. Attach applicable pricing rules for the event type and date
5. Persist the enquiry and initial inbound message

The intake endpoint (`POST /api/v1/enquiries/intake`) is public — no authentication required for POC. Source defaults to `webform`.

### AI draft generation

Two providers implement a shared interface:

- **FallbackProvider** — deterministic template-based draft. Always available; no API key required. Used when `ANTHROPIC_API_KEY` is absent.
- **AnthropicProvider** — Claude-powered draft via the Anthropic Messages API. Activated when `ANTHROPIC_API_KEY` is set.

`make_provider()` selects the appropriate provider based on the environment. The draft context (`DraftContext`) carries guest name, event details, persona, and pricing to the provider.

### Gmail credential activation

SMTP and IMAP providers are disabled by default. They activate automatically when the corresponding environment variables (`SMTP_USERNAME`, `SMTP_PASSWORD`, `IMAP_USERNAME`, `IMAP_PASSWORD`) are present. No code change required to switch between disabled and live modes.

### Draft response storage

Drafts are stored in the `enquiry_messages` table with `direction=outbound` and `channel=draft`. The draft endpoint (`POST /api/v1/enquiries/{id}/draft`) generates and persists a draft; `GET` retrieves the latest.

---

## Gmail Credential Setup (for live validation)

Before enabling live email:

- [ ] Create a dedicated test Gmail account
- [ ] Enable 2-Step Verification and generate a Gmail App Password
- [ ] Set `SMTP_*` and `IMAP_*` environment variables in `.env`
- [ ] Confirm `.env` is in `.gitignore`
- [ ] Restart services — SMTP/IMAP activate automatically

---

## Architecture Guardrails

All Sprint 4 work must preserve the architecture established in Sprints 1–3:

| Guardrail | Rule |
|-----------|------|
| Modular monolith | All new modules live in `services/api/app/modules/` |
| PostgreSQL source of truth | Draft content stored in `enquiry_messages`; email events in `email_events` |
| No live email to real addresses | Gmail test account or `.example.com` addresses only |
| No ML pricing | Pricing rules remain deterministic — no confidence scores from AI |
| FallbackProvider always available | Draft generation must work without `ANTHROPIC_API_KEY` |
| Celery async deferred | SMTP send and IMAP read are synchronous stubs in Sprint 4; Celery wiring deferred to Sprint 5 |
| Fake/seeded data only | Webform uses seeded restaurants; AI drafts use seeded persona/pricing data |

---

## Operational Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Anthropic API key absent | High (POC default) | FallbackProvider covers this case — draft generation always works |
| Gmail App Password not configured | High (POC default) | SMTP/IMAP gracefully disabled; UI shows placeholder |
| Draft generation latency with Anthropic | Medium | FallbackProvider as fallback; UI shows loading state |
| Intake endpoint receives spam without auth | Low | POC scope — no public exposure; auth deferred to Sprint 6 |
| Draft content includes real PII | Low | All seed data uses `.example.com` addresses |

---

## Success Criteria

- [ ] `POST /api/v1/enquiries/intake` creates an enquiry with persona and pricing attached
- [ ] Webform page at `/webform` submits successfully and shows the enquiry reference
- [ ] `POST /api/v1/enquiries/{id}/draft` generates a draft (FallbackProvider, no API key needed)
- [ ] Draft appears in the Enquiry Detail Drawer
- [ ] Gmail SMTP provider exists and is disabled without credentials
- [ ] Gmail IMAP provider exists and is disabled without credentials
- [ ] `POST /api/v1/email/send-draft` returns `503` when SMTP not configured
- [ ] TEST-004 tests pass without any live external services

---

## Definition of Done

- All 11 Sprint 4 issues are merged
- Draft generation works end-to-end with FallbackProvider (no API key)
- Gmail providers are wired but disabled by default
- TEST-004 test suite passes (deterministic — no live API calls)
- No credentials committed to source control
- No real customer or restaurant data used at any point
- No POC guardrails violated
