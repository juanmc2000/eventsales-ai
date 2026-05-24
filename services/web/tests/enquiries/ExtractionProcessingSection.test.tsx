/**
 * ExtractionProcessingSection component tests.
 *
 * UI-019: Show Extraction and Processing Summary in Enquiry Detail
 */
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/enquiries",
  useRouter: () => ({ push: vi.fn() }),
}));

const ENQUIRY_ID = "enq-abc-001";

// ─── Fetch helpers ─────────────────────────────────────────────────────────────

function mockFetch(extractionBody: unknown, processingBody: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((url: string) => {
      if (url.includes("/extractions/latest")) {
        const ok = extractionBody !== null;
        return Promise.resolve({
          ok,
          status: ok ? 200 : 404,
          json: async () => extractionBody,
        });
      }
      if (url.includes("/processing/latest")) {
        const ok = processingBody !== null;
        return Promise.resolve({
          ok,
          status: ok ? 200 : 404,
          json: async () => processingBody,
        });
      }
      return Promise.resolve({ ok: false, status: 404, json: async () => null });
    })
  );
}

function makeExtraction(overrides: Record<string, unknown> = {}) {
  return {
    id: "ext-001",
    enquiry_id: ENQUIRY_ID,
    tenant_id: "default",
    extracted_json: {
      guest_count: 20,
      event_date: "2026-08-15",
      event_type: "corporate_dinner",
      occasion: "anniversary dinner",
    },
    normalized_json: {
      guest_count: 20,
      event_date: "2026-08-15",
      event_type: "corporate_dinner",
    },
    missing_fields: ["budget"],
    confidence_json: null,
    created_at: "2026-05-24T09:00:00Z",
    ...overrides,
  };
}

function makeProcessing(overrides: Record<string, unknown> = {}) {
  return {
    id: "proc-001",
    enquiry_id: ENQUIRY_ID,
    extraction_id: "ext-001",
    recommended_action: "send_availability_confirmation",
    availability_result_json: {
      room_name: "The Grand Ballroom",
      status: "available",
    },
    room_suitability_json: { room_name: "The Grand Ballroom" },
    pricing_result_json: {
      recommended_minimum_spend: 2500,
      explanation: "Weekend evening rate for 20 guests",
    },
    missing_fields_json: [],
    created_at: "2026-05-24T09:00:00Z",
    ...overrides,
  };
}

// ─── Tests ─────────────────────────────────────────────────────────────────────

describe("ExtractionProcessingSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows empty state when no extraction or processing exists", async () => {
    mockFetch(null, null);
    const { ExtractionProcessingSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<ExtractionProcessingSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(
        screen.getByText(/no extraction has been run yet/i)
      ).toBeInTheDocument();
    });
  });

  it("shows extracted guest count when extraction data is available", async () => {
    mockFetch(makeExtraction(), null);
    const { ExtractionProcessingSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<ExtractionProcessingSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText("20")).toBeInTheDocument();
    });
  });

  it("shows extracted event date", async () => {
    mockFetch(makeExtraction(), null);
    const { ExtractionProcessingSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<ExtractionProcessingSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText("2026-08-15")).toBeInTheDocument();
    });
  });

  it("shows missing fields when present", async () => {
    mockFetch(makeExtraction({ missing_fields: ["budget", "guest_count"] }), null);
    const { ExtractionProcessingSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<ExtractionProcessingSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText(/missing information/i)).toBeInTheDocument();
      expect(screen.getByText(/budget/i)).toBeInTheDocument();
    });
  });

  it("shows matched room from processing snapshot", async () => {
    mockFetch(makeExtraction(), makeProcessing());
    const { ExtractionProcessingSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<ExtractionProcessingSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText("The Grand Ballroom")).toBeInTheDocument();
    });
  });

  it("shows availability status badge from processing snapshot", async () => {
    mockFetch(makeExtraction(), makeProcessing());
    const { ExtractionProcessingSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<ExtractionProcessingSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText("available")).toBeInTheDocument();
    });
  });

  it("shows pricing recommendation from processing snapshot", async () => {
    mockFetch(makeExtraction(), makeProcessing());
    const { ExtractionProcessingSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<ExtractionProcessingSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText(/£2,500/i)).toBeInTheDocument();
    });
  });

  it("shows recommended action label from processing snapshot", async () => {
    mockFetch(makeExtraction(), makeProcessing());
    const { ExtractionProcessingSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<ExtractionProcessingSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText(/send availability confirmation/i)).toBeInTheDocument();
    });
  });

  it("shows 'no processing snapshot' message when extraction exists but processing does not", async () => {
    mockFetch(makeExtraction(), null);
    const { ExtractionProcessingSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<ExtractionProcessingSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(
        screen.getByText(/no processing snapshot available/i)
      ).toBeInTheDocument();
    });
  });

  it("does not show raw prompts or internal confidence math", async () => {
    mockFetch(makeExtraction(), makeProcessing());
    const { ExtractionProcessingSection } = await import(
      "@/components/enquiries/EnquiryDetailDrawer"
    );
    render(<ExtractionProcessingSection enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.queryByText(/system_prompt/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/user_message/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/confidence_json/i)).not.toBeInTheDocument();
    });
  });
});
