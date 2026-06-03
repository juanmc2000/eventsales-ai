# Sprint Status Overview

**Project:** EventSales AI
**Phase:** POC (Proof of Concept)
**Last Updated:** 2026-06-03 (post-Sprint-8C)

---

## Sprint Summary

| Sprint | Theme | Status | PRs |
|--------|-------|--------|-----|
| Sprint 1 | Architecture Foundation | ✓ Complete | #1–#20 |
| Sprint 2 | Product Foundation | ✓ Complete | #21–#50 |
| Sprint 3 | UI Shell and Core Pages | ✓ Complete | #51–#82 |
| Sprint 4 | Webform and Email Wiring | ✓ Complete | #83–#93 |
| Sprint 5A | Live Gmail Validation | ✓ Complete | #104–#111 |
| Sprint 5B | Live Gmail SMTP + IMAP | ✓ Complete | #113–#114 |
| Sprint 5C | Venue Context (Rooms/PDR) | ✓ Complete | #126–#135 |
| Sprint 5D | Freeform Webform + Audience Routing | ✓ Complete | #138–#141 |
| Sprint 5E | AI Transparency + Room Availability | ✓ Complete | #145, #148–#149 |
| Sprint 6 | AI Gateway, Prompt Registry, and Traceability | ✓ Complete | #160–#168, DOC-013 |
| Sprint 7 | Freeform Enquiry Extraction & Deterministic Processing | ✓ Complete | #181–#190 |
| Hotfix | Fix generation failed and send failed errors in freeform webform | ✓ Complete | #192 |
| Sprint 8 | Prompt Run Experimentation & Quality Scoring | ✓ Complete | #207–#216 |
| Sprint 8B | Extraction Schema Hardening & Deterministic Date Resolution | ✓ Complete | #217–#236 |
| Sprint 8C | Extraction Quality & Deterministic Enrichment | ✓ Complete | #247–#252 |

---

## Sprint 5A Issues

| Issue | PR | Title | Status |
|-------|----|-------|--------|
| DOC-009 | #104 | Sprint 5A plan | ✓ Merged |
| UI-012 | #105 | DraftSection component | ✓ Merged |
| EMAIL-005 | #106 | Email delivery service and router | ✓ Merged |
| WORKFLOW-005 | #107 | SMTP Celery worker task | ✓ Merged |
| WORKFLOW-006 | #108 | Inbound email → enquiry pipeline | ✓ Merged |
| UI-013 | #109 | Email Activity Timeline component | ✓ Merged |
| TEST-005 | #110 | End-to-end POC workflow tests (73 tests) | ✓ Merged |
| DOC-010 | #111 | POC demo and validation guide | ✓ Merged |

---

## Sprint 5B Issues

| Issue | PR | Title | Status |
|-------|----|-------|--------|
| EMAIL-004 | #113 | Live Gmail SMTP send (GmailSMTPProvider) | ✓ Merged |
| EMAIL-006 | #114 | Live Gmail IMAP polling (GmailIMAPProvider) | ✓ Merged |

---

## Sprint 5C Issues

| Issue | PR | Title | Status |
|-------|----|-------|--------|
| DATA-005 | #126 | Rooms/PDR database model, schemas, migration | ✓ PR open |
| API-010 | #127 | Rooms/PDR backend CRUD module | ✓ PR open |
| DATA-006 | #128 | Seed data: 7 rooms across 4 restaurants | ✓ PR open |
| API-011 | #129 | Restaurant AI context endpoint | ✓ PR open |
| AI-002 | #130 | AI draft generation uses room context | ✓ PR open |
| UI-014 | #131 | Restaurant rooms summary section | ✓ PR open |
| UI-015 | #132 | Rooms/PDR management page (`/rooms`) | ✓ PR open |
| UI-016 | #133 | Webform room selection + enquiry detail | ✓ PR open |
| TEST-006 | #134 | Venue context workflow tests | ✓ PR open |
| DOC-011 | #135 | Update POC demo guide with venue context | ✓ PR open |

---

## Sprint 5D Issues

| Issue | PR | Title | Status |
|-------|----|-------|--------|
| UI-017 | #141 | Freeform enquiry tab + two-tab webform toggle | ✓ Merged |
| DATA-007 | #141 | Audience type on RestaurantPersona + migration | ✓ Merged |
| API-012 | #141 | Intake service resolves persona by audience type | ✓ Merged |

---

## Sprint 5E Issues

