# Database Architecture

## Purpose

This document describes the database architecture and initial entity plan for the EventSales AI POC.

## POC Scope

PostgreSQL is the source of truth for all persistent data. All entities are written to and read from PostgreSQL. Redis is not used for durable storage.

See `docs/adr/ADR-003-postgres-source-of-truth.md` for the full architecture decision record.

## Database

- **System:** PostgreSQL 16
- **ORM:** SQLAlchemy (declarative models)
- **Migrations:** Alembic

## Common Columns

All tables include:

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Primary key |
| `tenant_id` | UUID | Tenant identifier (single-tenant for POC) |
| `created_at` | TIMESTAMPTZ | Record creation timestamp |
| `updated_at` | TIMESTAMPTZ | Last update timestamp |

---

## Core Entities

### restaurants

Stores the 4 seeded test restaurants.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `tenant_id` | UUID | |
| `name` | VARCHAR(255) | e.g. "The Garden Table" |
| `codename` | VARCHAR(100) | Short reference code |
| `address` | TEXT | |
| `prestige_tier` | VARCHAR(50) | casual / casual-premium / luxury / ultra-luxury |
| `audience_type` | VARCHAR(100) | |
| `is_active` | BOOLEAN | |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

---

### personas

AI communication persona configurations.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `tenant_id` | UUID | |
| `name` | VARCHAR(255) | e.g. "Corporate", "Social / Casual" |
| `description` | TEXT | |
| `tone` | VARCHAR(100) | |
| `warmth` | INTEGER | 1–10 scale |
| `urgency` | INTEGER | 1–10 scale |
| `formality` | INTEGER | 1–10 scale |
| `sales_assertiveness` | INTEGER | 1–10 scale |
| `luxury_level` | INTEGER | 1–10 scale |
| `communication_density` | VARCHAR(50) | concise / moderate / detailed |
| `default_sign_off` | VARCHAR(255) | |
| `is_active` | BOOLEAN | |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

---

### restaurant_personas

Join table: persona-to-restaurant assignment.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `restaurant_id` | UUID FK → restaurants | |
| `persona_id` | UUID FK → personas | |
| `is_default` | BOOLEAN | One default persona per restaurant |
| `created_at` | TIMESTAMPTZ | |

---

### pricing_rules

Manual deterministic pricing rules.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `tenant_id` | UUID | |
| `restaurant_id` | UUID FK → restaurants | Nullable for group-level rules |
| `name` | VARCHAR(255) | Rule display name |
| `day_of_week` | VARCHAR(20) | monday–sunday or null (any) |
| `meal_period` | VARCHAR(50) | breakfast / lunch / dinner / late_night / null |
| `event_type` | VARCHAR(100) | Nullable |
| `guest_count_min` | INTEGER | Nullable |
| `guest_count_max` | INTEGER | Nullable |
| `base_minimum_spend` | NUMERIC(10,2) | |
| `adjustment_type` | VARCHAR(20) | fixed / percentage |
| `adjustment_value` | NUMERIC(8,2) | |
| `priority` | INTEGER | Lower = higher priority |
| `explanation_notes` | TEXT | Human-readable rationale |
| `is_active` | BOOLEAN | |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

---

### enquiries

Inbound event enquiry records.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `tenant_id` | UUID | |
| `restaurant_id` | UUID FK → restaurants | |
| `persona_id` | UUID FK → personas | Assigned persona |
| `source` | VARCHAR(50) | webform / email |
| `status` | VARCHAR(50) | new / missing_information / proposal_drafted / proposal_sent / follow_up_due / converted / lost / closed |
| `customer_name` | VARCHAR(255) | |
| `customer_email` | VARCHAR(255) | |
| `customer_phone` | VARCHAR(100) | Nullable |
| `company_name` | VARCHAR(255) | Nullable |
| `event_date` | DATE | Nullable |
| `event_time` | TIME | Nullable |
| `party_size` | INTEGER | Nullable |
| `event_type` | VARCHAR(100) | |
| `budget_indication` | VARCHAR(255) | Nullable |
| `preferred_room` | VARCHAR(255) | Nullable |
| `special_requests` | TEXT | Nullable |
| `raw_message` | TEXT | Original email body or form message |
| `recommended_minimum_spend` | NUMERIC(10,2) | Nullable |
| `pricing_rule_applied` | UUID FK → pricing_rules | Nullable |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

---

### enquiry_messages

