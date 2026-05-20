# ADR-003: PostgreSQL as Source of Truth

## Status

Accepted

## Date

2026-05-20

## Context

The EventSales AI POC requires persistent storage for:

- restaurant and room records
- persona configurations
- pricing rules
- inbound enquiries
- enquiry message timelines
- email event logs
- calendar and demand events
- insight snapshots
- background job state

A reliable, ACID-compliant database is required as the authoritative system of record. The system also uses Redis for caching and task queuing, and in future may use vector search for AI features. A clear data ownership model is needed from the start to prevent ambiguity about which system holds the truth.

## Decision

**PostgreSQL is the source of truth for all persistent data.**

All entities are created, updated, and read from PostgreSQL. No other system (Redis, an in-memory store, or an external API) is treated as authoritative for data that must survive a process restart.

## Options Considered

### Option A: PostgreSQL as sole persistent store (chosen)

**Chosen because:**
- ACID-compliant — transactions, rollbacks, and data integrity are guaranteed
- Well-understood query model for relational data (enquiries → restaurants → personas → pricing rules)
- Strong ecosystem: SQLAlchemy ORM, Alembic migrations, psycopg2
- Single source of truth simplifies debugging — there is one place to check
- Supports future pgvector extension for AI embeddings without adding a new system
- Simple to run in Docker Compose

### Option B: Redis as primary store

**Rejected because:**
- Redis is not ACID-compliant
- Redis data is volatile by default — restart risk
- Not designed for complex relational queries
- No structured schema or migration tooling

### Option C: SQLite for POC

**Rejected because:**
- Does not support production-realistic concurrency
- Not available as a shared Docker Compose service
- Would require a full migration to PostgreSQL before MVP deployment
- Adds unnecessary migration work

### Option D: Multiple databases (polyglot persistence)

**Rejected because:**
- Adds significant complexity for a POC
- Data consistency across systems requires distributed transaction logic
- No justification at current scale

## Schema Ownership

- PostgreSQL owns all entity schemas.
- Alembic manages all migrations.
- Redis holds no schema — it is a broker and cache only.
- No entity may exist only in Redis. All entities that must survive a restart are in PostgreSQL.

## Initial POC Entities

| Table | Description |
|---|---|
| `restaurants` | Restaurant profiles for the 4 seeded test restaurants |
| `personas` | AI communication persona configurations |
| `restaurant_personas` | Persona-to-restaurant assignment |
| `pricing_rules` | Manual deterministic pricing rule definitions |
| `enquiries` | Inbound event enquiry records |
| `enquiry_messages` | Timeline messages per enquiry |
| `email_events` | Sent and received email event log |
| `calendar_events` | Booking and event calendar entries |
| `demand_events` | Seeded fake demand events |
| `insight_snapshots` | Aggregated analytics snapshots |

Optional POC entities: `rooms`, `users`, `audit_logs`, `background_jobs`.

## Redis Role

Redis is **not** a system of record. Its roles are:

1. **Celery broker** — queues background tasks. Tasks that complete write their outcomes to PostgreSQL.
2. **Short-lived cache** — stores pre-aggregated dashboard metrics. Always rebuildable from PostgreSQL. Cache expiry does not cause data loss.

## Future pgvector Compatibility

PostgreSQL supports the `pgvector` extension for embedding storage and similarity search. This is noted for potential future use (e.g., semantic enquiry matching, persona similarity search) but is **not implemented during POC**.

No separate vector database (Pinecone, Weaviate, Qdrant) will be introduced unless `pgvector` is demonstrated to be insufficient at scale.

## Data Integrity Expectations

- Foreign key constraints enforce entity relationships.
- All tables include `created_at` and `updated_at` timestamps.
- Soft deletes (using `deleted_at` or `is_active` flags) preferred over hard deletes where audit history matters.
- All tables include a `tenant_id` column for future multi-tenant row filtering.

## Consequences

### Positive

- Single authoritative data store simplifies debugging and recovery
- ACID guarantees ensure data consistency across enquiry, email, and pricing operations
- pgvector compatibility preserved without additional infrastructure
- Standard tooling: SQLAlchemy + Alembic well-understood by Python teams

### Negative

- PostgreSQL requires a running Docker service locally (accepted)
- All queries hit one database — no horizontal read scaling during POC (accepted)
- Schema migrations require Alembic discipline (accepted)

## POC Limitations

- No production high-availability PostgreSQL setup
- No replication or read replicas
- No data warehouse or analytical database
- No ML feature store
- No external analytics database