| Issue | PR | Title | Status |
|-------|----|-------|--------|
| DATA-008 | #145 | room_availability table, Alembic migration, deterministic seed (5,124 rows) | ✓ Merged |
| API-013 | #148 | Room availability endpoint + AIContextOut with raw prompts in draft response | ✓ Merged |
| UI-018 | #149 | Enrich webform response panels: AI transparency + room availability card | ✓ Merged |

---

## Sprint 6 Issues

| Issue | PR | Title | Status |
|-------|----|-------|--------|
| DOC-012 | #160 | Sprint 6 plan: AI Gateway, Prompt Registry, Traceability | ✓ Merged |
| DATA-014 | #161 | Prompt versioning and AI run trace tables (5 tables, migration) | ✓ Merged |
| AI-003 | #162 | Prompt registry and renderer foundation | ✓ Merged |
| AI-004 | #163 | AI Gateway service (single LLM execution entry point) | ✓ Merged |
| AI-005 | #164 | Structured output validation for AI Gateway calls | ✓ Merged |
| AI-006 | #165 | Migrate draft generation to AI Gateway | ✓ Merged |
| AI-007 | #166 | Prompt run trace API (`/api/v1/ai/prompt-runs`) | ✓ Merged |
| AI-008 | #167 | Training example capture from prompt runs | ✓ Merged |
| TEST-007 | #168 | AI Gateway and prompt traceability tests (140 new tests) | ✓ Merged |
| DOC-013 | DOC-013 PR | AI architecture and prompt governance notes | ✓ Merged |

---

## POC Feature Coverage

