/**
 * DraftSection smoke tests — verifies the draft response UI renders
 * in the idle state and triggers generation on button click.
 *
 * TEST-004: Sprint 4 Webform and Email Wiring Tests
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

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

beforeEach(() => {
  mockFetch.mockReset();
  mockFetch.mockResolvedValue({ ok: true, json: async () => [] });
});

describe("EnquiryDetailDrawer — Draft Response section", () => {
  it("renders without crashing", () => {
    const { container } = render(
      <EnquiryDetailDrawer
        enquiry={MOCK_ENQUIRY}
        restaurants={[{ id: "bbbbbbbb-0000-0000-0000-000000000001", name: "The Grand" }]}
        personas={[]}
        onClose={vi.fn()}
      />
    );
    expect(container.firstChild).not.toBeNull();
  });

  it("renders the Draft Response section heading", () => {
    render(
      <EnquiryDetailDrawer
        enquiry={MOCK_ENQUIRY}
        restaurants={[{ id: "bbbbbbbb-0000-0000-0000-000000000001", name: "The Grand" }]}
        personas={[]}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText("Draft Response")).toBeInTheDocument();
  });

  it("shows Generate Draft button in idle state", () => {
    render(
      <EnquiryDetailDrawer
        enquiry={MOCK_ENQUIRY}
        restaurants={[{ id: "bbbbbbbb-0000-0000-0000-000000000001", name: "The Grand" }]}
        personas={[]}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByRole("button", { name: /generate draft/i })).toBeInTheDocument();
  });

  it("Generate Draft button is enabled in idle state", () => {
    render(
      <EnquiryDetailDrawer
        enquiry={MOCK_ENQUIRY}
        restaurants={[{ id: "bbbbbbbb-0000-0000-0000-000000000001", name: "The Grand" }]}
        personas={[]}
        onClose={vi.fn()}
      />
    );
    const btn = screen.getByRole("button", { name: /generate draft/i });
    expect(btn).not.toBeDisabled();
  });

  it("clicking Generate Draft calls the draft POST endpoint", () => {
    render(
      <EnquiryDetailDrawer
        enquiry={MOCK_ENQUIRY}
        restaurants={[{ id: "bbbbbbbb-0000-0000-0000-000000000001", name: "The Grand" }]}
        personas={[]}
        onClose={vi.fn()}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: /generate draft/i }));
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining(`/enquiries/${MOCK_ENQUIRY.id}/draft`),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("no 'Coming Soon' placeholder present — draft UI is wired", () => {
    render(
      <EnquiryDetailDrawer
        enquiry={MOCK_ENQUIRY}
        restaurants={[{ id: "bbbbbbbb-0000-0000-0000-000000000001", name: "The Grand" }]}
        personas={[]}
        onClose={vi.fn()}
      />
    );
    expect(screen.queryByText(/coming soon/i)).not.toBeInTheDocument();
  });
});
