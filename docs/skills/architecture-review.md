---
name: architecture-review
description: Review a PR or code change against EventSales AI architecture guardrails. Use when asked to review architecture, check module boundaries, or validate that a change preserves the modular monolith, PostgreSQL source-of-truth, and Redis/Celery boundaries.
---

# Architecture Review

## Purpose

Verify that a code change preserves the EventSales AI POC architecture. Catch violations before they are merged.

This skill reviews:

- modular monolith boundaries
- module layer separation (routes → services → repositories)
- database ownership (PostgreSQL as source of truth)
- background job boundaries (Celery/Redis)
- frontend/backend separation
- POC scope boundaries

---

# Required Inputs

Provide one of:

- a PR number, e.g. `#20`
- a branch name
- a file path or diff to review

---

# Review Steps

## 1. Fetch the change

```bash
gh pr view <number> --comments
git diff main...<branch>
```

Read all changed files before forming an opinion.

---

## 2. Check module boundaries

For each changed Python file under `services/api/app/modules/`:

- Does it belong to its own module only?
- Does it import another module's `repositories` or `services` directly?
- Is any business logic sitting in a route handler (`router.py`)?
- Is pricing logic outside `modules/pricing/`?
- Is email sending logic outside `modules/email/` or the Celery worker?

**Violation examples:**

```python
# BAD — route handler contains business logic
@router.post("/enquiries")
def create_enquiry(data: EnquiryIn, db: Session = Depends(get_db)):
    spend = data.party_size * 45  # pricing logic in route
    ...

# BAD — module A imports module B's repository
from app.modules.pricing.repositories import PricingRepository  # inside enquiries module
```

---

## 3. Check database ownership

- Are all writes going to PostgreSQL via SQLAlchemy?
- Is any durable state written only to Redis?
- Does the change introduce a new database that is not PostgreSQL?

**Violation example:**

```python
# BAD — storing durable enquiry state in Redis
redis_client.set(f"enquiry:{id}", json.dumps(enquiry_data))
# No PostgreSQL write. Redis is not the source of truth.
```

---

## 4. Check background job boundaries

For any Celery task change:

- Does the task write its outcome to PostgreSQL (not only Redis)?
- Is the task idempotency-aware (checks for existing records before inserting)?
- Is the task on the correct queue (`email`, `inbox`, `enquiry`, `seed`, `metrics`)?
- Does the task handle retry correctly (`max_retries`, `autoretry_for`)?

**Violation example:**

```python
# BAD — task result stored only in Redis result backend, no PostgreSQL write
@app.task
def send_test_email(enquiry_id, ...):
    send_via_smtp(...)
    # No email_events record written to PostgreSQL
```

---

## 5. Check frontend/backend separation

- Is business logic (pricing, persona selection, rule evaluation) duplicated in the frontend?
- Are API responses hardcoding values that should come from the backend?

---

## 6. Check for POC scope violations

See `poc-scope-review` skill for a full scope check. Quick flags:

- New third-party integration introduced? (Salesforce, Stripe, Adyen, live sports API)
- ML pricing logic introduced?
- Microservice introduced?
- Production infrastructure introduced?

---

## 7. Output the review

Structure your response as:

```md
## Architecture Review — <PR or branch>

### Verdict
PASS / FAIL / PASS WITH NOTES

### Violations Found
- ...

### Recommendations
- ...

### Checklist
- [ ] No business logic in route handlers
- [ ] Modules do not import each other's internal layers
- [ ] Pricing logic stays in modules/pricing/
- [ ] Email logic stays in modules/email/ or Celery worker
- [ ] PostgreSQL is the source of truth for all writes
- [ ] Redis used only as broker/cache
- [ ] Celery tasks are idempotency-aware
- [ ] No new database systems introduced
- [ ] No premature microservices
- [ ] No production integrations introduced
- [ ] No ML pricing introduced
- [ ] POC scope preserved
```

---

# Stop Conditions

Stop and raise with the author if:

- A new database system has been introduced without an ADR
- Business logic is entangled in route handlers across multiple files (systemic issue)
- A microservice pattern has been introduced
- A production third-party integration has been added

---

# References

- `docs/adr/ADR-001-modular-monolith.md`
- `docs/adr/ADR-002-celery-redis-background-jobs.md`
- `docs/adr/ADR-003-postgres-source-of-truth.md`
- `docs/architecture/module-boundaries.md`
- `docs/architecture/background-jobs.md`
- `CLAUDE.md`