| Feature | Sprint | Status |
|---------|--------|--------|
| Dashboard KPIs | 3 | ✓ |
| Restaurants configuration | 2–3 | ✓ |
| Personas configuration | 2–3 | ✓ |
| Pricing Rules (deterministic) | 2–3 | ✓ |
| Calendar + demand events | 2–3 | ✓ |
| Insights / reporting | 2–3 | ✓ |
| Enquiries list + detail drawer | 3 | ✓ |
| Webform intake endpoint | 4 | ✓ |
| Webform page (`/webform`) | 4 | ✓ |
| Draft generation (FallbackProvider) | 4 | ✓ |
| Draft generation (AnthropicProvider) | 4 | ✓ |
| Gmail SMTP send (wired, disabled without creds) | 4 | ✓ |
| Gmail IMAP inbox reader (wired, disabled without creds) | 4 | ✓ |
| DraftSection UI (generate + send + states) | 5A | ✓ |
| Email Activity Timeline UI | 5A | ✓ |
| Email delivery status logging | 5A | ✓ |
| SMTP Celery worker with retry | 5A | ✓ |
| Inbound email → enquiry pipeline | 5A | ✓ |
| Deterministic end-to-end tests (73) | 5A | ✓ |
| Live Gmail SMTP send (GmailSMTPProvider) | 5B | ✓ |
| Live Gmail IMAP polling (GmailIMAPProvider) | 5B | ✓ |
| Rooms/PDR model, schemas, migration | 5C | ✓ |
| Rooms/PDR CRUD API (nested under restaurants) | 5C | ✓ |
| Seed data: 7 rooms/PDRs across 4 restaurants | 5C | ✓ |
| Restaurant AI context endpoint (`/restaurants/{id}/context`) | 5C | ✓ |
| AI draft uses room context (capacity, amenities, suitability) | 5C | ✓ |
| Restaurant detail — room summary section | 5C | ✓ |
| Rooms/PDR management page (`/rooms`) | 5C | ✓ |
| Webform room selection (backend-driven dropdown) | 5C | ✓ |
| Venue context workflow tests (332 backend, 79 frontend) | 5C | ✓ |
| POC demo guide (updated with venue context) | 5C | ✓ |
| Freeform enquiry tab (natural-language → AI → SMTP auto-flow) | 5D | ✓ |
| Two-tab webform toggle (Structured / Freeform) | 5D | ✓ |
| Audience type selector (Social / Corporate / Agency) on both tabs | 5D | ✓ |
| Audience-based persona routing (Eleanor=social, James=corporate, Sophia=agency) | 5D | ✓ |
| RestaurantPersona audience column + Alembic migration | 5D | ✓ |
| Freeform smoke tests (84 frontend, 332 backend total) | 5D | ✓ |
| room_availability table (7 rooms × 366 days × 2 periods = 5,124 rows) | 5E | ✓ |
| Room availability endpoint (`GET /restaurants/{id}/rooms/{rid}/availability?date=`) | 5E | ✓ |
| AIContextOut in draft response (model, persona, prompts, room, spend) | 5E | ✓ |
| Raw system prompt + user message exposed in draft response | 5E | ✓ |
| AI Transparency Panel on webform success page (collapsible) | 5E | ✓ |
| Room Availability Card on webform success page (status pills) | 5E | ✓ |
| Tests: 353 backend, 84 frontend (437 total) | 5E | ✓ |
| AI Gateway (single LLM execution entry point, all prompts routed through gateway) | 6 | ✓ |
| Prompt registry (code-first frozen dataclasses, 5 prompt definitions, SHA-256 hashing) | 6 | ✓ |
| Prompt renderer (Python string.Formatter, required/optional variable validation) | 6 | ✓ |
| Structured output validation (DraftEmailOutput, EnquiryExtractionOutput, Pydantic) | 6 | ✓ |
| AI run trace tables (ai_prompt_runs, ai_prompt_templates, ai_prompt_versions, etc.) | 6 | ✓ |
| Prompt run trace API (`GET /api/v1/ai/prompt-runs`, `GET /api/v1/ai/prompt-runs/{id}`) | 6 | ✓ |
| Training example capture (POST/GET `/api/v1/ai/training-examples`) | 6 | ✓ |
| prompt_run_id exposed in draft response (AIContextOut) | 6 | ✓ |
| Tests: 493 backend, 84 frontend (577 total) | 6 | ✓ |
| Freeform extraction (LLM Call 1): guest_count, event_date, event_type, occasion, budget | 7 | ✓ |
| Deterministic processing: room match + availability + pricing + recommended_action | 7 | ✓ |
| Draft enrichment (LLM Call 2): context from processing snapshot | 7 | ✓ |
| POST /intake/freeform single-call endpoint (extraction → processing → draft) | 7 | ✓ |
| Extraction + processing summary section in enquiry detail drawer | 7 | ✓ |
| enquiry_extractions + enquiry_processing_snapshots tables | 7 | ✓ |
| Extraction tests, processing tests, orchestration tests | 7 | ✓ |
| Tests: 628 backend, 102 frontend (730 total) | 7 | ✓ |
| Fix: Enquiry model recommended_minimum_spend property (Pydantic from_attributes) | Hotfix | ✓ |
| Fix: get_db() rollback on exception (prevents PendingRollbackError across requests) | Hotfix | ✓ |
| Fix: Freeform emailSent null-safe (no false "Send failed" badge when send not attempted) | Hotfix | ✓ |
| LLM parameter fields on PromptDefinition (name, goal, temperature as float, top_p, top_k) | 8 | ✓ |
| LLM parameter persistence in AIGateway (written to ai_prompt_runs before provider call) | 8 | ✓ |
| AIPromptRun: temperature/top_p Numeric(4,2), prompt_name/goal, token counts | 8 | ✓ |
| Prompt run trace API exposes all LLM parameter fields | 8 | ✓ |
| ai_prompt_experiments table + API (6 endpoints, status lifecycle, goal/notes) | 8 | ✓ |
| ai_prompt_experiment_runs table + API (variant metadata, evaluator_score, winner flag) | 8 | ✓ |
| ai_prompt_run_reviews table (6 Numeric score fields, ready_to_send, reviewer_notes) | 8 | ✓ |
| Quality review API (create/list/update, 0.0–5.0 validation, prompt_run_id immutable) | 8 | ✓ |
| PromptRunReviewPanel UI (collapsed, 6 scores, toggle, notes, saved state) | 8 | ✓ |
| AIContextOut.prompt_run_id in TypeScript types | 8 | ✓ |
| Tests: 734 backend, 111 frontend (845 total) | 8 | ✓ |
| Enquiry extraction prompt V3 — explicit JSON contract, date_request object, schema version 3.0, temperature 0.05 | 8B | ✓ |
| EnquiryExtractionOutput extended with date_request, customer_name, email, phone, preferred_room, customer_tone, audience_type, meal_period | 8B | ✓ |
| NULL placeholder convention — `"NULL"` string coercion in Pydantic validators | 8B | ✓ |
| enquiry_date_requests table (Alembic migration 20260527_000010) | 8B | ✓ |
| enquiry_candidate_dates table (same migration) | 8B | ✓ |
| EnquiryDateResolutionService — deterministic expansion for all 8 date_request_type values, cap 60, Europe/London default | 8B | ✓ |
| EnquiryProcessingService extended — candidate date availability + pricing per date, candidate_date_summary in snapshot | 8B | ✓ |
| GET /enquiries/{id}/date-request/latest and GET /enquiries/{id}/candidate-dates endpoints | 8B | ✓ |
| DateResolutionSection in enquiry detail drawer — date intent, clarification badge, candidate date rows with availability pills and pricing | 8B | ✓ |
| Tests: 828 backend, 126 frontend (954 total) | 8B | ✓ |
| Canonical occasion normalisation — OccasionNormalisationService, 10 canonical values (birthday, anniversary, engagement_party, baby_shower, hen_party, stag_party, graduation, retirement, christmas, corporate_event), keyword-first-match mapping | 8C | ✓ |
| occasion_canonical stored in normalized_json and surfaced in ExtractionSummaryOut (occasion_raw alongside canonical) | 8C | ✓ |
| Simplified date intent model — DateIntentNormalizer collapses LLM raw types into 5 categories: exact / range / recurring / ambiguous / unknown | 8C | ✓ |
| date_request_type_normalized column on enquiry_date_requests (Alembic migration 20260602_000012, indexed) | 8C | ✓ |
| EnquiryDateResolutionService extended — dispatches _expand() on normalized type; structural heuristics inside _expand_range() and _expand_recurring() preserve all existing sub-type expansion logic | 8C | ✓ |
| Enquiry extraction prompt V4 — DATE CONTEXT RULES section instructs LLM to always populate month, year, date_range bounds, weekdays, and relative_period when inferable; V3 archived | 8C | ✓ |
| DateContextValidator — post-extraction validation of date_request block; emits human-readable warnings for missing month/year, absent date_range bounds, missing weekdays, incomplete relative_period; stored in normalized_json['date_context_warnings'] | 8C | ✓ |
| EnquiryReadinessEvaluator — deterministic READY_FOR_AVAILABILITY / NEEDS_CLARIFICATION / WEBFORM_REQUIRED / INSUFFICIENT_INFORMATION assessment; evaluates date_understood, guest_count_present, occasion_understood, meal_period_present, audience_identified, availability_check_possible | 8C | ✓ |
| Readiness evaluation stored in normalized_json['readiness_evaluation'] and exposed via GET /enquiries/{id}/readiness | 8C | ✓ |
| DiagnosticsAggregator — unified per-enquiry diagnostic view aggregated from stored normalized_json; covers missing critical fields, occasion normalisation, date context warnings, date ambiguity, date clarification flag, and readiness outcome; graceful on-the-fly fallback when stored values absent | 8C | ✓ |
| GET /enquiries/{id}/diagnostics endpoint returning EnquiryDiagnosticsOut; returns INSUFFICIENT_INFORMATION when no extraction exists | 8C | ✓ |
| Tests: 998 backend, 126 frontend (1,124 total) | 8C | ✓ |

