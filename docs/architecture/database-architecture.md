# Database Architecture

## Purpose

This document describes the database architecture for the EventSales AI POC.

## POC Scope

PostgreSQL is the source of truth for all persistent data. All entities are written to and read from PostgreSQL. Redis is not used for durable storage.

See `docs/adr/ADR-003-postgres-source-of-truth.md` for the full architecture decision record.

## Database

- **System:** PostgreSQL 16
- **ORM:** SQLAlchemy
- **Migrations:** Alembic

## POC Entities

### Core Entities

| Table | Description |
|---|---|
| `restaurants` | Test restaurant records (4 seeded for POC) |
| `personas` | AI communication persona configurations |
| `restaurant_personas` | Join table: persona-to-restaurant assignment |
| `pricing_rules` | Manual deterministic pricing rules |
| `enquiries` | Inbound event enquiry records |
| `enquiry_messages` | Timeline messages associated with an enquiry |
| `email_events` | Log of sent and received email events |
| `calendar_events` | Booking and event calendar entries |
| `demand_events` | Seeded fake demand events (sports, holidays, etc.) |
| `insight_snapshots` | Aggregated analytics snapshots |

### Optional POC Entities

| Table | Description |
|---|---|
| `rooms` | Restaurant room configurations |
| `users` | Basic user records |
| `audit_logs` | Action audit trail |
| `background_jobs` | Background task state log |

## Entity Relationships (Outline)

```
restaurants ←──── restaurant_personas ────→ personas
restaurants ←──── pricing_rules
restaurants ←──── enquiries
enquiries   ←──── enquiry_messages
enquiries   ←──── email_events
restaurants ←──── calendar_events
restaurants ←──── demand_events
```

## POC Limitations

- No CRM integration tables
- No payment tables
- No production multi-tenant row-level security
- No full-text search indexes
- No pgvector embeddings (noted for future MVP use)
- Schema is POC-focused and will be extended for MVP
