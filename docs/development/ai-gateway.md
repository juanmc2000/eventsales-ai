# AI Gateway — Architecture and Prompt Governance

**Sprint:** 6
**Status:** Implemented (POC)

---

## Overview

The AI Gateway (`services/api/app/modules/ai/gateway.py`) is the **single backend entry point for all LLM calls**.

No business service may call `AnthropicProvider` or the Anthropic SDK directly. All AI execution flows through `AIGateway.run()`, which handles:

1. Prompt resolution (from the code-first prompt registry)
2. Prompt rendering (system + user prompts from template + context variables)
3. Input hash computation (deterministic SHA-256)
4. `ai_prompt_run` record creation (persisted before the provider call)
5. Provider execution (`AnthropicProvider` or `FallbackProvider`)
6. Structured output validation (Pydantic schemas)
7. Run record update (raw response, latency, validation status)
8. Result return (`AIGatewayResult`)

---

## AI Module Structure

```
services/api/app/modules/ai/
├── constants.py         — prompt keys, model names, status constants
├── gateway.py           — AIGateway — the single LLM execution boundary
├── models.py            — SQLAlchemy models for 5 AI tables
├── provider.py          — AnthropicProvider, FallbackProvider, make_provider()
├── prompt_registry.py   — PromptDefinition, PromptRegistry (code-first)
├── prompt_renderer.py   — PromptRenderer — renders {variable} templates
├── repository.py        — AIPromptRunRepository — persistence for run traces
├── router.py            — FastAPI endpoints for traces and training examples
├── schemas.py           — Pydantic/dataclass schemas (internal + API)
├── service.py           — DraftGenerationService, TrainingExampleService
└── validators.py        — OutputValidator, DraftEmailOutput, EnquiryExtractionOutput
```

---

## Prompt Registry

For the POC, prompt templates are owned in code in `prompt_registry.py`. This avoids a prompt-management UI while still providing version tracking and structured metadata.

Each `PromptDefinition` is a frozen dataclass containing:

| Field | Description |
|-------|-------------|
| `key` | Stable logical identifier (e.g. `"draft_response"`) |
| `version` | Integer, auto-incremented per key |
| `status` | `"active"`, `"archived"`, or `"draft"` |
| `system_template` | Jinja2-compatible `{variable}` template string |
| `user_template` | Jinja2-compatible `{variable}` template string |
| `required_variables` | Frozenset of variable names that must be present |
| `optional_variables` | Frozenset of variables that default to `""` if absent |
| `output_schema_name` | Logical name of the expected Pydantic output schema |
| `model_provider`, `model_name` | Target provider and model |

### Registered prompt keys

| Key | Category | Output schema |
|-----|----------|---------------|
| `draft_response` | `draft_generation` | `DraftEmailOutput` |
| `enquiry_extraction` | `intake` | `EnquiryExtractionOutput` |
| `missing_info_request` | `intake` | — |
| `follow_up_response` | `follow_up` | — |
| `availability_alternative_response` | `draft_generation` | — |

---

## Prompt Renderer

`PromptRenderer` (`prompt_renderer.py`) renders templates using Python's built-in `string.Formatter` — no new dependencies.

- `render_system(defn, context)` → validates required variables, renders system prompt
- `render_user(defn, context)` → validates required variables, renders user prompt
- `input_hash(system, user)` → deterministic SHA-256 of rendered prompts
- `extract_variables(template)` → returns set of `{variable}` names in a template

Missing required variables raise `MissingPromptVariables(missing: set[str])` immediately.

---

## Provider Abstraction

Two providers are available:

| Provider | When used | API call |
|----------|-----------|---------|
| `AnthropicProvider` | `ANTHROPIC_API_KEY` is set | Yes — Anthropic Messages API |
| `FallbackProvider` | No API key | No — deterministic hospitality template |

`make_provider(api_key) -> (provider, is_fallback)` selects the correct provider at runtime.

Both providers implement:
- `generate(context: DraftContext) -> str` — used by legacy path (pre-gateway)
- `generate_from_prompts(system, user) -> str` — used by the AI Gateway

---

## Prompt Versioning

POC approach: **code-owns templates, database-owns traceability**.

- Prompt definitions are in `prompt_registry.py` (code)
- `ai_prompt_templates` + `ai_prompt_versions` tables exist in PostgreSQL for future DB-driven overrides
- `tenant_prompt_configs` allows per-tenant/per-restaurant/per-persona active version selection (not wired in POC)
- The gateway always selects the single `status="active"` version for a given key from the code registry

