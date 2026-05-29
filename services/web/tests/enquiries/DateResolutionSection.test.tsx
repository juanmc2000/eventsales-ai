/**
 * DateResolutionSection component tests.
 *
 * UI-022: Show Date Resolution Summary in Enquiry Detail
 */
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/enquiries",
  useRouter: () => ({ push: vi.fn() }),
}));

const ENQUIRY_ID = "enq-date-001";

// ─── Fetch helpers ─────────────────────────────────────────────────────────────

function mockFetch(dateRequestBody: unknown, candidatesBody: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((url: string) => {
      if (url.includes("/date-request/latest")) {
        const ok = dateRequestBody !== null;
        return Promise.resolve({
          ok,
          status: ok ? 200 : 404,
          json: async () => dateRequestBody,
        });
      }
      if (url.includes("/candidate-dates")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => candidatesBody ?? [],
        });
      }
      return Promise.resolve({ ok: false, status: 404, json: async () => null });
    })
  );
}

function makeDateRequest(overrides: Record<string, unknown> = {}) {
  return {
    id: "dr-001",
    enquiry_id: ENQUIRY_ID,
    extraction_id: "ext-001",
    prompt_run_id: null,
    raw_text: "sometime in August",
    date_request_type: "month_flexible",
    anchor_date: "2026-05-29",
    timezone: "Europe/London",
    extracted_json: {},
    requires_date_clarification: false,
    clarification_question: null,
    confidence: 0.9,
    created_at: "2026-05-29T10:00:00Z",
    ...overrides,
  };
}

function makeCandidate(overrides: Record<string, unknown> = {}) {
  return {
    id: "cand-001",
    enquiry_id: ENQUIRY_ID,
    date_request_id: "dr-001",
    candidate_date: "2026-08-15",
    source_type: "deterministic",
    availability_status: "available",
    pricing_checked: true,
    recommended_minimum_spend: 2500,
    ranking_score: null,
    created_at: "2026-05-29T10:00:00Z",
    ...overrides,
  };
}

// ─── Tests ─────────────────────────────────────────────────────────────────────

describe("DateResolutionSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows empty state when no date request exists", async () => {
    mockFetch(null, []);
    const { DateResolutionSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<DateResolutionSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(
        screen.getByText(/no date resolution has been run yet/i)
      ).toBeInTheDocument();
    });
  });

  it("shows date request type label", async () => {
    mockFetch(makeDateRequest({ date_request_type: "month_flexible" }), []);
    const { DateResolutionSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<DateResolutionSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText(/month flexible/i)).toBeInTheDocument();
    });
  });

  it("shows raw_text from the date request", async () => {
    mockFetch(makeDateRequest({ raw_text: "sometime in August" }), []);
    const { DateResolutionSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<DateResolutionSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText(/sometime in August/i)).toBeInTheDocument();
    });
  });

  it("shows 'Needs clarification' badge when requires_date_clarification is true", async () => {
    mockFetch(
      makeDateRequest({
        requires_date_clarification: true,
        clarification_question: "Did you mean the 4th or the 14th?",
      }),
      []
    );
    const { DateResolutionSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<DateResolutionSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText(/needs clarification/i)).toBeInTheDocument();
    });
  });

  it("shows clarification question when present and clarification is required", async () => {
    mockFetch(
      makeDateRequest({
        requires_date_clarification: true,
        clarification_question: "Did you mean the 4th or the 14th?",
      }),
      []
    );
    const { DateResolutionSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<DateResolutionSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(
        screen.getByText(/Did you mean the 4th or the 14th\?/i)
      ).toBeInTheDocument();
    });
  });

  it("does not show clarification question when clarification is not required", async () => {
    mockFetch(
      makeDateRequest({
        requires_date_clarification: false,
        clarification_question: "Did you mean the 4th or the 14th?",
      }),
      []
    );
    const { DateResolutionSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<DateResolutionSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(
        screen.queryByText(/Did you mean the 4th or the 14th\?/i)
      ).not.toBeInTheDocument();
    });
  });

  it("shows candidate dates when available", async () => {
    mockFetch(makeDateRequest(), [
      makeCandidate({ candidate_date: "2026-08-15" }),
    ]);
    const { DateResolutionSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<DateResolutionSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      // Formatted as "Sat, 15 Aug 2026" or similar
      expect(screen.getByText(/Aug 2026/i)).toBeInTheDocument();
    });
  });

  it("shows candidate count label", async () => {
    mockFetch(makeDateRequest(), [
      makeCandidate({ id: "cand-001" }),
      makeCandidate({ id: "cand-002", candidate_date: "2026-08-16" }),
    ]);
    const { DateResolutionSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<DateResolutionSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText(/Candidate Dates \(2\)/i)).toBeInTheDocument();
    });
  });

  it("shows availability status badge per candidate date", async () => {
    mockFetch(makeDateRequest(), [
      makeCandidate({ availability_status: "available" }),
    ]);
    const { DateResolutionSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<DateResolutionSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText("available")).toBeInTheDocument();
    });
  });

  it("shows booked availability status badge", async () => {
    mockFetch(makeDateRequest(), [
      makeCandidate({ availability_status: "booked" }),
    ]);
    const { DateResolutionSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<DateResolutionSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText("booked")).toBeInTheDocument();
    });
  });

  it("shows recommended minimum spend per candidate date", async () => {
    mockFetch(makeDateRequest(), [
      makeCandidate({ recommended_minimum_spend: 3200 }),
    ]);
    const { DateResolutionSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<DateResolutionSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText(/£3,200/i)).toBeInTheDocument();
    });
  });

  it("does not show spend when recommended_minimum_spend is null", async () => {
    mockFetch(makeDateRequest(), [
      makeCandidate({ recommended_minimum_spend: null }),
    ]);
    const { DateResolutionSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<DateResolutionSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.queryByText(/£/)).not.toBeInTheDocument();
    });
  });

  it("shows 'no candidate dates' message when list is empty", async () => {
    mockFetch(makeDateRequest(), []);
    const { DateResolutionSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<DateResolutionSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(
        screen.getByText(/no candidate dates generated/i)
      ).toBeInTheDocument();
    });
  });

  it("shows source_type label per candidate date", async () => {
    mockFetch(makeDateRequest(), [
      makeCandidate({ source_type: "deterministic" }),
    ]);
    const { DateResolutionSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<DateResolutionSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText(/deterministic/i)).toBeInTheDocument();
    });
  });

  it("does not expose raw prompts or internal JSON", async () => {
    mockFetch(makeDateRequest(), [makeCandidate()]);
    const { DateResolutionSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<DateResolutionSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.queryByText(/system_prompt/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/user_message/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/extracted_json/i)).not.toBeInTheDocument();
    });
  });
});