---

## Sprint 7 Issues

| Issue | PR | Title | Status |
|-------|----|-------|--------|
| DOC-014 | #181 | Sprint 7 plan: Freeform Extraction & Processing | ✓ Merged |
| DATA-015 | #182 | Enquiry extraction + processing tables and models | ✓ Merged |
| AI-010 | #183 | Enquiry extraction prompt schema V2 (rich schema) | ✓ Merged |
| AI-011 | #184 | Draft prompt V2 with enriched extraction context | ✓ Merged |
| API-014 | #185 | EnquiryExtractionService (LLM Call 1) | ✓ Merged |
| WORKFLOW-007 | #186 | Deterministic enquiry processing (no LLM) | ✓ Merged |
| API-015 | #187 | Wire freeform intake to extraction → processing → draft | ✓ Merged |
| UI-019 | #188 | Extraction and processing summary in enquiry detail drawer | ✓ Merged |
| TEST-008 | #189 | Freeform extraction and processing tests | ✓ Merged |
| DOC-015 | #190 | Update AI workflow documentation | ✓ Merged |
| — | #192 | Hotfix: generation failed + send failed errors | ✓ Merged |

---

## Sprint 8 Issues

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

## Sprint 8B Issues

| Issue | PR | Title | Status |
|-------|----|-------|--------|
| DOC-017 | #217 | Sprint 8B planning document | ✓ Merged |
| AI-013 | #218 | Enquiry extraction prompt V3 — explicit JSON contract | ✓ Merged |
| AI-014 | #219 | Extend EnquiryExtractionOutput schema for date_request | ✓ Merged |
| DATA-019 | #220 | Add EnquiryDateRequest and EnquiryCandidateDate models + migration | ✓ Merged |
| WORKFLOW-008 | #221 | Deterministic date resolution service | ✓ Merged |
| WORKFLOW-009 | #222 | Wire candidate dates into availability and pricing processing | ✓ Merged |
| API-019 | #223 | Expose date request and candidate date endpoints | ✓ Merged |
| UI-022 | #235 | Show date resolution summary in enquiry detail | ✓ PR open |
| TEST-010 | #236 | Add extraction schema and date resolution tests | ✓ PR open |
| DOC-018 | — | Update freeform extraction and date processing documentation | ✓ In progress |

