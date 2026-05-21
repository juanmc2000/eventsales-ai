# Sprint 5 — Live Gmail Validation

## Sprint Goal

Validate the end-to-end POC email loop using a test Gmail account: activate SMTP sending, add delivery status logging, wire Celery send and inbound intake tasks, expose email activity in the UI, and produce a POC demo and validation guide.

---

## Sprint Non-Goals

- Production email sending to real customers
- OAuth 2.0 Gmail authentication (Gmail App Password only)
- Microsoft 365 / Microsoft Graph integration
- CRM email sync (Salesforce, TripleSeat, Cvent, etc.)
- Bulk or marketing email functionality
- Deliverability infrastructure (SPF, DKIM, DMARC hardening for production)
- ML-based pricing
- Third-party integrations
- Production authentication hardening
- Microservices extraction

---

## Ordered Issue List

| Order | Issue ID | Title | Type |
|-------|----------|-------|------|
| 1 | DOC-009 | Create Sprint 5 Live Gmail Validation Plan | Documentation |
| 2 | UI-012 | Add Send Draft Email Action | Frontend |
| 3 | EMAIL-005 | Add Email Delivery Status Logging | Backend |
| 4 | WORKFLOW-005 | Add Celery Send Email Task | Backend/Worker |
| 5 | WORKFLOW-006 | Create Inbound Email to Enquiry Flow | Backend/Worker |
| 6 | UI-013 | Add Email Activity Timeline to Enquiry Detail | Frontend |
| 7 | TEST-005 | Add End-to-End POC Workflow Tests | Testing |
| 8 | DOC-010 | Create POC Demo and Validation Guide | Documentation |

---

## Live Gmail Testing Assumptions

- A dedicated test Gmail account is used exclusively for POC validation. No real customer or venue email addresses are involved.
- Gmail App Password is configured and stored in local `.env` only — never committed to source control.
- SMTP sending is enabled only when `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, and `SMTP_PASSWORD` environment variables are present.
- IMAP inbox reading is enabled only when `IMAP_HOST`, `IMAP_PORT`, `IMAP_USER`, and `IMAP_PASSWORD` environment variables are present.
- The test account sends and receives within its own mailbox (send to self or to a second test address).
- Rate limits: Gmail SMTP free tier allows ~500 messages/day — the POC will not approach this limit.
- All email addresses used in tests must use `.example.com` domains or the designated test Gmail account. No `.com` / real domains in seeded data.

---

## Credential Setup Checklist

Before running live email validation:

- [ ] Create a dedicated test Gmail account (e.g. `eventsalesai.test@gmail.com`)
- [ ] Enable 2-Step Verification on the test account
- [ ] Generate a Gmail App Password (Google Account → Security → App Passwords)
- [ ] Copy `.env.example` to `.env` and populate the following variables:
  ```
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=<test-gmail-address>
  SMTP_PASSWORD=<app-password>
  IMAP_HOST=imap.gmail.com
  IMAP_PORT=993
  IMAP_USER=<test-gmail-address>
  IMAP_PASSWORD=<app-password>
  ```
- [ ] Confirm `.env` is listed in `.gitignore` (never commit credentials)
- [ ] Restart Docker Compose services after updating `.env`
- [ ] Verify SMTP connection: send one test email via the `/api/v1/email/send-draft` endpoint with a draft enquiry
- [ ] Verify IMAP connection: confirm inbox reader returns at least one message from the test mailbox

---

## Test Gmail-Only Constraint

**This sprint must not send email to any real customer, venue operator, or business email address.**

All email activity during Sprint 5 is confined to:

1. The designated test Gmail account sending to itself or to a second test Gmail account
2. Seeded enquiry data using `.example.com` guest email addresses
3. Manual validation steps documented in DOC-010

Any attempt to route live email to real external addresses is out of scope and violates POC guardrails.

---

## Operational Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Gmail App Password not set — SMTP/IMAP stays disabled | Medium | Credential setup checklist in this document |
| App Password revoked or expired mid-sprint | Low | Re-generate and update `.env`; services activate automatically on restart |
| Gmail rate limit hit during testing | Very Low | POC volumes are well below 500/day free tier limit |
| Inbound email parser misidentifies enquiry match | Medium | WORKFLOW-006 scoped to enquiry ID matching only; unmatched emails are logged and discarded |
| Celery task retry storm on SMTP failure | Low | Use `max_retries=3` with exponential backoff; log failure to `email_events` table |
| Credentials committed to source control | Low | `.env` in `.gitignore`; pre-commit check documented in DOC-010 |
| Docker Compose network issue prevents Celery from reaching Redis | Low | Verify `docker compose ps` before running live tests |
| Frontend send action triggers duplicate sends | Medium | Disable send button after first click; backend deduplicates by `enquiry_id` + draft hash |

---

## POC Success Criteria

The following outcomes must be demonstrated during Sprint 5 validation:

- [ ] A draft response generated in the Enquiry Detail Drawer can be sent via SMTP to the test Gmail inbox
- [ ] The `email_events` table records a `sent` status entry for the outbound message
- [ ] A reply to the test Gmail inbox is read by the IMAP reader Celery task
- [ ] The inbound email is parsed and appended as a new `enquiry_messages` row on the correct enquiry
- [ ] The Email Activity Timeline in the Enquiry Detail Drawer shows both the outbound and inbound messages
- [ ] The full webform → draft → send → receive → timeline loop is demonstrable with no manual database edits
- [ ] TEST-005 end-to-end tests pass with SMTP/IMAP credentials present (or with mocked providers if credentials absent)
- [ ] DOC-010 demo guide allows a new observer to reproduce the full loop independently

---

## Architecture Guardrails

All Sprint 5 work must preserve the architecture established in Sprints 1–4:

| Guardrail | Rule |
|-----------|------|
| Modular monolith | All new code lives inside `services/api/app/modules/` or `services/web/` |
| PostgreSQL source of truth | Email event state is written to `email_events` table — not only to Redis |
| Celery for async work | SMTP send and IMAP read run as Celery tasks — not synchronous in the request cycle |
| Redis as broker only | No durable state stored exclusively in Redis |
| Email module boundary | All email logic stays in `services/api/app/modules/email/` |
| No ML pricing | Pricing recommendations remain deterministic rule output |
| No production integrations | Gmail test account only — no SendGrid, Mailgun, or Postmark |
| Fake/seeded data only | Enquiries used in tests come from the seeded dataset |

---

## Definition of Done

- All 8 Sprint 5 issues are merged to `main`
- Live SMTP send is demonstrated against the test Gmail account
- Live IMAP read is demonstrated, with at least one inbound email parsed into `enquiry_messages`
- `email_events` table reflects accurate `sent` and `received` records
- Email Activity Timeline renders in the Enquiry Detail Drawer
- TEST-005 test suite passes
- DOC-010 demo guide is complete and peer-reviewed
- No credentials committed to source control
- No real customer or venue email addresses used at any point
- No POC guardrails violated
