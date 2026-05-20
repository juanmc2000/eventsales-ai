# EventSales AI — POC Specification

## 1. Purpose

This document defines the scope, features, data, and technical boundaries for the EventSales AI proof of concept.

The POC is intended to validate the core product experience before building the full MVP.

The POC should demonstrate:

- configurable restaurant event sales workflows
- basic enquiry intake
- persona-based AI communication
- manual pricing rules
- a commercial dashboard
- calendar-based demand visibility
- basic insights and analytics
- test email sending through Gmail SMTP
- inbound email enquiry reading
- webform-based test enquiry submission

The POC is not intended to validate full third-party integrations, ML pricing optimisation, production authentication, enterprise deployment, or real customer data processing.

---

# 2. POC Pages

The POC must include the following pages:

## 2.1 Dashboard

Purpose:

Provide a high-level view of enquiry activity, proposal activity, pricing recommendations, and commercial performance across the four test restaurants.

Must include:

- total enquiries
- enquiries by restaurant
- enquiries by status
- enquiries by persona
- upcoming event bookings
- pending follow-ups
- test email activity
- recent inbound enquiries
- quick links to pricing rules, personas, calendar, and insights

Recommended dashboard cards:

- New enquiries this week
- Open enquiries
- Proposals generated
- Emails sent
- Average recommended minimum spend
- Upcoming high-demand dates
- Restaurants with demand spikes

POC constraints:

- data may be generated from seeded fake data
- no real CRM data
- no live third-party analytics
- no production-grade reporting layer required

---

## 2.2 Pricing Rules

Purpose:

Allow users to define simple manual pricing rules for each restaurant.

The POC pricing rules page should support:

- view pricing rules
- create pricing rule
- edit pricing rule
- delete pricing rule
- assign pricing rule to restaurant
- assign pricing rule to day of week
- assign pricing rule to meal period
- define base minimum spend
- define simple uplift or discount
- define notes explaining the rule

Supported rule fields:

- restaurant
- room or venue area
- day of week
- meal period: breakfast, lunch, dinner, late night
- event type
- guest count minimum
- guest count maximum
- base minimum spend
- adjustment type: fixed amount or percentage
- adjustment value
- rule priority
- active/inactive
- explanation notes

Example rules:

- Friday dinner at luxury restaurant: +20%
- Monday lunch at casual restaurant: -10%
- Graduation week at university-area restaurant: +15%
- Bank holiday tourist venue: +10%

POC constraints:

- no ML pricing
- no external demand-source integration
- no automated optimisation
- no competitor pricing intelligence
- no production-grade revenue model
- pricing recommendations should be deterministic and explainable

---

## 2.3 Personas

Purpose:

Allow users to configure the communication style used when responding to enquiries.

The POC must include three default personas:

## Default Persona 1 — Corporate

Use case:

Corporate events, work dinners, client entertainment, business meetings.

Style:

- concise
- professional
- commercially direct
- efficient
- clear call to action

Default behaviour:

- mention menus and room suitability
- emphasise availability and next steps
- encourage quick confirmation
- avoid excessive emotional language

---

## Default Persona 2 — Social / Casual

Use case:

Birthdays, family meals, casual celebrations, informal group bookings.

Style:

- warm
- friendly
- helpful
- lightly enthusiastic
- approachable

Default behaviour:

- make the venue feel welcoming
- explain options clearly
- avoid being too sales-heavy
- encourage the customer to share missing details

---

## Default Persona 3 — Luxury / Ultra Luxury

Use case:

Premium private dining, luxury celebrations, VIP guests, high-value enquiries.

Style:

- refined
- polished
- calm
- discreet
- high-touch

Default behaviour:

- emphasise service quality
- avoid pushy language
- use elegant wording
- present the venue as premium and carefully managed

---

## Persona Page Requirements

The Personas page must allow users to:

- view all personas
- edit persona name
- edit persona description
- edit tone attributes
- assign persona to restaurant
- see which restaurants use each persona
- preview a sample customer email generated with that persona

Persona configuration fields:

