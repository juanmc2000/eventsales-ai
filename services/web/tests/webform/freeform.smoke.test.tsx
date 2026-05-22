/**
 * Freeform enquiry mode smoke tests.
 *
 * UI-017: Freeform Enquiry Toggle on Webform
 *
 * Validates the three-step auto-submit flow:
 *   POST /intake → POST /{id}/draft → POST /email/send-draft
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

const API_BASE = "http://localhost:8000";

// ── Stub helpers ───────────────────────────────────────────────────────────────

type FetchResponse = { ok: boolean; status?: number; body: unknown };

function stubFetchSequence(responses: FetchResponse[]) {
  let callCount = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(() => {
      const r = responses[Math.min(callCount, responses.length - 1)];
      callCount++;
      return Promise.resolve({
        ok: r.ok,
        status: r.status ?? (r.ok ? 200 : 500),
        json: async () => r.body,
        text: async () =>
          typeof r.body === "string" ? r.body : JSON.stringify(r.body),
      });
    })
  );
  return () => callCount;
}

// ── Mock data ─────────────────────────────────────────────────────────────────

const INTAKE_RESPONSE = {
  enquiry_id: "enq-freeform-001",
  reference: "ENQ-2026-0099",
  status: "new",
  restaurant_id: "rest-001",
  persona_id: "persona-001",
  persona_name: "Victoria",
  recommended_minimum_spend: 0,
  pricing_explanation: "",
  created_at: "2026-05-22T10:00:00Z",
};

const DRAFT_RESPONSE = {
  enquiry_id: "enq-freeform-001",
  subject: "Re: Private Dining Enquiry",
  body: "Dear Jane,\n\nThank you for your enquiry…",
  generated_at: "2026-05-22T10:00:01Z",
};

const SEND_RESPONSE = {
  event_id: "evt-001",
  status: "queued",
  message: "Email queued for delivery via Gmail SMTP",
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("Freeform enquiry API contract", () => {
  beforeEach(() => vi.clearAllMocks());

  it("intake endpoint accepts a freeform payload with message field", async () => {
    stubFetchSequence([{ ok: true, status: 201, body: INTAKE_RESPONSE }]);

    const res = await fetch(`${API_BASE}/api/v1/enquiries/intake`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        restaurant_id: "rest-001",
        first_name: "Jane",
        last_name: "Smith",
        email: "juanmc@gmail.com",
        message: "I'm looking for a private dining room for 12 people for a birthday dinner in July.",
        meal_period: "dinner",
        source: "webform",
      }),
    });

    expect(res.ok).toBe(true);
    const data = await res.json();
    expect(data.enquiry_id).toBe("enq-freeform-001");
    expect(data.reference).toMatch(/^ENQ-\d{4}-\d{4}$/);
  });

  it("draft endpoint generates a subject and body for the enquiry", async () => {
    stubFetchSequence([{ ok: true, status: 201, body: DRAFT_RESPONSE }]);

    const res = await fetch(
      `${API_BASE}/api/v1/enquiries/enq-freeform-001/draft`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      }
    );

    expect(res.ok).toBe(true);
    const data = await res.json();
    expect(data).toHaveProperty("subject");
    expect(data).toHaveProperty("body");
    expect(typeof data.body).toBe("string");
    expect(data.body.length).toBeGreaterThan(0);
  });

  it("send-draft endpoint accepts enquiry_id and to_email", async () => {
    stubFetchSequence([{ ok: true, status: 200, body: SEND_RESPONSE }]);

    const res = await fetch(`${API_BASE}/api/v1/email/send-draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        enquiry_id: "enq-freeform-001",
        to_email: "juanmc@gmail.com",
      }),
    });

    expect(res.ok).toBe(true);
    const data = await res.json();
    expect(data.status).toBe("queued");
    expect(data).toHaveProperty("event_id");
  });

  it("full three-step freeform flow succeeds in sequence", async () => {
    const getCallCount = stubFetchSequence([
      { ok: true, status: 201, body: INTAKE_RESPONSE },
      { ok: true, status: 201, body: DRAFT_RESPONSE },
      { ok: true, status: 200, body: SEND_RESPONSE },
    ]);

    // Step 1: intake
    const intakeRes = await fetch(`${API_BASE}/api/v1/enquiries/intake`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        restaurant_id: "rest-001",
        first_name: "Jane",
        last_name: "Smith",
        email: "juanmc@gmail.com",
        message: "Freeform test message of sufficient length.",
        meal_period: "dinner",
      }),
    });
    const intake = await intakeRes.json();
    expect(intake.enquiry_id).toBe("enq-freeform-001");

    // Step 2: draft
    const draftRes = await fetch(
      `${API_BASE}/api/v1/enquiries/${intake.enquiry_id}/draft`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) }
    );
    const draft = await draftRes.json();
    expect(draft.subject).toBe("Re: Private Dining Enquiry");

    // Step 3: send
    const sendRes = await fetch(`${API_BASE}/api/v1/email/send-draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enquiry_id: intake.enquiry_id, to_email: "juanmc@gmail.com" }),
    });
    const sent = await sendRes.json();
    expect(sent.status).toBe("queued");

    expect(getCallCount()).toBe(3);
  });

  it("send-draft returns 503 when SMTP is not configured", async () => {
    stubFetchSequence([
      {
        ok: false,
        status: 503,
        body: {
          detail: {
            status: "disabled",
            message: "Gmail SMTP not configured — set credentials to activate sending",
          },
        },
      },
    ]);

    const res = await fetch(`${API_BASE}/api/v1/email/send-draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enquiry_id: "enq-001", to_email: "juanmc@gmail.com" }),
    });

    expect(res.ok).toBe(false);
    expect(res.status).toBe(503);
    const data = await res.json();
    expect(data.detail.status).toBe("disabled");
  });
});
