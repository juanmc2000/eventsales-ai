# Sprint 16 — Audience-Aware Persona Restoration

## Sprint Goal

Restore and enforce audience-specific tone behaviour in CONFIRM_AVAILABLE response generation.
Sprint 15 achieved 100% factual compliance and 99% auto-send utilisation, but did not surface
corporate tone degradation (e.g. social warmth openers in corporate or agency emails). Sprint 16
adds the evaluation layer, deterministic tone guards, and audience-specific copy blocks needed to
make tone failures visible, preventable, and auto-send-blocking.

---

## Background: The Persona Regression

EventSales AI's core differentiator is configurable persona-based communication. Prior to Sprint 16,
all CONFIRM_AVAILABLE openers used the same warmth LLM prompt, which reliably produced celebratory
language ("How wonderful — a birthday celebration!") regardless of the audience type.

This was correct for **social** audiences (birthday parties, anniversaries, celebrations) but was
off-brand for:

- **Corporate** audiences (team dinners, board meetings, client events) — should be efficient and
  commercially direct, not celebratory
- **Agency** audiences (event planners booking on behalf of clients) — should be operational and
  logistics-focused
- **Luxury / HNW** audiences — should be refined and understated, not enthusiastically casual

Sprint 15 compliance checks did not include tone checking, so the regression was not caught by the
existing test suite.

---

## Issue Summary

| Issue | PR | Description | Status |
|---|---|---|---|
| TEST-022 | #499 | 30-scenario audience tone regression fixture + runner | ✓ |
| RESP-074 | #500 | Audience-specific deterministic opener copy blocks | ✓ |
| RESP-075 | #498 | AudienceToneValidator — deterministic forbidden-phrase guard | ✓ |
| RESP-076 | #501 | Audience-specific system prompts + inline tone guard in warmth generator | ✓ |
| TEST-023 | #502 | Extend 100-record runner with persona-fit scoring layer | ✓ |
| RESP-077 | #503 | Auto-send blocker for audience tone failures (Rule 7) | ✓ |
| DOC-020 | #504 | Document Sprint 16 persona restoration rules (this document) | ✓ |

---

## Audience-Specific Opener Strategy

Each audience type has a distinct tone family. The correct opener depends on who is sending the
enquiry, not on the occasion itself.

### Audience Types

| Audience Type | Tone Family | Opener Style |
|---|---|---|
| `social` | warm_celebratory | Enthusiastic acknowledgement of the occasion |
| `corporate` | professional | Efficient, courteous, commercially direct |
| `agency` | operational | Clear, logistics-focused, planner-friendly |
| `luxury` | refined | Calm, gracious, understated high-touch |
| `unknown` | neutral | Courteous, professional, no assumptions |

### Tone Selection in the Pipeline

1. `CustomerTypeResolver` classifies the sender as `social`, `corporate`, `agency`, or `unknown`.
2. `PersonaRoutingContextBuilder` sets `audience_type` in the response context.
3. `generate_warmth_sentence()` selects an audience-specific system prompt, then runs an inline
   tone guard before returning the sentence.
4. `AudienceToneValidator.validate()` is called by the caller before using the warmth sentence.
5. If tone validation fails, the warmth sentence is dropped and the deterministic fallback opener
   from `FirstResponseCopyLibrary.audience_opener()` is used instead.
6. `AutoSendReadinessGate.evaluate()` (Rule 7) blocks auto-send if tone validation failed.

---

## Corporate Tone Rules

### Forbidden Phrases (RESP-075, RESP-076)

The following phrases are **never acceptable** in corporate or agency CONFIRM_AVAILABLE drafts:

| Phrase | Category |
|---|---|
| "How wonderful" | Social warmth |
| "How lovely" | Social warmth |
| "How exciting" | Social warmth |
| "How delightful" | Social warmth |
| "What a lovely occasion" | Social warmth |
| "What a wonderful" | Social warmth |
| "Such a special occasion" | Social warmth |
| "Such a meaningful occasion" | Social warmth |
| "Celebration with us" | Social warmth |
| "Will be special" | Social warmth |
| "Delighted to celebrate" | Social warmth |
| "Thrilled" | Excessive enthusiasm |

### Acceptable Corporate Openers (RESP-074)

The deterministic fallback opener for corporate audiences is:

> "Thank you for your enquiry. I'm pleased to confirm that we have availability for {meal_period} on {event_date}."

Other acceptable openers produced by the audience-specific LLM prompt:

- "We would be delighted to accommodate your team —"
- "We look forward to supporting your event —"
- "We are pleased to assist with your upcoming dinner —"

### Example: Correct Corporate Draft

```
Dear James,

Thank you for your enquiry. I'm pleased to confirm that we have availability for dinner on Friday, 19 June 2026.

Please note that our minimum spend for this space is £2,000.

Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.

Warm regards,
Eleanor
```

### Example: Incorrect Corporate Draft (blocked by RESP-075 / RESP-077)

```
Dear James,

How wonderful — a corporate dinner is always such a special occasion!

I'm delighted to confirm that we have availability for dinner on Friday, 19 June 2026.
```

This draft would:
- Fail `AudienceToneValidator` ("How wonderful", "such a special occasion")
- Be blocked from auto-send by Rule 7
- Require human review before sending

---

## Social Tone Rules

Social audiences (birthdays, anniversaries, celebrations) should receive warm, enthusiastic,
occasion-referencing warmth sentences. There are no forbidden phrases for social audiences.

