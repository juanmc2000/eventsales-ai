# Sprint 8B — Extraction Schema Hardening & Deterministic Date Resolution

## Sprint Goal

Harden the freeform enquiry extraction contract so the LLM produces consistent structured JSON,
and add a deterministic backend layer that expands extracted date intent into explicit candidate
dates before availability and pricing checks.

## Non-Goals

- No prompt editing UI
- No automated experiment sweeps
- No response planning layer beyond the existing `recommended_action`
- No production availability engine or live calendar integration
- No ML pricing — all pricing remains deterministic rule-based
- No real customer or restaurant data

---

## Issue Order and Critical Path

```
DOC-017   Sprint 8B planning document         (this file)
AI-013    Enquiry extraction prompt V3         LLM extracts date intent only
AI-014    EnquiryExtractionOutput schema       date_request object
DATA-019  DB models + migration                enquiry_date_requests, enquiry_candidate_dates
WORKFLOW-008  Date resolution service          deterministic expansion
WORKFLOW-009  Wire candidate dates             availability + pricing per candidate date
API-019   Expose read-only endpoints           date-request/latest, candidate-dates
UI-022    Show date resolution summary         enquiry detail drawer
TEST-010  Tests                                all layers
DOC-018   Update documentation                 ai-gateway.md, demo guide, sprint status
```

Critical path: `AI-013 → AI-014 → DATA-019 → WORKFLOW-008 → WORKFLOW-009`

---

## Extraction JSON Contract

The `enquiry_extraction` prompt V3 instructs the LLM to return **only** a valid JSON object
matching this schema. No markdown fences, no preamble, no explanation.

### Schema name: `enquiry_extraction_output`
### Schema version: `3.0`

```json
{
  "customer_name": "string or \"NULL\"",
  "email": "string or \"NULL\"",
  "phone": "string or \"NULL\"",
  "event_type": "string or \"NULL\"",
  "occasion": "string or \"NULL\"",
  "date_request": {
    "raw_text": "string or \"NULL\"",
    "date_request_type": "exact|date_range|multiple_choice|month_flexible|weekday_range_over_relative_period|recurring_window|mixed_relative_dates|ambiguous_numeric_date|unknown",
    "anchor_date": "ISO 8601 date or null",
    "timezone": "string or null",
    "explicit_dates": ["ISO 8601 date", "..."],
    "date_range": {
      "start_date": "ISO 8601 date or null",
      "end_date": "ISO 8601 date or null",
      "flexibility_notes": "string or null"
    },
    "relative_period": {
      "amount": "integer or null",
      "unit": "day|week|month|year or null",
      "direction": "next|last|this or null"
    },
    "weekdays": ["monday", "saturday", "..."],
    "month": "integer 1-12 or null",
    "year": "integer or null",
    "ambiguous_dates": [
      {
        "raw_value": "string",
        "possible_dates": ["ISO 8601 date", "..."],
        "reason": "string"
      }
    ],
    "requires_date_clarification": "boolean",
    "clarification_question": "string or null",
    "confidence": "float 0.0-1.0"
  },
  "event_time": "HH:MM or \"NULL\"",
  "guest_count": "integer or null",
  "meal_period": "lunch|dinner|\"NULL\"",
  "budget": {
    "amount": "number or null",
    "currency": "string or null",
    "budget_type": "total|per_head|null"
  },
  "preferred_room": "string or \"NULL\"",
  "special_requirements": {
    "children": "boolean or null",
    "pets": "boolean or null",
    "disabled_access": "boolean or null",
    "music": "boolean or null",
    "microphone": "boolean or null",
    "screen_or_tv": "boolean or null"
  },
  "dietary_requirements": ["string", "..."],
  "customer_tone": "formal|informal|casual|\"unknown\"",
  "audience_type": "social|corporate|agency|\"unknown\"",
  "missing_fields": ["field_name", "..."],
  "confidence": { "field_name": 0.0 },
  "freeform_notes": "string or \"NULL\""
}
```

---

## NULL Placeholder Convention

The extraction prompt uses a consistent NULL placeholder convention so downstream Pydantic
validation can distinguish "the LLM was unable to extract this value" from a JSON null
(which may have schema implications).

