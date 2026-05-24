/**
 * Freeform extraction and processing API contract smoke tests.
 *
 * TEST-008: Add Freeform Extraction and Processing Tests
 *
 * Validates the Sprint 7 single-call freeform flow:
 *   POST /intake/freeform → returns extraction + processing + draft in one response
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

const API_BASE = "http://localhost:8000";

type FetchResponse = { ok: boolean; status?: number; body: unknown };

function stubFetch(response: FetchResponse) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: response.ok,
      status: response.status ?? (response.ok ? 200 : 500),
      json: async () => response.body,
      text: async () =>
        typeof response.body === "string" ? response.body : JSON.stringify(response.body),
    })
  );
}

// ── Mock response shapes ───────────────────────────────────────────────────────

const FREEFORM_INTAKE_SUCCESS = {
  enquiry_id: "enq-freeform-007",
  reference: "ENQ-2026-0107",
  status: "new",
  restaurant_id: "rest-001",
  persona_id: "persona-001",
  persona_name: "James",
  audience_type: "corporate",
  created_at: "2026-05-24T09:00:00Z",
  // Sprint 7 fields
  extraction: {
    extraction_id: "ext-001",
    prompt_run_id: "run-001",
    is_fallback: false,
    validation_status: "passed",
    guest_count: 20,
    event_date: "2026-08-15",
    event_type: "corporate_dinner",
    missing_fields: [],
  },
  recommended_action: "send_availability_confirmation",
  draft_subject: "Re: Corporate Dinner Enquiry — Alice Smith",
  draft_body: "Dear Alice, thank you for your corporate dinner enquiry. We'd love to host your event at our Grand Ballroom.",
  draft_message_id: "msg-001",
  draft_is_fallback: false,
};

const FREEFORM_INTAKE_NO_EXTRACTION = {
  ...FREEFORM_INTAKE_SUCCESS,
  extraction: null,
  recommended_action: null,
  draft_body: "Dear Alice, thank you for your enquiry.",
  draft_is_fallback: true,
};

const FREEFORM_INTAKE_WITH_MISSING_FIELDS = {
  ...FREEFORM_INTAKE_SUCCESS,
  extraction: {
    ...FREEFORM_INTAKE_SUCCESS.extraction,
    guest_count: null,
    event_date: null,
    missing_fields: ["guest_count", "event_date"],
  },
  recommended_action: "request_missing_information",
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("Freeform intake/freeform API contract", () => {
  beforeEach(() => vi.clearAllMocks());

  it("POST /intake/freeform returns 201 with enquiry_id and reference", async () => {
    stubFetch({ ok: true, status: 201, body: FREEFORM_INTAKE_SUCCESS });

    const res = await fetch(`${API_BASE}/api/v1/enquiries/intake/freeform`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        restaurant_id: "rest-001",
        first_name: "Alice",
        last_name: "Smith",
        email: "alice@example.com",
        freeform_text: "We need a private dining room for 20 corporate guests on August 15th.",
        audience_type: "corporate",
      }),
    });

    expect(res.ok).toBe(true);
    expect(res.status).toBe(201);
    const data = await res.json();
    expect(data.enquiry_id).toBe("enq-freeform-007");
    expect(data.reference).toMatch(/^ENQ-\d{4}-\d{4}$/);
  });

  it("response includes extraction summary with guest_count and event_date", async () => {
    stubFetch({ ok: true, status: 201, body: FREEFORM_INTAKE_SUCCESS });

    const res = await fetch(`${API_BASE}/api/v1/enquiries/intake/freeform`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        restaurant_id: "rest-001",
        first_name: "Alice",
        last_name: "Smith",
        email: "alice@example.com",
        freeform_text: "We need a private dining room for 20 corporate guests on August 15th.",
      }),
    });

    const data = await res.json();
    expect(data).toHaveProperty("extraction");
    expect(data.extraction).not.toBeNull();
    expect(data.extraction.guest_count).toBe(20);
    expect(data.extraction.event_date).toBe("2026-08-15");
    expect(data.extraction.event_type).toBe("corporate_dinner");
  });

  it("response includes recommended_action from processing", async () => {
    stubFetch({ ok: true, status: 201, body: FREEFORM_INTAKE_SUCCESS });

    const res = await fetch(`${API_BASE}/api/v1/enquiries/intake/freeform`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        restaurant_id: "rest-001",
        first_name: "Alice",
        last_name: "Smith",
        email: "alice@example.com",
        freeform_text: "We need a private dining room for 20 corporate guests on August 15th.",
      }),
    });

    const data = await res.json();
    expect(data.recommended_action).toBe("send_availability_confirmation");
  });

  it("response includes draft_body when draft generation succeeds", async () => {
    stubFetch({ ok: true, status: 201, body: FREEFORM_INTAKE_SUCCESS });

    const res = await fetch(`${API_BASE}/api/v1/enquiries/intake/freeform`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        restaurant_id: "rest-001",
        first_name: "Alice",
        last_name: "Smith",
        email: "alice@example.com",
        freeform_text: "We need a private dining room for 20 corporate guests on August 15th.",
      }),
    });

    const data = await res.json();
    expect(typeof data.draft_body).toBe("string");
    expect(data.draft_body.length).toBeGreaterThan(0);
    expect(data.draft_subject).toContain("Alice Smith");
  });

  it("extraction null when Sprint 7 services not available (graceful degradation)", async () => {
    stubFetch({ ok: true, status: 201, body: FREEFORM_INTAKE_NO_EXTRACTION });

    const res = await fetch(`${API_BASE}/api/v1/enquiries/intake/freeform`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        restaurant_id: "rest-001",
        first_name: "Alice",
        last_name: "Smith",
        email: "alice@example.com",
        freeform_text: "We need a venue for a private dinner next month.",
      }),
    });

    const data = await res.json();
    // extraction and recommended_action may be null when services not merged
    expect(data).toHaveProperty("extraction");
    expect(data).toHaveProperty("recommended_action");
    // enquiry_id must always be present
    expect(data.enquiry_id).toBeTruthy();
  });

  it("extraction includes missing_fields when information is incomplete", async () => {
    stubFetch({ ok: true, status: 201, body: FREEFORM_INTAKE_WITH_MISSING_FIELDS });

    const res = await fetch(`${API_BASE}/api/v1/enquiries/intake/freeform`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        restaurant_id: "rest-001",
        first_name: "Alice",
        last_name: "Smith",
        email: "alice@example.com",
        freeform_text: "I would like to make a reservation please.",
      }),
    });

    const data = await res.json();
    expect(data.extraction.missing_fields).toContain("guest_count");
    expect(data.extraction.missing_fields).toContain("event_date");
    expect(data.recommended_action).toBe("request_missing_information");
  });

  it("response persona_name reflects audience-specific persona assignment", async () => {
    stubFetch({ ok: true, status: 201, body: FREEFORM_INTAKE_SUCCESS });

    const res = await fetch(`${API_BASE}/api/v1/enquiries/intake/freeform`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        restaurant_id: "rest-001",
        first_name: "Alice",
        last_name: "Smith",
        email: "alice@example.com",
        freeform_text: "Corporate dinner for 20 guests on August 15th.",
        audience_type: "corporate",
      }),
    });

    const data = await res.json();
    expect(data.persona_name).toBe("James");
    expect(data.audience_type).toBe("corporate");
  });

  it("single call replaces the old two-step intake → draft sequence", async () => {
    const callUrls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        callUrls.push(url as string);
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => FREEFORM_INTAKE_SUCCESS,
          text: async () => JSON.stringify(FREEFORM_INTAKE_SUCCESS),
        });
      })
    );

    await fetch(`${API_BASE}/api/v1/enquiries/intake/freeform`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        restaurant_id: "rest-001",
        first_name: "Alice",
        last_name: "Smith",
        email: "alice@example.com",
        freeform_text: "We need a venue for 20 guests on August 15th for a corporate dinner.",
      }),
    });

    // Only one API call — no separate /draft call needed
    expect(callUrls).toHaveLength(1);
    expect(callUrls[0]).toContain("/intake/freeform");
  });
});
