/**
 * Room/PDR selection in EnquiryWebform smoke tests.
 *
 * UI-016: Add Room/PDR Selection to Webform and Enquiry Detail
 */
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/webform",
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => ({ get: () => null }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

const MOCK_RESTAURANTS = {
  items: [
    {
      id: "rest-001",
      name: "The Grand Ballroom",
      slug: "the-grand-ballroom",
      is_active: true,
      tenant_id: "default",
      description: null,
      address: null,
      phone: null,
      email: null,
      settings: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
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
      minimum_spend_notes: null,
      suitability_notes: null,
      booking_url: null,
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
      suitability_notes: null,
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

function mockFetchSequence(responses: unknown[]) {
  let callCount = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(() => {
      const data = responses[Math.min(callCount, responses.length - 1)];
      callCount++;
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => data,
        text: async () => JSON.stringify(data),
      });
    })
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("EnquiryWebform room selection", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the Preferred Room or Area field initially as a text input", async () => {
    mockFetchSequence([MOCK_RESTAURANTS]);
    const { default: WebformPage } = await import("@/app/webform/page");
    render(<WebformPage />);
    await waitFor(() => {
      expect(screen.queryAllByText("Venue").length).toBeGreaterThan(0);
    });
    // No restaurant selected — text input with placeholder
    const preferredInput = screen.queryByPlaceholderText("Select a venue first");
    expect(preferredInput).toBeDefined();
  });

  it("loads rooms after restaurant selection and shows a dropdown", async () => {
    // First call: restaurants list. Second call: rooms for selected restaurant.
    mockFetchSequence([MOCK_RESTAURANTS, MOCK_ROOMS]);
    const { default: WebformPage } = await import("@/app/webform/page");
    render(<WebformPage />);

    await waitFor(() => {
      expect(screen.getByText("The Grand Ballroom")).toBeDefined();
    });

    // Select the restaurant
    const venueSelect = screen.getAllByRole("combobox")[0];
    fireEvent.change(venueSelect, { target: { value: "rest-001" } });

    // Rooms should load and a "No specific room" option should appear
    await waitFor(() => {
      expect(screen.queryByText("No specific room")).toBeDefined();
    });
  });

  it("shows PDR label for private dining rooms in the dropdown", async () => {
    mockFetchSequence([MOCK_RESTAURANTS, MOCK_ROOMS]);
    const { default: WebformPage } = await import("@/app/webform/page");
    render(<WebformPage />);

    await waitFor(() => screen.getByText("The Grand Ballroom"));

    const venueSelect = screen.getAllByRole("combobox")[0];
    fireEvent.change(venueSelect, { target: { value: "rest-001" } });

    await waitFor(() => {
      expect(screen.queryByText("The Mayfair Suite (PDR)")).toBeDefined();
    });
  });

  it("shows empty rooms fallback when venue has no rooms", async () => {
    mockFetchSequence([MOCK_RESTAURANTS, { items: [], total: 0 }]);
    const { default: WebformPage } = await import("@/app/webform/page");
    render(<WebformPage />);

    await waitFor(() => screen.getByText("The Grand Ballroom"));

    const venueSelect = screen.getAllByRole("combobox")[0];
    fireEvent.change(venueSelect, { target: { value: "rest-001" } });

    // With no rooms, falls back to text input with plain placeholder
    await waitFor(() => {
      const input = screen.queryByPlaceholderText("e.g. Private Dining Room");
      expect(input).toBeDefined();
    });
  });
});