To change a prompt in the POC:
1. Increment the `version` in `prompt_registry.py`
2. Update the templates
3. Update `change_notes`

Do not delete or overwrite old version entries — they are historical record.

---

## Prompt Run Traceability

Every `AIGateway.run()` call — including fallback runs — creates an `ai_prompt_runs` row.

| Field | Description |
|-------|-------------|
| `id` | UUID primary key |
| `tenant_id` | Tenant identifier (nullable in POC, required in production) |
| `enquiry_id`, `restaurant_id`, `persona_id` | Context linkage |
| `prompt_key`, `prompt_version` | Denormalised for fast querying |
| `model_provider`, `model_name` | Provider used |
| `rendered_system_prompt`, `rendered_user_prompt` | Exact strings sent to the LLM |
| `input_payload` | JSONB context variables passed to the renderer |
| `input_hash` | SHA-256 of rendered prompts |
| `raw_response` | Raw LLM text output |
| `parsed_response` | JSONB validated structured output (null if failed/fallback) |
| `validation_status` | `passed`, `invalid`, `parse_error`, `skipped`, `fallback_valid`, `fallback_invalid` |
| `validation_errors` | JSONB serialised Pydantic errors |
| `fallback_used` | True when no LLM call was made |
| `latency_ms` | Wall-clock LLM call duration |
| `status` | `success`, `fallback`, `error` |

### Trace API

```
GET  /api/v1/ai/prompt-runs                      — list with filters
GET  /api/v1/ai/prompt-runs/{id}                 — full detail (admin only)
```

Filters: `enquiry_id`, `restaurant_id`, `persona_id`, `prompt_key`, `status`, `validation_status`

---

## Structured Output Validation

The `OutputValidator` in `validators.py` validates raw LLM responses against declared Pydantic output schemas.

| Validation status | Meaning |
|-------------------|---------|
| `passed` | JSON parsed + schema validated |
| `invalid` | JSON parsed but schema validation failed |
| `parse_error` | Response could not be parsed as JSON |
| `skipped` | No output schema declared, or fallback run |
| `fallback_valid` | Fallback run + schema valid (future use) |
| `fallback_invalid` | Fallback run + schema failed (future use) |

Validation failures **never crash the application** — the raw response is preserved and the status is recorded.

---

## Fallback Handling

When `ANTHROPIC_API_KEY` is absent:

1. `make_provider("")` returns `(FallbackProvider(), True)`
2. `AIGateway.run()` records the run with `fallback_used=True`, `status="fallback"`, no rendered prompts
3. `DraftGenerationService.generate_draft()` calls `FallbackProvider().generate(context)` for the draft body
4. `AIContextOut.is_fallback=True` and `prompt_run_id=None` are returned to the caller

The fallback path produces a deterministic hospitality template using `DraftContext` fields. No LLM call is made.

---

## Training Example Capture

Every prompt run can be linked to a `ai_training_examples` row for future evaluation or fine-tuning.

```
POST /api/v1/ai/training-examples        — create linked to a run
GET  /api/v1/ai/training-examples        — list with filters
GET  /api/v1/ai/training-examples/{id}   — single example
```

Fields: `original_output` (from run's `parsed_response`), `corrected_output`, `correction_reason`, `quality_rating` (1–5), `approved_for_training`.

Human review is required before `approved_for_training=True`.

**No training pipeline, export tooling, or fine-tuning is implemented in the POC.**

---

## POC Limitations

| Limitation | Planned resolution |
|------------|-------------------|
| Prompt templates in code (not DB-editable) | Add prompt editor admin UI in post-POC |
| No tenant override activation (tenant_prompt_configs table exists but not wired) | Wire in multi-tenant auth sprint |
| No A/B testing or prompt versioning UI | Post-POC |
| No automated retention on ai_prompt_runs | Post-POC data governance |
| Rendered prompts may contain guest PII | Post-POC PII scrubbing |
| No retry logic for failed provider calls | Post-POC reliability hardening |
| Training example review is manual (API-only, no UI) | Post-POC review UI |

---

## What Is Intentionally Not Built

- Prompt editing or approval UI
- A/B testing or experimentation framework
- Fine-tuning pipeline or dataset export
- Multi-provider cost optimisation
- Real-time streaming responses
- Automatic prompt improvement loops
- Production prompt approval workflows
- Any prompt UI visible to end users
