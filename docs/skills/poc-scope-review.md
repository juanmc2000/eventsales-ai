---
name: poc-scope-review
description: Check whether a proposed change, issue, or PR stays within EventSales AI POC scope. Use when asked to review scope, before starting work on an issue that feels large, or when something seems out of place for the POC phase.
---

# POC Scope Review

## Purpose

Confirm that a change, issue, or feature request is within the boundaries defined by `docs/product/POC_SPECIFICATION.md`.

The POC exists to validate the core product experience — not to build production infrastructure, integrate live third-party systems, or implement ML pricing. This skill catches scope creep before it is built.

---

# Required Inputs

Provide one of:

- a GitHub issue number or description
- a PR number
- a feature description to evaluate

---

# POC In-Scope Reference

The following are explicitly in scope for the POC:

**Pages and UI**
- Dashboard (seeded data)
- Pricing Rules (manual CRUD)
- Personas (3 defaults, edit)
- Calendar (seeded demand events)
- Insights / Analytics (seeded data, simple charts)
- Test enquiry webform
- Enquiry list and detail view

**Backend**
- FastAPI modular monolith
- PostgreSQL with SQLAlchemy + Alembic
- Redis + Celery background jobs
- Manual deterministic pricing rules (no ML)
- Persona-based AI response generation (Anthropic API)
- Gmail SMTP test email sending
- Gmail IMAP inbound inbox reading
- Seed data generation (fake restaurants, personas, enquiries, demand events)

**Data**
- 4 seeded test restaurants
- 3 default personas
- 1 year of fake demand events
- Fake enquiries across all statuses
- No real customer data

**Infrastructure**
- Docker Compose (local only)
- Python 3.11 / FastAPI / React/Next.js

---

# POC Out-of-Scope Reference

The following are explicitly out of scope for the POC:

**Integrations**
- Salesforce, TripleSeat, Cvent
- OpenTable, SevenRooms, DesignMyNight
- Stripe, Adyen (no deposit collection)
- Live sports APIs, live theatre APIs
- Live school holiday or university calendar APIs
- Live weather APIs
- Competitor pricing APIs

**AI and Pricing**
- ML pricing optimisation
- Predictive pricing models
- Automated revenue management
- AI voice or telephony
- Autonomous multi-step AI sales agents
- Complex prompt governance UI

**Production Readiness**
- Production authentication (enterprise SSO, MFA)
- Cloud deployment (AWS, GCP, Azure)
- CI/CD pipelines
- Production monitoring (Datadog, Sentry, etc.)
- Multi-tenant production hardening (RLS, isolated schemas)
- Kubernetes or Docker Swarm

**Data**
- Real customer data
- Real restaurant data (unless manually provided for testing)
- CRM historical import
- Production email inboxes

---

# Review Steps

## 1. Identify what is being proposed

Read the issue or PR. Write one sentence describing what it adds or changes.

---

## 2. Check against in-scope list

Is the proposed change clearly in the POC in-scope list above?

- If yes → proceed, no scope concern.
- If it is not on either list → use judgement. Ask: does it support the 10 POC success criteria in `docs/product/POC_SPECIFICATION.md` section 10?

---

## 3. Check against out-of-scope list

Does the proposed change introduce anything on the out-of-scope list?

- If yes → flag it and do not implement.

---

## 3a. Check UI/UX Reference Pack compliance (frontend issues only)

The UI/UX Reference Pack is a **delivery constraint system**, not optional inspiration.

For any frontend issue or PR:

- Does the issue include `## UI/UX Reference Requirements` with specific reference images?
- Is the implementation constrained to `design/reference_images/` and `design/docs/`?
- Is the dark left sidebar + dark topbar + light main workspace shell preserved?
- Are only approved colour tokens from `design/docs/UI_DESIGN_SYSTEM.md` used?

Watch for these UI scope violations:

| Pattern | Concern |
|---|---|
| "Improve the layout while I'm here" | Out of scope — only implement the referenced issue |
| "The sidebar looks better in light mode" | Shell must stay dark — see UI_DESIGN_SYSTEM.md |
| "I added a modern card design" | Must match reference pack — not generic SaaS styling |
| "I replaced the KPI colours" | KPI card colours are fixed tokens — do not change sequence |
| "I added a floating action button" | Not in the reference pack — flag before implementing |

If the issue does not include reference images for a frontend change, flag and ask the author to add them.

---

## 4. Check for hidden scope expansion

Watch for these patterns even when they sound reasonable:

| Pattern | Concern |
|---|---|
| "Just add Stripe for deposit testing" | Stripe is out of scope for POC |
| "Connect to a live sports API for better data" | Live sports integration is out of scope |
| "Use ML to improve pricing accuracy" | ML pricing is post-MVP |
| "Add a production auth flow" | Production auth is not required for POC |
| "Split this into its own service" | No microservices during POC |
| "Add a second database for analytics" | No data warehouse during POC |
| "This feature needs a webhook from Salesforce" | No CRM integrations during POC |

---

## 5. Output the review

```md
## POC Scope Review — <issue or PR>

### Verdict
IN SCOPE / OUT OF SCOPE / PARTIAL — NEEDS TRIMMING

### What is being proposed
<one sentence>

### In-Scope Items
- ...

### Out-of-Scope Items (if any)
- ...

### UI/UX Reference Pack Check (frontend issues only)
- [ ] Issue includes `## UI/UX Reference Requirements`
- [ ] Specific reference image(s) identified
- [ ] Shell layout preserved
- [ ] No unapproved design tokens

### Recommendation
- Proceed as written
- OR: Trim <specific item> before implementing
- OR: Defer entirely to MVP — raise a new issue tagged MVP
```

---

# Stop Conditions

Do not implement and raise with the user if:

- The change requires a live third-party integration not in scope
- The change requires real customer data
- The change introduces ML pricing
- The change introduces a production deployment requirement
- The change fundamentally expands what the POC is supposed to validate

---

# References

- `docs/product/POC_SPECIFICATION.md` — authoritative POC scope (sections 7–11 especially)
- `docs/business/business-capabilities.md` — POC vs deferred capability map
- `CLAUDE.md` — POC guardrails summary
