/**
 * DraftSection smoke tests — verifies the draft response UI renders
 * in the idle state and triggers generation on button click.
 *
 * UI-011: Show Generated Draft Response in Enquiry Detail
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Import after mocking
// We need to access the DraftSection component — it's not exported from EnquiryDetailDrawer,
// so we test via the drawer itself with a minimal Enquiry prop.
import { EnquiryDetailDrawer } from "@/components/enquiries/EnquiryDetailDrawer";

const MOCK_ENQUIRY = {
  id: "aaaaaaaa-0000-0000-0000-000000000001",
  restaurant_id: "bbbbbbbb-0000-0000-0000-000000000001",
  persona_id: null,
  reference: "ENQ-2026-0001",
  status: "new",
  first_name: "Alice",
  last_name: "Smith",
  email: "alice@example.com",
  phone: null,
  company_name: null,
  party_size: 10,
  event_date: "2026-07-01",
  event_type: "Birthday",
  budget_indication: null,
  preferred_area: null,
  dietary_requirements: null,
  special_requests: null,
  message: "Looking forward to the event.",
  source: "webform",
  recommended_minimum_spend: 1500,
  notes: null,
  created_at: "2026-05-01T10:00:00Z",
  updated_at: "2026-05-01T10:00:00Z",
};

const MOCK_RESTAURANTS = [
  { id: "bbbbbbbb-0000-0000-0000-000000000001", name: "The Grand" },
];

beforeEach(() => {
  mockFetch.mockReset();
  // Default: return empty messages list
  mockFetch.mockResolvedValue({
    ok: true,
    json: async () => [],
  });
});

describe("EnquiryDetailDrawer — DraftSection (idle state)", () => {
  it("renders without crashing", () => {
    const { container } = render(
      <EnquiryDetailDrawer
        enquiry={MOCK_ENQUIRY}
        restaurants={MOCK_RESTAURANTS}
        personas={[]}
        onClose={vi.fn()}
      />
    );
    expect(container.firstChild).not.toBeNull();
  });

  it("shows the Draft Response section heading", () => {
    render(
      <EnquiryDetailDrawer
        enquiry={MOCK_ENQUIRY}
        restaurants={MOCK_RESTAURANTS}
        personas={[]}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText("Draft Response")).toBeInTheDocument();
  });

  it("shows the Generate Draft button in idle state", () => {
    render(
      <EnquiryDetailDrawer
        enquiry={MOCK_ENQUIRY}
        restaurants={MOCK_RESTAURANTS}
        personas={[]}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByRole("button", { name: /generate draft/i })).toBeInTheDocument();
  });

  it("calls the draft POST endpoint when Generate Draft is clicked", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/draft") && !url.includes("GET")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            enquiry_id: MOCK_ENQUIRY.id,
            message_id: "cccccccc-0000-0000-0000-000000000001",
            subject: "Your enquiry at The Grand",
            body: "Dear Alice,\n\nThank you for your enquiry.",
            persona_name: "The Host",
            recommended_minimum_spend: 1500,
            pricing_explanation: "Based on 10 guests.",
            is_fallback: false,
            model: "claude-haiku-4-5-20251001",
            generated_at: "2026-05-21T10:00:00Z",
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => [] });
    });

    render(
      <EnquiryDetailDrawer
        enquiry={MOCK_ENQUIRY}
        restaurants={MOCK_RESTAURANTS}
        personas={[]}
        onClose={vi.fn()}
      />
    );

    const btn = screen.getByRole("button", { name: /generate draft/i });
    fireEvent.click(btn);

    // fetch should have been called with the draft endpoint
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining(`/enquiries/${MOCK_ENQUIRY.id}/draft`),
      expect.objectContaining({ method: "POST" })
    );
  });
});
