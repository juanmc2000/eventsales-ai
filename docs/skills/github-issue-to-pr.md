---
name: github-issue-to-pr
description: Work on one EventSales AI GitHub issue at a time, only modifying files allowed by the issue, then create a PR with clear notes. Use when asked to implement a specific GitHub issue.
---

# GitHub Issue to PR Workflow

## Purpose

Implement exactly one GitHub issue at a time with strict scope control.

This skill is designed for the EventSales AI POC and must preserve:

- POC scope
- modular monolith architecture
- FastAPI backend boundaries
- PostgreSQL source-of-truth model
- Redis/Celery background job architecture
- frontend/backend separation
- issue-defined file boundaries

---

# Required Inputs

The user must provide either:

- a GitHub issue number, e.g. `DEVOPS-001`, `API-001`, `DOC-002`
- a GitHub issue number such as `#12`
- or a GitHub issue URL

If the issue is ambiguous, ask for clarification before making changes.

---

# Core Rules

- Work only on the specified issue.
- Read the issue before making changes.
- Only modify files explicitly listed in the issue’s `Allowed Files` section.
- If the issue does not list allowed files, stop and ask the user to clarify.
- Do not modify protected areas.
- Do not redesign architecture.
- Do not introduce new dependencies unless the issue explicitly allows it.
- Do not work on future issues.
- Do not implement out-of-scope improvements.
- Do not modify unrelated documentation.
- Do not overwrite `docs/product/POC_SPECIFICATION.md`.
- Do not commit secrets.
- Do not store real customer data.
- Do not add production integrations during the POC.
- Do not add ML pricing during the POC.
- Follow `CLAUDE.md`.

---

# EventSales AI Architecture Rules

All implementation must preserve:

- modular monolith architecture
- Python/FastAPI backend
- React/Next.js frontend
- PostgreSQL as source of truth
- Redis as broker/cache only
- Celery for background jobs
- Docker Compose for local development
- deterministic pricing rules
- persona-based communication
- POC-only Gmail SMTP and inbox reading
- no production third-party integrations

Do not introduce:

- microservices
- Neo4j
- Kafka
- Temporal
- Kubernetes
- Salesforce
- Stripe
- Adyen
- live sports/theatre/university APIs
- ML pricing
- customer-facing production email sending

unless a future issue explicitly allows it.

---

# Required Workflow

## 1. Confirm clean working tree

Run:

```bash
git status
````

If there are uncommitted changes, stop and ask the user how to proceed.

---

## 2. Fetch the issue

Use:

```bash
gh issue view <issue-number> --comments
```

Summarize:

* objective
* business context
* scope
* allowed files
* protected areas
* out-of-scope items
* acceptance criteria

If the issue does not include allowed files, stop.

---

## 3. Create a branch

Use branch format:

```text
issue/<issue-id>-short-title
```

Examples:

```text
issue/devops-001-repo-structure
issue/api-001-fastapi-skeleton
issue/workflow-001-celery-worker-skeleton
```

---

## 4. Plan the change

Before editing files, list:

* exact files to create
* exact files to modify
* exact files to leave untouched
* relevant acceptance criteria

Confirm every file is allowed by the issue.

If implementation requires a file not listed in `Allowed Files`, stop.

### Frontend issues: UI/UX Reference Requirements

If the issue touches any frontend file, the issue body must include a `## UI/UX Reference Requirements` section specifying:

* page-specific reference image(s) from `design/reference_images/`
* which design system docs apply (`design/docs/UI_DESIGN_SYSTEM.md`, `design/docs/UI_COMPONENT_RULES.md`, etc.)
* UI guardrails that apply to the page

If a frontend issue lacks a `## UI/UX Reference Requirements` section, stop and ask the author to add it before implementing.

Do not implement frontend changes without confirmed reference images. Do not redesign any layout element outside the issue scope.

---

## 5. Implement

Implementation rules:

* Modify only approved files.
* Keep changes minimal.
* Prefer simple, readable code.
* Do not create speculative abstractions.
* Do not add unused infrastructure.
* Do not add unrelated docs.
* Do not change POC scope.
* Use clear comments only where intent is not obvious.

