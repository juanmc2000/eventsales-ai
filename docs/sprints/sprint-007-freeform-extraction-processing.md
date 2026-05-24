# Sprint 7 — Freeform Enquiry Extraction and Deterministic Processing

## Sprint Goal

Split freeform enquiry handling into three distinct stages — extraction, deterministic processing, and draft generation — so that each stage has a single, testable responsibility and the system never delegates availability, pricing, or room matching decisions to an LLM.

---

## Non-Goals

- Prompt editing or approval UI
- Multi-tenant authentication hardening
- Inbound email classification
- Live room availability from a booking system API
- Audience auto-detection from email domain
- Advanced response planning LLM call (deferred to MVP three-call architecture)
- A/B testing or experimentation framework
- Fine-tuning or model training pipelines
- Production workflow automation
- Any new frontend page beyond the extraction/processing summary panel in enquiry detail

---

## Issue Order

| Order | Issue | Description |
|-------|-------|-------------|
| 1 | DOC-014 | Create Sprint 7 Freeform Processing Plan (this document) |
| 2 | DATA-015 | Add Enquiry Extraction and Processing Snapshot Tables |
| 3 | AI-010 | Add Enquiry Extraction Prompt and Schema |
| 4 | API-014 | Add Enquiry Extraction Service |
| 5 | WORKFLOW-007 | Add Deterministic Enquiry Processing Service |
| 6 | AI-011 | Update Draft Generation to Use Extraction and Processing Snapshot |
| 7 | API-015 | Wire Freeform Intake to Extraction → Processing → Draft |
| 8 | UI-019 | Show Extraction and Processing Summary in Enquiry Detail |
| 9 | TEST-008 | Add Freeform Extraction and Processing Tests |
| 10 | DOC-015 | Update AI Workflow Documentation |

---

## Two-Call POC Architecture

The POC uses two AI Gateway calls per freeform enquiry. Deterministic processing runs between them.

```
Freeform customer text
        |
        v
[Call 1: Extraction]
  AIGateway.run(prompt_key="enquiry_extraction", ...)
  Output: structured EnquiryExtractionOutput
  Persisted: enquiry_extractions row
        |
        v
[Deterministic Processing]
  Room matching (by capacity, type, preferred_area)
  Pricing calculation (from pricing rules)
  Availability check (from room_availability table)
  Missing field identification
  Persisted: enquiry_processing_snapshots row
        |
        v
[Call 2: Draft Generation]
  AIGateway.run(prompt_key="draft_response_v1", ...)
  Context enriched with extraction + processing snapshot
  Output: DraftEmailOutput (subject + body)
  Persisted: ai_prompt_runs row
```

### Call 1 — Extraction

**Prompt key:** `enquiry_extraction`

**Input:** raw freeform customer text (from enquiry_messages)

**Output:** structured JSON with:
- `occasion`, `guest_count`, `event_date`, `event_time`, `event_type`
- `budget` (amount, currency, budget_type)
- `allergens`
- `special_requirements` (children, pets, disabled_access, music, microphone, screen_or_tv)
- `freeform_notes`
- `missing_fields` (list of field names the model could not extract)
- `confidence` (per-field confidence values)

**Constraints:**
- The extraction prompt must explicitly prohibit pricing decisions.
- The extraction prompt must explicitly prohibit availability decisions.
- The extraction prompt must explicitly prohibit customer-facing copy.
- If a field is ambiguous, the model must include it in `missing_fields` rather than guessing.

### Deterministic Processing

Runs entirely in Python. No LLM involvement. Reads from PostgreSQL only.

**Responsibilities:**
- Room matching: select the best matching room using `_match_room()` logic (preferred_area → capacity → first active)
- Pricing: apply pricing rules deterministically based on guest count, event type, and demand events
- Availability: query `room_availability` for the extracted date and meal period
- Missing field aggregation: merge model-reported missing fields with business-logic gaps (e.g. no date → cannot check availability)
- Recommended action: one of `send_draft`, `request_more_info`, `flag_for_review`

