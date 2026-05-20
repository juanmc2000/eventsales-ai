# EventSales AI — MVP Engineering Specifications
## Items 1–8

---

# 1. Authentication & User Management

## Objective
Provide secure multi-tenant authentication and role-based access control for hospitality groups.

---

## User Roles

### Event Sales Manager
Permissions:
- Manage pricing rules
- Configure personas
- Configure workflows
- View all venues
- View analytics
- Configure automation

---

### Event Sales Representative
Permissions:
- View assigned enquiries
- Handle escalations
- View proposals
- Access CRM-linked workflows

---

### Administrator
Permissions:
- Configure integrations
- Manage environments
- Manage user access
- View audit logs
- Manage deployment settings

---

## Functional Requirements

### Authentication
- Email/password login
- OAuth support (Google/Microsoft)
- Password reset flow
- Session management
- MFA-ready architecture

---

### Role-Based Access Control (RBAC)
Support:
- tenant isolation
- granular permissions
- future custom roles

---

### Multi-Tenant Architecture
Each hospitality group should have:
- isolated restaurant data
- isolated pricing rules
- isolated personas
- isolated workflows

---

## Backend Requirements
- JWT authentication
- Refresh token support
- Secure password hashing
- Tenant-aware middleware

---

## Suggested Stack
- FastAPI Auth
- PostgreSQL
- Redis session caching

---

# 2. Restaurant & Room Management

## Objective
Central management of:
- restaurants
- rooms
- capacities
- assets
- personas
- restaurant groups

---

## Functional Requirements

### Restaurant Configuration
Each restaurant must support:
- restaurant name
- codename
- address
- geo coordinates
- prestige classification
- audience type
- opening hours
- serving schedule
- event manager
- lead team
- booking webform URL
- assigned personas
- restaurant group assignment

---

### Restaurant Groups
Support:
- creating groups
- assigning restaurants to groups
- group inheritance logic
- group-level pricing rules
- group-level personas

Examples:
- London Premium Group
- Airport Venues
- Leisure Portfolio

---

### Room Management
Each room supports:
- room name
- seated capacity
- standing capacity
- multiple layouts
- room hire fee
- room assets
- availability status

---

### Room Layouts
Example layouts:
- One Long Table: 24
- Round Tables: 32
- Standing Reception: 50

Store as:
- JSON configuration object

---

### Asset Management
Support:
- menus
- wine lists
- brochures
- room images
- videos
- 360 tours

Requirements:
- CDN-backed storage
- tagging support
- room-level association

---

## Search Requirements

### Dynamic Restaurant Search
Search must support:
- autocomplete
- fuzzy matching
- partial matching
- codename matching
- address matching

Examples:
- "Ivy Chelsea"
- "Chelsea Ivy"
- "St Paul Ivy"

---

### Search UX
Requirements:
- instant dropdown suggestions
- keyboard navigation
- enter-to-select
- highlighted matching text
- recent searches

---

## Spreadsheet Upload
Support:
- CSV
- XLSX

Workflow:
1. Upload
2. AI field detection
3. Mapping preview
4. Validation
5. Import

---

## AI Extraction
Use LLM extraction for:
- capacities
- amenities
- serving schedules
- asset classification

---

# 3. Pricing Rule Engine

## Objective
Allow configurable minimum spend optimisation.

---

## Pricing Philosophy
The system optimises:
- occupancy
- expected revenue
- conversion probability

NOT simply:
- maximum quoted spend

---

## Pricing Rule Types

### Capacity-Based Rules

Inputs:
- room capacity %
- booking lead time

Example:
| Capacity % | Lead Time | Adjustment |
|---|---|---|
| >=80% | >3 months | +10% |
| <=50% | <1 month | -10% |

---

### Time Decay Rules

Example:
| Lead Time | Adjustment |
|---|---|
| >=3 months | +10% |
| <=1 month | -20% |

---

## Revenue Intelligence Inputs

### Internal Signals
- occupancy
- historical conversions
- room utilisation
- lead time
- event type
- historical pricing outcomes

---

### External Signals
- weather
- sports fixtures
- concerts
- theatre schedules
- conferences
- tourist traffic
- bank holidays
- school holidays
- competitor pressure

---

## Geographic Intelligence
System must understand:
- walking cities
- driving cities
- event radius influence

Examples:
- Central London = small radius
- Regional cities = larger radius

---

## Explainability Requirements
Every recommendation logs:
- source rules
- adjustments applied
- influencing factors
- timestamp
- confidence score

---

## Technical Requirements
- weighted rule engine
- priority resolution
- extensible architecture
- ML-ready pricing layer

---

# 4. AI Persona Engine

## Objective
Allow leadership teams to configure AI communication behaviour.

---

## Persona Philosophy
The AI should feel like:
- a trained hospitality sales representative
NOT:
- a chatbot

---

## Persona Configuration

