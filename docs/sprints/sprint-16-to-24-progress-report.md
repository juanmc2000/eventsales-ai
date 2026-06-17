# EventSales AI — Sprint 16 to 24 Progress Report

**Period:** 2026-06-15 to 2026-06-17
**Total PRs merged:** #498–#526 (27 PRs)
**Test count at start (post-Sprint 15):** ~2,826 backend | 126 frontend
**Test count at end (post-Sprint 24):** **2,948 backend | 126 frontend = 3,074 total**
**Evaluation score at start:** 9.8/10 (100 records, 60% persona-fit)
**Evaluation score at end:** **10/10** (110 records, 100% on all metrics)

---

## Overview

These nine sprints completed the response preparation evaluation pipeline and hardened the AI-generated first-response system against a series of correctness gaps exposed when end-to-end LLM testing was first enabled. The work fell into four themes:

1. **Persona restoration** (Sprint 16–17) — audience-specific tone enforcement so corporate, agency, luxury, and social audiences each receive correctly-toned responses
2. **Evaluation pipeline completion** (Sprints 18–20) — fixture staleness fixes, luxury audience coverage, and upstream classification corrections
3. **Fixture integrity** (Sprints 21–23) — email_108 date ambiguity fix, social/corporate boundary refinement, accuracy runner staleness fixes
4. **Hardening and date detection** (Sprint 24) — safety regression fixture corrections, fixture re-anchoring, freeform date expression handling

---

## Sprint 16 — Audience-Aware Persona Restoration

**PRs:** #498–#504 | **Date:** 2026-06-15

### Problem

Sprint 15 achieved 100% factual compliance but did not surface tone failures. All `CONFIRM_AVAILABLE` drafts used the same LLM warmth prompt regardless of audience, reliably producing social warmth openers ("How wonderful — a board meeting with us!") for corporate, agency, and luxury senders. These were off-brand and would have blocked auto-send had tone validation existed. Persona-fit score: 60/100.

### Deliverables

| Issue | PR | Description |
|---|---|---|
| TEST-022 | #499 | 30-scenario audience tone regression fixture + offline runner |
| RESP-074 | #500 | Audience-specific deterministic opener copy blocks in `FirstResponseCopyLibrary.audience_opener()` |
| RESP-075 | #498 | `AudienceToneValidator` — deterministic forbidden-phrase guard per audience type |
| RESP-076 | #501 | Audience-specific system prompts + inline `_audience_tone_guard()` in warmth generator |
| TEST-023 | #502 | Persona-fit scoring layer in 100-record evaluation runner |
| RESP-077 | #503 | `AutoSendReadinessGate` Rule 7 — audience tone failure blocks auto-send |
| DOC-020 | #504 | Sprint 16 reference doc |

### Tone Rules Introduced

**Corporate / agency forbidden phrases:** "how wonderful", "how lovely", "how exciting", "how delightful", "what a lovely occasion", "what a wonderful", "such a special occasion", "such a meaningful occasion", "celebration with us", "will be special", "delighted to celebrate", "thrilled"

**Luxury forbidden phrases:** "amazing", "fantastic", "brilliant", "super", "totally", "can't wait", "how exciting"

**Social / unknown:** no restrictions

### Auto-send Rule 7

