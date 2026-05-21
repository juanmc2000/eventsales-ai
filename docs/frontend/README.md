# EventSales AI Frontend

Next.js 14 application with TypeScript and TailwindCSS.

## Stack

- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** TailwindCSS + CSS custom properties (design tokens)
- **API:** Fetch-based client in `lib/api.ts`

## Development

```bash
cd services/web
npm install
npm run dev
# App available at http://localhost:3000
```

## Docker

```bash
docker-compose up web
```

## Structure

```
services/web/
├── app/                  # Next.js App Router pages
│   ├── layout.tsx        # Root layout with shell (sidebar + topbar)
│   ├── globals.css       # Design system CSS tokens
│   ├── dashboard/
│   ├── enquiries/
│   ├── restaurants/
│   ├── personas/
│   ├── pricing-rules/
│   ├── calendar/
│   ├── insights/
│   └── admin/
├── components/
│   └── shell/
│       ├── Sidebar.tsx   # Fixed dark left navigation
│       └── Topbar.tsx    # Dark top command bar
└── lib/
    └── api.ts            # API client (no business logic)
```

## Design System

All pages must comply with:
- `design/docs/UI_DESIGN_SYSTEM.md`
- `design/docs/UI_COMPONENT_RULES.md`
- `design/docs/AI_DRIFT_GUARDRAILS.md`

Reference image: `design/reference_images/10_Composite_Overview.png`

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000` |
