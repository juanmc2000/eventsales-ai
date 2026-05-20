---
name: code-quality-review
description: Review a PR or code change for code quality, layering discipline, type safety, and test coverage. Use when asked to review code quality, check for logic in the wrong layer, or validate that new code is clean and maintainable.
---

# Code Quality Review

## Purpose

Review code changes for quality, correctness, and maintainability within the EventSales AI POC standards.

This skill checks:

- layer separation (routes, services, repositories, schemas)
- type annotations and Pydantic schema usage
- test coverage for new behaviour
- error handling at system boundaries
- no speculative or over-engineered code
- no unused code committed

This is not an architecture review (use `architecture-review` for that) and not a scope review (use `poc-scope-review` for that).

---

# Required Inputs

Provide one of:

- a PR number, e.g. `#20`
- a branch name
- specific files to review

---

# Review Steps

## 1. Fetch the change

```bash
gh pr view <number>
git diff main...<branch>
```

Read all changed files. Do not review from memory.

---

## 2. Check layer discipline

Each file should do one thing:

| File | Allowed content |
|---|---|
| `router.py` | Route definitions, dependency injection, request/response shapes only |
| `services.py` | Business logic, orchestration, calls to repositories |
| `repositories.py` | Database queries via SQLAlchemy only |
| `schemas.py` | Pydantic input/output models only |
| `models.py` | SQLAlchemy ORM model definitions only |

**Flags:**

- Database query in `services.py` directly (bypass repository layer)?
- Business logic in `router.py`?
- HTTP concern (status code, response model) in `services.py`?
- Raw SQL string in application code instead of SQLAlchemy?

---

## 3. Check type annotations

- Do all function signatures have type annotations (arguments and return type)?
- Are Pydantic models used for all API request and response bodies?
- Are SQLAlchemy models not used directly as API response types?

**Violation example:**

```python
# BAD — no return type, raw dict as response
def get_enquiry(enquiry_id):
    return {"id": enquiry_id, "status": "new"}

# GOOD
def get_enquiry(enquiry_id: str) -> EnquiryOut:
    ...
```

---

## 4. Check error handling

- Are errors at system boundaries (external calls, DB, email) caught and handled?
- Do route handlers return structured error responses (not raw exceptions)?
- Are Celery task failures logged to PostgreSQL where relevant?

**Flags:**

- Bare `except Exception` that swallows errors silently?
- Stack trace exposed directly in an API response?
- Email send failure with no `email_events` record written?

---

## 5. Check for over-engineering

The POC standard: build exactly what the issue requires. Flag:

- Abstractions created for a single use case
- Configurable behaviour that has no current use
- Helper utilities that wrap one line of standard library code
- Speculative future-proofing not required by the issue

---

## 6. Check for unused code

- Imported modules not used?
- Functions defined but never called?
- Variables assigned but never read?
- TODO comments left in committed code without a linked issue?

---

## 7. Check test coverage

For each new function or endpoint:

- Is there a test in `tests/api/`, `tests/workers/`, or `tests/integration/`?
- Does the test cover the happy path at minimum?
- Are there tests for known failure modes (invalid input, missing record)?

**POC standard:** full test coverage is not required, but architecture-critical paths must have tests. Refer to `docs/business/non-functional-requirements.md` for the test strategy.

Flags:

- New API endpoint with no corresponding test?
- New Celery task with no import/registration test?
- Pricing rule change with no determinism test?

---

## 8. Output the review

```md
## Code Quality Review — <PR or branch>

### Verdict
PASS / PASS WITH NOTES / NEEDS CHANGES

### Layer Issues
- ...

### Type Annotation Issues
- ...

### Error Handling Issues
- ...

### Over-Engineering Flags
- ...

### Test Coverage Gaps
- ...

### Checklist
- [ ] Route handlers are thin — no business logic
- [ ] Services contain business logic only
- [ ] Repositories contain database queries only
- [ ] All function signatures have type annotations
- [ ] Pydantic schemas used for API contracts
- [ ] Errors handled at system boundaries
- [ ] No bare except blocks that swallow errors silently
- [ ] No unused imports or dead code committed
- [ ] No speculative abstractions for single-use cases
- [ ] New behaviour has at least a smoke test
- [ ] No TODO comments without a linked issue
```

---

# Stop Conditions

Stop and raise with the author if:

- A module's layering is systematically broken (logic spread across all layers)
- A Celery task has no error handling and no PostgreSQL write on failure
- Pricing logic is implemented outside `modules/pricing/`
- A new dependency is introduced without being in `requirements.txt`

---

# References

- `docs/architecture/module-boundaries.md` — layer rules
- `docs/business/non-functional-requirements.md` — test strategy and quality targets
- `docs/adr/ADR-001-modular-monolith.md` — module boundary guardrails
- `CLAUDE.md` — backend-specific coding rules
