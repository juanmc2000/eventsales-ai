# ADR-001: Modular Monolith Architecture

## Status

Accepted

## Date

2026-05-20

## Context

EventSales AI is being built from scratch as a POC to validate the core product experience. The team needs to move quickly, deploy simply, and maintain strong code boundaries without the operational overhead of microservices.

Key constraints for the POC:

- Single developer / small team building quickly
- Local development only during POC (Docker Compose)
- No production deployment required during POC
- Strong module boundaries are required to prevent logic from spreading across the codebase
- The architecture must allow future service extraction without a full rewrite

The system has clearly separable business domains:

- Authentication and tenancy
- Restaurant and room management
- Persona configuration
- Pricing rule engine
- Enquiry management
- Email and communication
- Calendar and demand intelligence
- Insights and analytics
- Dashboard aggregation

## Decision

The POC and initial MVP will use a **modular monolith** architecture.

All backend modules are deployed as a single FastAPI application. Modules have clearly defined boundaries: their own routes, services, repositories, and schemas. Modules do not import each other's internal layers.

## Options Considered

### Option A: Microservices from day one

Each domain is a separate deployable service with its own database and API.

**Rejected because:**
- Massive operational overhead for a POC
- Requires inter-service communication (HTTP, gRPC, or messaging)
- Complex local development setup
- No business justification at POC scale
- Premature optimisation for a product not yet validated

### Option B: Monolith without module boundaries

A single FastAPI app with no internal separation — routes, logic, and queries mixed freely.

**Rejected because:**
- Logic spreads freely across the codebase as it grows
- Makes future service extraction very difficult
- Difficult to reason about, test, and maintain
- Cannot enforce the principle that pricing logic stays in the pricing module

### Option C: Modular monolith (chosen)

A single deployable FastAPI app with strong internal module boundaries.

**Chosen because:**
- Single deployment unit — simple for POC and early MVP
- Clear boundaries enforced by directory structure and code conventions
- No inter-service networking to manage
- Future service extraction is possible: each module can become a service if warranted
- Aligns with team size and velocity needs

## Module Boundary Guardrails

The following rules must be followed:

1. **Thin route handlers.** No business logic in route handlers. Route handlers call services only.
2. **Services own business logic.** Each module has a `services/` layer containing all business rules.
3. **Repositories own persistence.** Each module has a `repositories/` layer for all database queries.
4. **Pydantic schemas define API contracts.** `schemas/` contains all request/response models.
5. **Modules do not import each other's internal layers.** If cross-module data is needed, it is accessed via a service interface — never by importing another module's repository.
6. **Pricing logic stays in the pricing module.** No pricing calculations occur outside `modules/pricing/`.
7. **Email logic stays in the email module or worker queue.** No email sending occurs outside `modules/email/` or the Celery worker.

## Module Structure

```
backend/app/modules/
├── auth/
├── restaurants/
├── personas/
├── pricing/
├── enquiries/
├── email/
├── calendar/
├── insights/
└── dashboard/
```

Each module contains:

```
<module>/
├── router.py       # FastAPI route handlers (thin)
├── services.py     # Business logic
├── repositories.py # Database queries
├── schemas.py      # Pydantic request/response models
└── models.py       # SQLAlchemy ORM models (if applicable)
```

## Consequences

### Positive

- Simple local development with Docker Compose
- Single deployment unit during POC
- Strong boundary enforcement through directory structure
- Future service extraction is possible per module if needed
- Easy to onboard: one codebase, one app to run

### Negative

- All modules share the same database and process — a bug in one module can affect others
- Cannot scale individual modules independently (not a POC concern)
- Must enforce module boundaries through discipline and code review (no technical enforcement during POC)

## Future Considerations

If any module warrants independent scaling or deployment in the MVP or beyond (e.g., the email/worker module, or the pricing engine), it can be extracted to a separate service without a full rewrite because the boundary already exists.

Microservices should only be introduced when there is a clear operational or scaling justification — not as a default architectural choice.