---

## Sprint 8C Issues

Sprint 8C — **Extraction Quality & Deterministic Enrichment** — focused on closing the accuracy gaps identified in Sprint 8B's three-layer accuracy run (87.1% weighted POC score). All five issues address the LLM-vs-deterministic boundary: push more normalisation and quality assessment into the deterministic layer so the system's behaviour is auditable and testable independent of model variation.

| Issue | PR | Title | Status |
|-------|----|-------|--------|
| ENQ-001 | #247 | Canonical occasion normalisation (OccasionNormalisationService) | ✓ Merged |
| ENQ-002 | #248 | Simplify date intent model (DateIntentNormalizer, migration 20260602_000012) | ✓ Merged |
| ENQ-003 | #249 | Improve date context extraction reliability (DateContextValidator, prompt V4) | ✓ Merged |
| ENQ-004 | #250 | Enquiry readiness evaluation service (EnquiryReadinessEvaluator, /readiness endpoint) | ✓ Merged |
| ENQ-005 | #252 | Extraction quality diagnostics (DiagnosticsAggregator, /diagnostics endpoint) | ✓ Merged |

### What was delivered

**ENQ-001 — Canonical Occasion Normalisation**

The LLM was returning highly variable occasion strings ("sister's birthday dinner", "joint celebration", "leaving do") that downstream code could not match deterministically. `OccasionNormalisationService` maps any raw string to one of 10 canonical values using a keyword-first-match table. The canonical value is written into `normalized_json['occasion_canonical']` at persistence time and exposed alongside the raw value in `ExtractionSummaryOut`. Intake service populates both `occasion_raw` and `occasion_canonical` in the freeform response. 58 unit tests.

**ENQ-002 — Simplified Date Intent Model**

The V3 extraction schema had 9+ fine-grained `date_request_type` values. The LLM conflated them frequently (68% accuracy in the accuracy run). `DateIntentNormalizer` collapses the raw LLM type into 5 stable categories: `exact`, `range`, `recurring`, `ambiguous`, `unknown`. The normalized type is stored in a new `date_request_type_normalized` column (`enquiry_date_requests`, Alembic migration `20260602_000012`, indexed). `EnquiryDateResolutionService._expand()` now dispatches on the normalized type via new `_expand_range()` and `_expand_recurring()` methods that use structural heuristics (presence of `date_range`, `explicit_dates`, `month`, `weekdays`) to route to the correct existing expander — preserving all sub-type expansion logic while making the top-level dispatch stable. 15 unit tests.

**ENQ-003 — Date Context Extraction Reliability**

The accuracy run showed that the LLM left `month`, `year`, `date_range.start_date/end_date`, and `weekdays` null in ~30–40% of applicable cases — the resolver then had no window to expand. Two complementary fixes:

1. **Prompt V4** — `_ENQUIRY_EXTRACTION_V4` adds a `DATE CONTEXT RULES` section instructing the model to always populate month when inferable, year when inferable, `date_range.start_date/end_date` when a range is described, `weekdays` when specific days are mentioned, and `relative_period` when relative language is used. V3 archived.
2. **DateContextValidator** — deterministic post-extraction validation of the `date_request` block. Emits structured warning strings for each missing or inconsistent field. Warnings stored in `normalized_json['date_context_warnings']` and surfaced on `ExtractionResult.date_context_warnings`. 32 unit tests.

**ENQ-004 — Enquiry Readiness Evaluation Service**

`EnquiryReadinessEvaluator` answers "can the system proceed with this enquiry?" deterministically after extraction. Evaluates six criteria (date_understood, guest_count_present, occasion_understood, meal_period_present, audience_identified, availability_check_possible) and maps them to four statuses:

- `READY_FOR_AVAILABILITY` — date + guest count both present, no clarification required
- `NEEDS_CLARIFICATION` — date ambiguous, or guest count missing, or date clarification flagged by LLM
- `WEBFORM_REQUIRED` — date and guest count absent but some context captured (occasion, audience, meal period)
- `INSUFFICIENT_INFORMATION` — nothing critical extracted; cannot determine enquiry intent

The full evaluation (all criteria + status + notes) is stored in `normalized_json['readiness_evaluation']` at persistence time. `GET /enquiries/{id}/readiness` reads the stored evaluation or re-evaluates on the fly for older extractions. 21 unit tests.

**ENQ-005 — Extraction Quality Diagnostics**

`DiagnosticsAggregator` assembles a unified per-enquiry diagnostic view from a stored `EnquiryExtraction` row, reading from `missing_fields`, `extracted_json`, and `normalized_json`. Aggregated signals:

- **Missing critical fields** — `date` and `guest_count` filtered from `extraction.missing_fields`
- **Occasion normalisation** — `occasion_raw` vs `occasion_canonical`, `occasion_normalised` flag
- **Date context warnings** — full list from `normalized_json['date_context_warnings']`, `date_ambiguity_detected` flag
- **Date clarification** — `requires_date_clarification` and `clarification_question` from `extracted_json.date_request`
- **Readiness outcome** — `readiness_status`, `readiness_missing_for_availability`, `readiness_notes` from stored evaluation

The aggregator falls back to on-the-fly computation (via lazy imports of ENQ-001/003/004 services) when stored values are absent, ensuring the endpoint is backward-compatible with pre-Sprint-8C extractions. `GET /enquiries/{id}/diagnostics` returns `EnquiryDiagnosticsOut`; returns `INSUFFICIENT_INFORMATION` when no extraction has been run. 36 unit tests.

UI display for the diagnostics endpoint is deferred — the ENQ-005 issue lacks the mandatory `## UI/UX Reference Requirements` section required by CLAUDE.md.

### Test count summary

| Scope | Before 8C | After 8C | Delta |
|-------|-----------|----------|-------|
| Backend (pytest) | 836 | 998 | +162 |
| Frontend (vitest) | 126 | 126 | 0 |
| **Total** | **962** | **1,124** | **+162** |

---

## Remaining Gaps

| Gap | Priority | Sprint |
|-----|----------|--------|
| ENQ-005 UI — diagnostics display in enquiry detail view (blocked: no UI/UX Reference Requirements in issue) | P2 | 8C |
| Gmail App Password not in CI/CD | P1 | 6 |
| Celery send-draft dispatch not wired in main.py | P1 | 6 |
| Inbound email Celery beat schedule | P2 | 6 |
| Multi-tenant authentication | P1 | 6 |
| E2E browser test (Playwright) | P2 | 6 |
| Audience auto-detection from email domain + CRM lookup | P2 | 6 |
| Production email relay (SendGrid/Postmark) | P2 | Post-POC |
| Room availability — replace seed with live booking system API | P3 | Post-POC |
| Third LLM call for response planning | P2 | Post-POC |
| token_input_count / token_output_count population (Anthropic usage API) | P3 | Post-POC |
| Automated experiment parameter sweep | P3 | Post-POC |
| Experiment comparison dashboard UI | P3 | Post-POC |

---

## Key Reference Documents

| Document | Purpose |
|---|---|
| `docs/product/POC_SPECIFICATION.md` | Full POC scope |
| `docs/demo/poc-demo-guide.md` | Demo walkthrough and stakeholder talking points |
| `docs/sprints/sprint-005-completion-review.md` | Sprint 5A delivery review |
| `docs/demo/poc-demo-guide.md` (updated) | Demo walkthrough including venue context and room selection |
| `docs/sprints/sprint-005c-venue-context.md` | Sprint 5C delivery review |
| `docs/sprints/sprint-006-ai-gateway-prompt-registry.md` | Sprint 6 plan: AI Gateway, Prompt Registry, Traceability |
| `docs/development/ai-gateway.md` | AI Gateway architecture, freeform extraction workflow, prompt governance, experiments, quality scoring |
| `docs/sprints/sprint-007-freeform-extraction-processing.md` | Sprint 7 plan and architecture |
| `docs/sprints/sprint-008-prompt-experimentation-quality-scoring.md` | Sprint 8 plan and architecture |
| `docs/sprints/sprint-008b-extraction-schema-date-resolution.md` | Sprint 8B plan: extraction schema hardening, date resolution, candidate dates |
| `CLAUDE.md` | Developer and AI assistant instructions |