| Field type           | Missing value placeholder |
|---------------------|--------------------------|
| String fields        | `"NULL"` (string)        |
| Numeric fields       | `null` (JSON null)       |
| Object fields        | `null` (JSON null)       |
| Array fields         | `[]` (empty array)       |
| Unknown enum values  | `"unknown"` where schema permits |

The Pydantic schema normalises `"NULL"` string values to Python `None` where appropriate.

---

## date_request Schema

The `date_request` object captures the guest's date intent as stated. The LLM must:

- Extract the raw text from the guest message.
- Classify `date_request_type`.
- Populate the relevant sub-fields.
- Set `requires_date_clarification = true` when the date is ambiguous and cannot be
  deterministically resolved.
- Provide a `clarification_question` when clarification is required.

The LLM must **not**:

- Calculate explicit candidate dates.
- Check availability.
- Assume a specific date from an ambiguous input.
- Expand relative periods (e.g. "next Friday") into calendar dates.

### Supported `date_request_type` values

| Type | Description | Example |
|------|-------------|---------|
| `exact` | Single unambiguous date | "15th August 2026" |
| `date_range` | Start and end date | "3rd to 5th September" |
| `multiple_choice` | Two or more explicit options | "next Friday or Saturday" |
| `month_flexible` | Any date within a month | "sometime in July" |
| `weekday_range_over_relative_period` | Specific weekday(s) within a period | "any Saturday in the next three weeks" |
| `recurring_window` | Repeating pattern | "every Friday in August" |
| `mixed_relative_dates` | Combination of relative references | "next weekend or the one after" |
| `ambiguous_numeric_date` | Date that could be interpreted multiple ways | "05/06" (May 6 or June 5) |
| `unknown` | Cannot classify date intent | Free-text with no recognisable date pattern |

---

## Deterministic Date Resolution Rules

The `EnquiryDateResolutionService` (WORKFLOW-008) expands an extracted `date_request` into
explicit `EnquiryCandidateDate` rows. This service:

