"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Card } from "@/components/layout/Card";
import type { Restaurant, RestaurantListOut } from "@/lib/types/restaurant";
import type { EnquiryIntakeOut } from "@/lib/types/enquiry";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const EVENT_TYPE_OPTIONS = [
  { value: "", label: "Select event type" },
  { value: "birthday", label: "Birthday" },
  { value: "corporate", label: "Corporate" },
  { value: "wedding", label: "Wedding" },
  { value: "private_dining", label: "Private Dining" },
  { value: "anniversary", label: "Anniversary" },
  { value: "other", label: "Other" },
];

const MEAL_PERIOD_OPTIONS = [
  { value: "dinner", label: "Dinner" },
  { value: "lunch", label: "Lunch" },
  { value: "breakfast", label: "Breakfast" },
];

type FormState = {
  restaurant_id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  company_name: string;
  event_date: string;
  event_type: string;
  party_size: string;
  meal_period: string;
  budget_indication: string;
  preferred_area: string;
  dietary_requirements: string;
  special_requests: string;
  message: string;
  consent: boolean;
};

const EMPTY: FormState = {
  restaurant_id: "",
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  company_name: "",
  event_date: "",
  event_type: "",
  party_size: "",
  meal_period: "dinner",
  budget_indication: "",
  preferred_area: "",
  dietary_requirements: "",
  special_requests: "",
  message: "",
  consent: false,
};

// ── Section heading ────────────────────────────────────────────────────────────
function SectionHeading({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <h3 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
        {title}
      </h3>
      {subtitle && (
        <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>{subtitle}</p>
      )}
    </div>
  );
}

// ── Field row (two columns on wide screens) ────────────────────────────────────
function FieldRow({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
        gap: 16,
      }}
    >
      {children}
    </div>
  );
}

// ── Divider ────────────────────────────────────────────────────────────────────
function Divider() {
  return (
    <hr
      style={{
        border: "none",
        borderTop: "1px solid var(--border)",
        margin: "24px 0",
      }}
    />
  );
}

// ── Success state ──────────────────────────────────────────────────────────────
function SuccessPanel({ result, restaurantName }: { result: EnquiryIntakeOut; restaurantName: string }) {
  return (
    <Card padding="lg">
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Icon + heading */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: "50%",
              background: "rgba(22,166,106,0.12)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 6L9 17l-5-5" />
            </svg>
          </div>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
              Enquiry Submitted
            </h2>
            <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 2 }}>
              Successfully created for {restaurantName}
            </p>
          </div>
        </div>

        {/* Reference badge */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "10px 16px",
            borderRadius: 10,
            background: "rgba(109,61,245,0.06)",
            border: "1px solid rgba(109,61,245,0.15)",
          }}
        >
          <span style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 500 }}>Reference</span>
          <span
            style={{
              fontFamily: "monospace",
              fontSize: 15,
              fontWeight: 700,
              color: "var(--brand-purple)",
            }}
          >
            {result.reference}
          </span>
        </div>

        {/* Context grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: 12,
          }}
        >
          {result.persona_name && (
            <div
              style={{
                padding: "12px 16px",
                borderRadius: 10,
                background: "var(--surface-soft)",
                border: "1px solid var(--border)",
              }}
            >
              <p style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>
                Assigned Persona
              </p>
              <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", marginTop: 4 }}>
                {result.persona_name}
              </p>
            </div>
          )}
          <div
            style={{
              padding: "12px 16px",
              borderRadius: 10,
              background: "var(--surface-soft)",
              border: "1px solid var(--border)",
            }}
          >
            <p style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>
              Recommended Min. Spend
            </p>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--brand-purple)", marginTop: 4 }}>
              {result.recommended_minimum_spend > 0
                ? `£${Math.round(result.recommended_minimum_spend).toLocaleString()}`
                : "No rule matched"}
            </p>
          </div>
          <div
            style={{
              padding: "12px 16px",
              borderRadius: 10,
              background: "var(--surface-soft)",
              border: "1px solid var(--border)",
            }}
          >
            <p style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>
              Status
            </p>
            <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", marginTop: 4, textTransform: "capitalize" }}>
              {result.status}
            </p>
          </div>
        </div>

        {/* Pricing explanation */}
        {result.pricing_explanation && (
          <p style={{ fontSize: 12, color: "var(--text-muted)", lineHeight: 1.6 }}>
            {result.pricing_explanation}
          </p>
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Link href="/enquiries">
            <Button variant="primary" size="md">
              View All Enquiries
            </Button>
          </Link>
          <Button
            variant="secondary"
            size="md"
            onClick={() => window.location.reload()}
          >
            Submit Another
          </Button>
        </div>
      </div>
    </Card>
  );
}

