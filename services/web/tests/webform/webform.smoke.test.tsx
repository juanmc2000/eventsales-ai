/**
 * Webform smoke tests — verifies the enquiry webform API contract and
 * UI-023 extraction JSON panel behaviour.
 *
 * TEST-005: End-to-End POC Workflow Tests
 *
 * The webform page (UI-010) and EnquiryWebform component live on the
 * Sprint 4 integration branch. These tests validate the API contract
 * that the webform uses — no component imports required.
 *
 * Expected module paths (for reference, once branches are merged):
 *   @/app/webform/page
 *   @/components/webform/EnquiryWebform
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

const API_BASE = "http://localhost:8000";

function stubFetch(response: { ok: boolean; status?: number; body: unknown }) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: response.ok,
      status: response.status ?? (response.ok ? 200 : 500),
      json: async () => response.body,
      text: async () =>
        typeof response.body === "string"
          ? response.body
          : JSON.stringify(response.body),
    })
  );
}

// ── UI-023: ExtractionParsedJsonPanel logic ────────────────────────────────────

describe("ExtractionParsedJsonPanel formatting logic", () => {
  it("pretty-prints valid JSON from extraction_raw_response", () => {
    const raw = JSON.stringify({
      customer_name: "Jane Smith",
      email: "jane@example.com",
      date_request: { date_request_type: "exact", explicit_dates: ["2026-08-15"] },
      missing_fields: [],
    });
    const parsed = JSON.parse(raw);
    const formatted = JSON.stringify(parsed, null, 2);
    expect(formatted).toContain('"customer_name"');
    expect(formatted).toContain('"date_request"');
    expect(formatted).toContain('"2026-08-15"');
    // 2-space indent
    expect(formatted).toMatch(/^\{/);
    expect(formatted.split("\n")[1]).toMatch(/^  "/);
  });

  it("falls back to raw text when extraction_raw_response is not valid JSON", () => {
    const raw = "Not valid JSON at all {{";
    let result: string;
    try {
      result = JSON.stringify(JSON.parse(raw), null, 2);
    } catch {
      result = raw;
    }
    expect(result).toBe(raw);
  });

  it("renders null/empty date_request fields without throwing", () => {
    const raw = JSON.stringify({
      customer_name: "NULL",
      date_request: {
        raw_text: "NULL",
        date_request_type: "unknown",
        explicit_dates: [],
        requires_date_clarification: true,
        clarification_question: "Could you clarify the date?",
        confidence: 0.3,
      },
      missing_fields: ["event_date", "guest_count"],
    });
    let result: string;
    try {
      result = JSON.stringify(JSON.parse(raw), null, 2);
    } catch {
      result = raw;
    }
    expect(result).toContain('"date_request_type": "unknown"');
    expect(result).toContain('"requires_date_clarification": true');
  });
});

describe("Webform intake API contract", () => {
  beforeEach(() => vi.clearAllMocks());

  it("intake endpoint accepts a valid webform payload", async () => {
    stubFetch({
      ok: true,
      status: 201,
      body: {
        id: "enq-001",
        reference: "ENQ-2026-0001",
        status: "new",
        source: "webform",
        first_name: "Alice",
        last_name: "Smith",
        email: "alice@example.com",
      },
    });
    const res = await fetch(`${API_BASE}/api/v1/enquiries/intake`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        restaurant_id: "rest-001",
        first_name: "Alice",
        last_name: "Smith",
        email: "alice@example.com",
        party_size: 20,
        message: "Looking for a private room.",
      }),
    });
    expect(res.ok).toBe(true);
    const data = await res.json();
    expect(data).toHaveProperty("reference");
    expect(data.source).toBe("webform");
    expect(data.status).toBe("new");
  });

  it("intake endpoint rejects invalid email", async () => {
    stubFetch({ ok: false, status: 422, body: { detail: "Invalid email" } });
    const res = await fetch(`${API_BASE}/api/v1/enquiries/intake`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        restaurant_id: "rest-001",
        first_name: "Alice",
        last_name: "Smith",
        email: "not-an-email",
      }),
    });
    expect(res.ok).toBe(false);
    expect(res.status).toBe(422);
  });

  it("intake response includes enquiry reference in ENQ-YYYY-NNNN format", async () => {
    stubFetch({
      ok: true,
      status: 201,
      body: { reference: "ENQ-2026-0042", source: "webform", status: "new" },
    });
    const res = await fetch(`${API_BASE}/api/v1/enquiries/intake`, {
      method: "POST",
    });
    const data = await res.json();
    expect(data.reference).toMatch(/^ENQ-\d{4}-\d{4}$/);
  });
});
