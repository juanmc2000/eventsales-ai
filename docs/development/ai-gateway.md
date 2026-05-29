# AI Gateway — Architecture and Prompt Governance

**Sprint:** 6 (architecture) · Sprint 7 (freeform extraction + processing split) · Sprint 8 (LLM parameters, experiments, quality scoring) · Sprint 8B (extraction schema hardening, deterministic date resolution)
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

| Field | Type | Description |
|-------|------|-------------|
| `key` | `str` | Stable logical identifier (e.g. `"draft_response"`) |
| `version` | `int` | Integer, auto-incremented per key |
| `status` | `str` | `"active"`, `"archived"`, or `"draft"` |
| `name` | `str` | Human-readable prompt name (e.g. `"Draft Response v2"`) |
| `goal` | `str` | Purpose statement for documentation and tracing |
| `system_template` | `str` | `{variable}` template string for system turn |
| `user_template` | `str` | `{variable}` template string for user turn |
| `required_variables` | `frozenset` | Variable names that must be present |
| `optional_variables` | `frozenset` | Variables that default to `""` if absent |
| `output_schema_name` | `str` | Logical name of the expected Pydantic output schema |
| `model_provider`, `model_name` | `str` | Target provider and model |
| `temperature` | `float` | Configured sampling temperature (stored as float, not string) |
| `top_p` | `float \| None` | Nucleus sampling probability (optional) |
| `top_k` | `int \| None` | Top-k sampling limit (optional; not forwarded to Anthropic API) |
| `max_tokens` | `int \| None` | Maximum response tokens (optional) |

### Configured vs actual parameter distinction

`PromptDefinition` holds the **configured** (intended) parameters.
`AIPromptRun` records hold the **actual** (runtime) parameters that were used.

For the POC these are always identical, but the schema separation allows:
- Detecting configuration drift (e.g. after a registry edit)
- Comparing multiple runs of the same prompt with different configurations
- Informing experiment analysis

> **Important:** `temperature` is stored as a Python `float`, never as a string. A type coercion bug (e.g. `"0.7"` instead of `0.7`) would break numerical comparisons and is guarded by tests.

### Registered prompt keys

| Key | Category | Output schema | Temperature | Notes |
|-----|----------|---------------|-------------|-------|
| `draft_response` | `draft_generation` | `DraftEmailOutput` | 0.7 | Main venue response draft |
| `enquiry_extraction` | `intake` | `EnquiryExtractionOutput` | 0.05 | V3 — explicit JSON contract with `date_request` object; very low temp for structured JSON fidelity |
| `missing_info_request` | `intake` | — | 0.5 | Polite follow-up questions |
| `follow_up_response` | `follow_up` | — | 0.5 | Proactive re-engagement |
| `availability_alternative_response` | `draft_generation` | — | 0.7 | Alternative date/room suggestion |

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
| `prompt_name` | Human-readable prompt name from the definition |
| `prompt_goal` | Purpose statement from the definition |
| `temperature` | Actual temperature used at runtime (Numeric 4,2) |
| `top_p` | Actual top_p used at runtime (Numeric 4,2; nullable) |
| `top_k` | Actual top_k used at runtime (Integer; nullable) |
| `max_tokens` | Actual max_tokens used at runtime (Integer; nullable) |
| `token_input_count` | Input token count from provider response (nullable) |
| `token_output_count` | Output token count from provider response (nullable) |
| `estimated_cost` | Cost string for audit (nullable; not calculated in POC) |

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

---

## Freeform Enquiry Workflow (Sprint 7)

Freeform (natural-language) enquiry submissions use a **two-call LLM architecture**. Structured webform submissions continue to use the original single-call draft path.

### Two-call POC architecture

```
POST /api/v1/enquiries/intake/freeform
  │
  ├─ 1. Create enquiry + inbound message (DB, no LLM)
  │
  ├─ 2. LLM Call 1 — Extraction (prompt_key: "enquiry_extraction", V3)
  │      Input:  freeform_text, restaurant_name
  │      Output: guest_count, event_type, occasion, budget, allergens,
  │              special_requirements, customer_tone, audience_type,
  │              preferred_room, missing_fields, confidence
  │              + date_request object (see Sprint 8B below)
  │      Stored: enquiry_extractions table
  │
  ├─ 3. Deterministic Date Resolution (no LLM)
  │      Expand date_request → EnquiryCandidateDate rows
  │      source_type: "explicit" or "deterministic", cap: 60 dates
  │      Stored: enquiry_date_requests, enquiry_candidate_dates tables
  │
  ├─ 4. Deterministic Processing (no LLM)
  │      Room matching → availability lookup per candidate date
  │      → pricing calculation per available date
  │      → recommended_action selection
  │      Stored: enquiry_processing_snapshots table
  │              (availability_result_json includes candidate_date_summary)
  │
  └─ 5. LLM Call 2 — Draft Generation (prompt_key: "draft_response")
         Input:  DraftContext enriched from processing snapshot
         Output: email subject + body
         Stored: enquiry_messages (draft)
```

