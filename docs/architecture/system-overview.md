# System Overview

## Purpose

This document provides a high-level overview of the EventSales AI system architecture for the POC phase.

## POC Scope

The POC validates the core product experience across five functional areas:

- configurable restaurant event sales workflows
- basic enquiry intake (webform + inbound email)
- persona-based AI communication
- manual deterministic pricing rules
- commercial dashboard, calendar, and basic analytics

The POC runs entirely locally using Docker Compose. No production deployment, no real customer data, no live third-party integrations.

## System Components

### Backend API

- **Runtime:** Python 3.11
- **Framework:** FastAPI
- **Role:** Serves all product APIs. Contains all business logic in a modular monolith structure.

### Frontend

- **Framework:** React / Next.js
- **Role:** Single-page application. API-driven. No business logic in the UI.

### Database

- **System:** PostgreSQL
- **Role:** Source of truth for all persistent data. All entities are written to and read from PostgreSQL.

### Cache / Message Broker

- **System:** Redis
- **Role:** Celery task broker and short-lived cache. Not a system of record. No durable state stored only in Redis.

### Background Workers

- **System:** Celery
- **Role:** Handles async jobs: test email sending, inbox reading, email-to-enquiry processing, seed data generation, and metric refreshes.

## High-Level Data Flow

```
Inbound Enquiry (Webform or Email)
        ↓
  FastAPI Endpoint / Celery Inbox Reader
        ↓
  Enquiry Record Created (PostgreSQL)
        ↓
  AI Classification + Persona Selection
        ↓
  Pricing Rule Engine (Deterministic)
        ↓
  Draft Response Generated
        ↓
  Test Email Sent (Gmail SMTP) via Celery
        ↓
  Enquiry Timeline Updated (PostgreSQL)
```

## Architecture Pattern

The POC uses a **modular monolith**. All modules are deployed as a single FastAPI application. Modules have clear internal boundaries. No microservices during POC.

See `docs/adr/ADR-001-modular-monolith.md` for the full decision record.

## Testing Approach

Tests are organised into three directories:

| Directory | Scope |
|---|---|
| `tests/api/` | FastAPI endpoint tests (health check, DB connectivity, CORS) |
| `tests/workers/` | Celery app config and task import tests |
| `tests/integration/` | Seeded data validation, pricing rule determinism |

Full test strategy: `docs/business/non-functional-requirements.md`.

## POC Limitations

- No production authentication
- No enterprise SSO
- No live external data sources (sports, weather, etc.)
- No CRM integrations
- No payment providers
- No ML pricing
- No cloud deployment