### Acceptable Social Openers

- "How wonderful — a birthday celebration is always such a special occasion!"
- "How lovely — an anniversary dinner is something truly worth celebrating!"
- "What a lovely occasion — we look forward to helping you celebrate!"
- "That sounds wonderful — a surprise dinner for your partner is a beautiful idea."

**Rule:** The warmth sentence must reference the occasion or guest context. It must not describe
the room, venue suitability, or operational details. It must not start with "Thank you".

---

## Agency Tone Rules

Agency senders (event planners booking on behalf of clients) require a professional, operational
tone. The same forbidden phrases apply as for corporate.

### Acceptable Agency Openers

- "We can confirm availability for your client event —"
- "We are pleased to assist with the upcoming booking —"
- "Thank you for your enquiry. I can confirm that we have availability for {meal_period} on {event_date}."

---

## Luxury / HNW Tone Rules

Luxury and high-net-worth guests require refined, understated language. The forbidden phrases are
different from corporate — casual and enthusiastically colloquial words are blocked.

### Forbidden Phrases (Luxury)

| Phrase | Reason |
|---|---|
| "Amazing" | Casual |
| "Fantastic" | Casual |
| "Brilliant" | Casual |
| "Super" | Casual |
| "Totally" | Casual |
| "Can't wait" | Casual |
| "How exciting" | Over-enthusiastic |

### Acceptable Luxury Openers

- "It would be a pleasure to welcome your guests —"
- "We look forward to hosting your private dinner —"
- "We would be honoured to accommodate your guests on this occasion."

Note: "How wonderful" passes the luxury guard (it is only forbidden for corporate/agency).

---

## Persona-Fit Scoring (TEST-023)

Sprint 16 adds persona-fit scoring as an additional evaluation layer to the 100-record runner.
This layer is reported separately and does not affect factual compliance or auto-send scores.

### New Output Fields (per result record)

```json
"persona_fit": {
  "audience_type": "corporate",
  "persona_fit_passed": false,
  "persona_fit_score": 0.75,
  "persona_fit_violations": ["persona_tone_violation: corporate — 'how wonderful' detected"],
  "opener_tone_category": "warm_celebratory",
  "forbidden_phrase_hits": ["how wonderful"]
}
```

### Opener Tone Categories

| Category | Description | Example |
|---|---|---|
| `warm_celebratory` | Enthusiastic, occasion-referencing | "How wonderful — a birthday celebration!" |
| `refined` | Gracious, understated | "It would be a pleasure to welcome your guests." |
| `professional` | Efficient, courteous | "We are pleased to assist with your upcoming dinner." |
| `neutral` | No clear signal | Any opener not matching the above |

### Persona-Fit Pass Rate Target

- Social: 100% (no forbidden phrases)
- Corporate: ≥ 95% (warmth LLM guided by audience-specific prompt + inline guard)
- Agency: ≥ 95%
- Luxury: ≥ 95%
- Unknown: 100% (no forbidden phrases)

---

## Auto-Send Treatment of Tone Failures (RESP-077)

Auto-send is blocked (Rule 7) whenever `tone_validation_result.passed` is `False`. The blocker
message is included in `auto_send_blockers` and `review_required_reason`.

**Example blocker:**
```
Audience tone validation failed — draft requires human review before auto-send:
audience_tone_violation: corporate — 'how wonderful' detected
```

Social and unknown audience types have no forbidden phrases and will never trigger Rule 7.

When `tone_validation_result` is `None` (not provided), Rule 7 is skipped — this preserves
backwards-compatibility with callers that do not run tone validation.

---

## Regression Testing Expectations

### Minimum coverage required for any CONFIRM_AVAILABLE change

1. `test_confirm_available_warmth_generator.py` — audience prompt registry, tone guard patterns, early exits
2. `test_audience_tone_validator.py` — per-audience pass/fail for all audience types
3. `test_auto_send_readiness_gate.py` — Rule 7 corporate/agency/luxury/social/unknown cases
4. `tests/scripts/run_audience_tone_regression.py` — 30-scenario offline LLM regression fixture

### Sprint 15 baseline (must not regress)

| Metric | Sprint 15E | Sprint 16 target |
|---|---|---|
| Compliance pass rate | 100/100 (100%) | ≥ 100/100 |
| Auto-send allowed | 99/100 (99%) | ≥ 99/100 |
| Safety issues | 0/100 (0%) | 0/100 |
| Persona-fit pass rate | Not measured | ≥ 95/100 |

---

## Key Principles

1. **Tone selection is deterministic** — the LLM is given an audience-specific system prompt, and
   an inline guard drops the output if forbidden phrases appear. The caller then validates with
   `AudienceToneValidator`. At no point does the pipeline rely on the LLM to "know" which phrases
   are forbidden.

2. **Warmth is optional** — if the warmth sentence fails tone validation, the deterministic
   fallback opener from `FirstResponseCopyLibrary.audience_opener()` is used. The email is always
   sent on time; warmth personalisation is best-effort.

3. **Tone failures do not replace compliance failures** — they are reported separately. An email
   can pass factual compliance but still fail tone validation. Both failures block auto-send, but
   through separate rules (Rule 1 and Rule 7).

4. **Social warmth is the default for unknown** — when audience type is unknown, the neutral
   professional tone is used (neither explicitly celebratory nor explicitly operational).
