# Sprint 2 — Product Data Foundation

## Sprint Goal

Establish the product data foundation for the EventSales AI POC: database schema, migrations, seed data, and backend module APIs for restaurants, personas, pricing rules, demand calendar, and enquiries — with baseline test coverage.

---

## Sprint Non-Goals

- Frontend implementation (deferred to Sprint 3)
- Gmail SMTP / IMAP integration (deferred)
- ML pricing (out of scope for POC)
- Production authentication hardening
- Third-party CRM integrations (Salesforce, TripleSeat, Cvent, etc.)
- Microservices extraction
- Live third-party data (sports, theatre, university APIs)
- Real customer or restaurant data
- Production email sending to real recipients

---

## Ordered Issue List

| Order | Issue ID | Title | Type |
|-------|----------|-------|------|
| 1 | DOC-005 | Create Sprint 2 Product Foundation Plan | Documentation |
| 2 | DOC-006 | Add UI/UX Reference Pack Rules to Issue Governance | Documentation |
| 3 | DATA-002 | Add Alembic Migration Framework | Data |
| 4 | DATA-003 | Create Core POC Database Models and Initial Migration | Data |
| 5 | DATA-004 | Add POC Seed Data Framework | Data |
| 6 | API-002 | Add Restaurant Backend Module | Backend |
| 7 | API-003 | Add Persona Backend Module | Backend |
| 8 | API-004 | Add Deterministic Pricing Rules Backend Module | Backend |
| 9 | API-005 | Add Demand Calendar Backend Module | Backend |
| 10 | API-006 | Add Enquiry Backend Foundation | Backend |
| 11 | TEST-002 | Add Sprint 2 Backend Test Coverage Baseline | Testing |

---

## Product Scope

Sprint 2 delivers the following product capabilities in a testable but non-production state:

### Database Models

- `restaurants` — multi-tenant venue records
- `personas` — AI communication persona definitions
- `restaurant_personas` — persona assignment to restaurants
- `pricing_rules` — deterministic pricing rule records
- `enquiries` — inbound event enquiry records
- `enquiry_messages` — message thread per enquiry
- `email_events` — email send/receive log
- `calendar_events` — event bookings
- `demand_events` — demand signal records (fake seeded data)
- `insight_snapshots` — pre-computed insight records

### Backend APIs

- Restaurant CRUD (list, get, create, update, delete)
- Persona CRUD
- Pricing rule CRUD with restaurant assignment
- Demand calendar read (list demand events by date range, by restaurant)
- Enquiry CRUD with status management

### Seed Data

- 4 test restaurants with profiles
- 3 personas with tone and style definitions
- Pricing rules per restaurant
- 1 year of fake demand events
- Representative fake enquiries

---

## Architecture Guardrails

All Sprint 2 work must preserve Sprint 1 architecture decisions:

| Guardrail | Rule |
|-----------|------|
| Modular monolith | All modules in one FastAPI app — no microservices |
| PostgreSQL source of truth | All durable state in PostgreSQL — Redis is broker/cache only |
| Redis/Celery | Background jobs via Celery — not inline in API handlers |
| Module boundaries | Each domain has its own `modules/<domain>/` directory |
| Multi-tenancy | All models must carry tenant context |
| Deterministic pricing | No ML pricing — rules only |
| POC email | Gmail SMTP test accounts only — no production sending |
| No live integrations | No Salesforce, TripleSeat, Cvent, Stripe, Adyen |

### ADRs in force

- ADR-001: Modular Monolith
- ADR-002: Celery + Redis Background Jobs
- ADR-003: PostgreSQL as Source of Truth

---

## UI/UX Governance (Active from Sprint 2)

UI implementation is deferred to Sprint 3, but UI governance is active now. All future frontend issues must:

- Reference the UI/UX Reference Pack (`design/docs/` and `design/reference_images/`)
- Include a `## UI/UX Reference Requirements` section
- Specify page-specific reference images
- Preserve the dark left sidebar, dark topbar, and light main workspace shell
- Use only approved design tokens from `design/docs/UI_DESIGN_SYSTEM.md`
- Not redesign any UI element outside the scope of the issue

---

## Success Criteria

| Criterion | Test |
|-----------|------|
| Alembic migrations run cleanly | `alembic upgrade head` succeeds from clean state |
| All 10 core tables exist | Schema inspection confirms tables present |
| Seed data loads without error | Seed script runs successfully |
| Seed produces 4 restaurants | Query returns 4 restaurant records |
| Seed produces 3 personas | Query returns 3 persona records |
| Restaurant API responds | `GET /api/v1/restaurants` returns 200 |
| Persona API responds | `GET /api/v1/personas` returns 200 |
| Pricing rules API responds | `GET /api/v1/pricing-rules` returns 200 |
| Demand calendar API responds | `GET /api/v1/demand-events` returns 200 |
| Enquiry API responds | `GET /api/v1/enquiries` returns 200 |
| Backend tests pass | `pytest` returns no failures |
| No ML pricing introduced | Code review confirms no ML model usage |
| No production integrations | No live third-party API keys or calls |

---

## Known Risks

| Risk | Mitigation |
|------|-----------|
| SQLAlchemy model complexity grows beyond POC needs | Keep models minimal — only POC-required fields |
| Alembic auto-generation misses relationships | Review migration scripts before applying |
| Seed data volume causes slow tests | Use small representative datasets in tests |
| Multi-tenancy enforcement gaps | Add tenant_id to all models; middleware review in TEST-002 |
| Over-engineering module abstractions | Follow issue-scoped file boundaries strictly |

---

## Definition of Done

A Sprint 2 issue is done when:

- [ ] Branch created from `main`
- [ ] Only allowed files modified
- [ ] No protected areas changed
- [ ] No secrets committed
- [ ] No real customer data included
- [ ] POC scope preserved
- [ ] Relevant tests pass or absence documented
- [ ] PR created with required sections
- [ ] PR linked to issue
- [ ] Architecture guardrails confirmed in PR body
