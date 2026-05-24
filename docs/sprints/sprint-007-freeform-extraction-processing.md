# Sprint 7 — Freeform Enquiry Extraction & Deterministic Processing

**Sprint:** 7
**Theme:** Freeform Enquiry Extraction & Deterministic Processing
**Status:** In Progress

---

## Objective

Split the freeform enquiry handling into three distinct steps:
1. **LLM Call 1 — Extraction**: structured fact extraction from natural-language text
2. **Deterministic Processing**: room matching, availability, pricing, recommended action
3. **LLM Call 2 — Draft Generation**: response drafted using enriched context from steps 1–2

This replaces the original single-call freeform flow (intake → draft) with a more traceable, debuggable pipeline.

---

## Two-call POC Architecture

```
POST /api/v1/enquiries/intake/freeform
  │
  ├─ 1. Create enquiry + inbound message
  │
  ├─ 2. LLM Call 1: EnquiryExtractionService
  │      prompt_key = "enquiry_extraction" (V2)
  │      extracts: guest_count, event_date, event_type, occasion, budget,
  │                allergens, special_requirements, missing_fields, confidence
  │
  ├─ 3. Deterministic: EnquiryProcessingService
  │      room match → availability → pricing → recommended_action
  │      (pure Python, no LLM)
  │
  └─ 4. LLM Call 2: DraftGenerationService.generate_draft()
         prompt_key = "draft_response" (V2)
         enriched context from processing snapshot
```

---

## Future Three-call MVP Architecture

In the production MVP, a third LLM call may be added for **response planning** (e.g. handling room conflicts, generating multiple alternatives, personalising based on CRM data). This is **not** built in the POC.

---

## Deterministic Processing Responsibilities

`EnquiryProcessingService` is **pure Python — no LLM calls**:

| Step | Logic |
|------|-------|
| Room matching | preferred_area substring → capacity >= party_size → first active room |
| Availability | `RoomAvailabilityRepository.get_for_room_date(room_id, event_date)` |
| Meal period | Inferred from event_time: before 15:00 = lunch, else dinner |
| Pricing | `PricingRuleService.calculate_recommendation()` |
| Missing fields | Checks `guest_count` and `event_date` as critical fields |
| Recommended action | Deterministic selection from 6 defined actions |

---

## AI Gateway Rules

- **All LLM calls route through `AIGateway.run()`** — no direct `AnthropicProvider` calls in service code
- **Extraction and draft are separate prompt keys** — they must not share a prompt definition
- **Deterministic processing must run before draft** — the draft uses the processing snapshot
- **Failures are isolated** — extraction failure does not prevent draft; processing failure does not prevent draft

---

## Storage Tables

| Table | Migration | Purpose |
|-------|-----------|---------|
| `enquiry_extractions` | `20260524_000006` | Per-extraction row: extracted/normalized JSON, missing fields, confidence |
| `enquiry_processing_snapshots` | `20260524_000006` | Per-processing row: availability, room suitability, pricing, recommended_action |

Both are linked to `enquiries.id` (foreign key). The extraction is also linked to `ai_prompt_runs.id` via `prompt_run_id`.

---

## Prompt Versions

| Prompt key | V1 status | V2 status |
|------------|-----------|-----------|
| `enquiry_extraction` | Archived | Active — Sprint 7 rich schema |
| `draft_response` | Archived | Active — enriched with availability/pricing/missing_questions |

---

## Issues

| Issue ID | Title | PR | Status |
|----------|-------|-----|--------|
| DOC-014 | Sprint 7 plan | #181 | ✓ Merged |
| DATA-015 | Enquiry extraction + processing models and migration | #182 | Open |
| AI-010 | Enquiry extraction prompt schema (V2) | #183 | Open |
| AI-011 | Update draft prompt to use extraction context (V2) | #184 | Open |
| API-014 | EnquiryExtractionService | #185 | Open |
| WORKFLOW-007 | Deterministic enquiry processing | #186 | Open |
| API-015 | Wire freeform intake to extraction → processing → draft | #187 | Open |
| UI-019 | Show extraction and processing summary in enquiry detail | #188 | Open |
| TEST-008 | Add freeform extraction and processing tests | #189 | Open |
| DOC-015 | Update AI workflow documentation | In progress | Open |

---

## Acceptance Criteria

- [ ] Freeform submission creates enquiry
- [ ] Freeform submission runs LLM extraction and stores `enquiry_extractions` row
- [ ] Freeform submission runs deterministic processing and stores `enquiry_processing_snapshots` row
- [ ] Draft generation loads processing snapshot and enriches `DraftContext`
- [ ] Freeform intake response includes extraction summary and recommended action
- [ ] Enquiry detail drawer shows extraction facts and processing results
- [ ] Tests cover extraction, processing, draft enrichment, and orchestration ordering
- [ ] Documentation updated to reflect split architecture
- [ ] No direct LLM calls outside AI Gateway

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Freeform end-to-end latency | < 15s (two LLM calls + processing) |
| Extraction validation rate | > 80% `passed` with ANTHROPIC_API_KEY set |
| Draft generation fallback rate | < 10% with ANTHROPIC_API_KEY set |
| Test coverage | New tests for all three services + orchestration |

---

## Definition of Done

1. All 10 Sprint 7 PRs reviewed and merged to `main`
2. `pytest` suite passes at ≥ 600 tests (up from 493)
3. Frontend vitest suite passes at ≥ 90 tests (up from 84)
4. Docker Compose demo (`/webform`) shows extraction summary + recommended action
5. `SPRINT_STATUS_OVERVIEW.MD` updated with Sprint 7

---

## Out of Scope

- Third LLM call for response planning
- Pricing algorithm redesign
- Room availability redesign (live booking system integration)
- Prompt editing UI
- Evaluation dashboard or quality scoring
- CRM integrations
- Production workflow builder
- Multi-tenant authentication
