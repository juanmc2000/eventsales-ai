# AI Drift Guardrails

## Purpose
Prevent Claude Code or any AI coding agent from drifting away from the approved EventSales AI UI direction.

## Absolute Rules
1. Keep the dark left sidebar and dark topbar on all main product pages.
2. Keep the main workspace light, clean and card-based.
3. Use the approved colour tokens only.
4. Do not redesign into generic CRM blue/grey styling.
5. Do not add cartoon mascots, childish illustrations or unrelated visual themes.
6. Do not make the product look like a consumer booking app.
7. Do not make admin pages look like client hospitality pages.
8. Do not remove AI rationale from recommendations.
9. Do not create manual approval-queue UX unless the page explicitly requires escalation.
10. Do not add visual clutter that slows operational use.

## Product Positioning Guard Rail
EventSales AI is commercial operating infrastructure for hospitality event sales. It is not a chatbot, generic CRM, calendar tool or proposal template tool.

## UI Personality
The interface should feel:
- premium
- fast
- modern
- commercially intelligent
- hospitality-aware
- calm under operational pressure

The interface should not feel:
- childish
- gimmicky
- generic enterprise grey
- over-animated
- crypto/trading app aggressive
- consumer marketplace-like

## Page Consistency Checklist
Before completing any page, verify:
- sidebar matches shell rules
- topbar matches shell rules
- page uses approved tokens
- cards use consistent radius and shadow
- typography matches design system
- status pills match approved language
- forms and tables follow component rules
- AI suggestions include rationale
- responsive layout is considered

## Admin Guard Rails
Admin pages are for internal technical and access-management use.
They should prioritise:
- auditability
- permissions
- environment health
- system status
- deployment visibility
- user access control

Admin pages should not prioritise:
- venue imagery
- hospitality atmosphere
- sales dashboard flourish
- colourful KPI storytelling

## Claude Code Implementation Instruction
When implementing, always read these files first:
1. `REFERENCE_IMAGES.md`
2. `UI_DESIGN_SYSTEM.md`
3. `UI_COMPONENT_RULES.md`
4. `UI_PAGE_BRIEFS.md`
5. `AI_DRIFT_GUARDRAILS.md`

Then inspect the corresponding reference image for the page being built.

## Do Not Invent New Navigation
Use the navigation taxonomy from `UI_COMPONENT_RULES.md` unless the product specification explicitly changes.

## Do Not Invent New Brand Colours
Use colour tokens from `UI_DESIGN_SYSTEM.md`. Any new semantic colour must map to an existing token.