**Response** includes: extraction summary, recommended action, draft subject/body — in a single HTTP response.

### Three-call MVP architecture (future)

A third LLM call for **response planning** (e.g. availability conflict handling, multi-room comparison) is deliberately out of scope for the POC. The deterministic processing step is the placeholder for this logic.

### Deterministic processing responsibilities

`EnquiryProcessingService` (`enquiries/processing_service.py`) runs between extraction and drafting. It is **pure Python — no LLM calls**:

| Responsibility | Output field |
|----------------|-------------|
| Match a suitable room (by preferred area / capacity / display order) | `room_suitability_json` |
| Look up availability for the matched room and event date | `availability_result_json` |
| Calculate minimum spend via `PricingRuleService` | `pricing_result_json` |
| Identify missing critical fields (guest_count, event_date) | `missing_fields_json` |
| Select a recommended action | `recommended_action` |

### Recommended actions

| Action | Trigger condition |
|--------|-------------------|
| `send_availability_confirmation` | Room available, no missing critical fields |
| `send_availability_with_missing_info_question` | Room available, missing non-critical fields |
| `request_missing_information` | Missing critical fields (guest_count or event_date) |
| `suggest_alternative_room` | No room matched or preferred room not available |
| `escalate_to_human` | Multiple conflicts, unusual requirements |
| `unable_to_process` | Extraction failed, no usable data |

### Storage tables (Sprint 7)

| Table | Purpose |
|-------|---------|
| `enquiry_extractions` | One row per extraction run; stores extracted_json, normalized_json, missing_fields, confidence_json |
| `enquiry_processing_snapshots` | One row per processing run; stores availability, room suitability, pricing, recommended_action |
| `enquiry_date_requests` | One row per extraction; stores extracted date intent, date_request_type, anchor_date, requires_date_clarification |
| `enquiry_candidate_dates` | One row per candidate date; stores candidate_date, source_type, availability_status, recommended_minimum_spend |

`enquiry_extractions` and `enquiry_processing_snapshots` are created by migration `20260524_000006`.
`enquiry_date_requests` and `enquiry_candidate_dates` are created by migration `20260527_000010`.

### Draft context enrichment

`DraftGenerationService.generate_draft()` loads the latest `EnquiryProcessingSnapshot` for the enquiry and enriches `DraftContext` using `dataclasses.replace()` (immutable pattern):

- `availability_status`, `availability_date`, `availability_meal_period`
- `confirmed_minimum_spend`, `pricing_explanation`
- `missing_questions`, `recommended_action`

These fields become optional variables in the `draft_response` prompt template (V2).

### Prompt versioning (Sprint 7)

| Prompt key | V1 | V2 | V3 |
|------------|----|----|----|
| `enquiry_extraction` | Archived — contact-info extraction schema | Archived — freeform extraction with guest_count, occasion, budget, allergens | **Active** — explicit JSON contract with `date_request` object, NULL convention, schema version 3.0, temperature 0.05 |
| `draft_response` | Archived — original single-context draft | **Active** — enriched with availability, pricing, missing_questions, recommended_action | — |

Old versions are archived (not deleted) per the registry's historical record rule.

---

## Prompt Experiments (Sprint 8)

Prompt experiments group multiple prompt runs for parameter comparison. They provide a lightweight structure for manual A/B testing without a dedicated experimentation UI.

### Tables

| Table | Purpose |
|-------|---------|
| `ai_prompt_experiments` | Groups runs for comparison (status: `active`, `completed`, `archived`) |
| `ai_prompt_experiment_runs` | Links a prompt run to an experiment with variant metadata |

### AIPromptExperiment fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `tenant_id` | String | Tenant (nullable in POC) |
| `prompt_key` | String | The prompt being experimented on |
| `name` | String | Short experiment label |
| `goal` | Text | What the experiment is trying to determine |
| `baseline_prompt_version_id` | UUID FK (nullable) | Reference run (control) |
| `status` | String | `active`, `completed`, `archived` |
| `notes` | Text | Freeform experimenter notes |
| `created_at` | Timestamp | — |