- name
- description
- tone
- warmth
- urgency
- communication density
- formality
- sales assertiveness
- luxury level
- default sign-off
- active/inactive

Restaurant assignment:

Each of the four test restaurants must have one assigned default persona.

POC constraints:

- no complex persona versioning
- no approval workflows
- no multi-brand inheritance
- no advanced prompt management UI
- no production prompt governance required

---

## 2.4 Calendar

Purpose:

Show pricing, demand signals, holidays, and fake local events across the test restaurants.

The Calendar page should support:

- restaurant selector
- month view
- week view if feasible
- date-level demand indicators
- event markers
- holiday markers
- university event markers
- sports event markers
- theatre event markers
- recommended minimum spend display
- enquiry count per date
- booking status indicators

Calendar event categories:

- bank holiday
- school holiday
- sports event
- theatre event
- university move-in
- university end of term
- university graduation
- university move-out
- local festival
- seasonal tourism event

Calendar display requirements:

Each date should be able to show:

- demand level: low, normal, high, very high
- one or more local demand events
- recommended pricing impact
- number of enquiries
- booking status summary

Example calendar cell:

```text
15 June
High Demand
Graduation Week
3 enquiries
Recommended uplift: +15%
````

POC constraints:

* event data is fake and seeded
* no live sports integration
* no live theatre integration
* no live university calendar integration
* no school holiday API integration
* no external data-source integration

---

## 2.5 Insights Analytics

Purpose:

Provide simple commercial insight into enquiry patterns, pricing rules, and demand signals.

The Insights page should include:

* enquiries by restaurant
* enquiries by event type
* enquiries by persona
* enquiries by source: webform or email
* estimated demand by date
* pricing rule usage
* average recommended minimum spend
* top demand drivers
* upcoming high-demand dates
* enquiry status breakdown

Recommended charts:

* enquiries over time
* enquiries by restaurant
* enquiries by event type
* demand events by category
* recommended minimum spend by restaurant
* persona usage by restaurant

POC constraints:

* simple charts only
* fake historical data acceptable
* no advanced BI tool required
* no forecasting model
* no ML insights
* no production reporting warehouse

---

# 3. Enquiry Intake

The POC must support two enquiry intake methods:

1. test webform
2. inbound email inbox reading

---

## 3.1 Test Webform

Purpose:

Allow users to submit test event enquiries without integrating with a real restaurant website.

The webform must include:

* restaurant dropdown
* customer name
* customer email
* customer phone
* company name
* event date
* event time
* party size
* event purpose
* event type
* budget indication
* preferred room or area
* dietary requirements
* special requests
* message
* consent checkbox for test communication

Restaurant dropdown must include the four seeded test restaurants.

Event type options:

* corporate event
* private dining
* birthday
* wedding-related
* family celebration
* agency enquiry
* VIP event
* casual group booking

On submission, the system should:

* create an enquiry record
* classify the enquiry
* apply the assigned restaurant persona
* calculate a basic pricing recommendation using manual rules
* generate a draft response
* optionally send a test email through Gmail SMTP
* show the enquiry in the dashboard

POC constraints:

* no public production webform
* no spam protection required beyond basic validation
* no payment or deposit link required
* no real customer data should be used

---

## 3.2 Inbound Email Inbox Reading

Purpose:

Allow the POC to read inbound test enquiries from an email inbox.

The system should connect to a test Gmail mailbox and read inbound messages.

Required behaviour:

* connect to mailbox
* fetch unread or recent inbound emails
* parse sender email
* parse subject
* parse body
* create enquiry record
* classify source as email
* optionally mark email as processed
* show email enquiry in dashboard

POC email parsing may be simple.

Minimum extraction fields:

* sender email
* sender name if available
* subject
* body text
* received timestamp
* inferred restaurant if mentioned
* inferred event date if obvious
* inferred party size if obvious
* inferred event type if obvious

POC constraints:

* no production Gmail integration
* no Microsoft Graph integration
* no CRM email sync
* no advanced natural language extraction required
* no attachment processing required
* no mailbox multi-tenancy required

---

# 4. Test Email Sending

The POC will send test emails using Gmail SMTP.

Purpose:

Validate that generated persona-based responses can be sent by email.

Required behaviour:

* configure Gmail SMTP credentials through environment variables
* send test email from generated proposal/response screen
* log sent email event
* show sent email in enquiry timeline
* handle send failure gracefully

Environment variables:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_FROM_NAME=EventSales AI
```