Backend-specific rules:

* Keep FastAPI route handlers thin.
* Put business logic in services.
* Put persistence logic in repositories.
* Use Pydantic schemas for API contracts.
* Use SQLAlchemy only where scoped.
* Do not implement pricing logic outside the pricing module.
* Do not implement email logic outside the email module or worker queue.

Frontend-specific rules:

* Do not duplicate backend business logic.
* Do not hardcode pricing rules in UI.
* Use API-driven state where available.
* Keep POC UI simple.

Worker-specific rules:

* Use Celery.
* Use Redis as broker.
* Ensure tasks are idempotency-aware.
* Do not store durable state only in Redis.
* Keep job state in PostgreSQL when implemented.

---

## 6. Validate

### Frontend issues: UI drift check

For any frontend change, validate against the reference pack before committing:

* Does the implementation match the page-specific reference image?
* Does the shell (sidebar, topbar) remain unchanged?
* Are only approved design tokens used?
* Is there no generic CRM, chatbot, or consumer-app styling introduced?

If UI drift is detected, correct it before committing.

### Backend / data / doc issues

Run only relevant checks.

Examples:

```bash
pytest
```

```bash
python -m compileall services packages
```

```bash
docker compose config
```

```bash
ruff check .
```

Only run checks that are available in the repo.

If tests/checks are unavailable, document that clearly in the PR.

---

## 7. Review changes

Run:

```bash
git diff
git status
```

Confirm:

* only allowed files changed
* no protected files changed
* no secrets committed
* no unrelated refactors included
* no generated cache files included
* no real customer data included

---

## 8. Commit

Use commit message format:

```text
<ISSUE-ID>: <short description>
```

Examples:

```text
DEVOPS-001: create repository structure
API-001: create FastAPI skeleton
WORKFLOW-001: create Celery worker skeleton
```

---

## 9. Push branch

```bash
git push -u origin <branch-name>
```

---

## 10. Create PR

Use:

```bash
gh pr create
```

PR title format:

```text
<ISSUE-ID>: <short title>
```

Example:

```text
API-001: Create FastAPI application skeleton
```

PR body must include:

```md
## Summary

- ...

## Files Changed

- ...

## Validation

- [ ] Relevant checks/tests run
- [ ] No unrelated files changed
- [ ] No new dependencies added unless approved
- [ ] No secrets committed
- [ ] No real customer data committed
- [ ] POC scope preserved
- [ ] (Frontend only) UI matches page-specific reference image
- [ ] (Frontend only) Shell layout (sidebar, topbar) unchanged
- [ ] (Frontend only) No unapproved design tokens introduced
- [ ] (Frontend only) No generic CRM / chatbot styling introduced

## Scope Confirmation

This PR only addresses the referenced issue and only modifies files allowed by the issue.

## Architecture Confirmation

- [ ] Modular monolith preserved
- [ ] PostgreSQL remains source of truth
- [ ] Redis/Celery boundaries preserved where relevant
- [ ] No production integrations added
- [ ] No ML pricing added

## Linked Issue

Closes #<issue-number>
```

---

## 11. Do not merge automatically

Do not merge the PR unless the user explicitly asks.

---

## 12. Do not close the issue automatically

Do not close the issue unless:

* the PR is merged
* and the user explicitly asks

---

# Stop Conditions

Stop and ask the user if:

* the working tree is dirty
* the issue does not specify allowed files
* implementation requires files not listed in the issue
* a protected area must be modified
* a new dependency seems necessary
* architecture changes are required
* tests fail and the fix is outside issue scope
* POC scope needs to change
* the implementation would require production integrations
* the implementation would require ML pricing
* the implementation would require real customer data

---

# Final Response Template

After completing work, respond with:

```md
Implemented issue: <ISSUE-ID>

Branch:
- <branch-name>

Summary:
- ...

Validation:
- ...

PR:
- <PR URL>

Notes:
- ...
```