### AIPromptExperimentRun fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `experiment_id` | UUID FK | Parent experiment |
| `prompt_run_id` | UUID FK | The actual `ai_prompt_runs` row |
| `variant_name` | String | Short label for this variant (e.g. `"temp=0.3"`) |
| `temperature` | Numeric(4,2) | Parameter used for this variant |
| `top_p`, `top_k`, `max_tokens` | Numeric/Integer | Other parameters |
| `evaluator_score` | Numeric(4,2) | Human-assigned overall score (0–5) |
| `reviewer_notes` | Text | Evaluation notes |
| `selected_as_winner` | Boolean | True if this variant was chosen (default False, non-nullable) |
| `created_at` | Timestamp | — |

### Experiment API

```
POST /api/v1/ai/prompt-experiments                                  — create experiment
GET  /api/v1/ai/prompt-experiments                                  — list (filter by prompt_key, status)
GET  /api/v1/ai/prompt-experiments/{id}                             — detail
POST /api/v1/ai/prompt-experiments/{id}/runs                        — link a prompt run as a variant
GET  /api/v1/ai/prompt-experiments/{id}/runs                        — list variants
PATCH /api/v1/ai/prompt-experiments/{experiment_id}/runs/{run_id}   — update score/winner flag
```

### Experiment workflow (POC)

The POC requires manual steps:
1. Create an experiment via the API with a goal statement
2. Run the gateway with different prompt definitions in `prompt_registry.py`
3. Link the resulting `ai_prompt_runs` rows to the experiment via `POST .../runs`
4. Score each variant using `PATCH .../runs/{run_id}` with `evaluator_score`
5. Mark the winner with `selected_as_winner: true`

There is no automated parameter sweep, scheduled runner, or experiment UI.

### Recommended parameter test matrix (draft generation)

| Variable | Values to test |
|----------|---------------|
| `temperature` | 0.3, 0.5, 0.7 |
| `top_p` | 0.8, 0.9, 1.0 |
| `top_k` | 40, 80, unset |
| `max_tokens` | 600, 900, 1200 |

Run each combination for the same enquiry context; score using the quality review dimensions below.

### Recommended extraction parameter ranges

Extraction prompts require factual accuracy over creativity. Use conservative settings:

| Parameter | Recommended range |
|-----------|------------------|
| `temperature` | 0.0–0.2 (currently 0.1) |
| `top_p` | 0.8–1.0 |
| `top_k` | Low or unset |
| `max_tokens` | Enough for JSON output only (not full prose) |

---

## Quality Scoring (Sprint 8)

Reviewers can rate any prompt run using `ai_prompt_run_reviews`. This supports the manual improvement loop without requiring an automated evaluator.

### AIPromptRunReview fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `prompt_run_id` | UUID FK | The reviewed `ai_prompt_runs` row |
| `tenant_id` | String | Tenant (nullable in POC) |
| `reviewer_user_id` | String | Who performed the review |
| `accuracy_score` | Numeric(4,2) | Factual correctness 0–5 |
| `tone_fit_score` | Numeric(4,2) | Tone matches persona and context 0–5 |
| `persona_fit_score` | Numeric(4,2) | Response feels like the assigned persona 0–5 |
| `commercial_quality_score` | Numeric(4,2) | Sells the venue effectively 0–5 |
| `completeness_score` | Numeric(4,2) | Addresses all guest questions 0–5 |
| `hallucination_risk_score` | Numeric(4,2) | Absence of fabricated facts 0–5 |
| `ready_to_send` | Boolean (nullable) | Reviewer judgment — does not trigger any automated action |
| `reviewer_notes` | Text | Freeform feedback |
| `created_at`, `updated_at` | Timestamp | — |

All score fields are nullable; a review can be submitted with partial scores.

> **POC guardrail:** `ready_to_send` is reviewer intent only. It does **not** trigger automated email sending. No automated evaluator or ML scoring field exists in this schema.

### Quality review API

```
POST  /api/v1/ai/prompt-runs/{id}/reviews          — create review
GET   /api/v1/ai/prompt-runs/{id}/reviews          — list reviews (newest-first)
PATCH /api/v1/ai/prompt-run-reviews/{review_id}    — update scores, notes, or ready_to_send
```

Score validation: all score values must be between 0.0 and 5.0 (inclusive). Out-of-range values return HTTP 422.

`prompt_run_id` cannot be changed via PATCH — it is immutable after creation.

### Quality review UI

`PromptRunReviewPanel` (`services/web/components/enquiries/PromptRunReviewPanel.tsx`) renders inside the enquiry detail drawer when a draft was produced by the live LLM (i.e. `ai_context.prompt_run_id` is non-null). It is **collapsed by default** to keep the main enquiry workflow clean.

The panel is not shown when the fallback provider was used (`is_fallback=true`).

---

## POC Limitations (updated Sprint 8)