### Editable Attributes
- tone
- warmth
- urgency
- communication density
- emotional style
- sales aggressiveness
- operational detail level

---

## Default Personas

### Corporate Persona
- concise
- commercially direct
- urgency-driven

Automatically includes:
- menus
- wine list
- room images

---

### Social Persona
- warm
- celebratory
- emotionally engaging

---

### Ultra Luxury Persona
- refined
- discreet
- calm
- anticipatory

---

### Agency Persona
- highly detailed
- negotiation-aware
- operationally precise

---

## Natural Language Editing
Managers can type:
"Make this more warm but still concise"

LLM converts into:
- updated structured configuration

---

## Persona Assignment
Support:
- global personas
- group personas
- restaurant-specific personas

---

## Operational Model
The platform:
- automatically sends communications
- applies configured personas
- executes without manual approval queues

---

# 5. Proposal Generation & Deposit Engine

## Objective
Reduce time from:
- enquiry
to
- proposal and deposit

within minutes.

---

## Automated Workflow

The system automatically:
- analyses enquiries
- extracts booking details
- identifies missing information
- calculates minimum spend
- selects rooms
- suggests alternatives
- generates proposals
- sends proposals
- sends deposit links
- follows up automatically

---

## Proposal Assets
Support:
- menus
- wine lists
- brochures
- room images
- 360 tours
- package documents

---

## Deposit Integrations
Integrations:
- Stripe
- Adyen

Capabilities:
- deposit collection
- T&Cs acceptance
- digital agreements
- booking confirmation

---

## Escalation Rules
Escalate:
- VIP enquiries
- exceptional pricing requests
- large buyouts
- complex multi-venue bookings

---

## Performance Requirements
- Proposal generation <30 seconds
- Pricing calculation <3 seconds

---

# 6. Email & Workflow Automation Engine

## Objective
Automate:
- proposals
- follow-ups
- enquiry closures
- deposit reminders

using configurable workflow logic.

---

## Email Configuration
Support:
- headers
- footers
- signatures
- branding
- typography
- disclaimers
- CTA buttons

---

## Follow-Up Workflows

### Example Workflow
- Follow-up after 48h
- Second follow-up after 72h
- Close enquiry after no response

---

## Availability-Lost Workflow

If:
- enquiry remains unconfirmed
AND
- venue becomes unavailable

Then:
- notify customer
- suggest alternatives
- close enquiry after configurable delay

---

## Workflow Builder UX

### Timeline Builder
Visual workflow:
Enquiry → Wait → Follow-Up → Wait → Closure

Support:
- drag/drop timing
- inline editing
- add/remove steps

---

### Rule Cards
WHEN:
Corporate enquiry

WAIT:
24h

THEN:
Send follow-up

---

## Natural Language Workflow Configuration

Example:
"For social users follow up twice, first after 48h, then after 72h. Close if no response."

LLM converts into:
- structured workflow
- readable explanation
- confirmation preview

---

## Technical Requirements
Workflow engine must support:
- delayed jobs
- event triggers
- branching logic
- cancellation conditions
- retries
- idempotent execution

---

# 7. CRM Integration Layer

## Objective
Enrich CRMs with commercial intelligence.

---

## Supported CRMs
- Salesforce
- TripleSeat
- Cvent

---

## CRM Data Sync

### Sync Into CRM
- enquiry status
- proposal history
- pricing recommendations
- urgency indicators
- customer preferences
- venue recommendations
- follow-up history

---

## CRM Purpose
Allow:
- reservation agents
- event sales teams
- existing AI/voice systems

to access:
- latest commercial context
during customer interactions.

---

## Technical Requirements
- webhook support
- bidirectional sync
- retry handling
- audit logging
- conflict resolution

---

# 8. Minimum Spend Calendar & Commercial Dashboard

## Objective
Provide:
- operational visibility
- pricing visibility
- occupancy monitoring
- commercial insights

across the portfolio.

---

## Calendar Modes

### Monthly View
Display:
- breakfast pricing
- lunch pricing
- dinner pricing
- availability indicators
- event indicators

---

### Weekly View
Display:
- customer name
- booking stage
- notes
- operational tasks

---

### Annual View
Display:
- seasonality
- demand trends
- pricing trends
- event concentration

---

## Event Indicators
Examples:
- Sports
- Theatre
- Conferences
- Graduation
- Tourist events

---

## Availability Status Colours
- Green = Available
- Amber = Enquiry In Progress
- Gold = Deposit Paid
- Grey = Fully Booked

---

## Dashboard Metrics

### Operational Metrics
- response time
- proposal conversion
- deposit conversion
- enquiry volume

---

### Commercial Metrics
- occupancy
- pricing performance
- conversion trends
- venue performance

---

## Opportunity Detection
Examples:
- underperforming venue alerts
- pricing resistance alerts
- demand surge alerts
- tourist traffic impact alerts

---

## Technical Requirements
- real-time updates
- async event processing
- caching layer
- dashboard aggregation service