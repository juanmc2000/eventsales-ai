# Sprint 8 — Prompt Run Experimentation & Quality Scoring

**Sprint:** 8
**Theme:** Prompt Run Experimentation & Quality Scoring
**Status:** Complete

---

## Objective

Give developers a systematic way to improve AI response quality by:

1. Persisting the exact LLM configuration (temperature, top_p, top_k, max_tokens) used for every prompt run
2. Grouping prompt runs into experiments for manual parameter comparison
3. Capturing human reviewer scores across six quality dimensions
4. Surfacing the review panel inline in the enquiry detail drawer

---

## Issues and PRs

| Issue | PR | Title | Status |
|-------|----|-------|--------|
| DATA-016 | #207 | Add LLM parameter fields to prompt versions and runs | ✓ Merged |
| AI-012 | #208 | Persist exact LLM runtime configuration in AI Gateway | ✓ Merged |
| API-016 | #209 | Expose LLM parameters in prompt run trace API | ✓ Merged |
| DATA-017 | #210 | Add prompt experiment tables | ✓ Merged |
| API-017 | #211 | Add prompt experiment backend API | ✓ Merged |
| DATA-018 | #212 | Add prompt run quality scoring | ✓ Merged |
| API-018 | #213 | Add prompt run quality review API | ✓ Merged |
| UI-021 | #214 | Add prompt run quality review panel | ✓ Merged |
| TEST-009 | #215 | Add prompt parameter and quality scoring tests | ✓ Merged |
| DOC-016 | #216 | Update prompt experimentation documentation | ✓ Merged |

---

## Architecture Changes

### LLM Parameter Persistence (DATA-016, AI-012)

`PromptDefinition` dataclass gained four new fields:
- `name: str` — human-readable prompt name
- `goal: str` — purpose statement for tracing
- `temperature: float` — sampling temperature (changed from `str` to `float`)
- `top_p: float | None` — nucleus sampling (optional)
- `top_k: int | None` — top-k sampling (optional; not forwarded to Anthropic API)

`AIPromptRun` model gained:
- `prompt_name`, `prompt_goal` (String) — denormalised from definition at write time
- `temperature` (Numeric 4,2) — **changed type from String(10) to Numeric(4,2)**
- `top_p` (Numeric 4,2), `top_k` (Integer), `max_tokens` (Integer)
- `token_input_count`, `token_output_count` (Integer) — for future cost tracking
- `estimated_cost` (String) — nullable, for future provider cost logging

`AIGateway.run()` now writes all parameter fields to the run record before the provider call.

`AnthropicProvider.generate_from_prompts()` now accepts and forwards `temperature`, `top_p`, and `max_tokens`. `top_k` is persisted but not forwarded (not supported by Anthropic Messages API).

### Prompt Experiment Tables (DATA-017, API-017)

Two new tables in Alembic migration `20260526_000008`:

- `ai_prompt_experiments` — groups runs for comparison with a goal statement and status lifecycle
- `ai_prompt_experiment_runs` — links `ai_prompt_runs` rows to experiments with variant metadata and scoring

Six REST endpoints added to the AI router.

### Quality Scoring (DATA-018, API-018)

New table `ai_prompt_run_reviews` in Alembic migration `20260526_000009`:

Six Numeric(4,2) score fields (0.0–5.0): accuracy, tone fit, persona fit, commercial quality, completeness, hallucination risk.

Three REST endpoints: create review, list reviews (newest-first), update review.

Score validation enforced in `PromptRunReviewService` — values outside 0.0–5.0 return HTTP 422. `prompt_run_id` is immutable after creation.

### Quality Review UI (UI-021)

`PromptRunReviewPanel` component added to enquiry detail drawer:

- Rendered inline below the Draft Response section when `ai_context.prompt_run_id` is non-null
- Collapsed by default — does not interrupt normal enquiry workflow
- Fetches the most recent review on expand; shows a summary badge when one exists
- 6 score inputs (number, 0–5 step 0.5), ready_to_send checkbox, reviewer notes textarea
- Saves via `POST /api/v1/ai/prompt-runs/{id}/reviews`

`AIContextOut.prompt_run_id` added to the TypeScript type (was already in the backend dataclass but missing from `enquiry.ts`).

---

## Migrations (in order)

| Revision | File | Change |
|----------|------|--------|
| `20260525_000007` | `add_llm_parameters_to_prompt_versions_and_runs.py` | Adds LLM param columns to `ai_prompt_versions` and `ai_prompt_runs`; ALTERs `temperature` from VARCHAR to NUMERIC using `postgresql_using` cast |
| `20260526_000008` | `add_prompt_experiment_tables.py` | Creates `ai_prompt_experiments` + `ai_prompt_experiment_runs` |
| `20260526_000009` | `add_prompt_run_reviews_table.py` | Creates `ai_prompt_run_reviews` |

---

## Test Counts (post-Sprint-8)

- Backend (pytest): **734 passed** (was 628 post-Sprint-7; +106 tests)
- Frontend (vitest): **111 passed across 14 files** (was 102 across 13 files; +9 tests)
- Total: **845 tests**

New test files:
- `tests/ai/test_gateway.py` — `TestAIGatewayParameterPersistence` (6 tests)
- `tests/ai/test_prompt_experiment_models.py` — 11 tests
- `tests/ai/test_prompt_experiment_api.py` — 19 tests
- `tests/ai/test_prompt_run_review_models.py` — 11 tests
- `tests/ai/test_prompt_run_review_api.py` — 13 tests
- `tests/ai/test_sprint8_parameter_scoring.py` — 44 focused cross-cutting tests
- `tests/enquiries/PromptRunReviewPanel.test.tsx` — 9 frontend tests

---

## POC Guardrails Maintained

- `ready_to_send` is reviewer judgment only — does not trigger automated email send
- No automated evaluator or ML scoring fields (guarded by `test_review_has_no_ml_auto_score_fields`)
- No prompt editing UI
- No automated experiment parameter sweep
- `temperature` stored as numeric float, never string (guarded by `test_extraction_temperature_is_float_not_string`)
- Pricing logic untouched (deterministic rules only)

---

## What Is Not Built in Sprint 8

- Automated A/B testing or parameter sweep scheduler
- Automated evaluator scoring
- Export of reviews to external analytics
- Fine-tuning dataset generation from reviews
- Experiment dashboard or comparison UI
- `token_input_count` / `token_output_count` population (Anthropic usage API not wired)
- `estimated_cost` calculation