POC constraints:

* use test Gmail only
* no production email sending
* no bulk email
* no unsubscribe management
* no marketing email functionality
* no email deliverability optimisation
* no SendGrid/Mailgun/Postmark integration

---

# 5. Test Restaurants

The POC must include four seeded restaurants.

## Restaurant 1 — Casual Restaurant A

Profile:

* casual
* high-volume
* accessible price point
* suitable for birthdays, team dinners, informal groups

Suggested default persona:

* Social / Casual

Example name:

```text
The Garden Table
```

---

## Restaurant 2 — Casual Restaurant B

Profile:

* casual-premium
* tourist-friendly
* suitable for group dining, celebrations, informal corporate bookings

Suggested default persona:

* Social / Casual or Corporate

Example name:

```text
Harbour & Hearth
```

---

## Restaurant 3 — Luxury Restaurant

Profile:

* premium restaurant
* private dining capability
* corporate and social events
* higher minimum spend

Suggested default persona:

* Corporate or Luxury / Ultra Luxury

Example name:

```text
Lumière Dining Room
```

---

## Restaurant 4 — Ultra Luxury Restaurant

Profile:

* ultra luxury
* VIP events
* private rooms
* high-touch communication
* premium minimum spend

Suggested default persona:

* Luxury / Ultra Luxury

Example name:

```text
Maison Aurelia
```

---

# 6. Fake Data Requirements

The POC must include one year of seeded fake data.

The fake data should support:

* dashboard metrics
* calendar demand markers
* pricing rule examples
* insights analytics
* enquiry testing
* restaurant-specific demand patterns

---

## 6.1 Fake Demand Events

The system should include fake demand events for each restaurant.

Demand event types:

* bank holidays
* public holidays
* school holidays
* sports events
* theatre events
* university move-in
* university end of term
* university graduation
* university move-out
* conferences
* local festivals
* tourism peaks

Each event should include:

* restaurant
* event name
* event category
* start date
* end date
* demand level
* expected impact
* pricing impact suggestion
* notes

Example:

```json
{
  "restaurant": "Maison Aurelia",
  "event_name": "University Graduation Week",
  "event_category": "university_graduation",
  "start_date": "2026-07-08",
  "end_date": "2026-07-14",
  "demand_level": "high",
  "pricing_impact_suggestion": 15,
  "notes": "Expected increase in family celebration and private dining demand."
}
```

---

## 6.2 Fake Enquiry Data

Seed fake enquiries across one year.

Each enquiry should include:

* restaurant
* customer name
* customer email
* enquiry source
* event date
* event time
* party size
* event type
* customer message
* status
* assigned persona
* recommended minimum spend
* created timestamp

Statuses:

* new
* missing information
* proposal drafted
* proposal sent
* follow-up due
* converted
* lost
* closed

---

## 6.3 Fake Pricing Data

Seed basic pricing rules for each restaurant.

Pricing should vary by:

* restaurant type
* day of week
* meal period
* party size
* event type
* fake demand event

POC pricing must be deterministic.

No ML.

---

# 7. Integrations

## Included in POC

The POC includes:

* Gmail SMTP for sending test emails
* Gmail inbox reading for inbound test enquiries
* webform-based test enquiry submission

---

## Not Included in POC

The POC excludes:

* Salesforce
* TripleSeat
* Cvent
* OpenTable
* SevenRooms
* DesignMyNight
* Stripe
* Adyen
* live sports APIs
* live theatre APIs
* university APIs
* school holiday APIs
* weather APIs
* competitor pricing APIs

---

# 8. Technical Scope

Recommended POC stack:

* Python
* FastAPI
* PostgreSQL
* Redis
* Celery
* SQLAlchemy
* Alembic
* React / Next.js frontend
* Gmail SMTP
* IMAP or Gmail-compatible inbox reading
* Docker Compose for local services

---

## 8.1 Backend Modules

Suggested backend modules:

```text
backend/app/modules/auth
backend/app/modules/restaurants
backend/app/modules/personas
backend/app/modules/pricing
backend/app/modules/enquiries
backend/app/modules/email
backend/app/modules/calendar
backend/app/modules/insights
backend/app/modules/dashboard
```

---

## 8.2 Background Jobs

Use Celery and Redis for background jobs.

POC background jobs:

* send test email
* read inbound email inbox
* process inbound email into enquiry
* generate seeded fake data
* refresh dashboard metrics if required

Redis is the broker.

PostgreSQL remains the source of truth.

---

## 8.3 Database Entities

Minimum POC tables:

```text
restaurants
personas
restaurant_personas
pricing_rules
enquiries
enquiry_messages
email_events
calendar_events
demand_events
insight_snapshots
```

Optional POC tables:

```text
rooms
users
audit_logs
background_jobs
```

---

# 9. Out of Scope

The following are explicitly out of scope for the POC:

## Pricing

* no ML pricing engine
* no predictive pricing model
* no optimisation model
* no competitor intelligence
* no real-time demand ingestion
* no automated revenue management

## Integrations

* no Salesforce
* no TripleSeat
* no Cvent
* no OpenTable
* no SevenRooms
* no DesignMyNight
* no payment provider
* no live sports/theatre/university/school APIs

## Production Readiness

* no production authentication required unless needed for local testing
* no enterprise SSO
* no multi-tenant production hardening
* no production monitoring
* no cloud deployment requirement
* no customer-facing public deployment

## AI Scope

* no autonomous AI sales agent
* no full agentic workflow system
* no complex prompt governance
* no human approval queue
* no AI voice
* no telephony

## Data Scope

* no real customer data
* no real restaurant data unless manually provided for testing
* no production email inbox
* no historical CRM import

---

# 10. Success Criteria

The POC is successful if a user can:

* open the dashboard
* view seeded restaurant activity
* view and edit pricing rules
* view and assign the three default personas
* submit a test enquiry through the webform
* read a test inbound email enquiry
* generate a persona-based response
* send a test email through Gmail SMTP
* view the enquiry in the dashboard
* view demand events on the calendar
* view simple insights analytics
* understand how pricing recommendations were produced
* understand which persona was used and why

---

# 11. POC Non-Goals

The POC is not expected to:

* close real bookings
* collect deposits
* integrate with CRMs
* run real pricing optimisation
* ingest live event data
* support production users
* handle real customer communication at scale
* replace event sales staff
* support multiple hospitality groups

---

# 12. Recommended First Build Order

## Phase 1 — Foundation

* repo structure
* FastAPI backend
* PostgreSQL
* Redis
* Celery
* frontend scaffold
* environment configuration
* seed script framework

## Phase 2 — Seed Data

* create four restaurants
* create three personas
* assign personas to restaurants
* create pricing rules
* create one year of fake demand events
* create fake enquiries

## Phase 3 — Core Pages

* dashboard
* pricing rules
* personas
* calendar
* insights analytics

## Phase 4 — Webform

* build test enquiry webform
* save enquiry to database
* classify enquiry source
* show enquiry in dashboard

## Phase 5 — Email

* Gmail SMTP send test email
* Gmail inbox reading
* create enquiry from inbound email
* log email events

## Phase 6 — POC Review

* validate end-to-end flow
* document gaps
* identify MVP issues
* create GitHub issues for next sprint

---

# 13. POC Guardrails

All implementation must preserve the intended future architecture:

* modular monolith
* Python/FastAPI backend
* PostgreSQL source of truth
* Redis/Celery background jobs
* deterministic pricing rules
* persona-based AI communication
* no third-party production integrations during POC
* no premature microservices
* no ML pricing during POC
* no production email sending

Any feature that requires substantial production-grade integration should be deferred to MVP or later.

---

