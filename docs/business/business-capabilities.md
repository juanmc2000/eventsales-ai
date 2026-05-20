# Business Capabilities

## Purpose

This document maps EventSales AI business capabilities to the POC implementation scope.

## POC Scope

The POC validates the core product experience. Not all business capabilities are fully implemented during the POC. This document clarifies which capabilities are active during POC and which are deferred to MVP.

---

## Capability Map

### 1. Enquiry Intake

| Capability | POC Status | Notes |
|---|---|---|
| Webform enquiry submission | In scope | Test webform only, no public deployment |
| Inbound email reading | In scope | Gmail IMAP, test inbox only |
| CRM intake (Salesforce, TripleSeat) | Deferred (MVP) | No CRM integrations during POC |
| Enquiry classification | In scope | Event type, source, persona selection |
| Missing information detection | Partial | Logged in enquiry record |

---

### 2. AI Communication (Persona Engine)

| Capability | POC Status | Notes |
|---|---|---|
| Persona configuration (tone, warmth, etc.) | In scope | 3 default personas + edit |
| Persona-to-restaurant assignment | In scope | |
| AI response generation | In scope | Persona-based draft generation |
| Natural language persona editing | Deferred (MVP) | |
| Multi-brand persona inheritance | Deferred (MVP) | |

---

### 3. Pricing

| Capability | POC Status | Notes |
|---|---|---|
| Manual pricing rule creation | In scope | |
| Deterministic pricing calculation | In scope | Rules-based, no ML |
| Pricing explainability | In scope | explanation_notes per rule |
| Capacity-based dynamic pricing | Deferred (MVP) | |
| External demand signal integration | Deferred (MVP) | No live sports/weather APIs |
| ML pricing optimisation | Deferred (post-MVP) | |

---

### 4. Proposal Generation

| Capability | POC Status | Notes |
|---|---|---|
| Draft response generation | In scope | |
| Test email sending (Gmail SMTP) | In scope | |
| Full branded proposal PDF | Deferred (MVP) | |
| Deposit link generation | Deferred (MVP) | No Stripe/Adyen during POC |
| Automatic follow-up workflows | Deferred (MVP) | |

---

### 5. Calendar and Demand Intelligence

| Capability | POC Status | Notes |
|---|---|---|
| Demand event calendar (seeded fake data) | In scope | |
| Monthly calendar view | In scope | |
| Pricing impact per date | In scope | |
| Live sports/theatre/holiday API integration | Deferred (MVP) | |
| Competitor pricing signals | Deferred (post-MVP) | |

---

### 6. Dashboard and Insights

| Capability | POC Status | Notes |
|---|---|---|
| Enquiry KPIs (volume, status breakdown) | In scope | |
| Venue performance summary | In scope | |
| Pricing rule usage stats | In scope | |
| Revenue trend charts | Partial (seeded data) | |
| Advanced BI reporting | Deferred (MVP) | |
| Forecasting | Deferred (post-MVP) | |

---

### 7. User and Access Management

| Capability | POC Status | Notes |
|---|---|---|
| Basic JWT authentication | Optional (POC) | Not required for local testing |
| Role-based access control | Partial | Roles defined, not enforced for POC |
| Multi-tenant isolation | Partial | tenant_id present, not enforced via RLS |
| Enterprise SSO (Google/Microsoft) | Deferred (MVP) | |
| MFA | Deferred (MVP) | |

---

### 8. Integrations

| Capability | POC Status | Notes |
|---|---|---|
| Gmail SMTP (test sending) | In scope | |
| Gmail IMAP (test inbox reading) | In scope | |
| Salesforce | Deferred (MVP) | |
| TripleSeat | Deferred (MVP) | |
| Cvent | Deferred (MVP) | |
| Stripe / Adyen | Deferred (MVP) | |

---

## Database Entity-to-Capability Mapping

| Entity | Capabilities Supported |
|---|---|
| `restaurants` | All venue-scoped capabilities |
| `personas` | AI communication |
| `restaurant_personas` | Persona assignment |
| `pricing_rules` | Pricing calculation |
| `enquiries` | Enquiry intake, classification, status tracking |
| `enquiry_messages` | Timeline, communication log |
| `email_events` | Email sending/reading log |
| `calendar_events` | Calendar display |
| `demand_events` | Demand intelligence (seeded) |
| `insight_snapshots` | Dashboard and insights |

---

## POC Success Criteria (Data Perspective)

The POC is successful from a data perspective when:

- 4 test restaurants are seeded with correct profiles
- 3 personas are seeded and assignable to restaurants
- Pricing rules exist for each restaurant covering day, meal period, and event type variations
- 1 year of fake demand events is seeded for calendar display
- Fake enquiries exist across all statuses for dashboard testing
- A real test enquiry can be submitted via webform and stored in `enquiries`
- A real inbound email can be read and stored in `enquiries` (source = email)
- A test email can be sent and logged in `email_events`
