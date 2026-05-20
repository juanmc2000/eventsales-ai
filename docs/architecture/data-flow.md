# Data Flow

## Purpose

This document describes how data flows through the EventSales AI POC system.

## POC Scope

Data flow covers two enquiry intake paths (webform and inbound email), enquiry processing, persona-based response generation, and test email sending.

## Enquiry Intake: Webform

```
User submits test webform
        ↓
POST /api/enquiries (FastAPI)
        ↓
Enquiry record created in PostgreSQL
        ↓
Event type classified
        ↓
Assigned persona selected for restaurant
        ↓
Pricing rule engine calculates minimum spend recommendation
        ↓
Draft response generated using assigned persona
        ↓
Celery task queued: send test email
        ↓
Email sent via Gmail SMTP
        ↓
email_events record written to PostgreSQL
        ↓
Enquiry timeline updated
```

## Enquiry Intake: Inbound Email

```
Celery periodic task: read Gmail inbox (IMAP)
        ↓
Unread/new emails fetched
        ↓
Email parsed: sender, subject, body, timestamp
        ↓
Enquiry record created in PostgreSQL (source = email)
        ↓
Email marked as processed
        ↓
Standard enquiry processing flow (as above)
```

## Dashboard / Insights Data Flow

```
PostgreSQL enquiry and event data
        ↓
Aggregation queries (via FastAPI service layer)
        ↓
Optional: Celery task refreshes cached metrics
        ↓
Redis short-lived cache (non-authoritative)
        ↓
Dashboard API response
        ↓
Frontend renders KPIs and charts
```

## Calendar Data Flow

```
PostgreSQL demand_events table (seeded fake data)
        ↓
Calendar API (FastAPI)
        ↓
Frontend calendar renders demand indicators + enquiry counts
```

## Data Ownership

| Data | Owner |
|---|---|
| Enquiry records | PostgreSQL (`enquiries` table) |
| Email event log | PostgreSQL (`email_events` table) |
| Pricing rules | PostgreSQL (`pricing_rules` table) |
| Personas | PostgreSQL (`personas` table) |
| Demand events | PostgreSQL (`demand_events` table) |
| Task queue state | Redis (transient, not source of truth) |
| Metric cache | Redis (short-lived, always rebuildable from PostgreSQL) |

## POC Limitations

- No real-time websocket updates
- No streaming ingest
- No live external demand data
- Metric cache is optional — all data is rebuildable from PostgreSQL
