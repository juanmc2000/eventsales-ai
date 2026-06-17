# Response Preparation Accuracy — Sprint 24 Evaluation Report

**Date:** 2026-06-17
**Run timestamp:** 20260617T183121Z
**Model:** claude-haiku-4-5-20251001
**Temperature:** 0.4
**Prompt version:** V7
**Fixture anchor date:** 2026-07-01
**Fixture:** `tests/data/freeform_group_booking_response_preparation_test_100.json` (110 records)

---

## Summary

| Metric | Score |
|---|---|
| Compliance pass rate | **110/110 (100%)** |
| Auto-send allowed | **110/110 (100%)** |
| Persona-fit pass rate | **110/110 (100%)** |
| Safety issues found | **0/110** |
| **Overall** | **10/10** |

---

## Goal Distribution

| Response Goal | Count |
|---|---|
| CONFIRM_AVAILABLE (LLM) | 95 |
| REQUEST_DATE_CONFIRMATION (deterministic) | 15 |

---

## Persona-Fit by Audience

| Audience | Pass | Total | Rate |
|---|---|---|---|
| social | 51 | 51 | 100% |
| corporate | 38 | 38 | 100% |
| agency | 9 | 9 | 100% |
| luxury | 10 | 10 | 100% |
| unknown | 2 | 2 | 100% |

---

## Opener Tone Distribution

| Tone | Count |
|---|---|
| neutral | 54 |
| warm_celebratory | 47 |
| refined | 8 |
| professional | 1 |

---

## Notes

- Baseline established after TEST-029 re-anchor (+28 days, 2026-06-03 → 2026-07-01). No past assumed_date values remain in fixture.
- 15 RDTC records are fully deterministic (no LLM call) — all passed by construction.
- 95 CONF records all passed compliance, auto-send, and persona-fit checks.
- Tone distribution is consistent with Sprint 22 baseline (neutral/warm dominance; refined for luxury audience).
- Results file: `tests/data/response_prep_100_results_sprint15b_20260617T183121Z.json`