- Must not call any LLM.
- Uses the `anchor_date` from the extraction (today's date when absent).
- Uses `Europe/London` as the default timezone when not provided.
- Caps candidate date generation at **60 dates** to prevent runaway expansion.
- Stores `source_type = "deterministic"` on all generated candidate rows.
- Stores `source_type = "explicit"` when `explicit_dates` are provided directly by the LLM.

### Expansion rules per `date_request_type`

| Type | Expansion |
|------|-----------|
| `exact` | One candidate date from `explicit_dates[0]` or parsed anchor |
| `date_range` | All dates from `start_date` to `end_date` inclusive, capped at 60 |
| `multiple_choice` | All dates in `explicit_dates` |
| `month_flexible` | All dates in `month`/`year` up to cap |
| `weekday_range_over_relative_period` | Matching weekdays inside relative period, capped at 60 |
| `recurring_window` | Matching pattern dates within period, capped at 60 |
| `mixed_relative_dates` | Combined from sub-patterns, capped at 60 |
| `ambiguous_numeric_date` | Store `possible_dates` from `ambiguous_dates[0]`, set `requires_date_clarification = true` |
| `unknown` | No candidate dates; set `requires_date_clarification = true` |

---

## Candidate Date Storage Model

Two new tables are created in DATA-019:

### `enquiry_date_requests`

Stores one row per extraction event containing the raw date intent.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| tenant_id | String | Nullable in POC |
| enquiry_id | UUID FK | enquiries.id |
| extraction_id | UUID FK | enquiry_extractions.id (nullable) |
| prompt_run_id | UUID FK | ai_prompt_runs.id (nullable) |
| raw_text | Text | As stated by guest |
| date_request_type | String | See supported types above |
| anchor_date | Date | Date used as reference for relative expansion |
| timezone | String | e.g. Europe/London |
| extracted_json | JSON | Full `date_request` object from LLM |
| requires_date_clarification | Boolean | |
| clarification_question | Text | Nullable |
| confidence | Numeric | LLM confidence 0.0–1.0 |
| created_at | DateTime | |

### `enquiry_candidate_dates`

Stores one row per candidate date generated by the date resolution service.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| tenant_id | String | Nullable in POC |
| enquiry_id | UUID FK | enquiries.id |
| date_request_id | UUID FK | enquiry_date_requests.id |
| candidate_date | Date | Expanded candidate date |
| source_type | String | `explicit` or `deterministic` |
| availability_status | String | Populated by WORKFLOW-009 |
| pricing_checked | Boolean | Set to true after WORKFLOW-009 runs |
| recommended_minimum_spend | Numeric | Nullable; from pricing rule |
| ranking_score | Numeric | Nullable; POC = null |
| created_at | DateTime | |

---

## Availability and Pricing Processing Flow

WORKFLOW-009 updates `EnquiryProcessingService` to operate across candidate dates:

1. Load all `EnquiryCandidateDate` rows for the enquiry (ordered by `candidate_date`).
2. For each candidate date:
   a. Infer `meal_period` from extraction's `event_time` (or default `dinner`).
   b. Call `RoomAvailabilityRepository.get_for_room_date(room_id, candidate_date)`.
   c. Update `availability_status` on the candidate row.
   d. If available, call `PricingRuleService.calculate_recommendation(...)`.
   e. Update `pricing_checked = True` and `recommended_minimum_spend` on the candidate row.
3. Select `recommended_candidate_date` — first available date with pricing.
4. Include a `candidate_date_summary` in the `EnquiryProcessingSnapshot`.
5. If no candidate dates exist, fall back to existing single-date processing flow.
6. If `requires_date_clarification = true`, override recommended action to `request_missing_information`.

The `EnquiryProcessingSnapshot` gains new JSON fields:

```json
{
  "candidate_dates_checked": 5,
  "available_candidate_dates": ["2026-08-15", "2026-08-16"],
  "unavailable_candidate_dates": ["2026-08-14"],
  "recommended_candidate_date": "2026-08-15",
  "requires_date_clarification": false,
  "clarification_question": null
}
```

---

## API Layer (API-019)

Two read-only endpoints:

- `GET /api/v1/enquiries/{id}/date-request/latest`
  Returns the most recent `EnquiryDateRequest` row for the enquiry, or `204` when absent.

- `GET /api/v1/enquiries/{id}/candidate-dates`
  Returns all `EnquiryCandidateDate` rows for the enquiry, ordered by `candidate_date`.

Neither endpoint triggers date resolution, availability checks, or pricing calculation.

---

## UI Layer (UI-022)

A `DateResolutionSection` component is added to `EnquiryDetailDrawer`. It:

- Fetches both endpoints after the drawer opens.
- Shows the extracted raw date text and `date_request_type`.
- Shows a clarification badge when `requires_date_clarification = true`.
- Shows the clarification question when present.
- Lists candidate dates as compact rows with availability status pills and minimum spend where available.
- Uses an empty state when no date request exists.
- Does not expose raw prompts.
- Collapses by default if the drawer is crowded.

---

## Test Strategy (TEST-010)

- **Prompt contract**: assert V3 prompt contains JSON structure, NULL convention, and prohibitions.
- **Extraction schema**: test all `date_request_type` values, NULL placeholder coercion, confidence range validation.
- **Date resolution service**: test every `date_request_type` expansion, cap enforcement, clarification flagging.
- **Candidate date persistence**: test rows are created with correct `source_type`.
- **Processing across candidates**: test available, unavailable, mixed, and clarification scenarios.
- **API endpoints**: test 200, 204, and 404 cases.
- **Frontend**: smoke test that `DateResolutionSection` renders without crashing.

All tests are deterministic — no live LLM calls, no live Gmail calls.

---

## Recommended Extraction LLM Parameters

| Parameter | Recommended starting value | Notes |
|-----------|---------------------------|-------|
| temperature | 0.0–0.1 | Fact extraction — low randomness required |
| top_p | 0.8 | Reduces vocabulary range for structured output |
| top_k | null | Omit unless provider supports cleanly |
| max_tokens | 900–1200 | Allow for full date_request object |

These are starting values for experimentation via the Sprint 8 quality scoring framework.

---

## POC Limitations

- Date resolution uses `Europe/London` timezone by default.
- Ranking score is not calculated in the POC — `ranking_score` is stored as `null`.
- Production systems would use a live calendar to confirm availability; the POC uses the
  `room_availability` seed table.
- The prompt editing UI is not included in this sprint.
- Automated experiment sweeps are not triggered automatically.
- No real customer data is used.
