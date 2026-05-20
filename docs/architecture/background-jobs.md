# Background Jobs

## Purpose

This document describes the background job architecture for the EventSales AI POC.

## POC Scope

The POC uses **Celery** with **Redis** as the broker for all background tasks. PostgreSQL remains the source of truth. Redis is not used for durable state.

See `docs/adr/ADR-002-celery-redis-background-jobs.md` for the full architecture decision record.

## Stack

| Component | Technology | Role |
|---|---|---|
| Worker | Celery | Executes background tasks |
| Broker | Redis | Queues and routes tasks |
| Result backend | Redis (transient) | Short-lived task result cache |
| Source of truth | PostgreSQL | Durable state for all job outcomes |

## POC Queues

| Queue | Purpose |
|---|---|
| `email` | Outbound test email sending (Gmail SMTP) |
| `inbox` | Inbound email inbox reading (IMAP) |
| `enquiry` | Email-to-enquiry processing |
| `seed` | Fake data generation |
| `metrics` | Dashboard metric refresh (optional) |

## POC Background Tasks

| Task | Queue | Description |
|---|---|---|
| `send_test_email` | `email` | Send a generated response via Gmail SMTP |
| `read_inbox` | `inbox` | Fetch unread emails from test Gmail inbox |
| `process_inbound_email` | `enquiry` | Parse email into enquiry record |
| `generate_seed_data` | `seed` | Populate fake restaurants, enquiries, demand events |
| `refresh_dashboard_metrics` | `metrics` | Rebuild cached dashboard KPIs from PostgreSQL |

## Idempotency

All tasks must be idempotent-aware. Tasks that create or update PostgreSQL records must check for existing records before inserting to prevent duplicate processing.

## Error Handling

- Tasks should use Celery `autoretry_for` with a maximum retry count.
- Failed task outcomes should be logged to PostgreSQL where relevant.
- Redis task results are transient — do not rely on them for durable state.

## POC Limitations

- No Temporal
- No additional brokers
- No distributed tracing
- No production observability tooling
- No scheduled periodic tasks beyond basic beat configuration
