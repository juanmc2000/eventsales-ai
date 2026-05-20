# Testing

EventSales AI uses [pytest](https://docs.pytest.org/) for the backend test suite.

---

## Test Categories

| Marker | Description | DB required? |
|--------|-------------|--------------|
| `smoke` | Schema validation, import checks, business logic invariants | No |
| `unit` | Isolated service/repository logic with mocks | No |
| `integration` | Full stack tests against live PostgreSQL | Yes |

---

## Running Tests

### Smoke and unit tests only (no database required)

```bash
cd services/api
pytest -m "not integration"
```

### All tests (requires PostgreSQL running and migrations applied)

```bash
# Start services
docker-compose up -d

# Apply migrations
cd services/api
alembic upgrade head

# Run all tests
pytest
```

### Sprint 2 baseline only

```bash
cd services/api
pytest tests/test_sprint2_baseline.py -v
```

### Single test

```bash
cd services/api
pytest tests/path/to/test_file.py::test_name -v
```

---

## Test File Structure

```
services/api/tests/
├── conftest.py                         # pytest fixtures and configuration
├── test_sprint2_baseline.py            # Sprint 2 consolidated smoke tests
├── test_models_import.py               # Model metadata smoke tests (DATA-003)
├── test_seed_data.py                   # Seed data validation (DATA-004)
├── restaurants/
│   └── test_restaurant_schema.py       # Restaurant schema tests (API-002)
├── personas/
│   └── test_persona_schema.py          # Persona schema tests (API-003)
├── pricing/
│   └── test_pricing_schema.py          # Pricing rule schema and logic (API-004)
├── calendar/
│   └── test_calendar_schema.py         # Calendar/demand event schema (API-005)
└── enquiries/
    └── test_enquiry_schema.py          # Enquiry schema tests (API-006)
```

---

## Coverage Baseline (Sprint 2)

The Sprint 2 baseline (`test_sprint2_baseline.py`) covers:

- All module imports compile without error
- All 10 POC tables registered in `Base.metadata`
- Restaurant slug pattern validation
- Persona assignment defaults
- Pricing rule day_of_week and minimum_spend validation
- Pricing recommendation `confidence=1.0` (deterministic only, no ML)
- Demand event score range (0–1)
- Enquiry email and message direction validation
- Enquiry status lifecycle set matches specification
- Seed data counts (4 restaurants, 3 personas)
- Seed email safety (`.example.com` domains)
- Seed data has no ML pricing fields
- Alembic migration imports correctly

---

## Adding Tests

- Smoke tests go in `tests/` or `tests/<module>/`.
- Integration tests that require a database should be marked `@pytest.mark.integration`.
- Never commit tests that depend on real customer data or production credentials.
- Pricing rule tests must assert deterministic behaviour — no ML model tests.

---

## POC Constraints

- No browser tests (deferred to MVP)
- No Gmail SMTP/IMAP integration tests (live email is POC-only; use mock where needed)
- No load tests
- Integration tests use local Docker Compose PostgreSQL only
