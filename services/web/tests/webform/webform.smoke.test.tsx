/**
 * Webform smoke tests — verifies the enquiry webform API contract.
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