Timeline messages and activity associated with an enquiry.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `enquiry_id` | UUID FK → enquiries | |
| `message_type` | VARCHAR(50) | inbound / outbound / system_note |
| `content` | TEXT | |
| `sent_by` | VARCHAR(100) | ai / user / system |
| `created_at` | TIMESTAMPTZ | |

---

### email_events

Log of sent and received email events.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `enquiry_id` | UUID FK → enquiries | Nullable |
| `direction` | VARCHAR(20) | inbound / outbound |
| `from_email` | VARCHAR(255) | |
| `to_email` | VARCHAR(255) | |
| `subject` | VARCHAR(500) | |
| `body_text` | TEXT | |
| `status` | VARCHAR(50) | sent / failed / received / processed |
| `error_message` | TEXT | Nullable |
| `external_message_id` | VARCHAR(500) | Gmail message ID |
| `created_at` | TIMESTAMPTZ | |

---

### calendar_events

Booking and confirmed event calendar entries.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `restaurant_id` | UUID FK → restaurants | |
| `enquiry_id` | UUID FK → enquiries | Nullable |
| `event_date` | DATE | |
| `event_time` | TIME | Nullable |
| `event_type` | VARCHAR(100) | |
| `customer_name` | VARCHAR(255) | |
| `party_size` | INTEGER | |
| `status` | VARCHAR(50) | provisional / confirmed / cancelled |
| `notes` | TEXT | Nullable |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

---

### demand_events

Seeded fake demand events (holidays, sports, theatre, etc.).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `restaurant_id` | UUID FK → restaurants | Nullable for city-wide events |
| `event_name` | VARCHAR(255) | |
| `event_category` | VARCHAR(100) | bank_holiday / sports_event / theatre / university_graduation / etc. |
| `start_date` | DATE | |
| `end_date` | DATE | |
| `demand_level` | VARCHAR(50) | low / normal / high / very_high |
| `pricing_impact_suggestion` | NUMERIC(5,2) | Suggested % uplift or discount |
| `notes` | TEXT | Nullable |
| `created_at` | TIMESTAMPTZ | |

---

### insight_snapshots

Aggregated analytics snapshots (pre-computed for dashboard performance).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `tenant_id` | UUID | |
| `restaurant_id` | UUID FK → restaurants | Nullable for portfolio-level |
| `snapshot_date` | DATE | |
| `metric_key` | VARCHAR(100) | e.g. enquiry_count, conversion_rate |
| `metric_value` | NUMERIC(12,4) | |
| `period` | VARCHAR(50) | daily / weekly / monthly |
| `created_at` | TIMESTAMPTZ | |

---

## Optional POC Entities

### rooms

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `restaurant_id` | UUID FK → restaurants | |
| `name` | VARCHAR(255) | |
| `seated_capacity` | INTEGER | |
| `standing_capacity` | INTEGER | |
| `room_hire_fee` | NUMERIC(10,2) | Nullable |
| `is_active` | BOOLEAN | |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

### users

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `tenant_id` | UUID | |
| `email` | VARCHAR(255) UNIQUE | |
| `hashed_password` | VARCHAR(255) | |
| `role` | VARCHAR(50) | sales_manager / sales_representative / administrator |
| `is_active` | BOOLEAN | |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

### background_jobs

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `task_name` | VARCHAR(255) | Celery task name |
| `queue` | VARCHAR(100) | |
| `status` | VARCHAR(50) | pending / running / success / failed |
| `error_message` | TEXT | Nullable |
| `started_at` | TIMESTAMPTZ | Nullable |
| `completed_at` | TIMESTAMPTZ | Nullable |
| `created_at` | TIMESTAMPTZ | |

---

## Entity Relationships

```
restaurants ←──── restaurant_personas ────→ personas
restaurants ←──── pricing_rules
restaurants ←──── enquiries ────→ enquiry_messages
enquiries   ←──── email_events
restaurants ←──── calendar_events
restaurants ←──── demand_events
restaurants ←──── rooms
```

---

## POC Limitations

- No CRM integration tables
- No payment or deposit tables
- No full multi-tenant row-level security (tenant_id present but not enforced via PostgreSQL RLS)
- No full-text search indexes (GIN/GiST) during POC
- No pgvector embeddings during POC
- Schema is POC-focused and will be extended for MVP

## MVP Extension Notes

For MVP, consider adding:
- `crm_sync_events` — CRM integration audit log
- `deposit_transactions` — Stripe/Adyen deposit tracking
- `workflow_executions` — Workflow step execution log
- `proposal_documents` — Generated proposal storage
- Row-level security policies for true multi-tenant isolation
- pgvector columns on relevant tables for semantic search