`tone_validation_result.passed = False` → blocked. `None` → skipped (backwards-compatible with callers that don't run tone validation).

### Result

Persona-fit: 60/100 → measured (infrastructure introduced; full fix in Sprint 17).
Test count: **2,866 backend + 126 frontend = 2,992 total**

---

## Sprint 17 — Audience-Conditional Warmth Wiring

**PRs:** #509–#510 | **Date:** 2026-06-15

### Problem

Sprint 16 introduced the validators and copy blocks but the test runner's `_build_confirm_available()` still passed a hardcoded social-warmth instruction to the LLM regardless of audience type. The production `service.py` had the same gap.

### Changes

| Issue | PR | Description |
|---|---|---|
| RESP-078 | #509 | Audience-conditional warmth instruction in `_build_confirm_available()` in the test runner |
| RESP-079 | #510 | Wire `AudienceToneValidator` + Rule 7 into runner and production `service.py` |

**Runner:** Added `_warmth_instruction_for_audience(audience_type)` helper dispatching on social / corporate / agency / luxury / unknown. `AudienceToneValidator.validate()` called post-generation; `tone_validation_result` passed to `AutoSendReadinessGate`.

**Production `service.py`:** `AudienceToneValidator.validate()` called in `_generate_deterministic_confirm_available_draft()`; tone result wired through to Rule 7.

### Baseline (100 records, run 20260615T102113Z)

| Metric | Score |
|---|---|
| Compliance | 100/100 (100%) |
| Auto-send | 99/100 (99%) |
| Persona-fit | **100/100 (100%)** ↑ from 60% |
| Tone validation | **86/86 CONF (100%)** |
| Overall | **9.8/10** |

---

## Sprint 18 — email_48 Fixture Meal Period Fix

**PRs:** #512 | **Date:** 2026-06-17

### Problem

`email_48` (work team meal, "around 4ish") predated RESP-066 (meal period inference from `event_time`). The fixture still had `meal_period = unknown` and `response_goal = REQUEST_MISSING_INFORMATION`, causing the system to ask "breakfast, lunch or dinner?" despite a clearly implied afternoon time.

### Change

| Issue | PR | Description |
|---|---|---|
| TEST-024 | #512 | Update email_48 fixture to reflect RESP-066 meal period inference |

Updated `email_48`: `meal_period` unknown→dinner, `response_goal` RMI→CONF, `availability_status` INSUFFICIENT→AVAILABLE, `clarification_questions` cleared, `spend_line` set to £1,100.

### Baseline (100 records, run 20260617T123025Z)

| Metric | Score |
|---|---|
| Compliance | 100/100 (100%) |
| Auto-send | **100/100 (100%)** ↑ from 99% — **first perfect** |
| Persona-fit | 100/100 (100%) |
| Overall | **10/10** — **first perfect** |

---

## Sprint 19 — Luxury/HNW Records Added to Fixture

**PRs:** #513 | **Date:** 2026-06-17

### Problem

Fixture had zero luxury/HNW records. The luxury warmth pathway (luxury system prompt, `_LUXURY_GUARD`, `AudienceToneValidator` luxury check) was never exercised by the main evaluation runner.

### Change

| Issue | PR | Description |
|---|---|---|
| TEST-025 | #513 | Add 10 luxury/HNW records (email_101–110) to fixture; per-audience runner breakdown |

10 luxury records added: 8 CONF (anniversary dinner, proposal dinner, 40th/50th birthday, wine pairing, private luncheon, family celebration, engagement dinner) + 2 RDTC (ambiguous-date private dinners). Guest counts 2–12. Spends £800–£4,800. Persona: Eleanor (refined/gracious).

Fixture expanded from 100 → **110 records**.

### Fixture Distribution (post-Sprint 19)

| Audience | Count |
|---|---|
| Social | 51 |
| Corporate | 38 |
| Agency | 9 |
| Luxury | **10** |
| Unknown | 2 |

### Baseline (110 records, run 20260617T134116Z)

| Metric | Score |
|---|---|
| Compliance | 110/110 (100%) |
| Auto-send | 110/110 (100%) |
| Persona-fit | 110/110 (100%) |
| Luxury persona-fit | **10/10** — first luxury run |
| Refined openers | **7** — new opener tone category |
| Overall | **10/10** |

---

## Sprint 20 — Corporate Context Classification (RESP-080)

**PRs:** #514 | **Date:** 2026-06-17

### Problem

`CustomerTypeResolver` Rule 5 (consumer domain → social) fired before any check on enquiry content. Board meetings, client dinners, and work team meals from Gmail or personal addresses classified as `social`. Affected records: email_48 (work team meal), email_57 (board meeting / proton.me), email_72 (board meeting / gmail), email_77 (client dinner / hotmail).

### Change

| Issue | PR | Description |
|---|---|---|
| RESP-080 | #514 | Rule 2b in `CustomerTypeResolver` — corporate context text overrides consumer-domain social inference |

New **Rule 2b** between Rule 2 and Rule 3:

```python
_CORPORATE_CONTEXT_SIGNALS = (
    "board meeting", "client meeting", "client dinner", "client lunch",
    "client workshop", "team meeting", "work team meal", "business breakfast",
    "corporate lunch", "corporate dinner", "pa booking", "ea booking",
    "managing director", "private office", "family office",
)
```

Confidence 0.88 — wins over consumer-domain Rule 5 (0.80); Rule 2 agency text still wins when both signals present.

4 fixture records reclassified social → corporate. 12 new tests in `TestRule2bCorporateContextText`.

### Baseline (110 records, run 20260617T143231Z)

| Metric | Score |
|---|---|
| Corporate records | **42** (↑ from 38) |
| Social records | **47** (↓ from 51) |
| All metrics | **110/110 (100%)** |
| Overall | **10/10** |

### Test count: 2,878 backend + 126 frontend = **3,004 total**

---

## Sprint 21 — email_108 Date Ambiguity Fix (TEST-026)

**PRs:** #516 | **Date:** 2026-06-17

### Problem

`email_108` (luxury RDTC, private dinner for 8 guests, Georgina Harlow) used date "5/7" which:
1. Auto-resolves via Rule 4 (HOTFIX-008) — British interpretation 5 July is within `NEAR_HORIZON_DAYS=120`; American rolls to 7 May 2027 at 338 days. Rule 4 fires: British near, American far → `RESOLVED`, no RDTC generated.
2. `alternative_date: 2026-05-07` was in the past relative to both anchor date and today.

### Change

| Issue | PR | Description |
|---|---|---|
| TEST-026 | #516 | Replace email_108 enquiry date "5/7" with genuinely ambiguous "7/8" |

Changed to **"7/8"**: British (7 August, 65 days) and American (8 July, 35 days) both within 120 days, difference 30 days ≤ `CLOSE_CALL_DAYS=30` → Rule 7 → `UNRESOLVED_AMBIGUITY` → RDTC. 17 fixture fields updated.

### Baseline (110 records, run 20260617T155603Z): **110/110, 10/10** — no regressions.

---

## Sprint 22 — Social Context Classification + Client Thank-You (RESP-081)

**PRs:** #518 | **Date:** 2026-06-17

### Problem

Two classification failures remained after Sprint 20:
1. `email_52` (client thank-you meal, hotmail) and `email_62` (client thank-you lunch, icloud) were classifying as `social` (consumer domain → Rule 5) instead of `corporate`. "Client thank-you" is a corporate-context signal not yet in `_CORPORATE_CONTEXT_SIGNALS`.
2. Personal occasion enquiries from corporate email addresses (e.g. birthday from deloitte.com, hen do from barclays.co.uk) were classifying as `corporate` because Rule 3 (known corporate domain) fired before any content check.

### Change

| Issue | PR | Description |
|---|---|---|
| RESP-081 | #518 | Rule 2c social context text + "client thank-you" extended to corporate signals |

**Part 1 — Corporate signal extension:** Added `"client thank-you"` and `"client thank you"` to `_CORPORATE_CONTEXT_SIGNALS`. Fixes email_52 and email_62 (social → corporate).

**Part 2 — New Rule 2c (`_SOCIAL_CONTEXT_SIGNALS`):** Inserted between Rule 2b (confidence 0.88) and Rule 3 (confidence 0.90). 16 signals: birthday, baby shower, baby naming, hen party, hen do, stag party, stag do, engagement party, leaving do, leaving party, flatmate, christening, graduation dinner/lunch/celebration, wedding anniversary. Fires at confidence 0.85. Rule 2b wins when both corporate + social context present.

8 fixture records corrected:
- email_52, email_62: social → corporate
- email_13 (google.com / birthday), email_24 (amazon.com / birthday), email_54 (deloitte.com / hen do), email_56 (barclays.co.uk / leaving do), email_58 (kpmg.com / stag do), email_80 (ambiguous / leaving party): corporate → social

**12 new tests** in `TestRule2cSocialContextText`.

### Final fixture distribution (post-Sprint 22)

| Audience | Count |
|---|---|
| Social | **51** |
| Corporate | **38** |
| Agency | 9 |
| Luxury | 10 |
| Unknown | 2 |

### Baseline (110 records, run 20260617T164349Z): **110/110, 10/10** | warm_celebratory 47, neutral 55.

### Test count: 2,890 backend + 126 frontend = **3,016 total**

---

## Sprint 23 — Accuracy Runner Staleness Fix (TEST-027)

**PRs:** #520 | **Date:** 2026-06-17

### Problem

`run_response_preparation_accuracy_100.py` was failing (score 0.839) with:
- **Layer 2 — ResponseGoalEngine: 14/110 passed.** 95 CONF fixture records had `response_goal: "READY_TO_CONFIRM_AVAILABILITY"` (deprecated alias from RESP-005). The engine never produces this string; it returns `ACKNOWLEDGE_AND_CHECK_AVAILABILITY` when no `availability_decision` is supplied.
- **Layer 3 — ResponsePriorityEngine: 100/110 passed.** 10 luxury records had `response_priority: "HIGH"` but their event dates were 23–80 days from anchor → NORMAL bucket. `ResponsePriorityEngine` is date-only; luxury audience has no priority boost.
- **email_108 secondary failure.** `date_status: "UNRESOLVED_AMBIGUITY"` was not in `_DATE_STATUS_MAP` → defaulted to `STATUS_UNKNOWN` → engine returned `REQUEST_MISSING_INFORMATION` instead of `REQUEST_DATE_CONFIRMATION`. Also, `candidate_dates` was still `["2026-07-05"]` from the old "5/7" date.

### Change

| Issue | PR | Description |
|---|---|---|
| TEST-027 | #520 | Fix accuracy runner: deprecated goal, luxury priority, UNRESOLVED_AMBIGUITY mapping, email_108 candidates |

Five fixes:
1. 95 CONF records: `"READY_TO_CONFIRM_AVAILABILITY"` → `"ACKNOWLEDGE_AND_CHECK_AVAILABILITY"`
2. 10 luxury records: `"HIGH"` → `"NORMAL"`
3. email_108 `candidate_dates`: `["2026-07-05"]` → `["2026-08-07", "2026-07-08"]`
4. `_DATE_STATUS_MAP`: added `"UNRESOLVED_AMBIGUITY"` and `"unresolved_ambiguity"` → `STATUS_AMBIGUOUS`
5. Goal distribution display list: added `ACKNOWLEDGE_AND_CHECK_AVAILABILITY` and `CONFIRM_AVAILABLE`

### Result

| Layer | Before | After |
|---|---|---|
| Layer 2 (ResponseGoalEngine) | 14/110 | **110/110** |
| Layer 3 (ResponsePriorityEngine) | 100/110 | **110/110** |
| Overall | 0.839 FAIL | **1.000 PASS** |

---

## Sprint 24 — Fixture Hardening + Freeform Date Detection

**PRs:** #522, #524, #526 | **Date:** 2026-06-17

Three parallel workstreams.

### TEST-028 — Safety Regression Fixture Staleness

| Issue | PR | Description |
|---|---|---|
| TEST-028 | #522 | Fix 3 pre-existing failures in `test_first_response_safety_regression_100.py` |

**Root cause A — RESP-042 / RESP-060 stale expected values:**

- `fs1_051–058`: Drafts suggest alternative dates when `CONFIRMED_UNAVAILABLE`. These scenarios were seeded before RESP-042 (Sprint 12) added the invented-alternatives check. Fixture said `compliance_passed: true`; validator now correctly flags as false.
- `fs1_097–100`: Drafts use room suitability language when venue is unavailable. Seeded before RESP-060 (Sprint 14). Fixture said `compliance_passed: true`; RESP-060 now catches these.

Fix: `compliance_passed: true → false` for 12 scenarios.

**Root cause B — RESP-062 validator silently skipped:**

`_context_from_scenario()` in the test file built a `ValidationContext` but never passed `guest_first_name` → `expected_customer_name`. `CustomerNameConsistencyValidator` requires this field; when absent it silently skips. `resp062_001` was failing because the validator was never invoked.

Fix: Added `expected_customer_name=ctx.get("guest_first_name")` to `_context_from_scenario()`.

**Result:** 0 failures (was 3 pre-existing).

---

### TEST-029 — Fixture Date Re-anchor (+28 days)

| Issue | PR | Description |
|---|---|---|
| TEST-029 | #524 | Re-anchor 110-record response-preparation fixture from 2026-06-03 to 2026-07-01 |

All 88 unique ISO date strings in `freeform_group_booking_response_preparation_test_100.json` shifted forward +28 days. No natural-language dates in the fixture (all freeform in guest bodies) — pure ISO string replacement. Day-of-week alignment preserved. Priority distribution unchanged: URGENT 2 / HIGH 21 / NORMAL 78 / LOW 9. Zero past `assumed_date` values remain.

`ANCHOR_DATE = date(2026, 7, 1)` updated in accuracy runner.

---

### DATE-003 — FreeformDateClarificationDetector

| Issue | PR | Description |
|---|---|---|
| DATE-003 | #526 | New service: freeform date expression detection for "next Friday or Saturday" / "mid-July" edge cases |

**New file:** `services/api/app/modules/enquiries/freeform_date_clarification_detector.py`

`DateResolutionService` previously had no handler for expressions like "next Friday or Saturday" or "mid-July". These produced `type=unknown`, no `candidate_dates`, and no `requires_clarification` flag → fell through to `STATUS_UNKNOWN` → engine returned `REQUEST_MISSING_INFORMATION` instead of the more precise `REQUEST_DATE_CONFIRMATION`.

**Pattern 1 — Multi-option weekday:**

Regex: `_MULTI_WEEKDAY_OR_PATTERN` — matches "next Friday or Saturday", "Thursday or Friday next week", "Could we book Saturday or Sunday?". Resolves both weekdays to ISO dates relative to `anchor_date`. Generates: "Could you confirm whether you mean Friday, 10 July or Saturday, 11 July?"

**Pattern 2 — Approximate month range:**

Regex: `_APPROXIMATE_MONTH_PATTERN` — matches "mid-July", "early August", "late September", "end of August". Year-wraps when named month is before anchor month. Generates: "Could you let me know the specific date you have in mind for mid-July 2026?"

**Integration:** Wired into `DateResolutionService` as step 3b (fallback). Fires only when `date_request_type_normalized == "unknown"` and `not candidate_dates` and `raw_text` is present. On match: `requires_clarification=True`, `clarification_question` set → propagates to `STATUS_AMBIGUOUS` → `REQUEST_DATE_CONFIRMATION`.

No LLM calls. Fully deterministic regex-based detection.

**18 new tests** in `test_freeform_date_clarification_detector.py`: `TestMultiOptionWeekday` (7), `TestApproximateMonthRange` (7), `TestNoMatchCases` (4).

---

### Sprint 24 Baseline (110 records, run 20260617T183121Z)

Anchor: 2026-07-01 | Model: claude-haiku-4-5-20251001 | Temp: 0.4 | Prompt V7

| Metric | Score |
|---|---|
| Compliance | 110/110 (100%) |
| Auto-send | 110/110 (100%) |
| Persona-fit | 110/110 (100%) |
| Safety | 0/110 |
| Goal distribution | CONF 95 / RDTC 15 |
| Overall | **10/10** |

### Test count: **2,948 backend + 126 frontend = 3,074 total**

---

## Summary Table

| Sprint | Theme | PRs | Test Count | LLM Score |
|---|---|---|---|---|
| 16 | Audience tone guards + persona-fit scoring | #498–#504 | 2,992 | — |
| 17 | Audience-conditional warmth wiring (runner + production) | #509–#510 | 2,992 | 9.8/10 |
| 18 | email_48 meal period fix (first perfect auto-send) | #512 | 2,992 | **10/10** |
| 19 | 10 luxury records added; fixture → 110 records | #513 | 2,992 | **10/10** |
| 20 | Rule 2b corporate context classification (RESP-080) | #514 | 3,004 | **10/10** |
| 21 | email_108 date ambiguity fix (5/7 → 7/8) | #516 | 3,004 | **10/10** |
| 22 | Rule 2c social context + client thank-you (RESP-081) | #518 | 3,016 | **10/10** |
| 23 | Accuracy runner staleness fix — L2/L3 failures | #520 | 3,016 | **10/10** |
| 24 | Safety fixture + date re-anchor + FreeformDateDetector | #522/#524/#526 | **3,074** | **10/10** |

---

## Key Files Modified (Sprint 16–24)

| File | Sprints | Change |
|---|---|---|
| `services/api/app/modules/enquiries/customer_type_resolver.py` | 20, 22 | Rule 2b (corporate context), Rule 2c (social context), client thank-you signal |
| `services/api/app/modules/ai/audience_tone_validator.py` | 16 | New — forbidden-phrase guard per audience type |
| `services/api/app/modules/ai/confirm_available_warmth_generator.py` | 16 | Audience-specific system prompts + inline `_audience_tone_guard()` |
| `services/api/app/modules/ai/first_response_copy_library.py` | 16 | `audience_opener()` — 5 audience-specific deterministic copy blocks |
| `services/api/app/modules/ai/auto_send_readiness_gate.py` | 16 | Rule 7 — tone validation failure blocks auto-send |
| `services/api/app/modules/ai/service.py` | 17 | `AudienceToneValidator` + Rule 7 wired in production path |
| `services/api/app/modules/enquiries/freeform_date_clarification_detector.py` | 24 | New — FreeformDateClarificationDetector (Pattern 1 + 2) |
| `services/api/app/modules/enquiries/date_resolution_service.py` | 24 | Step 3b fallback: FreeformDateClarificationDetector integration |
| `tests/data/freeform_group_booking_response_preparation_test_100.json` | 18–24 | email_48 fix; 10 luxury records; 4→8 corporate reclassifications; 88 dates +28d; email_108 5/7→7/8 |
| `tests/scripts/run_response_preparation_test_100.py` | 17, 19, 23, 24 | Audience warmth wiring; per-audience breakdown; UNRESOLVED_AMBIGUITY mapping; ANCHOR_DATE |
| `services/api/tests/fixtures/first_response_safety_cases_100.json` | 24 | 12 scenarios: `compliance_passed: true → false` (RESP-042 / RESP-060 staleness) |
| `services/api/tests/ai/test_first_response_safety_regression_100.py` | 24 | `_context_from_scenario()`: wire `expected_customer_name` |
| `services/api/tests/enquiries/test_customer_type_resolver.py` | 20, 22 | 24 new tests (Rule 2b + Rule 2c) |
| `services/api/tests/enquiries/test_freeform_date_clarification_detector.py` | 24 | New — 18 tests |