// ── Main form component ────────────────────────────────────────────────────────
export function EnquiryWebform() {
  const [form, setForm] = useState<FormState>(EMPTY);
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [result, setResult] = useState<EnquiryIntakeOut | null>(null);

  // Load restaurants for the dropdown
  useEffect(() => {
    fetch(`${API_BASE}/api/v1/restaurants?limit=100`)
      .then((r) => r.json())
      .then((d: RestaurantListOut) => setRestaurants(d.items ?? []))
      .catch(() => {});
  }, []);

  function set(key: keyof FormState, value: string | boolean) {
    setForm((prev) => ({ ...prev, [key]: value }));
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }));
  }

  function validate(): boolean {
    const next: Partial<Record<keyof FormState, string>> = {};
    if (!form.restaurant_id) next.restaurant_id = "Please select a venue.";
    if (!form.first_name.trim()) next.first_name = "First name is required.";
    if (!form.last_name.trim()) next.last_name = "Last name is required.";
    if (!form.email.trim()) next.email = "Email address is required.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
      next.email = "Please enter a valid email address.";
    if (form.party_size && isNaN(Number(form.party_size)))
      next.party_size = "Party size must be a number.";
    if (!form.consent) next.consent = "Please confirm this is a test submission.";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setApiError(null);
    if (!validate()) return;

    setSubmitting(true);
    try {
      const body: Record<string, unknown> = {
        restaurant_id: form.restaurant_id,
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        email: form.email.trim(),
        meal_period: form.meal_period || "dinner",
      };
      if (form.phone) body.phone = form.phone;
      if (form.company_name) body.company_name = form.company_name;
      if (form.event_date) body.event_date = form.event_date;
      if (form.event_type) body.event_type = form.event_type;
      if (form.party_size) body.party_size = Number(form.party_size);
      if (form.budget_indication) body.budget_indication = form.budget_indication;
      if (form.preferred_area) body.preferred_area = form.preferred_area;
      if (form.dietary_requirements) body.dietary_requirements = form.dietary_requirements;
      if (form.special_requests) body.special_requests = form.special_requests;
      if (form.message) body.message = form.message;

      const res = await fetch(`${API_BASE}/api/v1/enquiries/intake`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const text = await res.text().catch(() => res.statusText);
        throw new Error(text || `Request failed (${res.status})`);
      }

      const data: EnquiryIntakeOut = await res.json();
      setResult(data);
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Submission failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const restaurantName =
    restaurants.find((r) => r.id === result?.restaurant_id)?.name ?? "the selected venue";

  if (result) {
    return <SuccessPanel result={result} restaurantName={restaurantName} />;
  }

  const restaurantOptions = [
    { value: "", label: "Select a venue" },
    ...restaurants.map((r) => ({ value: r.id, label: r.name })),
  ];

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {/* ── API error banner ──────────────────────────────────────────────── */}
        {apiError && (
          <div
            role="alert"
            style={{
              padding: "12px 16px",
              borderRadius: 10,
              background: "rgba(229,72,77,0.08)",
              border: "1px solid rgba(229,72,77,0.25)",
              fontSize: 13,
              color: "var(--danger)",
            }}
          >
            {apiError}
          </div>
        )}

        {/* ── Section 1: Venue ─────────────────────────────────────────────── */}
        <Card padding="lg">
          <SectionHeading
            title="Venue"
            subtitle="Select the venue this enquiry is for."
          />
          <div style={{ maxWidth: 360 }}>
            <Select
              label="Venue"
              required
              value={form.restaurant_id}
              onChange={(e) => set("restaurant_id", e.target.value)}
              options={restaurantOptions}
              error={errors.restaurant_id}
            />
          </div>
        </Card>

        {/* ── Section 2: Contact Details ────────────────────────────────────── */}
        <Card padding="lg">
          <SectionHeading
            title="Contact Details"
            subtitle="Guest contact information."
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <FieldRow>
              <Input
                label="First Name"
                required
                value={form.first_name}
                onChange={(e) => set("first_name", e.target.value)}
                placeholder="Jane"
                error={errors.first_name}
              />
              <Input
                label="Last Name"
                required
                value={form.last_name}
                onChange={(e) => set("last_name", e.target.value)}
                placeholder="Smith"
                error={errors.last_name}
              />
            </FieldRow>
            <FieldRow>
              <Input
                label="Email Address"
                type="email"
                required
                value={form.email}
                onChange={(e) => set("email", e.target.value)}
                placeholder="jane@example.com"
                error={errors.email}
              />
              <Input
                label="Phone"
                type="tel"
                value={form.phone}
                onChange={(e) => set("phone", e.target.value)}
                placeholder="+44 7700 900000"
              />
            </FieldRow>
            <div style={{ maxWidth: 360 }}>
              <Input
                label="Company Name"
                value={form.company_name}
                onChange={(e) => set("company_name", e.target.value)}
                placeholder="Acme Ltd"
              />
            </div>
          </div>
        </Card>

        {/* ── Section 3: Event Details ──────────────────────────────────────── */}
        <Card padding="lg">
          <SectionHeading
            title="Event Details"
            subtitle="Tell us about the event you have in mind."
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <FieldRow>
              <Input
                label="Event Date"
                type="date"
                value={form.event_date}
                onChange={(e) => set("event_date", e.target.value)}
              />
              <Input
                label="Party Size"
                type="number"
                min={1}
                value={form.party_size}
                onChange={(e) => set("party_size", e.target.value)}
                placeholder="e.g. 20"
                error={errors.party_size}
              />
            </FieldRow>
            <FieldRow>
              <Select
                label="Event Type"
                value={form.event_type}
                onChange={(e) => set("event_type", e.target.value)}
                options={EVENT_TYPE_OPTIONS}
              />
              <Select
                label="Meal Period"
                value={form.meal_period}
                onChange={(e) => set("meal_period", e.target.value)}
                options={MEAL_PERIOD_OPTIONS}
                helper="Used to calculate pricing recommendation."
              />
            </FieldRow>
          </div>
        </Card>

        {/* ── Section 4: Preferences ────────────────────────────────────────── */}
        <Card padding="lg">
          <SectionHeading
            title="Preferences"
            subtitle="Optional details to help us prepare the best proposal."
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <FieldRow>
              <Input
                label="Budget Indication"
                value={form.budget_indication}
                onChange={(e) => set("budget_indication", e.target.value)}
                placeholder="e.g. Around £3,000"
              />
              <Input
                label="Preferred Room or Area"
                value={form.preferred_area}
                onChange={(e) => set("preferred_area", e.target.value)}
                placeholder="e.g. Private Dining Room"
              />
            </FieldRow>
            <FieldRow>
              <Input
                label="Dietary Requirements"
                value={form.dietary_requirements}
                onChange={(e) => set("dietary_requirements", e.target.value)}
                placeholder="e.g. 2 vegetarian, 1 nut allergy"
              />
              <Input
                label="Special Requests"
                value={form.special_requests}
                onChange={(e) => set("special_requests", e.target.value)}
                placeholder="e.g. Projector, cake, flowers"
              />
            </FieldRow>
          </div>
        </Card>

        {/* ── Section 5: Message ────────────────────────────────────────────── */}
        <Card padding="lg">
          <SectionHeading
            title="Message"
            subtitle="Any additional context from the guest."
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label
              htmlFor="message"
              style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}
            >
              Message
            </label>
            <textarea
              id="message"
              rows={5}
              value={form.message}
              onChange={(e) => set("message", e.target.value)}
              placeholder="e.g. We're celebrating our 10th anniversary and would love a private room with a personalised menu…"
              style={{
                width: "100%",
                borderRadius: 10,
                border: "1px solid var(--border)",
                backgroundColor: "var(--surface)",
                color: "var(--text-primary)",
                fontSize: 13,
                padding: "10px 12px",
                resize: "vertical",
                outline: "none",
                fontFamily: "inherit",
                lineHeight: 1.6,
              }}
            />
          </div>
        </Card>

        {/* ── Section 6: Consent + Submit ───────────────────────────────────── */}
        <Card padding="lg">
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
              <input
                id="consent"
                type="checkbox"
                checked={form.consent}
                onChange={(e) => set("consent", e.target.checked)}
                style={{ marginTop: 2, cursor: "pointer", flexShrink: 0 }}
              />
              <div>
                <label
                  htmlFor="consent"
                  style={{ fontSize: 13, color: "var(--text-secondary)", cursor: "pointer", lineHeight: 1.5 }}
                >
                  I understand this is a <strong>test submission</strong> for the EventSales AI POC.
                  No real communications will be sent to the guest email address.
                </label>
                {errors.consent && (
                  <p style={{ fontSize: 12, color: "var(--danger)", marginTop: 4 }}>
                    {errors.consent}
                  </p>
                )}
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <Button type="submit" variant="primary" size="lg" loading={submitting}>
                Submit Enquiry
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </form>
  );
}
