"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type FormState = "idle" | "submitting" | "success" | "error";

type IntakeResult = {
  enquiry_id: string;
  reference: string;
  status: string;
  persona_name: string | null;
  recommended_minimum_spend: number | null;
  pricing_explanation: string | null;
  created_at: string;
};

export function EnquiryWebform() {
  const [formState, setFormState] = useState<FormState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<IntakeResult | null>(null);

  const [restaurantId, setRestaurantId] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [partySize, setPartySize] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [eventType, setEventType] = useState("");
  const [message, setMessage] = useState("");
  const [consent, setConsent] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!consent) return;
    setFormState("submitting");
    setErrorMessage(null);
    try {
      const body: Record<string, unknown> = {
        restaurant_id: restaurantId || "00000000-0000-0000-0000-000000000001",
        first_name: firstName,
        last_name: lastName,
        email,
        source: "webform",
      };
      if (phone) body.phone = phone;
      if (partySize) body.party_size = parseInt(partySize, 10);
      if (eventDate) body.event_date = eventDate;
      if (eventType) body.event_type = eventType;
      if (message) body.message = message;

      const res = await fetch(`${API_BASE}/api/v1/enquiries/intake`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `HTTP ${res.status}`);
      }
      const data: IntakeResult = await res.json();
      setResult(data);
      setFormState("success");
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "An error occurred.");
      setFormState("error");
    }
  }

  if (formState === "success" && result) {
    return (
      <div data-testid="webform-success" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ padding: 20, borderRadius: 12, background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.3)" }}>
          <p style={{ fontWeight: 700, color: "var(--text-primary)" }}>Enquiry submitted successfully</p>
          <p style={{ fontFamily: "monospace", color: "var(--brand-purple)", marginTop: 6 }}>{result.reference}</p>
          {result.persona_name && (
            <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 8 }}>
              Assigned persona: <strong>{result.persona_name}</strong>
            </p>
          )}
          {result.recommended_minimum_spend != null && (
            <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              Recommended minimum spend: <strong>£{result.recommended_minimum_spend.toLocaleString()}</strong>
            </p>
          )}
          {result.pricing_explanation && (
            <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>{result.pricing_explanation}</p>
          )}
        </div>
        <Button variant="secondary" size="sm" onClick={() => { setFormState("idle"); setResult(null); }}>
          Submit another enquiry
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} data-testid="enquiry-webform" style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 640 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div>
          <label style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", display: "block", marginBottom: 6 }}>
            First Name <span style={{ color: "var(--brand-orange)" }}>*</span>
          </label>
          <input
            required
            type="text"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 14, boxSizing: "border-box" }}
          />
        </div>
        <div>
          <label style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", display: "block", marginBottom: 6 }}>
            Last Name <span style={{ color: "var(--brand-orange)" }}>*</span>
          </label>
          <input
            required
            type="text"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 14, boxSizing: "border-box" }}
          />
        </div>
      </div>

      <div>
        <label style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", display: "block", marginBottom: 6 }}>
          Email Address <span style={{ color: "var(--brand-orange)" }}>*</span>
        </label>
        <input
          required
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 14, boxSizing: "border-box" }}
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div>
          <label style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", display: "block", marginBottom: 6 }}>Event Date</label>
          <input
            type="date"
            value={eventDate}
            onChange={(e) => setEventDate(e.target.value)}
            style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 14, boxSizing: "border-box" }}
          />
        </div>
        <div>
          <label style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", display: "block", marginBottom: 6 }}>Party Size</label>
          <input
            type="number"
            min={1}
            value={partySize}
            onChange={(e) => setPartySize(e.target.value)}
            style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 14, boxSizing: "border-box" }}
          />
        </div>
      </div>

      <div>
        <label style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", display: "block", marginBottom: 6 }}>Message</label>
        <textarea
          rows={4}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 14, resize: "vertical", boxSizing: "border-box" }}
        />
      </div>

      <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
        <input
          type="checkbox"
          id="consent"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          style={{ marginTop: 2 }}
        />
        <label htmlFor="consent" style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.5 }}>
          I consent to my enquiry being stored and processed for the purpose of this event booking.
        </label>
      </div>

      {formState === "error" && errorMessage && (
        <div style={{ padding: "12px 16px", borderRadius: 8, background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.3)", fontSize: 13, color: "#dc2626" }}>
          {errorMessage}
        </div>
      )}

      <Button
        type="submit"
        variant="primary"
        loading={formState === "submitting"}
        disabled={!consent || formState === "submitting"}
      >
        Submit Enquiry
      </Button>
    </form>
  );
}
