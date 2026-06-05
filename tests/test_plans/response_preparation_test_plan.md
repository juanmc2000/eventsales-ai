# Response Preparation Test Plan — 100-Record Enquiry Dataset

## Purpose

Validate the Sprint 10 response-preparation layer using the enriched 100-record freeform enquiry dataset.

The test confirms that deterministic orchestration produces the expected:

- `response_goal`
- `response_priority`
- `readiness`
- `date_status`
- `availability_status`
- `missing_information`
- `persona_context`
- `draft_response` prompt variables

This test is designed to sit after extraction and deterministic date resolution, and before the second LLM draft call.

---

## Source Fixture

```text
freeform_group_booking_response_preparation_test_100.json
```

The fixture enriches each record under:

```json
record.target_extraction.response_preparation_target
```

---

## Sprint 10 Rule Coverage in This Fixture

| Response Goal | Records | Notes |
|---|---:|---|
| `READY_TO_CONFIRM_AVAILABILITY` | 86 | Fully usable enquiries with date, occasion, guest count and meal period. |
| `REQUEST_DATE_CONFIRMATION` | 13 | Ambiguous numeric dates resolved provisionally with confirmation required. |
| `REQUEST_MISSING_INFORMATION` | 1 | One case has an unknown meal period and requires clarification. |
| `UNABLE_TO_PROCESS` | 0 | Not naturally represented because the dataset intentionally contains booking enquiries. |
| `ESCALATE_TO_HUMAN` | 0 | Not naturally represented because records contain enough context for automation. |
| `REQUEST_WEBFORM` | 0 | Not naturally represented because no record has 3+ critical missing fields. |

Rules 1, 2 and 4 should remain covered by the existing Sprint 10 deterministic matrix tests. This fixture is primarily an integration-style regression dataset for realistic customer enquiries.

---

## Test Layers

### Layer 1 — Fixture Contract Validation

Validate every record contains:

- `sender`
- `target_extraction`
- `target_extraction.date_request`
- `target_extraction.response_preparation_target`
- `response_goal_engine`
- `draft_prompt_variables`

Expected result:

```text
100 / 100 records pass fixture contract validation
```

---

### Layer 2 — ResponseGoalEngine Accuracy

For each record, construct the service input from:

- date status
- readiness
- missing information
- critical missing fields
- webform flag

Compare actual output to:

```json
response_preparation_target.response_goal_engine.response_goal
```

Expected result:

```text
response_goal_accuracy >= 0.98
```

Hard fail if any `REQUEST_DATE_CONFIRMATION` case is misclassified as `READY_TO_CONFIRM_AVAILABILITY`.

---

### Layer 3 — ResponsePriorityEngine Accuracy

Compare the actual priority to:

```json
response_preparation_target.response_priority
```

Expected thresholds:

- 0–1 days → `URGENT`
- 2–14 days → `HIGH`
- 15–90 days → `NORMAL`
- >90 days → `LOW`
- no date → `NORMAL`

Expected result:

```text
response_priority_accuracy >= 0.98
```

---

### Layer 4 — MissingInformationDecisionEngine Accuracy

Compare:

```json
response_preparation_target.missing_information.critical_missing_fields
response_preparation_target.missing_information.should_send_webform
response_preparation_target.missing_information.clarification_questions
```

Expected result:

```text
missing_information_accuracy >= 0.98
```

---

### Layer 5 — Persona Routing Context Accuracy

Compare actual persona routing against:

```json
response_preparation_target.customer_type_context.audience_type
response_preparation_target.persona_context.persona_name
response_preparation_target.persona_context.persona_tone
```

Expected mappings:

- social → Eleanor
- corporate → James
- agency → Sophia
- unknown → Eleanor / professional fallback

Expected result:

```text
persona_routing_accuracy >= 0.95
```

Hard fail if an `agency` record with `commission_requested=true` is routed to `social`.

---

### Layer 6 — Draft Prompt Variable Readiness

Validate every record that can generate a draft has all required variables:

```text
persona_system_prompt
persona_name
restaurant_name
persona_tone
persona_style
response_goal
guest_first_name
guest_last_name
```

Validate optional variables are present as strings, even when empty:

```text
audience_type_line
event_type_line
event_date_line
party_size_line
availability_line
spend_line
guest_message_line
room_lines
clarification_questions_line
```

Expected result:

```text
prompt_variable_contract_accuracy = 1.00
```

Hard fail if `response_goal` is missing or defaults incorrectly.

---

## Requested Test Runner Output

The runner should output both a console summary and a JSON report.

### Console Summary

```text
Response Preparation Accuracy Run
Dataset: freeform_group_booking_response_preparation_test_100
Records: 100

Layer 1 Fixture Contract:            100/100 passed
Layer 2 Response Goal Accuracy:       100/100 passed
Layer 3 Priority Accuracy:            100/100 passed
Layer 4 Missing Info Accuracy:        100/100 passed
Layer 5 Persona Routing Accuracy:     100/100 passed
Layer 6 Prompt Variable Contract:     100/100 passed

Goal Distribution:
READY_TO_CONFIRM_AVAILABILITY: 86
REQUEST_DATE_CONFIRMATION: 13
REQUEST_MISSING_INFORMATION: 1

Priority Distribution:
URGENT: 2
HIGH: 21
NORMAL: 68
LOW: 9

Overall Score: 1.000
Result: PASS
```

### JSON Report Shape

```json
{
  "dataset_name": "freeform_group_booking_response_preparation_test_100",
  "run_id": "<uuid>",
  "anchor_date": "2026-06-03",
  "total_records": 100,
  "result": "PASS",
  "overall_score": 1.0,
  "layers": {
    "fixture_contract": {
      "passed": 100,
      "failed": 0,
      "accuracy": 1.0
    },
    "response_goal_engine": {
      "passed": 100,
      "failed": 0,
      "accuracy": 1.0,
      "goal_distribution": {
        "READY_TO_CONFIRM_AVAILABILITY": 86,
        "REQUEST_DATE_CONFIRMATION": 13,
        "REQUEST_MISSING_INFORMATION": 1
      }
    },
    "response_priority_engine": {
      "passed": 100,
      "failed": 0,
      "accuracy": 1.0
    },
    "missing_information_engine": {
      "passed": 100,
      "failed": 0,
      "accuracy": 1.0
    },
    "persona_routing_context": {
      "passed": 100,
      "failed": 0,
      "accuracy": 1.0
    },
    "draft_prompt_variables": {
      "passed": 100,
      "failed": 0,
      "accuracy": 1.0
    }
  },
  "failures": []
}
```

---

## Pass / Fail Criteria

PASS if:

- all required fixture keys are present
- response goal accuracy is at least 98%
- priority accuracy is at least 98%
- missing information accuracy is at least 98%
- persona routing accuracy is at least 95%
- prompt variable contract accuracy is 100%
- no agency commission case is routed as social
- no date-confirmation case is treated as availability-ready

FAIL if:

- any required prompt variable is missing
- any `REQUEST_DATE_CONFIRMATION` record is classified as `READY_TO_CONFIRM_AVAILABILITY`
- any `commission_requested=true` agency case is routed to social
- the runner cannot parse the fixture

---

## Notes

This dataset is intentionally realistic, so it does not force all six ResponseGoalEngine rules into the 100 records. Keep the Sprint 10 15-scenario unit matrix for exhaustive rule precedence coverage, and use this 100-record fixture for realistic pipeline regression testing.
