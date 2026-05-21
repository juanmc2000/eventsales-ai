/**
 * Rooms/PDR Management page smoke tests.
 *
 * UI-015: Build Rooms/PDR Management Page
 */
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/rooms",
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => ({
    get: () => null,
  }),
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

function mockFetch(data: unknown, ok = true) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    json: async () => data,
    text: async () => JSON.stringify(data),
  }));
}

const MOCK_RESTAURANTS = {
  items: [
    { id: "rest-001", name: "The Grand Ballroom", slug: "the-grand-ballroom", is_active: true, tenant_id: "default", description: null, address: null, phone: null, email: null, settings: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
  ],
  total: 1,
};

const MOCK_ROOMS = {
  items: [
    {
      id: "room-001",
      restaurant_id: "rest-001",
      tenant_id: "default",
      name: "The Grand Ballroom",
      slug: "grand-ballroom-main",
      description: null,
      room_type: "ballroom",
      seated_capacity: 300,
      standing_capacity: 500,
      min_capacity: 50,
      max_capacity: 500,
      layouts: ["theatre", "banquet"],
      amenities: ["Crystal chandeliers"],
      asset_links: null,
      room_hire_fee: null,
      minimum_spend_notes: "From £5,000",
      suitability_notes: "Ideal for gala dinners.",
      booking_url: "https://events.example.com",
      is_private_dining: false,
      is_active: true,
      display_order: 1,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    {
      id: "room-002",
      restaurant_id: "rest-001",
      tenant_id: "default",
      name: "The Mayfair Suite",
      slug: "mayfair-suite",
      description: null,
      room_type: "private_dining",
      seated_capacity: 24,
      standing_capacity: 35,
      min_capacity: 8,
      max_capacity: 35,
      layouts: ["boardroom"],
      amenities: ["Private butler"],
      asset_links: null,
      room_hire_fee: "750.00",
      minimum_spend_notes: null,
      suitability_notes: "Board dinners.",
      booking_url: null,
      is_private_dining: true,
      is_active: true,
      display_order: 2,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ],
  total: 2,
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("RoomsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders page title", async () => {
    mockFetch(MOCK_RESTAURANTS);
    const { default: RoomsPage } = await import("@/app/rooms/page");
    render(<RoomsPage />);
    expect(screen.getByText("Rooms & PDRs")).toBeDefined();
  });

  it("renders 'Add Room' button", async () => {
    mockFetch(MOCK_RESTAURANTS);
    const { default: RoomsPage } = await import("@/app/rooms/page");
    render(<RoomsPage />);
    expect(screen.getByText("Add Room")).toBeDefined();
  });

  it("renders room names after loading", async () => {
    let callCount = 0;
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => {
      callCount++;
      const data = callCount === 1 ? MOCK_RESTAURANTS : MOCK_ROOMS;
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => data,
        text: async () => JSON.stringify(data),
      });
    }));

    const { default: RoomsPage } = await import("@/app/rooms/page");
    render(<RoomsPage />);

    await waitFor(() => {
      expect(screen.queryByText("The Grand Ballroom")).toBeDefined();
    });
  });

  it("renders PDR badge for private dining rooms", async () => {
    let callCount = 0;
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => {
      callCount++;
      const data = callCount === 1 ? MOCK_RESTAURANTS : MOCK_ROOMS;
      return Promise.resolve({ ok: true, status: 200, json: async () => data, text: async () => JSON.stringify(data) });
    }));

    const { default: RoomsPage } = await import("@/app/rooms/page");
    render(<RoomsPage />);

    await waitFor(() => {
      const pdrs = screen.queryAllByText("PDR");
      expect(pdrs.length).toBeGreaterThan(0);
    });
  });

  it("shows empty state when no rooms", async () => {
    let callCount = 0;
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => {
      callCount++;
      const data = callCount === 1 ? MOCK_RESTAURANTS : { items: [], total: 0 };
      return Promise.resolve({ ok: true, status: 200, json: async () => data, text: async () => JSON.stringify(data) });
    }));

    const { default: RoomsPage } = await import("@/app/rooms/page");
    render(<RoomsPage />);

    await waitFor(() => {
      expect(screen.queryByText(/No rooms configured/i)).toBeDefined();
    });
  });
});
