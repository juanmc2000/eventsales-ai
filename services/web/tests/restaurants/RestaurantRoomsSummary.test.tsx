/**
 * RestaurantRoomsSummary component tests.
 *
 * UI-014: Add Restaurant Rooms Summary Section
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { RestaurantRoomsSummary } from "@/components/restaurants/RestaurantRoomsSummary";
import type { RestaurantContext } from "@/lib/types/restaurant";

// ── Fixtures ──────────────────────────────────────────────────────────────────

const CONTEXT_WITH_ROOMS: RestaurantContext = {
  id: "rest-001",
  tenant_id: "default",
  name: "The Grand Ballroom",
  slug: "the-grand-ballroom",
  description: "A grand venue.",
  address: "1 Grand Place, London",
  phone: null,
  email: null,
  default_persona: {
    id: "persona-001",
    name: "Eleanor",
    slug: "eleanor",
    description: "Warm and formal.",
    tone: "warm and formal",
    style: "considered",
    is_default: true,
  },
  personas: [
    {
      id: "persona-001",
      name: "Eleanor",
      slug: "eleanor",
      description: null,
      tone: "warm and formal",
      style: "considered",
      is_default: true,
    },
  ],
  rooms: [
    {
      id: "room-001",
      name: "The Grand Ballroom",
      slug: "grand-ballroom-main",
      description: "Our main ballroom.",
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
      suitability_notes: "Ideal for gala dinners.",
      booking_url: "https://events.example.com/enquire",
      is_private_dining: false,
      display_order: 1,
    },
    {
      id: "room-002",
      name: "The Mayfair Suite",
      slug: "grand-ballroom-mayfair-suite",
      description: "An intimate PDR.",
      room_type: "private_dining",
      seated_capacity: 24,
      standing_capacity: 35,
      min_capacity: 8,
      max_capacity: 35,
      layouts: ["boardroom"],
      amenities: ["Private butler service"],
      asset_links: null,
      room_hire_fee: "750.00",
      minimum_spend_notes: null,
      suitability_notes: "Perfect for board dinners.",
      booking_url: null,
      is_private_dining: true,
      display_order: 2,
    },
  ],
  pricing_rules: [],
};

const CONTEXT_NO_ROOMS: RestaurantContext = {
  ...CONTEXT_WITH_ROOMS,
  rooms: [],
  default_persona: null,
  personas: [],
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("RestaurantRoomsSummary", () => {
  it("renders room names", () => {
    render(
      <RestaurantRoomsSummary
        context={CONTEXT_WITH_ROOMS}
        restaurantId="rest-001"
      />
    );
    expect(screen.getByText("The Grand Ballroom")).toBeDefined();
    expect(screen.getByText("The Mayfair Suite")).toBeDefined();
  });

  it("renders PDR badge for private dining rooms", () => {
    render(
      <RestaurantRoomsSummary
        context={CONTEXT_WITH_ROOMS}
        restaurantId="rest-001"
      />
    );
    expect(screen.getByText("PDR")).toBeDefined();
  });

  it("renders seated capacity", () => {
    render(
      <RestaurantRoomsSummary
        context={CONTEXT_WITH_ROOMS}
        restaurantId="rest-001"
      />
    );
    expect(screen.getByText("300 seated")).toBeDefined();
    expect(screen.getByText("24 seated")).toBeDefined();
  });

  it("renders default persona name", () => {
    render(
      <RestaurantRoomsSummary
        context={CONTEXT_WITH_ROOMS}
        restaurantId="rest-001"
      />
    );
    expect(screen.getByText("Eleanor")).toBeDefined();
  });

  it("renders persona tone", () => {
    render(
      <RestaurantRoomsSummary
        context={CONTEXT_WITH_ROOMS}
        restaurantId="rest-001"
      />
    );
    expect(screen.getByText("warm and formal")).toBeDefined();
  });

  it("renders manage rooms link", () => {
    render(
      <RestaurantRoomsSummary
        context={CONTEXT_WITH_ROOMS}
        restaurantId="rest-001"
      />
    );
    const link = screen.getByText("Manage rooms");
    expect(link).toBeDefined();
  });

  it("renders room count badge", () => {
    render(
      <RestaurantRoomsSummary
        context={CONTEXT_WITH_ROOMS}
        restaurantId="rest-001"
      />
    );
    expect(screen.getByText("2")).toBeDefined();
  });

  it("renders empty state when no rooms", () => {
    render(
      <RestaurantRoomsSummary
        context={CONTEXT_NO_ROOMS}
        restaurantId="rest-001"
      />
    );
    expect(
      screen.getByText(/No rooms configured/i)
    ).toBeDefined();
  });

  it("renders no persona section when none assigned", () => {
    render(
      <RestaurantRoomsSummary
        context={CONTEXT_NO_ROOMS}
        restaurantId="rest-001"
      />
    );
    expect(screen.queryByText("Eleanor")).toBeNull();
  });
});
