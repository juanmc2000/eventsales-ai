# Sprint 23 — TEST-027: Fix Accuracy Runner Fixture Staleness

## Period

2026-06-17

## Sprint Goal

Fix `run_response_preparation_accuracy_100.py` which was failing with score 0.839 due to two fixture staleness issues and one missing status mapping, causing Layer 2 to report 14/110 and Layer 3 to report 100/110.

---

## Issue / PR

| Issue | PR | Description |
|---|---|---|
| TEST-027 (#519) | #520 | Fix accuracy runner fixture staleness — deprecated goal name + luxury priority mismatch |

---

## Problem

### Layer 2 — ResponseGoalEngine: 14/110 passed

95 CONF fixture records had `response_goal_engine.response_goal` set to `"READY_TO_CONFIRM_AVAILABILITY"`. This constant was deprecated in RESP-005 when three distinct availability-aware goals replaced the single pre-availability goal. The deprecated alias is kept only for backward compat with stored DB rows — **the engine never produces it for new records**.

The accuracy runner passes no `availability_decision` to `ResponseGoalEngine.decide()`. Without an availability decision, all eligible records fall through to the engine's final case and return `GOAL_ACKNOWLEDGE_AND_CHECK_AVAILABILITY`. The fixture expected the old name; the engine returned the current name.

### Layer 3 — ResponsePriorityEngine: 100/110 passed

Luxury records `email_101–110` (added in Sprint 19 / TEST-025) had `response_priority: "HIGH"`. Their event dates are 23–80 days from the fixture anchor date (2026-06-03), which falls in the NORMAL bucket (15–90 days). `ResponsePriorityEngine` is purely date-based — it has no luxury-audience logic. The records were seeded with `HIGH` under the assumption that luxury = high priority, but this was never implemented in the engine.

### Layer 2 secondary — email_108 UNRESOLVED_AMBIGUITY not mapped

After the Layer 2 bulk fix, `email_108` still failed because its `date_context.date_status` is `"UNRESOLVED_AMBIGUITY"` (the internal disambiguator state set by TEST-026). The accuracy runner's `_DATE_STATUS_MAP` only knew `"AMBIGUOUS"` / `"ambiguous"`. Without a mapping, the runner defaulted to `STATUS_UNKNOWN`, which does not trigger Rule 3 in the engine, causing it to return `REQUEST_MISSING_INFORMATION` instead of `REQUEST_DATE_CONFIRMATION`.

`date_resolution_status.py` line 197 documents that `UNRESOLVED_AMBIGUITY` maps to `STATUS_AMBIGUOUS` at the service boundary.

---

## Fixes

### Fix 1 — 95 CONF records: deprecated goal name

Updated `response_goal_engine.response_goal` from `"READY_TO_CONFIRM_AVAILABILITY"` → `"ACKNOWLEDGE_AND_CHECK_AVAILABILITY"` for all 95 CONF records in the fixture.

### Fix 2 — 10 luxury records: priority mismatch

Updated `response_priority` from `"HIGH"` → `"NORMAL"` for `email_101–110`. Priority is date-only; 23–80 days → NORMAL.

### Fix 3 — email_108 candidate_dates stale data

`email_108.date_context.candidate_dates` was `["2026-07-05"]` — a leftover from the old `"5/7"` date before TEST-026 changed it to `"7/8"`. Updated to `["2026-08-07", "2026-07-08"]` matching the British (7 August) and American (8 July) interpretations.

### Fix 4 — _DATE_STATUS_MAP: add UNRESOLVED_AMBIGUITY

Added `"UNRESOLVED_AMBIGUITY"` and `"unresolved_ambiguity"` → `STATUS_AMBIGUOUS` to `_DATE_STATUS_MAP` in the accuracy runner. Consistent with `date_resolution_status.py:197`.

### Fix 5 — Goal Distribution display list

Added `"ACKNOWLEDGE_AND_CHECK_AVAILABILITY"` and `"CONFIRM_AVAILABLE"` to the runner's display loop so CONF records appear in the printed goal distribution.

---

## Result

| Layer | Before | After |
|---|---|---|
| Layer 1 Fixture Contract | 110/110 | 110/110 |
| Layer 2 Response Goal | 14/110 | **110/110** |
| Layer 3 Priority | 100/110 | **110/110** |
| Layer 4 Missing Info | 110/110 | 110/110 |
| Layer 5 Persona Routing | 110/110 | 110/110 |
| Layer 6 Prompt Variables | 110/110 | 110/110 |
| **Overall Score** | **0.839 FAIL** | **1.000 PASS** |

Priority distribution after fix: URGENT 2 / HIGH 21 / NORMAL 78 / LOW 9

---

## Key Files Modified

| File | Change |
|---|---|
| `tests/data/freeform_group_booking_response_preparation_test_100.json` | 95 goal fields updated; 10 priority fields updated; email_108 candidate_dates corrected |
| `tests/scripts/run_response_preparation_accuracy_100.py` | `_DATE_STATUS_MAP` + UNRESOLVED_AMBIGUITY; goal display list updated |

---

## Test Counts

No new tests. `pytest` (excl. pre-existing `test_first_response_safety_regression_100.py`): **2,890 passed, 0 regressions**.
