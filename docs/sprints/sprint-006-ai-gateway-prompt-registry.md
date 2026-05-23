# Sprint 6 — AI Gateway, Prompt Registry, and Traceability

## Sprint Goal

Centralise all LLM calls through a dedicated AI Gateway service with a prompt registry, structured output validation, and full run traceability — without introducing a prompt-management UI or breaking existing draft generation behaviour.

---

## Non-Goals

- Prompt editing or approval UI
- A/B testing or experimentation framework
- Fine-tuning or model training
- Multi-provider cost optimisation or load balancing
- Production prompt approval workflows
- Anthropic-specific prompt management tooling
- Real-time streaming responses
- Any prompt UI visible to end users

---

## Issue Order

| Order | Issue | Description |
|-------|-------|-------------|
| 1 | DOC-012 | Create Sprint 6 AI Gateway Plan (this document) |
| 2 | DATA-014 | Add Prompt Versioning and AI Run Trace Tables |
| 3 | AI-003 | Create Prompt Registry and Renderer Foundation |
| 4 | AI-004 | Create AI Gateway Service |
| 5 | AI-005 | Add Structured Output Validation for AI Gateway Calls |
| 6 | AI-006 | Migrate Draft Generation to AI Gateway |
| 7 | AI-007 | Add Prompt Run Trace API |
| 8 | AI-008 | Add Training Example Capture from Prompt Runs |
| 9 | TEST-007 | Add AI Gateway and Prompt Traceability Tests |
| 10 | DOC-013 | Update AI Architecture and Prompt Governance Notes |

---

## AI Gateway Architecture Principles

### Single Entry Point

All LLM calls in the backend must go through `AIGatewayService`. No module may call an AI provider directly. This replaces direct usage of `AnthropicProvider` or `FallbackProvider` outside the AI module.

### Location

```
services/api/app/modules/ai/gateway.py
```

The AI module already exists. The gateway is an addition to the existing module structure — not a new service or microservice.

### Responsibilities

- Resolve the correct prompt version for a given prompt key and model
- Render the prompt template with runtime context variables
- Call the AI provider (Anthropic or fallback)
- Validate the structured output against the declared schema
- Record the full run trace in PostgreSQL
- Propagate `AIContextOut` for transparency display

### Provider Abstraction

The gateway uses the existing `make_provider()` factory. The fallback provider must remain functional when `ANTHROPIC_API_KEY` is absent. Provider selection is not configurable per call — the gateway always uses the environment-configured provider.

### No New Dependencies

The gateway must use only existing dependencies (Anthropic SDK, SQLAlchemy, Pydantic). No new Python packages unless explicitly approved in a downstream issue.

---

## Prompt Versioning Strategy

### Storage

Prompts are stored in PostgreSQL as versioned rows in `prompt_versions`. Each row contains:

- `prompt_key` — logical name (e.g. `draft_response_v1`)
- `version` — integer, auto-incremented per key
- `model_id` — target model (e.g. `claude-sonnet-4-6`)
- `system_template` — Jinja2 template string
- `user_template` — Jinja2 template string
- `is_active` — boolean; only one active version per key at a time
- `created_at` — timestamp

### Seed Data

Active prompt versions are seeded deterministically. The seed script populates the initial `draft_response_v1` prompt using the same logic as the current `build_system_prompt()` / `build_user_message()` functions.

### Rendering

A `PromptRenderer` class in `ai/prompt_registry.py` accepts a `prompt_key`, resolves the active version, and renders the Jinja2 templates with a `PromptContext` dict. Rendering is pure Python — no database writes during render.

### Version Selection

The gateway always selects the single `is_active=True` version for a given `prompt_key`. There is no runtime version switching. Changing the active version requires a database update (handled by future tooling, not in this sprint).

---

## Prompt Traceability Requirements

### AI Run Trace Table

Every call through the gateway is recorded in `ai_run_traces` with:

