/**
 * API mock pattern tests — verifies the fetch-mock pattern works correctly
 * and demonstrates how to mock API responses in component tests.
 *
 * This file also serves as documentation for other test authors.
 *
 * TEST-003: Frontend Smoke Test Baseline
 */
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// ── Mock pattern: how to mock a specific API endpoint ─────────────────────────
//
// Use vi.stubGlobal("fetch", ...) or mock the global fetch per-test.
// The setup.ts file provides a default catch-all mock returning { items: [], total: 0 }.
//
// Example:
//   vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
//     ok: true,
//     json: async () => ({ items: [{ id: "1", name: "Test" }], total: 1 }),
//   }));

vi.mock("next/navigation", () => ({
  usePathname: () => "/enquiries",
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// ─── Fetch mock helper ─────────────────────────────────────────────────────────

function mockFetch(responses: Record<string, unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((url: string) => {
      for (const [pattern, payload] of Object.entries(responses)) {
        if (url.includes(pattern)) {
          return Promise.resolve({ ok: true, json: async () => payload });
        }
      }
      // Default: empty list
      return Promise.resolve({ ok: true, json: async () => ({ items: [], total: 0 }) });
    })
  );
}

// ─── API mock tests ────────────────────────────────────────────────────────────

describe("API mock pattern", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("mockFetch returns matched payload for known endpoint", async () => {
    mockFetch({
      "/api/v1/restaurants": {
        items: [{ id: "r1", name: "The Grand", cuisine_type: "Modern European" }],
        total: 1,
      },
    });

    const res = await fetch("http://localhost:8000/api/v1/restaurants");
    const data = await res.json();
    expect(data.total).toBe(1);
    expect(data.items[0].name).toBe("The Grand");
  });

  it("mockFetch returns empty list for unmatched endpoint", async () => {
    mockFetch({});
    const res = await fetch("http://localhost:8000/api/v1/unknown");
    const data = await res.json();
    expect(data.items).toEqual([]);
    expect(data.total).toBe(0);
  });

  it("global fetch default mock in setup returns ok:true", async () => {
    // Uses the default from tests/setup.ts — no additional mocking needed
    const res = await fetch("http://localhost:8000/any");
    expect(res.ok).toBe(true);
  });
});

// ─── EnquiryDetailDrawer smoke test with mocked API ──────────────────────────

describe("EnquiryDetailDrawer with mocked API", () => {
  const mockEnquiry = {
    id: "e1",
    restaurant_id: "r1",
    persona_id: null,
    reference: "ENQ-001",
    status: "new",
    first_name: "Alice",
    last_name: "Smith",
    email: "alice@example.com",
    phone: null,
    company_name: null,
    party_size: 10,
    event_date: "2026-06-15",
    event_type: "birthday",
    budget_indication: null,
    preferred_area: null,
    dietary_requirements: null,
    special_requests: null,
    message: "Looking for a private dining room.",
    source: "webform",
    recommended_minimum_spend: 1500,
    notes: null,
    created_at: "2026-05-01T10:00:00Z",
    updated_at: "2026-05-01T10:00:00Z",
  };

  beforeEach(() => {
    mockFetch({
      "/messages": [],
      "/personas": { items: [], total: 0 },
    });
  });

  it("renders guest name in header", async () => {
    const { EnquiryDetailDrawer } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(
      <EnquiryDetailDrawer
        enquiry={mockEnquiry}
        restaurantName="The Grand"
        onClose={() => {}}
      />
    );
    expect(screen.getByText("Alice Smith")).toBeInTheDocument();
  });

  it("renders the reference code", async () => {
    const { EnquiryDetailDrawer } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(
      <EnquiryDetailDrawer
        enquiry={mockEnquiry}
        restaurantName="The Grand"
        onClose={() => {}}
      />
    );
    expect(screen.getByText("ENQ-001")).toBeInTheDocument();
  });

  it("renders the recommended minimum spend", async () => {
    const { EnquiryDetailDrawer } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(
      <EnquiryDetailDrawer
        enquiry={mockEnquiry}
        restaurantName="The Grand"
        onClose={() => {}}
      />
    );
    expect(screen.getByText("£1,500")).toBeInTheDocument();
  });

  it("renders the initial request message", async () => {
    const { EnquiryDetailDrawer } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(
      <EnquiryDetailDrawer
        enquiry={mockEnquiry}
        restaurantName="The Grand"
        onClose={() => {}}
      />
    );
    expect(
      screen.getByText("Looking for a private dining room.")
    ).toBeInTheDocument();
  });

  it("shows the draft response placeholder section", async () => {
    const { EnquiryDetailDrawer } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(
      <EnquiryDetailDrawer
        enquiry={mockEnquiry}
        restaurantName="The Grand"
        onClose={() => {}}
      />
    );
    expect(screen.getByText(/coming soon/i)).toBeInTheDocument();
  });

  it("loads messages from the API on mount", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    });
    vi.stubGlobal("fetch", fetchMock);

    const { EnquiryDetailDrawer } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(
      <EnquiryDetailDrawer
        enquiry={mockEnquiry}
        restaurantName="The Grand"
        onClose={() => {}}
      />
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining(`/enquiries/e1/messages`)
      );
    });
  });
});
