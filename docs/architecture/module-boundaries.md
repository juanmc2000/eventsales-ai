# Module Boundaries

## Purpose

This document defines the internal module structure of the EventSales AI backend and the boundaries each module must respect.

## POC Scope

The backend is a **modular monolith**. All modules are deployed as a single FastAPI application. Modules must have clear boundaries. Modules must not reach into each other's internal services or repositories.

See `docs/adr/ADR-001-modular-monolith.md` for the full architecture decision record.

## Backend Module Structure

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

## Module Definitions

### auth

Responsibilities:
- User authentication (JWT)
- Session management
- Role-based access control (RBAC)
- Tenant identification from request context

### restaurants

Responsibilities:
- Restaurant CRUD
- Room management
- Asset references
- Restaurant group assignment

### personas

Responsibilities:
- Persona CRUD
- Persona-to-restaurant assignment
- Persona configuration attributes
- Sample response generation

### pricing

Responsibilities:
- Pricing rule CRUD
- Minimum spend calculation
- Rule priority resolution
- Pricing recommendation explainability

No pricing logic may live outside this module.

### enquiries

Responsibilities:
- Enquiry creation (webform and email)
- Enquiry classification
- Enquiry status management
- Enquiry timeline
- Escalation logic

### email

Responsibilities:
- Test email sending (Gmail SMTP, via Celery)
- Inbound email inbox reading (IMAP, via Celery)
- Email event logging

No email sending may occur outside this module or the worker queue.

### calendar

Responsibilities:
- Demand event management
- Calendar display data
- Date-level pricing impact data

### insights

Responsibilities:
- Enquiry analytics
- Venue performance metrics
- Pricing rule usage stats

### dashboard

Responsibilities:
- Aggregated KPI calculation
- Recent enquiry summaries
- Pending follow-up indicators

## Module Boundary Rules

- Route handlers must be thin. No business logic in route handlers.
- Business logic lives in `services/` within each module.
- Persistence logic lives in `repositories/` within each module.
- API contracts use `schemas/` (Pydantic models).
- Modules communicate via service interfaces, not by importing each other's repositories.
- Pricing logic stays inside the `pricing` module.
- Email sending stays inside the `email` module or worker queue.

## POC Limitations

- No inter-module event bus during POC
- No module-level database schema isolation
- No module-level API versioning during POC
