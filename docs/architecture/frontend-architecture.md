# Frontend Architecture

## Purpose

This document describes the frontend architecture for the EventSales AI POC.

## POC Scope

The frontend is a React/Next.js single-page application. It is API-driven. No business logic lives in the frontend. No pricing calculations occur in the UI.

## Stack

| Component | Technology |
|---|---|
| Framework | Next.js (React) |
| State | React hooks / context (no complex state library for POC) |
| Styling | CSS modules or Tailwind (to be confirmed) |
| API client | Fetch / Axios calling FastAPI backend |
| Auth | JWT token stored in httpOnly cookie or memory (POC-grade) |

## Page Structure

Pages map 1:1 to the POC specification:

| Page | Route | Purpose |
|---|---|---|
| Dashboard | `/` | Portfolio overview, KPIs, recent enquiries |
| Enquiries | `/enquiries` | Enquiry list and status |
| Enquiry Detail | `/enquiries/[id]` | AI summary, actions, timeline |
| Calendar | `/calendar` | Demand indicators, pricing impact |
| Pricing Rules | `/pricing` | Rule management |
| Personas | `/personas` | Persona configuration |
| Insights | `/insights` | Analytics and charts |
| Webform | `/enquire` | Test enquiry submission form |

## Design System

All pages must follow the EventSales AI UI design system. See `design/docs/` for:

- colour tokens (`UI_DESIGN_SYSTEM.md`)
- component rules (`UI_COMPONENT_RULES.md`)
- page briefs (`UI_PAGE_BRIEFS.md`)
- drift guardrails (`AI_DRIFT_GUARDRAILS.md`)

Every page uses:
- dark left sidebar
- dark topbar
- light scrollable workspace
- white rounded cards

## API Communication

- All data fetched from FastAPI backend via REST
- No backend logic duplicated in the frontend
- No hardcoded pricing rules in the UI
- No hardcoded persona logic in the UI

## POC Limitations

- No SSR/SSG requirements for POC (client-side rendering acceptable)
- No production auth flows
- No real-time updates (polling acceptable for POC)
- No i18n / localisation
- No accessibility audit during POC (basic accessibility only)
- Frontend runs outside Docker Compose during POC development
