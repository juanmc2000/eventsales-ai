# Sprint 24 — TEST-028/029 Fixture Hardening + DATE-003 Freeform Date Detection

## Period

2026-06-17

## Sprint Goal

Three parallel workstreams:
1. **TEST-028** — Fix 3 pre-existing failures in `test_first_response_safety_regression_100.py` caused by fixture staleness and a missing validator wire
2. **TEST-029** — Re-anchor the 110-record response-preparation fixture from 2026-06-03 to 2026-07-01 so no `assumed_date` values are in the past
3. **DATE-003** — Implement `FreeformDateClarificationDetector` to handle "next Friday or Saturday" / "mid-July" style freeform date expressions that `DateResolutionService` previously left unresolved

---

## Issues / PRs

| Issue | PR | Description |
|---|---|---|
| TEST-028 (#521) | #522 | Fix safety regression fixture staleness + missing RESP-062 guest_first_name wire |
| TEST-029 (#523) | #524 | Re-anchor response-preparation fixture dates +28 days (2026-06-03 → 2026-07-01) |
| DATE-003 (#525) | #526 | Implement FreeformDateClarificationDetector for edge-case freeform date expressions |

---

## Problem 1 — TEST-028: Safety Regression Test Failures

### Root cause A: RESP-042 / RESP-060 stale expected values

`services/api/tests/fixtures/first_response_safety_cases_100.json` scenarios `fs1_051–058` and `fs1_097–100` were seeded before RESP-042 (Sprint 12) and RESP-060 (Sprint 14) were implemented. They had `compliance_passed: True` in the fixture, but the validators now correctly catch their violations:

- `fs1_051–058`: drafts suggest alternative dates when `CONFIRMED_UNAVAILABLE` — RESP-042 invented-alternatives check now flags these
- `fs1_097–100`: drafts use room suitability language when venue is unavailable — RESP-060 room suitability check now flags these

### Root cause B: RESP-062 validator silently skipped

`_context_from_scenario()` in `test_first_response_safety_regression_100.py` assembled a `ValidationContext` but never passed `guest_first_name` → `expected_customer_name`. `CustomerNameConsistencyValidator` requires this field; when absent it silently skips the check. Scenario `resp062_001` was failing because the validator was never exercised.

---

## Problem 2 — TEST-029: Stale Fixture Anchor Date

The 110-record fixture `freeform_group_booking_response_preparation_test_100.json` was anchored at 2026-06-03. Sprint 24 began 2026-06-17. All 88 unique `assumed_date` ISO strings predating 2026-07-01 would fall in the past, causing `ResponsePriorityEngine` to produce `URGENT` for any date < 2 days from today — inflating URGENT counts and invalidating priority Layer 3 checks.

No natural-language dates appeared in the fixture (all freeform date expressions in guest bodies); every date reference was a resolved ISO string. This allowed a clean mechanical +28-day shift.

---

## Problem 3 — DATE-003: Unresolved Freeform Date Expressions

`DateResolutionService` resolved structured and LLM-parsed date types but had no handler for expressions like "next Friday or Saturday" or "mid-July". These produced `type=unknown`, no `candidate_dates`, and no `requires_clarification` flag — so they fell through to `STATUS_UNKNOWN` and the engine returned `REQUEST_MISSING_INFORMATION` rather than the more precise `REQUEST_DATE_CONFIRMATION`.

---

## Fixes

### Fix 1 (TEST-028A) — Stale compliance_passed in fixture

Flipped `compliance_passed: true → false` for 12 scenarios in `first_response_safety_cases_100.json`:
- `fs1_051–058`: invented-alternatives violation (RESP-042)
- `fs1_097–100`: room suitability language when unavailable (RESP-060)

### Fix 2 (TEST-028B) — Missing RESP-062 validator wire

Added `expected_customer_name=ctx.get("guest_first_name")` to `_context_from_scenario()` in `test_first_response_safety_regression_100.py`. `CustomerNameConsistencyValidator` now fires on the `resp062_*` scenarios.

### Fix 3 (TEST-029) — Re-anchor fixture dates

Shifted all 88 unique ISO date strings in `freeform_group_booking_response_preparation_test_100.json` forward +28 days (minimum new anchor: 2026-07-01). Day-of-week alignment preserved; priority distribution unchanged (URGENT 2 / HIGH 21 / NORMAL 78 / LOW 9). Updated `ANCHOR_DATE = date(2026, 7, 1)` in `run_response_preparation_accuracy_100.py`.

### Fix 4 (DATE-003) — FreeformDateClarificationDetector

New service at `services/api/app/modules/enquiries/freeform_date_clarification_detector.py`:

- **Pattern 1 — Multi-option weekday**: `_MULTI_WEEKDAY_OR_PATTERN` regex matches "next Friday or Saturday", "Thursday or Friday next week", "Could we book Saturday or Sunday?". Resolves both weekdays to ISO dates relative to anchor; generates "Could you confirm whether you mean Friday, 10 July or Saturday, 11 July?"
- **Pattern 2 — Approximate month range**: `_APPROXIMATE_MONTH_PATTERN` regex matches "mid-July", "early August", "late September", "end of August". Year-wraps when named month is in the past. Generates "Could you let me know the specific date you have in mind for mid-July 2026?"

Wired into `DateResolutionService` as step 3b (fallback): fires only when `date_request_type_normalized == "unknown"` and `not candidate_dates` and `raw_text` is present. On match: sets `requires_clarification=True` and `clarification_question`. This propagates through `_build_date_resolution_status()` → `STATUS_AMBIGUOUS` → `REQUEST_DATE_CONFIRMATION`.

---

## Result

### Safety Regression Test (TEST-028)

| Before | After |
|---|---|
| 3 failures (fs1_051–058 × 8, fs1_097–100 × 4, resp062_001) | **0 failures — 100 passed** |

### Response Preparation Runner — 110-record LLM eval (TEST-029 baseline)

Run: `20260617T183121Z` | Model: claude-haiku-4-5-20251001 | Prompt V7 | Temp 0.4 | Anchor: 2026-07-01

| Metric | Score |
|---|---|
| Compliance | 110/110 (100%) |
| Auto-send | 110/110 (100%) |
| Persona-fit | 110/110 (100%) |
| Safety | 0/110 |
| Overall | **10/10** |

Goal distribution: CONFIRM_AVAILABLE 95 / REQUEST_DATE_CONFIRMATION 15

Opener tone: neutral 54 / warm_celebratory 47 / refined 8 / professional 1

---

## Key Files Modified

| File | Change |
|---|---|
| `services/api/tests/fixtures/first_response_safety_cases_100.json` | 12 scenarios: `compliance_passed: true → false` |
| `services/api/tests/ai/test_first_response_safety_regression_100.py` | `_context_from_scenario()`: pass `expected_customer_name=ctx.get("guest_first_name")` |
| `tests/data/freeform_group_booking_response_preparation_test_100.json` | 88 ISO dates shifted +28 days |
| `tests/scripts/run_response_preparation_accuracy_100.py` | `ANCHOR_DATE = date(2026, 7, 1)` |
| `services/api/app/modules/enquiries/freeform_date_clarification_detector.py` | NEW — FreeformDateClarificationDetector |
| `services/api/app/modules/enquiries/date_resolution_service.py` | Step 3b fallback: FreeformDateClarificationDetector integration |
| `services/api/tests/enquiries/test_freeform_date_clarification_detector.py` | NEW — 18 tests |

---

## Test Counts

| Suite | Count |
|---|---|
| Backend (pytest) | **2,948 passed** (+58 from Sprint 23 baseline of 2,890) |
| Frontend (vitest) | 126 passed |
| **Total** | **3,074** |

All pre-existing failures in `test_first_response_safety_regression_100.py` resolved in TEST-028.
