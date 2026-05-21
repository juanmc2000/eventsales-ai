# Sprint 4 — Webform and Email Wiring

## Sprint Goal

Deliver the first end-to-end POC path: test webform submission creates an enquiry, triggers persona-based draft response generation, and exposes the draft in the UI. Wire Gmail SMTP and IMAP structurally — dormant, credential-free — so the email layer can be activated without architectural rework.

---

## Sprint Non-Goals

- Live Gmail credential setup (no .env secrets required to pass Sprint 4)
- Production email sending to real recipients
- SMTP send execution (wired but disabled)
- IMAP inbox polling execution (wired but disabled)
- ML-based draft generation (persona-based only, deterministic prompt logic)
- Third-party CRM integrations (Salesforce, TripleSeat, Cvent, etc.)
- Microservices extraction
- Payment or deposit handling
- Inbound email-to-enquiry parsing (beyond structural wiring)
- Authentication hardening
- Real customer or restaurant data

---

## Ordered Issue List

| Order | Issue ID | Title | Type |
|-------|----------|-------|------|
| 1 | DOC-007 | Create Sprint 4 Webform and Email Wiring Plan | Documentation |
| 2 | API-008 | Add Enquiry Intake Orchestration Service | Backend |
| 3 | UI-010 | Build Test Enquiry Webform | Frontend |
| 4 | AI-001 | Add Persona-Based Draft Response Generation | Backend |
| 5 | API-009 | Add Draft Response Endpoint | Backend |
| 6 | UI-011 | Show Generated Draft Response in Enquiry Detail | Frontend |
| 7 | EMAIL-001 | Add Gmail Configuration and Provider Interfaces | Backend |
| 8 | EMAIL-002 | Add Disabled SMTP Send Service Wiring | Backend |
| 9 | EMAIL-003 | Add Disabled IMAP Inbox Reader Wiring | Backend |
| 10 | TEST-004 | Add Sprint 4 Webform and Email Wiring Tests | Testing |
| 11 | DOC-008 | Create Sprint 4 Completion Review | Documentation |

---

## Webform-First Delivery Rationale

Sprint 4 prioritises the webform intake path over Gmail activation for the following reasons:

1. **No credential dependency.** The webform path requires no external accounts, tokens, or secrets. It can be demonstrated in any environment immediately.
2. **Validates the enquiry lifecycle end-to-end.** A webform submission exercises enquiry creation, pricing rule application, persona assignment, and draft response generation — the full POC value loop.
3. **Unblocks frontend work.** UI-010 and UI-011 can be built and tested against real API responses without waiting for Gmail credentials to be provisioned.
4. **Reduces integration risk.** By deferring Gmail activation to the final issues of the sprint, the core product logic is stable before email plumbing is introduced.
5. **Matches POC risk profile.** The POC must demonstrate business value (AI-drafted responses, pricing recommendations) before demonstrating infrastructure (email routing). Webform-first achieves this.

---

## Gmail Credential-Free Wiring Approach

Gmail wiring (EMAIL-001, EMAIL-002, EMAIL-003) is included in Sprint 4 as structural scaffolding. The implementation must:

- Define provider interfaces (`GmailSMTPProvider`, `GmailIMAPProvider`) with clear method signatures
- Load SMTP and IMAP credentials from environment variables (`GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `IMAP_HOST`, etc.)
- Return a graceful no-op or log a warning when credentials are absent — never raise an unhandled exception at startup
- Guard all send and poll operations with an `EMAIL_ENABLED` feature flag (default: `false`)
- Ensure the application starts and runs normally with no Gmail environment variables set
- Document in `services/api/app/modules/email/README.md` (if created) the exact environment variables needed to activate email

This approach allows Gmail to be activated in a future sprint or by a developer with credentials by setting `EMAIL_ENABLED=true` and supplying credentials — without modifying any code.

---

## Architecture Notes

### Enquiry Intake Orchestration (API-008)

The enquiry intake service sits in `backend/app/modules/enquiries/` and coordinates:
1. Persisting the new enquiry record (PostgreSQL)
2. Applying deterministic pricing rules from the pricing module
3. Selecting the active persona for the restaurant
4. Enqueuing a Celery task for draft response generation

The service is thin — it delegates to the pricing and persona modules. No pricing logic lives outside the pricing module.

### Persona-Based Draft Generation (AI-001)

Draft generation uses the assigned persona's `tone`, `style`, and `greeting` fields to construct a prompt. This is deterministic string interpolation, not ML inference. The generated draft is stored on the `enquiry_messages` table with `message_type = 'draft'`.

### Email Module (EMAIL-001/002/003)

The email module lives in `backend/app/modules/email/`. It exposes:
- A configuration loader that reads from environment variables
- A `SmtpService` with a `send_draft` method guarded by `EMAIL_ENABLED`
- An `ImapService` with a `poll_inbox` method guarded by `EMAIL_ENABLED`
- Celery task stubs for `send_draft_task` and `poll_inbox_task`

No SMTP or IMAP connections are opened unless `EMAIL_ENABLED=true` and valid credentials are present.

---

## Architecture Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Celery task for draft generation fails silently | Medium | Log task state to PostgreSQL `background_jobs` table; surface errors in Enquiry Detail UI |
| EMAIL_ENABLED flag accidentally set true in dev without credentials | Low | Application logs a clear warning; send/poll methods return early with a log message |
| Draft generation prompt produces empty output | Low | Validate draft content before persisting; fall back to a persona-default template string |
| Cross-module import cycle (email imports enquiries, enquiries imports email) | Medium | Email module is write-only from the enquiry perspective; enquiry module never imports email module |
| Webform allows spam submissions | Low | POC only — no rate limiting required; access restricted to test environment |

---

## Success Criteria

All criteria are testable without Gmail credentials.

- [ ] A POST to `/enquiries/intake` with valid webform payload creates an enquiry record in PostgreSQL
- [ ] The created enquiry has a pricing recommendation attached (from deterministic pricing rules)
- [ ] The created enquiry has a persona assigned (active persona for the restaurant)
- [ ] A draft response is generated and stored as an `enquiry_message` with `message_type = 'draft'`
- [ ] GET `/enquiries/{id}/draft` returns the generated draft
- [ ] The test webform UI (UI-010) submits successfully and redirects to the enquiry detail page
- [ ] The enquiry detail page (UI-011) renders the generated draft response
- [ ] The application starts cleanly with no Gmail environment variables set
- [ ] `EMAIL_ENABLED=false` (default) means no SMTP or IMAP connections are attempted
- [ ] Sprint 4 tests (TEST-004) pass in CI

---

## Definition of Done

- All 11 Sprint 4 issues are merged to `main`
- No Gmail credentials are required for the test suite to pass
- The webform-to-draft end-to-end path works against the seeded test data
- Email module is structurally present and guarded by `EMAIL_ENABLED=false`
- DOC-008 sprint completion review is written and merged
- No POC guardrails have been violated (no ML pricing, no production email, no real customer data, no CRM integrations)