| Limitation | Planned resolution |
|------------|-------------------|
| Prompt templates in code (not DB-editable) | Add prompt editor admin UI in post-POC |
| No tenant override activation (`tenant_prompt_configs` table exists but not wired) | Wire in multi-tenant auth sprint |
| No automated A/B parameter sweep | Post-POC experimentation framework |
| No automated retention on `ai_prompt_runs` | Post-POC data governance |
| Rendered prompts may contain guest PII | Post-POC PII scrubbing |
| No retry logic for failed provider calls | Post-POC reliability hardening |
| Training example review is manual (API-only, no UI) | Post-POC review UI |
| `token_input_count`, `token_output_count`, `estimated_cost` not populated | Requires Anthropic usage API wiring (post-POC) |
| Experiment runner is manual (no scheduled or automated sweep) | Post-POC experimentation framework |
| `top_k` stored in `ai_prompt_runs` but not forwarded to Anthropic API (not supported) | Use with other providers |
| Date resolution uses `Europe/London` timezone by default | Timezone stored on `enquiry_date_requests`; override in production from guest locale |
| `ranking_score` on candidate dates is null | Post-POC — requires a scoring model |
| Candidate date availability uses seed `room_availability` table, not a live calendar | Post-POC — wire to booking system |

---

## Extraction Schema Hardening (Sprint 8B)

### Explicit JSON contract

Extraction prompt V3 instructs the LLM to return **only** a valid JSON object matching `schema_name: enquiry_extraction_output, schema_version: 3.0`. No markdown fences, no preamble, no explanation.

The prompt explicitly prohibits the LLM from:
- Calculating candidate dates
- Checking availability
- Performing pricing
- Writing any customer-facing draft copy

### NULL placeholder convention

| Field type | Missing value placeholder |
|-----------|--------------------------|
| String fields | `"NULL"` (string) |
| Numeric fields | `null` (JSON null) |
| Object fields | `null` (JSON null) |
| Array fields | `[]` (empty array) |
| Unknown enum values | `"unknown"` where schema permits |

`EnquiryExtractionOutput` (`validators.py`) normalises `"NULL"` string values to Python `None` using `mode="before"` Pydantic validators.

### date_request object

The `date_request` sub-object captures guest date intent as stated. Supported `date_request_type` values:

| Type | Description |
|------|-------------|
| `exact` | Single unambiguous date |
| `date_range` | Start and end date |
| `multiple_choice` | Two or more explicit options |
| `month_flexible` | Any date within a month |
| `weekday_range_over_relative_period` | Specific weekday(s) within a period |
| `recurring_window` | Repeating pattern |
| `mixed_relative_dates` | Combination of relative references |
| `ambiguous_numeric_date` | Date with multiple interpretations — sets `requires_date_clarification = true` |
| `unknown` | Cannot classify — sets `requires_date_clarification = true` |

The LLM records the raw date text, classifies the type, and populates sub-fields. It does **not** expand relative dates into explicit calendar dates — that is done deterministically by the backend.

### Deterministic date resolution service

`EnquiryDateResolutionService` (`enquiries/date_resolution_service.py`) expands the extracted `date_request` into `EnquiryCandidateDate` rows:

- No LLM calls.
- Uses `anchor_date` from extraction (defaults to today).
- Default timezone: `Europe/London`.
- Candidate date cap: **60 dates**.
- `source_type = "explicit"` for directly provided dates; `"deterministic"` for expanded dates.

Expansion is deterministic and fully covered by unit tests.

### Recommended extraction parameters (V3)

| Parameter | Recommended starting value | Notes |
|-----------|---------------------------|-------|
| `temperature` | 0.05 (current) | Very low — structured JSON fidelity over creativity |
| `top_p` | 0.8 | Reduces vocabulary range |
| `top_k` | null | Omit unless provider supports cleanly |
| `max_tokens` | 1200 | Allow for full `date_request` object |

### Date request and candidate date API

```
GET /api/v1/enquiries/{id}/date-request/latest  — latest EnquiryDateRequest for the enquiry (404 if none)
GET /api/v1/enquiries/{id}/candidate-dates      — all EnquiryCandidateDate rows, ordered by date
```

Neither endpoint triggers date resolution, availability checks, or pricing.

---

## What Is Intentionally Not Built

- Prompt editing or approval UI (any prompt UI visible to users or reviewers)
- Automated A/B testing or experiment parameter sweep
- Automated evaluator or ML scoring (all review scores are human-entered)
- Fine-tuning pipeline or dataset export
- Multi-provider cost optimisation
- Real-time streaming responses
- Automatic prompt improvement loops
- Production prompt approval workflows
- Third LLM call for response planning (planned for post-POC MVP)
- Audience auto-detection from email content (manual selector is the current workaround)