- `id` — UUID primary key
- `tenant_id` — foreign key (nullable for POC; required for multi-tenant production)
- `enquiry_id` — foreign key to `enquiries` (nullable for non-enquiry calls)
- `prompt_version_id` — foreign key to `prompt_versions`
- `model_id` — model used for the call
- `system_prompt` — rendered system prompt (the exact string sent)
- `user_message` — rendered user message (the exact string sent)
- `raw_response` — raw LLM response text
- `parsed_output` — JSON column; validated structured output (null if fallback)
- `validation_passed` — boolean
- `is_fallback` — boolean
- `latency_ms` — integer; wall-clock duration of the LLM call
- `created_at` — timestamp

### Tenant-Ready Fields

`tenant_id` is present on `ai_run_traces` from the start. It is nullable in the POC but must be populated when multi-tenant auth is added. This avoids a future migration.

### No PII in Traces

Rendered prompts may contain guest names or email addresses. This is acceptable for a POC. A production hardening issue (not in this sprint) should revisit PII scrubbing.

### Retention

No automated retention policy in the POC. All rows are kept indefinitely.

---

## Fallback Handling Requirements

### Fallback Provider

`FallbackProvider` must remain fully functional when `ANTHROPIC_API_KEY` is absent. The gateway must not raise an error when the fallback provider is used.

### Trace Recording

Fallback runs are still recorded in `ai_run_traces` with `is_fallback=True` and `validation_passed=False`. `raw_response` and `parsed_output` are null for fallback runs.

### AIContextOut

The `AIContextOut` dataclass is extended to include `prompt_run_trace_id` (UUID or None). This allows the transparency panel to link to the trace record.

### No Retry Logic

The gateway does not retry failed LLM calls in this sprint. Retry logic is deferred to a future issue.

---

## Validation Requirements

### Output Schema

Each prompt version declares an optional `output_schema` (JSON Schema). The gateway validates the LLM response against this schema after parsing.

### Validation Failure

If validation fails, the gateway logs the failure and returns the raw response with `validation_passed=False`. It does not raise an exception — the draft generation service must handle unvalidated output gracefully.

### Draft Response Validation

The `draft_response_v1` prompt declares a schema requiring:

```json
{
  "type": "object",
  "properties": {
    "subject": { "type": "string" },
    "body": { "type": "string" }
  },
  "required": ["subject", "body"]
}
```

If the LLM returns plain text instead of JSON, the gateway wraps it in `{"subject": "", "body": "<raw text>"}` with `validation_passed=False`.

---

## Training / Evaluation Capture Requirements

### Training Examples Table

A `training_examples` table records curated examples for future fine-tuning or evaluation:

- `id` — UUID primary key
- `ai_run_trace_id` — foreign key to `ai_run_traces`
- `quality_rating` — nullable integer (1–5); null until reviewed
- `include_in_training` — boolean, default false
- `reviewer_notes` — nullable text
- `created_at` — timestamp

### Capture Trigger

Every run trace is automatically inserted into `training_examples` with `include_in_training=False`. Human review is required before any example is included in training.

### No Training Pipeline

No training pipeline, export tooling, or fine-tuning integration is implemented in this sprint. The table exists for future use only.

---

## Definition of Done

- [ ] `prompt_versions` and `ai_run_traces` tables exist in PostgreSQL with Alembic migration
- [ ] `training_examples` table exists in PostgreSQL with Alembic migration
- [ ] `PromptRegistry` resolves active prompt versions from the database
- [ ] `PromptRenderer` renders Jinja2 templates with runtime context
- [ ] `AIGatewayService` is the single entry point for all LLM calls
- [ ] Structured output is validated against declared schema on every call
- [ ] Every gateway call is recorded in `ai_run_traces`
- [ ] Fallback runs are recorded with `is_fallback=True`
- [ ] `DraftGenerationService` uses the gateway (no direct provider calls)
- [ ] `GET /api/v1/ai/traces/{id}` returns the run trace for a given ID
- [ ] Training example rows are inserted for every run trace
- [ ] Tests cover gateway, registry, renderer, validation, and trace recording
- [ ] Sprint 6 architecture is documented in `docs/development/`
- [ ] `SPRINT_STATUS_OVERVIEW.MD` updated to reflect Sprint 6
- [ ] All existing tests pass (353 backend, 84 frontend)
- [ ] No new dependencies added without explicit approval
- [ ] No prompt-management UI added
- [ ] POC scope preserved