**Output:** `enquiry_processing_snapshots` row with:
- `availability_result_json`
- `room_suitability_json`
- `pricing_result_json`
- `missing_fields_json`
- `recommended_action`

### Call 2 — Draft Generation

**Prompt key:** `draft_response_v1` (existing, updated to accept enriched context)

**Context enrichment:** the system prompt and user message are built from:
- persona (tone, style)
- extracted facts from `enquiry_extractions`
- room name and suitability from processing snapshot
- pricing recommendation from processing snapshot
- availability status from processing snapshot
- missing fields list

**Output:** `DraftEmailOutput` (subject, body) — unchanged from Sprint 6 schema

---

## Future Three-Call MVP Architecture

The MVP will introduce a third call between extraction and draft generation for advanced response planning. This call is not implemented in this sprint.

```
[Call 1: Extraction]        — same as POC
        |
        v
[Deterministic Processing]  — same as POC
        |
        v
[Call 2: Response Planning] — NEW in MVP
  Input: extraction + processing snapshot + persona
  Output: structured response plan (tone, key points, what to ask for, what to offer)
        |
        v
[Call 3: Draft Generation]  — renamed from POC Call 2
  Input: response plan + persona
  Output: DraftEmailOutput
```

The POC keeps Call 2 and Call 3 combined. They must not be artificially split in this sprint. The sprint should be designed so the split can be added later without breaking the existing API contract.

---

## AI Gateway Usage Rules

- All LLM calls must go through `AIGateway.run()`. No module may call an AI provider directly.
- Every call must specify a `prompt_key` registered in `PromptRegistry`.
- Every call must declare an `output_schema` for structured validation.
- Fallback provider behaviour must remain functional when `ANTHROPIC_API_KEY` is absent.
- Extraction failures must be logged and surfaced as `status="error"` — never silently swallowed.
- The gateway must never be called inside a Celery task in this sprint (draft generation remains synchronous on the API side for the POC).

---

## Deterministic Processing Responsibilities

The following decisions are always deterministic. They must never be delegated to an LLM:

| Decision | Where |
|----------|-------|
| Which room to assign | `_match_room()` in DraftGenerationService or ProcessingService |
| Minimum spend / pricing | Pricing rules from `pricing_rules` table |
| Room availability status | `room_availability` table lookup |
| Whether to flag for review | Missing fields threshold in ProcessingService |
| Recommended action | ProcessingService; one of `send_draft`, `request_more_info`, `flag_for_review` |

---

## Success Criteria

- Freeform intake flow produces a stored extraction row before any draft is generated.
- Processing snapshot is persisted and linked to the extraction row.
- Draft generation prompt receives enriched context from the processing snapshot.
- Extraction failures do not crash the intake flow — they degrade gracefully to the existing fallback path.
- The enquiry detail page shows the extraction summary and processing snapshot to the operator.
- All existing tests continue to pass.
- New tests cover extraction service, processing service, and the wired intake flow.

---

## Definition of Done

- [ ] `enquiry_extractions` table exists with Alembic migration
- [ ] `enquiry_processing_snapshots` table exists with Alembic migration
- [ ] `enquiry_extraction` prompt is registered in `PromptRegistry` with output schema
- [ ] `EnquiryExtractionService` extracts structured facts from freeform text via AI Gateway
- [ ] `EnquiryProcessingService` runs deterministic room matching, pricing, and availability checks
- [ ] `DraftGenerationService` uses extraction + processing snapshot when available
- [ ] Freeform intake API wires extraction → processing → draft in sequence
- [ ] Extraction and processing summary panels are shown in the enquiry detail page
- [ ] All Sprint 7 tests pass
- [ ] All existing backend and frontend tests continue to pass (493 backend, 84 frontend baseline)
- [ ] AI Gateway is the sole LLM entry point — no direct provider calls
- [ ] No new Python packages added without explicit approval
- [ ] No prompt-management UI added
- [ ] No ML pricing added
- [ ] POC scope preserved
- [ ] `SPRINT_STATUS_OVERVIEW.MD` updated to reflect Sprint 7
- [ ] AI workflow documentation updated
