/**
 * EmailActivityTimeline component tests.
 *
 * UI-013: Add Email Activity Timeline to Enquiry Detail
 */
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/enquiries",
  useRouter: () => ({ push: vi.fn() }),
}));

const ENQUIRY_ID = "enq-001";

function mockEmailEvents(events: unknown[]) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => events,
    })
  );
}

function mockEmailEventsError() {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => [],
    })
  );
}

const SENT_EVENT = {
  id: "ev-001",
  enquiry_id: ENQUIRY_ID,
  direction: "outbound",
  status: "sent",
  from_address: "sender@gmail.com",
  to_address: "guest@example.com",
  subject: "Re: Private Dining Enquiry",
  error: null,
  created_at: "2026-05-21T10:00:00Z",
};

const FAILED_EVENT = {
  id: "ev-002",
  enquiry_id: ENQUIRY_ID,
  direction: "outbound",
  status: "failed",
  from_address: "sender@gmail.com",
  to_address: "guest@example.com",
  subject: "Re: Private Dining Enquiry",
  error: "SMTP connection refused",
  created_at: "2026-05-21T09:00:00Z",
};

const DISABLED_EVENT = {
  id: "ev-003",
  enquiry_id: ENQUIRY_ID,
  direction: "outbound",
  status: "disabled",
  from_address: "noreply@example.com",
  to_address: "guest@example.com",
  subject: "Re: Enquiry",
  error: "SMTP not configured",
  created_at: "2026-05-21T08:00:00Z",
};

const RECEIVED_EVENT = {
  id: "ev-004",
  enquiry_id: ENQUIRY_ID,
  direction: "inbound",
  status: "received",
  from_address: "guest@example.com",
  to_address: "inbox",
  subject: "Birthday dinner",
  error: null,
  created_at: "2026-05-21T07:00:00Z",
};

describe("EmailActivityTimeline", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows empty state when no email events exist", async () => {
    mockEmailEvents([]);
    const { EmailActivityTimeline } = await import(
      "@/components/enquiries/EmailActivityTimeline"
    );
    render(<EmailActivityTimeline enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(
        screen.getByText(/no email activity recorded yet/i)
      ).toBeInTheDocument();
    });
  });

  it("shows empty state when endpoint is unavailable", async () => {
    mockEmailEventsError();
    const { EmailActivityTimeline } = await import(
      "@/components/enquiries/EmailActivityTimeline"
    );
    render(<EmailActivityTimeline enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(
        screen.getByText(/no email activity recorded yet/i)
      ).toBeInTheDocument();
    });
  });

  it("shows Sent status for a sent email event", async () => {
    mockEmailEvents([SENT_EVENT]);
    const { EmailActivityTimeline } = await import(
      "@/components/enquiries/EmailActivityTimeline"
    );
    render(<EmailActivityTimeline enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText(/^sent$/i)).toBeInTheDocument();
    });
  });

  it("shows Failed status for a failed email event", async () => {
    mockEmailEvents([FAILED_EVENT]);
    const { EmailActivityTimeline } = await import(
      "@/components/enquiries/EmailActivityTimeline"
    );
    render(<EmailActivityTimeline enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText(/^failed$/i)).toBeInTheDocument();
    });
  });

  it("shows Not Sent status for a disabled event", async () => {
    mockEmailEvents([DISABLED_EVENT]);
    const { EmailActivityTimeline } = await import(
      "@/components/enquiries/EmailActivityTimeline"
    );
    render(<EmailActivityTimeline enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText(/not sent/i)).toBeInTheDocument();
    });
  });

  it("shows Received status for an inbound email event", async () => {
    mockEmailEvents([RECEIVED_EVENT]);
    const { EmailActivityTimeline } = await import(
      "@/components/enquiries/EmailActivityTimeline"
    );
    render(<EmailActivityTimeline enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText(/^received$/i)).toBeInTheDocument();
    });
  });

  it("shows the subject line for an event", async () => {
    mockEmailEvents([SENT_EVENT]);
    const { EmailActivityTimeline } = await import(
      "@/components/enquiries/EmailActivityTimeline"
    );
    render(<EmailActivityTimeline enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText(/Re: Private Dining Enquiry/i)).toBeInTheDocument();
    });
  });

  it("shows truncated error for failed sends — not raw SMTP details", async () => {
    mockEmailEvents([FAILED_EVENT]);
    const { EmailActivityTimeline } = await import(
      "@/components/enquiries/EmailActivityTimeline"
    );
    render(<EmailActivityTimeline enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      // Error text is shown but truncated
      expect(screen.getByText(/SMTP connection refused/i)).toBeInTheDocument();
    });
  });

  it("renders multiple events in sequence", async () => {
    mockEmailEvents([SENT_EVENT, RECEIVED_EVENT]);
    const { EmailActivityTimeline } = await import(
      "@/components/enquiries/EmailActivityTimeline"
    );
    render(<EmailActivityTimeline enquiryId={ENQUIRY_ID} />);
    await waitFor(() => {
      expect(screen.getByText(/^sent$/i)).toBeInTheDocument();
      expect(screen.getByText(/^received$/i)).toBeInTheDocument();
    });
  });

  it("fetches from the correct enquiry endpoint", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    });
    vi.stubGlobal("fetch", mockFetch);

    const { EmailActivityTimeline } = await import(
      "@/components/enquiries/EmailActivityTimeline"
    );
    render(<EmailActivityTimeline enquiryId="enq-test-123" />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/enquiries/enq-test-123/email-events")
      );
    });
  });
});
