# ADR-002: Celery and Redis Background Job Architecture

## Status

Accepted

## Date

2026-05-20

## Context

The EventSales AI POC requires asynchronous background tasks:

- Sending test emails via Gmail SMTP
- Reading inbound test email inbox via IMAP
- Processing inbound emails into enquiry records
- Generating and seeding fake data for local testing
- Optionally refreshing dashboard metrics

These tasks cannot run in the FastAPI request/response cycle because:

- Email sending has unpredictable latency
- Inbox reading is a polling operation, not an HTTP trigger
- Seed data generation can take significant time
- Enquiry processing following email intake is inherently async

A background job system is required. The system must:

- Run tasks outside the FastAPI process
- Queue work reliably
- Store durable task outcomes in PostgreSQL (not only in the broker)
- Support retry on failure
- Be simple to run locally with Docker Compose

## Decision

The POC and initial MVP will use **Celery** as the worker system and **Redis** as the message broker.

PostgreSQL is the **source of truth** for all durable state. Redis is used only for task queuing and short-lived result caching. No critical state is stored only in Redis.

## Options Considered

### Option A: Celery + Redis (chosen)

**Chosen because:**
- Celery is the de facto Python background task standard
- Redis is lightweight, simple to run in Docker Compose, and already in the stack as a cache
- Celery + Redis requires minimal configuration for POC needs
- Strong ecosystem support and documentation
- Retry, scheduling, and queue management are built-in
- PostgreSQL handles all durable state — Redis failure does not cause data loss

### Option B: Temporal

**Rejected because:**
- Significant operational overhead for a POC
- Requires a Temporal server process in addition to worker
- Complex local setup
- Overkill for POC-level task requirements
- No justification at current scale

### Option C: FastAPI BackgroundTasks

**Rejected because:**
- Runs in the same process as the API — resource contention
- No persistent queue — tasks are lost if the process restarts
- No retry support
- Not suitable for long-running or polling operations

### Option D: RQ (Redis Queue)

**Rejected because:**
- Less mature than Celery for complex queuing needs
- Smaller ecosystem
- Celery is better known across Python teams

## Architecture

### Components

| Component | Technology | Role |
|---|---|---|
| Worker | Celery | Executes background tasks |
| Broker | Redis | Routes and queues tasks |
| Result backend | Redis | Stores transient task results |
| Durable state | PostgreSQL | Records all job outcomes that matter |

### Queue Design

| Queue | Purpose |
|---|---|
| `email` | Outbound test email sending (Gmail SMTP) |
| `inbox` | Inbound email inbox polling (IMAP) |
| `enquiry` | Email-to-enquiry processing |
| `seed` | Fake data generation |
| `metrics` | Dashboard metric refresh (optional, low priority) |

### Source of Truth Rule

Redis holds work to be done. PostgreSQL holds what has been done.

- Celery task results in Redis are transient and may expire.
- All meaningful outcomes (email sent, enquiry created, seed completed) are written to PostgreSQL.
- If Redis is flushed or restarted, no data is permanently lost.

## Idempotency

All Celery tasks must be idempotency-aware:

- Tasks that create PostgreSQL records must check for existing records before inserting.
- Tasks triggered by inbox polling must track processed message IDs to avoid duplicate enquiries.
- Tasks are written assuming they could be called more than once.

## Retry Policy

- Default: 3 retries with exponential backoff.
- Failed task errors are logged. Critical failures (e.g., email send failure) should update the relevant PostgreSQL record.
- Do not rely on Celery's result backend for retry state — always check PostgreSQL.

## Consequences

### Positive

- Simple Docker Compose integration — Redis and Celery worker are standard services
- Proven Python ecosystem with strong documentation
- All durable state in PostgreSQL — Redis restart causes no data loss
- Queue separation allows different retry policies and priorities per job type

### Negative

- Requires Redis as an additional infrastructure component (acceptable — already needed as cache)
- Worker must be monitored separately from the API (accepted — Celery Flower or logs)
- No built-in workflow orchestration (Temporal-style step sequences) — accepted for POC

## Future Considerations

If background job complexity increases significantly (multi-step workflows, compensation logic, long-running sagas), Temporal may be introduced in a future phase. For POC and initial MVP, Celery is sufficient.

No additional brokers (Kafka, RabbitMQ, SQS) will be introduced unless there is a specific scaling justification.
