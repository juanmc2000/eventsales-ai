# EventSales AI UI Design System

## Purpose
Create a premium hospitality SaaS interface that feels fast, modern, artistic and commercially intelligent. The product should look like a high-end operating system for event sales, not a generic CRM.

## Core Ethos
- Dark luxury shell: deep navy / black-purple sidebar and top navigation.
- Light operational workspace: white, pearl and very pale lavender content area.
- Hospitality energy: controlled use of neon gradients, warm accents, venue imagery and soft glow.
- Enterprise trust: clear hierarchy, strong spacing, predictable tables, restrained animation.
- AI confidence: AI suggestions should feel explainable, calm and useful, never gimmicky.

## Visual North Star
Use `reference_images/01_dashboard_hero_reference.png` as the main visual anchor.
Use `reference_images/00_original_reference.png` as the structural inspiration for left navigation + top banner.
Use `reference_images/00_composite_all_pages.png` as the page-family reference.

## Colour Tokens
```css
:root {
  --nav-bg: #070A1F;
  --nav-bg-2: #0B102B;
  --topbar-bg: #080B24;
  --page-bg: #F8F7FC;
  --surface: #FFFFFF;
  --surface-soft: #FBFAFF;
  --border: #E7E3F2;
  --text-primary: #151525;
  --text-secondary: #6B6680;
  --text-muted: #9A94AD;

  --brand-purple: #6D3DF5;
  --brand-pink: #ED3D96;
  --brand-orange: #FF7A1A;
  --brand-teal: #2CC7C9;
  --brand-gold: #F5B84B;
  --success: #16A66A;
  --warning: #E99A1C;
  --danger: #E5484D;

  --gradient-primary: linear-gradient(135deg, #6D3DF5 0%, #ED3D96 55%, #FF7A1A 100%);
  --gradient-purple: linear-gradient(135deg, #4729E8 0%, #A33DF5 100%);
  --gradient-teal: linear-gradient(135deg, #2CC7C9 0%, #4BE0A0 100%);
  --shadow-card: 0 12px 32px rgba(22, 16, 64, 0.08);
  --shadow-hover: 0 18px 50px rgba(22, 16, 64, 0.14);
}
```

## Typography
- Font family: Inter, Satoshi, or similar modern SaaS font.
- Headings: semibold, tight tracking.
- Body: regular / medium, high readability.
- Numbers: tabular numerals where possible.

Recommended scale:
- Page title: 28–32px / 700
- Section title: 18–20px / 650
- Card title: 14–16px / 650
- Body: 14px / 400–500
- Metadata: 12px / 500

## Layout Rules
- Global layout: fixed dark sidebar, dark topbar, light scrollable content region.
- Sidebar width: 240px desktop, collapsible to icon rail.
- Topbar height: 72–80px.
- Content max width: fluid enterprise dashboard, usually 100% with 24–32px padding.
- Cards: 16–20px radius, white background, subtle border, soft shadow.
- Dashboards should use a 12-column grid.

## Motion
- Use subtle transitions only: 120–180ms ease-out.
- Hover cards lift very slightly.
- Avoid spinning AI animations except for loading states.
- Keep admin pages almost static.

## Accessibility
- Maintain strong contrast in dark navigation.
- Visible keyboard focus rings.
- Do not rely on colour alone for status.
- Tables need clear row hover, action labels and accessible menu buttons.
