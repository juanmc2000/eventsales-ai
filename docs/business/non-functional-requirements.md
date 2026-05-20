# Non-Functional Requirements

## Purpose

This document defines the non-functional requirements (NFRs) and testing strategy for the EventSales AI POC.

## POC Scope

The POC is a local-only, test-data-only system. NFRs are appropriate to the POC phase. Production-grade performance, scalability, and security requirements are deferred to MVP.

---

## Performance

| Requirement | POC Target | Notes |
|---|---|---|
| API health check response | < 200ms | Baseline benchmark |
| Enquiry creation response | < 2 seconds | Includes DB write |
| Pricing recommendation | < 1 second | Deterministic rule lookup |
| Dashboard load | < 3 seconds | Seeded data |
| Email send (async) | < 30 seconds | Via Celery task |
| Seed data generation | < 60 seconds | One-time task |

---

## Reliability

- Background jobs must be idempotent — duplicate task execution must not create duplicate records.
- All Celery tasks must write durable outcomes to PostgreSQL, not only to Redis.
- Failed email tasks must be logged in `email_events` with `status = failed`.
- API must return structured error responses, not raw stack traces.

---

## Security (POC)

- No `.env` files committed to version control.
- No real customer data stored or processed.
- No production Gmail credentials used.
- JWT secret key must not use the default placeholder in any test environment.
- API endpoints must not expose internal error details to clients.

---

## Testability

- Pricing rules must be deterministic — the same inputs always produce the same recommended spend.
- Seed data must be reproducible — re-running the seed task produces a consistent state.
- Tests must not depend on live external services (Gmail, Anthropic).
- Tests must not rely on specific timing — no `sleep`-based assertions.
- Database tests must use a separate test database or transactions that roll back after each test.

---

## Test Strategy

### Test Categories

#### 1. API Tests (`tests/api/`)

Test the FastAPI application in isolation.

| Test | Purpose |
|---|---|
| `test_health_check` | GET /health returns 200 and {status: ok} |
| `test_settings_load` | Settings module loads without error |
| `test_db_connection` | Database session can be created |
| `test_cors_headers` | CORS headers present for frontend origin |

Future API tests (added per module sprint):
- Enquiry creation endpoint
- Pricing rule CRUD
- Persona CRUD
- Restaurant CRUD
- Calendar data endpoint
- Insights endpoint

#### 2. Worker Tests (`tests/workers/`)

Test the Celery worker configuration and task imports.

| Test | Purpose |
|---|---|
| `test_celery_app_imports` | Celery app instantiates without error |
| `test_all_task_modules_import` | All 6 task modules import cleanly |
| `test_queue_configuration` | All 5 POC queues are defined |
| `test_ping_task` | workers.health.ping task is registered |

Future worker tests (added per feature sprint):
- send_test_email with mocked SMTP
- read_inbox with mocked IMAP
- process_inbound_email with fixture email data
- generate_seed_data idempotency check

#### 3. Data Validation Tests (`tests/integration/`)

Test seeded data integrity and pricing rule determinism.

| Test | Purpose |
|---|---|
| `test_four_restaurants_seeded` | 4 test restaurants exist after seed |
| `test_three_personas_seeded` | 3 default personas exist after seed |
| `test_pricing_rules_deterministic` | Same inputs → same recommended spend |
| `test_demand_events_seeded` | 1 year of demand events exist |
| `test_enquiry_statuses_valid` | All enquiry statuses are from allowed set |

#### 4. Frontend Smoke Tests

Not implemented during POC. Manual browser testing is sufficient for POC validation.

---

## POC Success Criteria (Testable)

The POC is testable end-to-end when:

1. `GET /health` returns `{status: ok}`
2. The database connection is reachable from the API
3. The Celery worker starts and the ping task responds
4. Seed data can be generated and verified in the database
5. A test enquiry can be submitted via the webform and appears in the dashboard
6. A test inbound email can be read and creates an enquiry record
7. A test email can be sent via Gmail SMTP and is logged in `email_events`
8. The calendar shows demand events for the current month
9. The insights page renders charts from seeded data

---

## Test Tooling

| Tool | Purpose |
|---|---|
| `pytest` | Python test runner |
| `pytest-asyncio` | Async test support |
| `httpx` | FastAPI test client (via `AsyncClient`) |
| Docker Compose | Integration test infrastructure |

No browser automation (Selenium, Playwright) during POC.

---

## POC Limitations

- No CI/CD pipeline during POC — tests run manually
- No code coverage enforcement during POC
- No load testing during POC
- No penetration testing during POC
- No browser automation during POC
