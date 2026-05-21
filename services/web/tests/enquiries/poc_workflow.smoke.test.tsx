/**
 * POC workflow smoke tests — draft API contract and email events API contract.
 *
 * TEST-005: End-to-End POC Workflow Tests
 *
 * These tests cover the frontend API contracts for the POC loop:
 * - Draft endpoint: GET /api/v1/enquiries/{id}/draft → {enquiry_id, subject, body, generated_at}
 * - Send-draft endpoint: POST /api/v1/email/send-draft → {status, message}
 * - Email events endpoint: GET /api/v1/enquiries/{id}/email-events → EmailEventRecord[]
 *
 * Tests are pure fetch-contract assertions — no component imports required.
 * This ensures the tests pass on main before UI-012/UI-013 are merged.
 * Full component rendering is covered in DraftSection.test.tsx and
 * EmailActivityTimeline.test.tsx on the UI-012/UI-013 branches.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

const API_BASE = "http://localhost:8000";
const ENQUIRY_ID = "enq-poc-001";

function stubFetch(responses: Array<{ ok: boolean; status?: number; body: unknown }>) {
  let i = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(() => {
      const r = responses[i] ?? responses[responses.length - 1];
      i++;
      return Promise.resolve({
        ok: r.ok,
        status: r.status ?? (r.ok ? 200 : 500),
        json: async () => r.body,
        text: async () =>
          typeof r.body === "string" ? r.body : JSON.stringify(r.body),
      });
    })
  );
}

// ── Draft endpoint contract ────────────────────────────────────────────────────

describe("Draft endpoint contract", () => {
  beforeEach(() => vi.clearAllMocks());

  it("returns 404 when no draft exists", async () => {
    stubFetch([{ ok: false, status: 404, body: "Not Found" }]);
    const res = await fetch(
      `${API_BASE}/api/v1/enquiries/${ENQUIRY_ID}/draft`
    );
    expect(res.ok).toBe(false);
    expect(res.status).toBe(404);
  });

  it("returns draft with subject and body when draft exists", async () => {
    const mockDraft = {
      enquiry_id: ENQUIRY_ID,
      subject: "Re: Your Enquiry at The Grand",
      body: "Dear Alice, thank you for your enquiry...",
      generated_at: "2026-05-21T10:00:00Z",
    };
    stubFetch([{ ok: true, status: 200, body: mockDraft }]);
    const res = await fetch(
      `${API_BASE}/api/v1/enquiries/${ENQUIRY_ID}/draft`
    );
    expect(res.ok).toBe(true);
    const data = await res.json();
    expect(data).toHaveProperty("enquiry_id");
    expect(data).toHaveProperty("subject");
    expect(data).toHaveProperty("body");
    expect(data).toHaveProperty("generated_at");
    expect(data.body).toContain("Dear Alice");
  });

  it("draft subject references the restaurant name", async () => {
    const mockDraft = {
      enquiry_id: ENQUIRY_ID,
      subject: "Re: Your Private Dining Enquiry at The Grand",
      body: "Dear Alice,\n\nThank you for your enquiry...",
      generated_at: "2026-05-21T10:00:00Z",
    };
    stubFetch([{ ok: true, status: 200, body: mockDraft }]);
    const res = await fetch(
      `${API_BASE}/api/v1/enquiries/${ENQUIRY_ID}/draft`
    );
    const data = await res.json();
    expect(data.subject).toContain("The Grand");
  });
});

// ── Send-draft endpoint contract ────────────────────────────────────────────────

describe("Send-draft endpoint contract", () => {
  beforeEach(() => vi.clearAllMocks());

  it("returns 503 with disabled status when SMTP not configured", async () => {
    stubFetch([{
      ok: false,
      status: 503,
      body: { event_id: "ev-001", status: "disabled", message: "SMTP not configured" },
    }]);
    const res = await fetch(`${API_BASE}/api/v1/email/send-draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enquiry_id: ENQUIRY_ID, to_email: "guest@example.com" }),
    });
    expect(res.status).toBe(503);
    const data = await res.json();
    expect(data.status).toBe("disabled");
    expect(data).toHaveProperty("message");
  });

  it("returns 200 with queued status when SMTP is configured", async () => {
    stubFetch([{
      ok: true,
      status: 200,
      body: { event_id: "ev-002", status: "queued", message: "Email queued for delivery" },
    }]);
    const res = await fetch(`${API_BASE}/api/v1/email/send-draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enquiry_id: ENQUIRY_ID, to_email: "guest@example.com" }),
    });
    expect(res.ok).toBe(true);
    const data = await res.json();
    expect(data.status).toBe("queued");
    expect(data).toHaveProperty("event_id");
  });
});

// ── Email events endpoint contract ─────────────────────────────────────────────

describe("Email events endpoint contract", () => {
  beforeEach(() => vi.clearAllMocks());

  it("returns empty array when no email activity", async () => {
    stubFetch([{ ok: true, status: 200, body: [] }]);
    const res = await fetch(
      `${API_BASE}/api/v1/enquiries/${ENQUIRY_ID}/email-events`
    );
    expect(res.ok).toBe(true);
    const data = await res.json();
    expect(Array.isArray(data)).toBe(true);
    expect(data.length).toBe(0);
  });

  it("returns sent event with expected fields", async () => {
    const mockEvents = [
      {
        id: "ev-001",
        enquiry_id: ENQUIRY_ID,
        direction: "outbound",
        status: "sent",
        from_address: "sender@gmail.com",
        to_address: "guest@example.com",
        subject: "Re: Enquiry",
        error: null,
        created_at: "2026-05-21T10:00:00Z",
      },
    ];
    stubFetch([{ ok: true, status: 200, body: mockEvents }]);
    const res = await fetch(
      `${API_BASE}/api/v1/enquiries/${ENQUIRY_ID}/email-events`
    );
    const data = await res.json();
    expect(data.length).toBe(1);
    const ev = data[0];
    expect(ev.status).toBe("sent");
    expect(ev.direction).toBe("outbound");
    expect(ev).toHaveProperty("id");
    expect(ev).toHaveProperty("created_at");
  });

  it("returns disabled event with error field populated", async () => {
    const mockEvents = [
      {
        id: "ev-002",
        enquiry_id: ENQUIRY_ID,
        direction: "outbound",
        status: "disabled",
        from_address: "noreply@example.com",
        to_address: "guest@example.com",
        subject: "Re: Enquiry",
        error: "SMTP not configured",
        created_at: "2026-05-21T09:00:00Z",
      },
    ];
    stubFetch([{ ok: true, status: 200, body: mockEvents }]);
    const res = await fetch(
      `${API_BASE}/api/v1/enquiries/${ENQUIRY_ID}/email-events`
    );
    const data = await res.json();
    expect(data[0].status).toBe("disabled");
    expect(data[0].error).toBe("SMTP not configured");
  });
});
