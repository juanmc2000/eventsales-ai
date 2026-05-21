# Sprint 5C — Venue Context (Rooms/PDR)

**Theme:** Extend the platform with room/PDR configuration, restaurant AI context, and room-aware draft generation.
**Status:** Complete
**Date:** 2026-05-21

---

## Objective

Introduce a two-level venue model: restaurants as venue containers and rooms/PDRs as physical spaces. Ensure AI draft generation can reference room context, and expose room management through the frontend.

---

## Issues Delivered

| Issue | PR | Description |
|-------|----|-------------|
| DATA-005 | #126 | Rooms/PDR database model, Pydantic schemas, Alembic migration |
| API-010 | #127 | Rooms/PDR CRUD backend (RoomRepository, RoomService, nested router) |
| DATA-006 | #128 | Seed data: 7 rooms/PDRs across 4 restaurants |
| API-011 | #129 | Restaurant AI context endpoint (`GET /restaurants/{id}/context`) |
| AI-002 | #130 | AI draft generation uses room context via `_match_room()` |
| UI-014 | #131 | Restaurant rooms summary section in detail drawer |
| UI-015 | #132 | Rooms/PDR management page (`/rooms`) with full CRUD UI |
| UI-016 | #133 | Webform room selection dropdown (backend-driven) |
| TEST-006 | #134 | Venue context workflow tests (migration sanity, CRUD, context, AI matching) |
| DOC-011 | #135 | Updated POC demo guide and sprint status overview |

---

## Architecture Decisions

### Restaurant vs Room separation
- Restaurants own the AI persona and pricing rules
- Rooms are physical spaces with capacity, layouts, amenities, and suitability notes
- Personas are always **restaurant-level** — no per-room persona configuration
- This keeps the model simple and prevents configuration explosion

### Room context in AI drafts
- `DraftGenerationService` queries active rooms for the restaurant via `RoomRepository`
- `_match_room()` applies a deterministic 3-priority algorithm:
  1. `preferred_area` text matches room name (case-insensitive substring)
  2. First room whose capacity range covers the party size
  3. First active room (fallback)
- No ML — matching is purely deterministic
- Draft generation degrades gracefully when no rooms exist (no error, just no room context)

### Restaurant context endpoint
- `GET /api/v1/restaurants/{id}/context` returns `RestaurantContextOut` including rooms, personas (without `system_prompt`), and pricing rules
- This is the single source of truth for AI context assembly
- Does not expose `system_prompt` from personas

### Frontend room selection
- Webform fetches rooms via `GET /api/v1/restaurants/{id}/rooms` when venue is selected
- Falls back to plain text input if venue has no rooms configured
- Room selection is always optional — form submits with "No specific room"
- `preferred_area` is reset when the venue changes

---

## Test Counts Post-Sprint 5C

| Suite | Count |
|-------|-------|
| Backend (pytest) | 332 passed |
| Frontend (vitest) | 79 passed |
| Total | 411 tests |

---

## Files Added or Modified

### Backend
- `services/api/app/modules/restaurants/models.py` — `Room` model added
- `services/api/app/modules/restaurants/schemas.py` — `RoomBase`, `RoomCreate`, `RoomUpdate`, `RoomOut`, `RoomListOut`, `RestaurantContextOut` and related schemas
- `services/api/app/modules/restaurants/repository.py` — `RoomRepository` added
- `services/api/app/modules/restaurants/service.py` — `RoomService` added, `RestaurantService.get_restaurant_context()` added
- `services/api/app/modules/restaurants/router.py` — 5 room endpoints + `/context` endpoint
- `services/api/app/modules/ai/schemas.py` — 10 room context fields added to `DraftContext`
- `services/api/app/modules/ai/service.py` — `_match_room()`, room population in draft context
- `services/api/app/modules/ai/provider.py` — Room context rendering in `FallbackProvider`
- `services/api/app/modules/shared/seed_data.py` — `SEED_ROOMS`, `_upsert_room()`, wired into `run_seed()`
- `services/api/app/db/models.py` — `Room` import added
- `services/api/alembic/versions/20260521_000002_add_rooms_table.py` — New migration

### Frontend
- `services/web/lib/types/restaurant.ts` — `Room`, `RoomListOut`, `RoomContext`, `RestaurantContext` types added
- `services/web/components/restaurants/RestaurantRoomsSummary.tsx` — New component
- `services/web/app/restaurants/page.tsx` — Room summary section in restaurant detail
- `services/web/app/rooms/page.tsx` — New Rooms/PDR management page
- `services/web/components/shell/Sidebar.tsx` — Rooms nav item enabled
- `services/web/components/webform/EnquiryWebform.tsx` — Room selection dropdown
- `services/web/components/enquiries/EnquiryDetailDrawer.tsx` — Label update

### Tests
- `services/api/tests/restaurants/test_room_schema.py` — 7 schema tests
- `services/api/tests/restaurants/test_room_service.py` — 16 service tests
- `services/api/tests/restaurants/test_restaurant_context.py` — 10 context tests
- `services/api/tests/restaurants/test_venue_context_workflow.py` — 12 workflow tests
- `services/api/tests/ai/test_draft_room_context.py` — 17 AI tests
- `services/api/tests/seed/test_seed_rooms.py` — 12 seed tests
- `services/web/tests/restaurants/RestaurantRoomsSummary.test.tsx` — 9 component tests
- `services/web/tests/rooms/rooms-page.smoke.test.tsx` — 5 smoke tests
- `services/web/tests/webform/room-selection.smoke.test.tsx` — 4 smoke tests

---

## Known Limitations Introduced

- Room availability checking is not implemented — rooms are reference data only
- No room asset management (images, floor plans)
- Room matching in AI drafts is deterministic (no ML ranking)
- Personas are restaurant-level; no per-room persona configuration
