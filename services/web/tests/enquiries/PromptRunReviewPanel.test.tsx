/**
 * PromptRunReviewPanel component tests.
 *
 * UI-021: Add Prompt Run Quality Review Panel
 */
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/enquiries",
  useRouter: () => ({ push: vi.fn() }),
}));

const PROMPT_RUN_ID = "pr-abc-123";

// ─── Fetch helpers ────────────────────────────────────────────────────────────

function mockFetchEmpty() {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [], total: 0 }),
    })
  );
}

function mockFetchWithReview() {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
            id: "rev-001",
            prompt_run_id: PROMPT_RUN_ID,
            reviewer_user_id: "admin",
            accuracy_score: 4.5,
            tone_fit_score: null,
            persona_fit_score: null,
            commercial_quality_score: null,
            completeness_score: null,
            hallucination_risk_score: null,
            ready_to_send: true,
            reviewer_notes: "Looks good.",
            created_at: "2026-05-28T10:00:00Z",
            updated_at: "2026-05-28T10:00:00Z",
          },
        ],
        total: 1,
      }),
    })
  );
}

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
      });
    })
  );
}

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("PromptRunReviewPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the Quality Review toggle button", async () => {
    mockFetchEmpty();
    const { PromptRunReviewPanel } = await import(
      "@/components/enquiries/PromptRunReviewPanel"
    );
    render(<PromptRunReviewPanel promptRunId={PROMPT_RUN_ID} />);
    expect(screen.getByText(/quality review/i)).toBeInTheDocument();
  });

  it("is collapsed by default — score fields not visible", async () => {
    mockFetchEmpty();
    const { PromptRunReviewPanel } = await import(
      "@/components/enquiries/PromptRunReviewPanel"
    );
    render(<PromptRunReviewPanel promptRunId={PROMPT_RUN_ID} />);
    expect(screen.queryByLabelText(/accuracy/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /save review/i })).not.toBeInTheDocument();
  });

  it("expands to show score fields when toggled", async () => {
    mockFetchEmpty();
    const { PromptRunReviewPanel } = await import(
      "@/components/enquiries/PromptRunReviewPanel"
    );
    render(<PromptRunReviewPanel promptRunId={PROMPT_RUN_ID} />);

    const toggle = screen.getByRole("button");
    fireEvent.click(toggle);

    await waitFor(() => {
      expect(screen.getByText("Accuracy")).toBeInTheDocument();
      expect(screen.getByText("Tone Fit")).toBeInTheDocument();
      expect(screen.getByText("Persona Fit")).toBeInTheDocument();
      expect(screen.getByText("Commercial Quality")).toBeInTheDocument();
      expect(screen.getByText("Completeness")).toBeInTheDocument();
      expect(screen.getByText("Hallucination Risk")).toBeInTheDocument();
    });
  });

  it("shows Save Review button when expanded", async () => {
    mockFetchEmpty();
    const { PromptRunReviewPanel } = await import(
      "@/components/enquiries/PromptRunReviewPanel"
    );
    render(<PromptRunReviewPanel promptRunId={PROMPT_RUN_ID} />);

    fireEvent.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /save review/i })).toBeInTheDocument();
    });
  });

  it("shows saved review summary when a review already exists", async () => {
    mockFetchWithReview();
    const { PromptRunReviewPanel } = await import(
      "@/components/enquiries/PromptRunReviewPanel"
    );
    render(<PromptRunReviewPanel promptRunId={PROMPT_RUN_ID} />);

    // Open the panel
    fireEvent.click(screen.getByRole("button"));

    await waitFor(() => {
      // "Review saved" appears in both the header subtitle and the badge
      expect(screen.getAllByText(/review saved/i).length).toBeGreaterThanOrEqual(1);
      // Reviewer notes text from saved review (may appear in summary + textarea)
      expect(screen.getAllByText(/looks good/i).length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows ready_to_send checkbox", async () => {
    mockFetchEmpty();
    const { PromptRunReviewPanel } = await import(
      "@/components/enquiries/PromptRunReviewPanel"
    );
    render(<PromptRunReviewPanel promptRunId={PROMPT_RUN_ID} />);

    fireEvent.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(screen.getByRole("checkbox")).toBeInTheDocument();
    });
  });

  it("shows Reviewer Notes textarea", async () => {
    mockFetchEmpty();
    const { PromptRunReviewPanel } = await import(
      "@/components/enquiries/PromptRunReviewPanel"
    );
    render(<PromptRunReviewPanel promptRunId={PROMPT_RUN_ID} />);

    fireEvent.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/optional notes/i)).toBeInTheDocument();
    });
  });

  it("shows saved review badge after a successful save", async () => {
    const savedReview = {
      id: "rev-new",
      prompt_run_id: PROMPT_RUN_ID,
      reviewer_user_id: null,
      accuracy_score: 3.5,
      tone_fit_score: null,
      persona_fit_score: null,
      commercial_quality_score: null,
      completeness_score: null,
      hallucination_risk_score: null,
      ready_to_send: null,
      reviewer_notes: null,
      created_at: "2026-05-28T11:00:00Z",
      updated_at: "2026-05-28T11:00:00Z",
    };

    mockFetchSequence([
      // GET reviews (load)
      { ok: true, status: 200, body: { items: [], total: 0 } },
      // POST review (save)
      { ok: true, status: 201, body: savedReview },
    ]);

    const { PromptRunReviewPanel } = await import(
      "@/components/enquiries/PromptRunReviewPanel"
    );
    render(<PromptRunReviewPanel promptRunId={PROMPT_RUN_ID} />);

    fireEvent.click(screen.getByRole("button"));

    const saveBtn = await screen.findByRole("button", { name: /save review/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(screen.getAllByText(/review saved/i).length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows error message when save fails", async () => {
    mockFetchSequence([
      // GET reviews
      { ok: true, status: 200, body: { items: [], total: 0 } },
      // POST review → 422
      { ok: false, status: 422, body: { detail: "accuracy_score must be between 0.0 and 5.0" } },
    ]);

    const { PromptRunReviewPanel } = await import(
      "@/components/enquiries/PromptRunReviewPanel"
    );
    render(<PromptRunReviewPanel promptRunId={PROMPT_RUN_ID} />);

    fireEvent.click(screen.getByRole("button"));

    const saveBtn = await screen.findByRole("button", { name: /save review/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(screen.getByText(/accuracy_score must be between/i)).toBeInTheDocument();
    });
  });
});
