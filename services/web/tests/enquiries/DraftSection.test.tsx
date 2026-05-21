/**
 * DraftSection component tests.
 *
 * UI-012: Add Send Draft Email Action
 */
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/enquiries",
  useRouter: () => ({ push: vi.fn() }),
}));

const BASE_PROPS = {
  enquiryId: "enq-001",
  toEmail: "guest@example.com",
};

// ─── Fetch helpers ────────────────────────────────────────────────────────────

function mockFetchSequence(responses: Array<{ ok: boolean; status?: number; body: unknown }>) {
  let call = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(() => {
      const res = responses[call] ?? responses[responses.length - 1];
      call++;
      return Promise.resolve({
        ok: res.ok,
        status: res.status ?? (res.ok ? 200 : 500),
        json: async () => res.body,
        text: async () => (typeof res.body === "string" ? res.body : JSON.stringify(res.body)),
      });
    })
  );
}

function mockFetchDraftNotFound() {
  // GET draft → 404, no further calls
  mockFetchSequence([{ ok: false, status: 404, body: "Not Found" }]);
}

function mockFetchDraftExists() {
  // GET draft → 200 with draft body
  mockFetchSequence([
    {
      ok: true,
      status: 200,
      body: {
        enquiry_id: "enq-001",
        subject: "Re: Private Dining Enquiry",
        body: "Dear Guest, thank you for your enquiry...",
        generated_at: "2026-05-21T10:00:00Z",
      },
    },
  ]);
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("DraftSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows Coming Soon badge when no draft exists (initial render)", async () => {
    mockFetchDraftNotFound();
    const { DraftSection } = await import(
      "@/components/enquiries/DraftSection"
    );
    render(<DraftSection {...BASE_PROPS} />);
    // Coming Soon badge is visible immediately (before fetch resolves) since
    // the component starts in no-draft state.
    expect(screen.getByText(/coming soon/i)).toBeInTheDocument();
  });

  it("shows Generate Draft button when no draft exists", async () => {
    mockFetchDraftNotFound();
    const { DraftSection } = await import(
      "@/components/enquiries/DraftSection"
    );
    render(<DraftSection {...BASE_PROPS} />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /generate draft/i })).toBeInTheDocument();
    });
  });

  it("renders the draft body when a draft exists", async () => {
    mockFetchDraftExists();
    const { DraftSection } = await import(
      "@/components/enquiries/DraftSection"
    );
    render(<DraftSection {...BASE_PROPS} />);
    await waitFor(() => {
      expect(
        screen.getByText(/Dear Guest, thank you for your enquiry/i)
      ).toBeInTheDocument();
    });
  });

  it("renders the draft subject when a draft exists", async () => {
    mockFetchDraftExists();
    const { DraftSection } = await import(
      "@/components/enquiries/DraftSection"
    );
    render(<DraftSection {...BASE_PROPS} />);
    await waitFor(() => {
      expect(screen.getByText(/Re: Private Dining Enquiry/i)).toBeInTheDocument();
    });
  });

  it("shows Send Draft button when draft exists", async () => {
    mockFetchDraftExists();
    const { DraftSection } = await import(
      "@/components/enquiries/DraftSection"
    );
    render(<DraftSection {...BASE_PROPS} />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /send draft/i })).toBeInTheDocument();
    });
  });

  it("shows sent state after a successful send", async () => {
    mockFetchSequence([
      // GET draft
      {
        ok: true,
        status: 200,
        body: {
          enquiry_id: "enq-001",
          subject: "Re: Enquiry",
          body: "Hello...",
          generated_at: "2026-05-21T10:00:00Z",
        },
      },
      // POST send-draft
      { ok: true, status: 200, body: { message_id: "msg-123", status: "sent" } },
    ]);

    const { DraftSection } = await import(
      "@/components/enquiries/DraftSection"
    );
    render(<DraftSection {...BASE_PROPS} />);

    const sendBtn = await screen.findByRole("button", { name: /send draft/i });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(screen.getByText(/sent — test email only/i)).toBeInTheDocument();
    });
  });

  it("shows Gmail disabled state when send returns 503", async () => {
    mockFetchSequence([
      // GET draft
      {
        ok: true,
        status: 200,
        body: {
          enquiry_id: "enq-001",
          subject: "Re: Enquiry",
          body: "Hello...",
          generated_at: "2026-05-21T10:00:00Z",
        },
      },
      // POST send-draft → 503 (Gmail not configured)
      { ok: false, status: 503, body: "Service Unavailable" },
    ]);

    const { DraftSection } = await import(
      "@/components/enquiries/DraftSection"
    );
    render(<DraftSection {...BASE_PROPS} />);

    const sendBtn = await screen.findByRole("button", { name: /send draft/i });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(screen.getByText(/gmail not configured/i)).toBeInTheDocument();
    });
  });

  it("shows failed state and retry button when send returns a non-503 error", async () => {
    mockFetchSequence([
      // GET draft
      {
        ok: true,
        status: 200,
        body: {
          enquiry_id: "enq-001",
          subject: "Re: Enquiry",
          body: "Hello...",
          generated_at: "2026-05-21T10:00:00Z",
        },
      },
      // POST send-draft → 500
      { ok: false, status: 500, body: "Internal Server Error" },
    ]);

    const { DraftSection } = await import(
      "@/components/enquiries/DraftSection"
    );
    render(<DraftSection {...BASE_PROPS} />);

    const sendBtn = await screen.findByRole("button", { name: /send draft/i });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(screen.getByText(/send failed/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
    });
  });

  it("shows test-only disclaimer while send is in idle state", async () => {
    mockFetchDraftExists();
    const { DraftSection } = await import(
      "@/components/enquiries/DraftSection"
    );
    render(<DraftSection {...BASE_PROPS} />);
    await waitFor(() => {
      expect(
        screen.getByText(/test email only/i)
      ).toBeInTheDocument();
    });
  });
});
