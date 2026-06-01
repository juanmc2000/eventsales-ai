"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Card } from "@/components/layout/Card";
import type { Restaurant, RestaurantListOut, Room } from "@/lib/types/restaurant";
import type { AIContextOut, EnquiryCandidateDateOut, EnquiryDateRequestOut, EnquiryDraft, EnquiryIntakeOut, ExtractionSummaryOut, FreeformIntakeOut, RoomAvailabilityOut } from "@/lib/types/enquiry";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Default reply-to for auto-sent drafts. */
const DEFAULT_REPLY_EMAIL = "juanmc@gmail.com";

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

const AUDIENCE_OPTIONS = [
  { value: "", label: "Default (no specific audience)" },
  { value: "social", label: "Social — leisure, celebrations, personal dining" },
  { value: "corporate", label: "Corporate — B2B, company events, offsite" },
  { value: "agency", label: "Agency — event agencies, intermediaries" },
];

// ── Shared helpers ─────────────────────────────────────────────────────────────

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

/** Badge showing email delivery outcome. */
function EmailStatusBadge({ sent, disabled }: { sent: boolean; disabled?: boolean }) {
  if (disabled) {
    return (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 5,
          padding: "3px 10px",
          borderRadius: 99,
          fontSize: 12,
          fontWeight: 600,
          backgroundColor: "rgba(160,160,180,0.12)",
          color: "var(--text-muted)",
          border: "1px solid var(--border)",
        }}
      >
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        SMTP not configured
      </span>
    );
  }
  if (sent) {
    return (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 5,
          padding: "3px 10px",
          borderRadius: 99,
          fontSize: 12,
          fontWeight: 600,
          backgroundColor: "rgba(22,166,106,0.1)",
          color: "var(--success, #16A66A)",
          border: "1px solid rgba(22,166,106,0.2)",
        }}
      >
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6L9 17l-5-5"/></svg>
        Email queued
      </span>
    );
  }
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        padding: "3px 10px",
        borderRadius: 99,
        fontSize: 12,
        fontWeight: 600,
        backgroundColor: "rgba(229,72,77,0.08)",
        color: "var(--danger, #E5484D)",
        border: "1px solid rgba(229,72,77,0.2)",
      }}
    >
      Send failed
    </span>
  );
}

// ── AI Transparency Panel ──────────────────────────────────────────────────────

const STATUS_PILL: Record<string, { bg: string; color: string; label: string }> = {
  available:   { bg: "rgba(22,166,106,0.1)",  color: "var(--success, #16A66A)", label: "Available" },
  booked:      { bg: "rgba(229,72,77,0.08)",  color: "var(--danger, #E5484D)",  label: "Booked" },
  held:        { bg: "rgba(245,158,11,0.1)",  color: "#B45309",                 label: "Held" },
  unavailable: { bg: "rgba(160,160,180,0.12)", color: "var(--text-muted)",       label: "Unavailable" },
};

function StatusPill({ status }: { status: string }) {
  const cfg = STATUS_PILL[status] ?? STATUS_PILL.unavailable;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "2px 10px", borderRadius: 99,
      fontSize: 11, fontWeight: 600,
      backgroundColor: cfg.bg, color: cfg.color,
      border: `1px solid ${cfg.color}33`,
    }}>
      {cfg.label}
    </span>
  );
}

function AITransparencyPanel({ aiContext, label = "AI Generation Details" }: { aiContext: AIContextOut; label?: string }) {
  const [open, setOpen] = useState(false);

  const rows: [string, string | null | undefined][] = [
    ["Model", aiContext.is_fallback ? "Deterministic fallback (no LLM call)" : aiContext.model],
    ["Persona", aiContext.persona_name],
    ["Tone", aiContext.persona_tone],
    ["Style", aiContext.persona_style],
    ["Guest message sent",
      aiContext.guest_message_used
        ? (aiContext.guest_message_used.length > 120
          ? aiContext.guest_message_used.slice(0, 120) + "…"
          : aiContext.guest_message_used)
        : null],
    ["Room context", aiContext.room_name],
    ["Min. spend in prompt",
      aiContext.recommended_minimum_spend && aiContext.recommended_minimum_spend > 0
        ? `£${Math.round(aiContext.recommended_minimum_spend).toLocaleString()}`
        : null],
  ];

  return (
    <div style={{
      borderRadius: 10,
      border: "1px solid var(--border)",
      overflow: "hidden",
    }}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        style={{
          width: "100%",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "10px 14px",
          background: "var(--surface-soft)",
          border: "none", cursor: "pointer",
          fontSize: 11, fontWeight: 600, color: "var(--text-muted)",
          textTransform: "uppercase", letterSpacing: "0.05em",
        }}
      >
        <span>{label}</span>
        <span style={{ fontSize: 10 }}>{open ? "▼" : "▶"}</span>
      </button>

      {open && (
        <div style={{
          padding: "12px 14px",
          background: "var(--surface-soft)",
          borderTop: "1px solid var(--border)",
          display: "flex", flexDirection: "column", gap: 6,
          fontFamily: "monospace",
          fontSize: 12,
        }}>
          {rows.map(([label, value]) =>
            value ? (
              <div key={label} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <span style={{ color: "var(--text-muted)", minWidth: 160, flexShrink: 0 }}>{label}</span>
                <span style={{ color: "var(--text-secondary)" }}>{value}</span>
              </div>
            ) : null
          )}

          {!aiContext.is_fallback && aiContext.system_prompt && (
            <>
              <div style={{ borderTop: "1px solid var(--border)", margin: "6px 0" }} />
              <div>
                <div style={{ color: "var(--text-muted)", marginBottom: 4 }}>System prompt</div>
                <pre style={{
                  margin: 0, fontSize: 11, lineHeight: 1.5,
                  color: "var(--text-secondary)",
                  whiteSpace: "pre-wrap", wordBreak: "break-word",
                  maxHeight: 160, overflowY: "auto",
                  background: "var(--surface)", padding: "8px 10px", borderRadius: 6,
                  border: "1px solid var(--border)",
                }}>{aiContext.system_prompt}</pre>
              </div>
              {aiContext.user_message && (
                <div>
                  <div style={{ color: "var(--text-muted)", marginBottom: 4 }}>User message</div>
                  <pre style={{
                    margin: 0, fontSize: 11, lineHeight: 1.5,
                    color: "var(--text-secondary)",
                    whiteSpace: "pre-wrap", wordBreak: "break-word",
                    maxHeight: 120, overflowY: "auto",
                    background: "var(--surface)", padding: "8px 10px", borderRadius: 6,
                    border: "1px solid var(--border)",
                  }}>{aiContext.user_message}</pre>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── Extraction Transparency Panel ─────────────────────────────────────────────

function ExtractionTransparencyPanel({ extraction }: { extraction: ExtractionSummaryOut }) {
  const [open, setOpen] = useState(false);

  if (extraction.is_fallback || !extraction.extraction_system_prompt) return null;

  return (
    <div style={{ borderRadius: 10, border: "1px solid var(--border)", overflow: "hidden" }}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        style={{
          width: "100%",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "10px 14px",
          background: "var(--surface-soft)",
          border: "none", cursor: "pointer",
          fontSize: 11, fontWeight: 600, color: "var(--text-muted)",
          textTransform: "uppercase", letterSpacing: "0.05em",
        }}
      >
        <span>LLM Call 1 — Extraction Details</span>
        <span style={{ fontSize: 10 }}>{open ? "▼" : "▶"}</span>
      </button>

      {open && (
        <div style={{
          padding: "12px 14px",
          background: "var(--surface-soft)",
          borderTop: "1px solid var(--border)",
          display: "flex", flexDirection: "column", gap: 10,
          fontFamily: "monospace",
          fontSize: 12,
        }}>
          <div>
            <div style={{ color: "var(--text-muted)", marginBottom: 4 }}>System prompt</div>
            <pre style={{
              margin: 0, fontSize: 11, lineHeight: 1.5,
              color: "var(--text-secondary)",
              whiteSpace: "pre-wrap", wordBreak: "break-word",
              maxHeight: 160, overflowY: "auto",
              background: "var(--surface)", padding: "8px 10px", borderRadius: 6,
              border: "1px solid var(--border)",
            }}>{extraction.extraction_system_prompt}</pre>
          </div>

          {extraction.extraction_user_prompt && (
            <div>
              <div style={{ color: "var(--text-muted)", marginBottom: 4 }}>User message</div>
              <pre style={{
                margin: 0, fontSize: 11, lineHeight: 1.5,
                color: "var(--text-secondary)",
                whiteSpace: "pre-wrap", wordBreak: "break-word",
                maxHeight: 120, overflowY: "auto",
                background: "var(--surface)", padding: "8px 10px", borderRadius: 6,
                border: "1px solid var(--border)",
              }}>{extraction.extraction_user_prompt}</pre>
            </div>
          )}

          {extraction.extraction_raw_response && (
            <div>
              <div style={{ color: "var(--text-muted)", marginBottom: 4 }}>Model response (extracted JSON)</div>
              <pre style={{
                margin: 0, fontSize: 11, lineHeight: 1.5,
                color: "var(--text-secondary)",
                whiteSpace: "pre-wrap", wordBreak: "break-word",
                maxHeight: 140, overflowY: "auto",
                background: "var(--surface)", padding: "8px 10px", borderRadius: 6,
                border: "1px solid var(--border)",
              }}>{extraction.extraction_raw_response}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Extraction Parsed JSON Panel ───────────────────────────────────────────────

function ExtractionParsedJsonPanel({ rawResponse }: { rawResponse: string }) {
  const [open, setOpen] = useState(true);

  let formatted: string;
  try {
    formatted = JSON.stringify(JSON.parse(rawResponse), null, 2);
  } catch {
    formatted = rawResponse;
  }

  return (
    <div style={{
      borderRadius: 10,
      border: "1px solid rgba(109,61,245,0.18)",
      overflow: "hidden",
    }}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        style={{
          width: "100%",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "10px 14px",
          background: "rgba(109,61,245,0.04)",
          border: "none", cursor: "pointer",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{
            fontSize: 11, fontWeight: 600, color: "var(--text-muted)",
            textTransform: "uppercase", letterSpacing: "0.05em",
          }}>
            Extracted Data — V3 JSON Contract
          </span>
          <span style={{
            fontFamily: "monospace", fontSize: 10, color: "var(--brand-purple)",
            background: "rgba(109,61,245,0.08)", padding: "1px 7px", borderRadius: 4,
          }}>
            enquiry_extraction_output · v3.0
          </span>
        </div>
        <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{open ? "▼" : "▶"}</span>
      </button>

      {open && (
        <div style={{
          background: "rgba(109,61,245,0.02)",
          borderTop: "1px solid rgba(109,61,245,0.12)",
          padding: "12px 14px",
        }}>
          <pre style={{
            margin: 0, fontSize: 11, lineHeight: 1.6,
            color: "var(--text-secondary)",
            whiteSpace: "pre-wrap", wordBreak: "break-all",
            maxHeight: 400, overflowY: "auto",
            background: "var(--surface)", padding: "10px 12px", borderRadius: 6,
            border: "1px solid var(--border)",
            fontFamily: "monospace",
          }}>
            {formatted}
          </pre>
        </div>
      )}
    </div>
  );
}

// ── Date Resolution Panel ──────────────────────────────────────────────────────

function DateResolutionPanel({
  dateRequestRecord,
  candidateDates,
}: {
  dateRequestRecord: EnquiryDateRequestOut | null;
  candidateDates: EnquiryCandidateDateOut[];
}) {
  if (!dateRequestRecord && candidateDates.length === 0) return null;

  const rawText = dateRequestRecord?.raw_text;
  const dateRequestType = dateRequestRecord?.date_request_type;
  const confidence = dateRequestRecord?.confidence;
  const requiresClarification = dateRequestRecord?.requires_date_clarification ?? false;
  const clarificationQuestion = dateRequestRecord?.clarification_question;

  return (
    <div style={{
      padding: "14px 16px",
      borderRadius: 10,
      background: "rgba(22,166,106,0.04)",
      border: "1px solid rgba(22,166,106,0.2)",
    }}>
      <p style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 10px 0" }}>
        Date Resolution
      </p>

      {/* Intent: raw text → calculated date(s) → type → confidence */}
      {dateRequestRecord && (
        <div style={{ marginBottom: candidateDates.length > 0 ? 12 : 0, display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            {rawText && rawText !== "NULL" && (
              <span style={{ fontSize: 13, color: "var(--text-secondary)", fontStyle: "italic" }}>
                &ldquo;{rawText}&rdquo;
              </span>
            )}
            {candidateDates.length > 0 && (
              <>
                <span style={{ fontSize: 13, color: "var(--text-muted)" }}>→</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
                  {candidateDates.map((cd) =>
                    new Date(cd.candidate_date + "T12:00:00").toLocaleDateString("en-GB", {
                      weekday: "short", day: "numeric", month: "short", year: "numeric",
                    })
                  ).join(", ")}
                </span>
              </>
            )}
            {dateRequestType && (
              <span style={{ fontFamily: "monospace", fontSize: 11, color: "var(--success, #16A66A)", background: "rgba(22,166,106,0.1)", padding: "2px 8px", borderRadius: 6, fontWeight: 600 }}>
                {dateRequestType}
              </span>
            )}
            {confidence != null && (
              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                {Math.round(confidence * 100)}% confidence
              </span>
            )}
            {requiresClarification && (
              <span style={{ fontSize: 11, color: "#B45309", background: "rgba(180,83,9,0.08)", padding: "2px 8px", borderRadius: 6, fontWeight: 600 }}>
                Needs clarification
              </span>
            )}
          </div>
          {requiresClarification && clarificationQuestion && (
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0, fontStyle: "italic" }}>
              {clarificationQuestion}
            </p>
          )}
        </div>
      )}

      {/* Candidate date rows — availability + pricing */}
      {candidateDates.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, borderTop: "1px solid rgba(22,166,106,0.12)", paddingTop: 10 }}>
          <p style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 4px 0" }}>
            Availability check
          </p>
          {candidateDates.map((cd) => (
            <div key={cd.id} style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", minWidth: 160, fontFamily: "monospace" }}>
                {cd.candidate_date}
              </span>
              <span style={{ fontSize: 11, color: "var(--text-muted)", background: "var(--surface-soft)", padding: "2px 7px", borderRadius: 4, border: "1px solid var(--border)" }}>
                {cd.source_type}
              </span>
              {cd.availability_status && <StatusPill status={cd.availability_status} />}
              {cd.recommended_minimum_spend != null && cd.recommended_minimum_spend > 0 && (
                <span style={{ fontSize: 12, color: "var(--brand-purple)", fontWeight: 600 }}>
                  £{Math.round(cd.recommended_minimum_spend).toLocaleString()}
                </span>
              )}
            </div>
          ))}
        </div>
      ) : dateRequestRecord ? (
        <p style={{ fontSize: 12, color: "var(--text-muted)", margin: 0 }}>
          No candidate dates resolved — the extraction type may not have produced explicit dates.
        </p>
      ) : null}
    </div>
  );
}

// ── Room Availability Card ─────────────────────────────────────────────────────

function RoomAvailabilityCard({
  restaurantId,
  rooms,
  roomName,
  eventDate,
}: {
  restaurantId: string;
  rooms: Room[];
  roomName: string;
  eventDate: string;
}) {
  const [availability, setAvailability] = useState<RoomAvailabilityOut | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const room = rooms.find((r) => r.name === roomName);
    if (!room) { setLoading(false); return; }
    fetch(`${API_BASE}/api/v1/restaurants/${restaurantId}/rooms/${room.id}/availability?date=${eventDate}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setAvailability(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [restaurantId, rooms, roomName, eventDate]);

  return (
    <div style={{
      padding: "12px 16px", borderRadius: 10,
      background: "var(--surface-soft)", border: "1px solid var(--border)",
    }}>
      <p style={{
        fontSize: 11, color: "var(--text-muted)", fontWeight: 600,
        textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 8px 0",
      }}>
        Room Availability — {roomName} · {eventDate}
      </p>

      {loading ? (
        <div style={{ height: 32, borderRadius: 6, background: "var(--border)", width: "60%" }} />
      ) : !availability || availability.slots.length === 0 ? (
        <p style={{ fontSize: 12, color: "var(--text-muted)", margin: 0 }}>
          No availability data for this date.
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {availability.slots.map((slot) => (
            <div key={slot.meal_period} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 12, color: "var(--text-secondary)", minWidth: 60, textTransform: "capitalize" }}>
                {slot.meal_period}
              </span>
              <StatusPill status={slot.status} />
              {slot.notes && (
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{slot.notes}</span>
              )}
            </div>
          ))}
          <p style={{ fontSize: 10, color: "var(--text-muted)", margin: "4px 0 0 0", fontStyle: "italic" }}>
            In production this will reflect live booking system status.
          </p>
        </div>
      )}
    </div>
  );
}

// ── Tab bar ────────────────────────────────────────────────────────────────────

type Tab = "structured" | "freeform";

function TabBar({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  const tabs: { key: Tab; label: string; description: string }[] = [
    { key: "structured", label: "Structured Enquiry", description: "Full event details form" },
    { key: "freeform", label: "Freeform Enquiry", description: "Natural-language message → AI reply" },
  ];

  return (
    <div
      style={{
        display: "flex",
        gap: 8,
        padding: "4px",
        borderRadius: 12,
        backgroundColor: "var(--surface-soft)",
        border: "1px solid var(--border)",
      }}
    >
      {tabs.map((tab) => {
        const isActive = active === tab.key;
        return (
          <button
            key={tab.key}
            type="button"
            onClick={() => onChange(tab.key)}
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-start",
              padding: "10px 16px",
              borderRadius: 9,
              border: "none",
              cursor: "pointer",
              transition: "all 0.15s ease",
              backgroundColor: isActive ? "var(--surface)" : "transparent",
              boxShadow: isActive ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
            }}
          >
            <span
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: isActive ? "var(--brand-purple)" : "var(--text-secondary)",
              }}
            >
              {tab.label}
            </span>
            <span
              style={{
                fontSize: 11,
                color: isActive ? "var(--text-muted)" : "var(--text-muted)",
                marginTop: 1,
              }}
            >
              {tab.description}
            </span>
          </button>
        );
      })}
    </div>
  );
}

// ── Structured form ────────────────────────────────────────────────────────────

type StructuredFormState = {
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
  audience_type: string;
  budget_indication: string;
  preferred_area: string;
  dietary_requirements: string;
  special_requests: string;
  message: string;
  consent: boolean;
};

const STRUCTURED_EMPTY: StructuredFormState = {
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
  audience_type: "",
  budget_indication: "",
  preferred_area: "",
  dietary_requirements: "",
  special_requests: "",
  message: "",
  consent: false,
};

type StructuredResult = {
  intake: EnquiryIntakeOut;
  restaurantName: string;
  draft: EnquiryDraft | null;
  emailSent: boolean | null; // null = not attempted, true = queued, false = failed/disabled
  rooms: Room[];
  eventDate: string; // ISO date string, may be empty
};

function StructuredSuccessPanel({ result }: { result: StructuredResult }) {
  const { intake, restaurantName, draft, emailSent, rooms, eventDate } = result;
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
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--success, #16A66A)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
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
            {intake.reference}
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
          {intake.persona_name && (
            <div style={{ padding: "12px 16px", borderRadius: 10, background: "var(--surface-soft)", border: "1px solid var(--border)" }}>
              <p style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>
                Assigned Persona
              </p>
              <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", marginTop: 4 }}>
                {intake.persona_name}
              </p>
            </div>
          )}
          <div style={{ padding: "12px 16px", borderRadius: 10, background: "var(--surface-soft)", border: "1px solid var(--border)" }}>
            <p style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>
              Recommended Min. Spend
            </p>
            <p style={{ fontSize: 14, fontWeight: 700, color: "var(--brand-purple)", marginTop: 4 }}>
              {intake.recommended_minimum_spend > 0
                ? `£${Math.round(intake.recommended_minimum_spend).toLocaleString()}`
                : "No rule matched"}
            </p>
          </div>
          <div style={{ padding: "12px 16px", borderRadius: 10, background: "var(--surface-soft)", border: "1px solid var(--border)" }}>
            <p style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>
              Status
            </p>
            <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", marginTop: 4, textTransform: "capitalize" }}>
              {intake.status}
            </p>
          </div>
        </div>

        {/* AI draft + email status */}
        {(draft !== null || emailSent !== null) && (
          <div
            style={{
              padding: "12px 16px",
              borderRadius: 10,
              background: "var(--surface-soft)",
              border: "1px solid var(--border)",
              display: "flex",
              flexDirection: "column",
              gap: 8,
            }}
          >
            <p style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>
              AI Draft Response
            </p>
            {draft ? (
              <p style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 500, margin: 0 }}>
                {draft.subject ?? "Draft generated"}
              </p>
            ) : (
              <p style={{ fontSize: 13, color: "var(--text-muted)", margin: 0 }}>Draft generation failed</p>
            )}
            {emailSent !== null && (
              <div style={{ marginTop: 2 }}>
                <EmailStatusBadge sent={emailSent} disabled={emailSent === false} />
                {emailSent && (
                  <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
                    Reply sent to {DEFAULT_REPLY_EMAIL}
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {intake.pricing_explanation && (
          <p style={{ fontSize: 12, color: "var(--text-muted)", lineHeight: 1.6 }}>
            {intake.pricing_explanation}
          </p>
        )}

        {/* Room availability */}
        {draft?.ai_context?.room_name && eventDate && (
          <RoomAvailabilityCard
            restaurantId={intake.restaurant_id}
            rooms={rooms}
            roomName={draft.ai_context.room_name}
            eventDate={eventDate}
          />
        )}

        {/* AI transparency */}
        {draft?.ai_context && (
          <AITransparencyPanel aiContext={draft.ai_context} />
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Link href="/enquiries">
            <Button variant="primary" size="md">View All Enquiries</Button>
          </Link>
          <Button variant="secondary" size="md" onClick={() => window.location.reload()}>
            Submit Another
          </Button>
        </div>
      </div>
    </Card>
  );
}

function StructuredEnquiryForm({
  restaurants,
}: {
  restaurants: Restaurant[];
}) {
  const [form, setForm] = useState<StructuredFormState>(STRUCTURED_EMPTY);
  const [errors, setErrors] = useState<Partial<Record<keyof StructuredFormState, string>>>({});
  const [rooms, setRooms] = useState<Room[]>([]);
  const [roomsLoading, setRoomsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [result, setResult] = useState<StructuredResult | null>(null);

  useEffect(() => {
    setForm((prev) => ({ ...prev, preferred_area: "" }));
    if (!form.restaurant_id) { setRooms([]); return; }
    setRoomsLoading(true);
    fetch(`${API_BASE}/api/v1/restaurants/${form.restaurant_id}/rooms?active_only=true&limit=50`)
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((d) => setRooms(d.items ?? []))
      .catch(() => setRooms([]))
      .finally(() => setRoomsLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.restaurant_id]);

  function set(key: keyof StructuredFormState, value: string | boolean) {
    setForm((prev) => ({ ...prev, [key]: value }));
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }));
  }

  function validate(): boolean {
    const next: Partial<Record<keyof StructuredFormState, string>> = {};
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
      // Step 1: Create enquiry
      const body: Record<string, unknown> = {
        restaurant_id: form.restaurant_id,
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        email: form.email.trim(),
        meal_period: form.meal_period || "dinner",
      };
      if (form.audience_type) body.audience_type = form.audience_type;
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

      const intakeRes = await fetch(`${API_BASE}/api/v1/enquiries/intake`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!intakeRes.ok) {
        const text = await intakeRes.text().catch(() => intakeRes.statusText);
        throw new Error(text || `Request failed (${intakeRes.status})`);
      }

      const intake: EnquiryIntakeOut = await intakeRes.json();
      const restaurantName =
        restaurants.find((r) => r.id === intake.restaurant_id)?.name ?? "the selected venue";

      // Step 2: Generate AI draft
      let draft: EnquiryDraft | null = null;
      try {
        const draftRes = await fetch(`${API_BASE}/api/v1/enquiries/${intake.enquiry_id}/draft`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });
        if (draftRes.ok) draft = await draftRes.json();
      } catch {
        // draft generation is best-effort
      }

      // Step 3: Send via SMTP
      let emailSent: boolean | null = null;
      if (draft) {
        try {
          const sendRes = await fetch(`${API_BASE}/api/v1/email/send-draft`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ enquiry_id: intake.enquiry_id, to_email: DEFAULT_REPLY_EMAIL }),
          });
          emailSent = sendRes.ok;
        } catch {
          emailSent = false;
        }
      }

      setResult({ intake, restaurantName, draft, emailSent, rooms, eventDate: form.event_date });
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Submission failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (result) return <StructuredSuccessPanel result={result} />;

  const restaurantOptions = [
    { value: "", label: "Select a venue" },
    ...restaurants.map((r) => ({ value: r.id, label: r.name })),
  ];

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
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

        {/* Section 1: Venue */}
        <Card padding="lg">
          <SectionHeading title="Venue" subtitle="Select the venue this enquiry is for." />
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

        {/* Section 2: Contact Details */}
        <Card padding="lg">
          <SectionHeading title="Contact Details" subtitle="Guest contact information." />
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

        {/* Section 3: Event Details */}
        <Card padding="lg">
          <SectionHeading title="Event Details" subtitle="Tell us about the event you have in mind." />
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
            <div style={{ maxWidth: 420 }}>
              <Select
                label="Audience Type"
                value={form.audience_type}
                onChange={(e) => set("audience_type", e.target.value)}
                options={AUDIENCE_OPTIONS}
                helper="Selects the persona tailored for this enquiry source."
              />
            </div>
          </div>
        </Card>

        {/* Section 4: Preferences */}
        <Card padding="lg">
          <SectionHeading title="Preferences" subtitle="Optional details to help us prepare the best proposal." />
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <FieldRow>
              <Input
                label="Budget Indication"
                value={form.budget_indication}
                onChange={(e) => set("budget_indication", e.target.value)}
                placeholder="e.g. Around £3,000"
              />
              {rooms.length > 0 ? (
                <Select
                  label="Preferred Room or Area"
                  value={form.preferred_area}
                  onChange={(e) => set("preferred_area", e.target.value)}
                  options={[
                    { value: "", label: roomsLoading ? "Loading rooms…" : "No specific room" },
                    ...rooms.map((r) => ({
                      value: r.name,
                      label: r.is_private_dining ? `${r.name} (PDR)` : r.name,
                    })),
                  ]}
                  helper="Rooms available at the selected venue."
                />
              ) : (
                <Input
                  label="Preferred Room or Area"
                  value={form.preferred_area}
                  onChange={(e) => set("preferred_area", e.target.value)}
                  placeholder={
                    form.restaurant_id
                      ? roomsLoading
                        ? "Loading rooms…"
                        : "e.g. Private Dining Room"
                      : "Select a venue first"
                  }
                  disabled={roomsLoading}
                />
              )}
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

        {/* Section 5: Message */}
        <Card padding="lg">
          <SectionHeading title="Message" subtitle="Any additional context from the guest." />
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label htmlFor="message" style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>
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

        {/* Section 6: Consent + Submit */}
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
                  The AI draft will be sent to <strong>{DEFAULT_REPLY_EMAIL}</strong> via SMTP.
                </label>
                {errors.consent && (
                  <p style={{ fontSize: 12, color: "var(--danger)", marginTop: 4 }}>{errors.consent}</p>
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

// ── Freeform form ──────────────────────────────────────────────────────────────

type FreeformFormState = {
  restaurant_id: string;
  preferred_area: string;
  audience_type: string;
  first_name: string;
  last_name: string;
  reply_email: string;
  message: string;
};

const FREEFORM_EMPTY: FreeformFormState = {
  restaurant_id: "",
  preferred_area: "",
  audience_type: "",
  first_name: "",
  last_name: "",
  reply_email: DEFAULT_REPLY_EMAIL,
  message: "",
};

type FreeformResult = {
  enquiry_id: string;
  reference: string;
  persona_name: string | null;
  audience_type: string | null;
  draft: EnquiryDraft | null;
  emailSent: boolean | null;
  smtpDisabled: boolean;
  reply_email: string;
  restaurantId: string;
  rooms: Room[];
  // Sprint 7 enrichments
  extraction: ExtractionSummaryOut | null;
  recommended_action: string | null;
  // Sprint 8B enrichments
  dateRequestRecord: EnquiryDateRequestOut | null;
  candidateDates: EnquiryCandidateDateOut[];
};

function FreeformSuccessPanel({
  result,
  restaurantName,
  onReset,
}: {
  result: FreeformResult;
  restaurantName: string;
  onReset: () => void;
}) {
  const { draft, restaurantId, rooms } = result;
  return (
    <Card padding="lg">
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Heading */}
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
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--success, #16A66A)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 6L9 17l-5-5" />
            </svg>
          </div>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
              Enquiry Processed
            </h2>
            <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 2 }}>
              AI draft generated for {restaurantName}
            </p>
          </div>
        </div>

        {/* Reference */}
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
          <span style={{ fontFamily: "monospace", fontSize: 15, fontWeight: 700, color: "var(--brand-purple)" }}>
            {result.reference}
          </span>
        </div>

        {/* Detail cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
          {result.persona_name && (
            <div style={{ padding: "12px 16px", borderRadius: 10, background: "var(--surface-soft)", border: "1px solid var(--border)" }}>
              <p style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>
                Persona Used
              </p>
              <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", marginTop: 4 }}>
                {result.persona_name}
              </p>
              {result.audience_type && (
                <p style={{ fontSize: 11, color: "var(--brand-purple)", marginTop: 2, textTransform: "capitalize" }}>
                  {result.audience_type} audience
                </p>
              )}
            </div>
          )}
          <div style={{ padding: "12px 16px", borderRadius: 10, background: "var(--surface-soft)", border: "1px solid var(--border)" }}>
            <p style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>
              Draft Subject
            </p>
            <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", marginTop: 4 }}>
              {draft?.subject ?? (draft ? "Generated" : "Generation failed")}
            </p>
          </div>
          {(result.emailSent !== null || result.smtpDisabled) && (
            <div style={{ padding: "12px 16px", borderRadius: 10, background: "var(--surface-soft)", border: "1px solid var(--border)" }}>
              <p style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", margin: 0 }}>
                Email Delivery
              </p>
              <div style={{ marginTop: 6 }}>
                <EmailStatusBadge sent={result.emailSent === true} disabled={result.smtpDisabled} />
              </div>
              {result.emailSent === true && (
                <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                  Sent to {result.reply_email}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Draft preview */}
        {draft?.body && (
          <div
            style={{
              padding: "14px 16px",
              borderRadius: 10,
              background: "var(--surface-soft)",
              border: "1px solid var(--border)",
            }}
          >
            <p style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 8px 0" }}>
              Draft Preview
            </p>
            <p
              style={{
                fontSize: 13,
                color: "var(--text-secondary)",
                lineHeight: 1.7,
                margin: 0,
                whiteSpace: "pre-wrap",
                maxHeight: 200,
                overflow: "auto",
              }}
            >
              {draft.body}
            </p>
          </div>
        )}

        {/* Extraction + recommended action summary */}
        {(result.extraction || result.recommended_action) && (
          <div
            style={{
              padding: "14px 16px",
              borderRadius: 10,
              background: "rgba(109,61,245,0.04)",
              border: "1px solid rgba(109,61,245,0.12)",
            }}
          >
            <p style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 10px 0" }}>
              AI Extraction Summary
            </p>
            {result.recommended_action && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 500 }}>Recommended action:</span>
                <span style={{ fontFamily: "monospace", fontSize: 12, color: "var(--brand-purple)", background: "rgba(109,61,245,0.08)", padding: "2px 8px", borderRadius: 6 }}>
                  {result.recommended_action.replace(/_/g, " ")}
                </span>
              </div>
            )}
            {result.extraction && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {result.extraction.guest_count != null && (
                  <span style={{ fontSize: 12, color: "var(--text-secondary)", background: "var(--surface-soft)", padding: "2px 8px", borderRadius: 6 }}>
                    Guests: {result.extraction.guest_count}
                  </span>
                )}
                {result.extraction.event_date && (
                  <span style={{ fontSize: 12, color: "var(--text-secondary)", background: "var(--surface-soft)", padding: "2px 8px", borderRadius: 6 }}>
                    Date: {result.extraction.event_date}
                  </span>
                )}
                {result.extraction.event_type && (
                  <span style={{ fontSize: 12, color: "var(--text-secondary)", background: "var(--surface-soft)", padding: "2px 8px", borderRadius: 6 }}>
                    Type: {result.extraction.event_type}
                  </span>
                )}
                {result.extraction.missing_fields && result.extraction.missing_fields.length > 0 && (
                  <span style={{ fontSize: 12, color: "var(--warning, #b45309)", background: "rgba(180,83,9,0.06)", padding: "2px 8px", borderRadius: 6 }}>
                    Missing: {result.extraction.missing_fields.join(", ")}
                  </span>
                )}
              </div>
            )}
          </div>
        )}

        {/* Date resolution — intent + candidate dates with availability */}
        <DateResolutionPanel dateRequestRecord={result.dateRequestRecord} candidateDates={result.candidateDates} />

        {/* Parsed extraction JSON contract */}
        {result.extraction?.extraction_raw_response && (
          <ExtractionParsedJsonPanel rawResponse={result.extraction.extraction_raw_response} />
        )}

        {/* Room availability — only when a room was matched (no event date for freeform) */}
        {draft?.ai_context?.room_name && (
          <RoomAvailabilityCard
            restaurantId={restaurantId}
            rooms={rooms}
            roomName={draft.ai_context.room_name}
            eventDate={new Date().toISOString().slice(0, 10)}
          />
        )}

        {/* AI transparency — extraction (LLM Call 1) then draft (LLM Call 2) */}
        {result.extraction && (
          <ExtractionTransparencyPanel extraction={result.extraction} />
        )}
        {draft?.ai_context && (
          <AITransparencyPanel aiContext={draft.ai_context} label="LLM Call 2 — Draft Generation Details" />
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Link href={`/enquiries`}>
            <Button variant="primary" size="md">View in Enquiries</Button>
          </Link>
          <Button variant="secondary" size="md" onClick={onReset}>
            Send Another
          </Button>
        </div>
      </div>
    </Card>
  );
}

function FreeformEnquiryForm({ restaurants }: { restaurants: Restaurant[] }) {
  const [form, setForm] = useState<FreeformFormState>(FREEFORM_EMPTY);
  const [errors, setErrors] = useState<Partial<Record<keyof FreeformFormState, string>>>({});
  const [rooms, setRooms] = useState<Room[]>([]);
  const [roomsLoading, setRoomsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [step, setStep] = useState<string | null>(null); // progress label
  const [apiError, setApiError] = useState<string | null>(null);
  const [result, setResult] = useState<FreeformResult | null>(null);
  const [restaurantName, setRestaurantName] = useState<string>("");

  useEffect(() => {
    setForm((prev) => ({ ...prev, preferred_area: "" }));
    if (!form.restaurant_id) { setRooms([]); return; }
    setRoomsLoading(true);
    fetch(`${API_BASE}/api/v1/restaurants/${form.restaurant_id}/rooms?active_only=true&limit=50`)
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((d) => setRooms(d.items ?? []))
      .catch(() => setRooms([]))
      .finally(() => setRoomsLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.restaurant_id]);

  function set(key: keyof FreeformFormState, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }));
  }

  function validate(): boolean {
    const next: Partial<Record<keyof FreeformFormState, string>> = {};
    if (!form.restaurant_id) next.restaurant_id = "Please select a venue.";
    if (!form.first_name.trim()) next.first_name = "First name is required.";
    if (!form.last_name.trim()) next.last_name = "Last name is required.";
    if (!form.reply_email.trim()) next.reply_email = "Reply-to email is required.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.reply_email))
      next.reply_email = "Please enter a valid email address.";
    if (!form.message.trim()) next.message = "Please enter your enquiry message.";
    else if (form.message.trim().length < 20)
      next.message = "Message is too short — please provide more detail.";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setApiError(null);
    if (!validate()) return;

    const venueName =
      restaurants.find((r) => r.id === form.restaurant_id)?.name ?? "the venue";
    setRestaurantName(venueName);
    setSubmitting(true);

    try {
      // Single call: extraction → processing → draft
      setStep("Processing enquiry…");
      const intakeBody: Record<string, unknown> = {
        restaurant_id: form.restaurant_id,
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        email: form.reply_email.trim(),
        freeform_text: form.message.trim(),
      };
      if (form.audience_type) intakeBody.audience_type = form.audience_type;

      const intakeRes = await fetch(`${API_BASE}/api/v1/enquiries/intake/freeform`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(intakeBody),
      });

      if (!intakeRes.ok) {
        const text = await intakeRes.text().catch(() => intakeRes.statusText);
        throw new Error(text || `Intake failed (${intakeRes.status})`);
      }

      const intake: FreeformIntakeOut = await intakeRes.json();

      // Map freeform response to EnquiryDraft shape for the success panel
      const draft: EnquiryDraft | null = intake.draft_body
        ? {
            enquiry_id: intake.enquiry_id,
            message_id: intake.draft_message_id ?? "",
            subject: intake.draft_subject ?? null,
            body: intake.draft_body,
            generated_at: intake.created_at,
            is_fallback: intake.draft_is_fallback ?? null,
            model: null,
            persona_name: intake.persona_name ?? null,
            ai_context: intake.draft_ai_context ?? null,
          }
        : null;

      // Fetch date resolution data (best-effort, parallel)
      let dateRequestRecord: EnquiryDateRequestOut | null = null;
      let candidateDates: EnquiryCandidateDateOut[] = [];
      try {
        const [drRes, cdRes] = await Promise.all([
          fetch(`${API_BASE}/api/v1/enquiries/${intake.enquiry_id}/date-request/latest`),
          fetch(`${API_BASE}/api/v1/enquiries/${intake.enquiry_id}/candidate-dates`),
        ]);
        if (drRes.ok) dateRequestRecord = await drRes.json();
        if (cdRes.ok) candidateDates = await cdRes.json();
      } catch {
        // best-effort
      }

      // Send via SMTP (best-effort)
      let emailSent: boolean | null = null;
      let smtpDisabled = false;
      if (draft) {
        setStep("Sending email…");
        try {
          const sendRes = await fetch(`${API_BASE}/api/v1/email/send-draft`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              enquiry_id: intake.enquiry_id,
              to_email: form.reply_email.trim(),
            }),
          });
          if (sendRes.ok) {
            emailSent = true;
          } else if (sendRes.status === 503) {
            smtpDisabled = true;
          } else {
            emailSent = false;
          }
        } catch {
          emailSent = false;
        }
      }

      setResult({
        enquiry_id: intake.enquiry_id,
        reference: intake.reference,
        persona_name: intake.persona_name,
        audience_type: intake.audience_type,
        draft,
        emailSent,
        smtpDisabled,
        reply_email: form.reply_email.trim(),
        restaurantId: intake.restaurant_id,
        rooms,
        extraction: intake.extraction,
        recommended_action: intake.recommended_action,
        dateRequestRecord,
        candidateDates,
      });
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Submission failed. Please try again.");
    } finally {
      setSubmitting(false);
      setStep(null);
    }
  }

  if (result) {
    return (
      <FreeformSuccessPanel
        result={result}
        restaurantName={restaurantName}
        onReset={() => { setResult(null); setForm(FREEFORM_EMPTY); }}
      />
    );
  }

  const restaurantOptions = [
    { value: "", label: "Select a venue" },
    ...restaurants.map((r) => ({ value: r.id, label: r.name })),
  ];

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
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

        {/* Venue + Room + Audience */}
        <Card padding="lg">
          <SectionHeading
            title="Venue & Audience"
            subtitle="Select the venue, optionally a room, and the enquiry audience to test the matching persona."
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
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
            {form.restaurant_id && (
              <div style={{ maxWidth: 360 }}>
                {rooms.length > 0 ? (
                  <Select
                    label="Room / PDR (optional)"
                    value={form.preferred_area}
                    onChange={(e) => set("preferred_area", e.target.value)}
                    options={[
                      { value: "", label: roomsLoading ? "Loading rooms…" : "No specific room" },
                      ...rooms.map((r) => ({
                        value: r.name,
                        label: r.is_private_dining ? `${r.name} (PDR)` : r.name,
                      })),
                    ]}
                    helper="Helps the AI personalise the response."
                  />
                ) : (
                  !roomsLoading && (
                    <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
                      No rooms configured for this venue.
                    </p>
                  )
                )}
              </div>
            )}
            <div style={{ maxWidth: 420 }}>
              <Select
                label="Audience Type"
                value={form.audience_type}
                onChange={(e) => set("audience_type", e.target.value)}
                options={AUDIENCE_OPTIONS}
                helper="Determines which persona generates the AI reply."
              />
            </div>
          </div>
        </Card>

        {/* Guest details + reply email */}
        <Card padding="lg">
          <SectionHeading
            title="Guest Details"
            subtitle="The AI response will be sent to the reply-to address."
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
            <div style={{ maxWidth: 360 }}>
              <Input
                label="Reply-to Email"
                type="email"
                required
                value={form.reply_email}
                onChange={(e) => set("reply_email", e.target.value)}
                placeholder="guest@example.com"
                error={errors.reply_email}
                helper="The AI draft will be sent to this address via SMTP."
              />
            </div>
          </div>
        </Card>

        {/* Freeform message */}
        <Card padding="lg">
          <SectionHeading
            title="Enquiry Message"
            subtitle="Write the guest's enquiry in natural language. The AI will generate a personalised reply."
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label
              htmlFor="freeform-message"
              style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}
            >
              Message <span style={{ color: "var(--danger)" }}>*</span>
            </label>
            <textarea
              id="freeform-message"
              rows={7}
              value={form.message}
              onChange={(e) => set("message", e.target.value)}
              placeholder="e.g. Hi, I'm looking for a private dining room for 12 people for a birthday dinner in July. We'd love a set menu and would appreciate any wine pairing options. Our budget is around £1,500. Could you let me know what's available?"
              style={{
                width: "100%",
                borderRadius: 10,
                border: `1px solid ${errors.message ? "var(--danger)" : "var(--border)"}`,
                backgroundColor: "var(--surface)",
                color: "var(--text-primary)",
                fontSize: 13,
                padding: "10px 12px",
                resize: "vertical",
                outline: "none",
                fontFamily: "inherit",
                lineHeight: 1.7,
              }}
            />
            {errors.message && (
              <p style={{ fontSize: 12, color: "var(--danger)", marginTop: 2 }}>{errors.message}</p>
            )}
            <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
              Minimum 20 characters. Write as the guest would.
            </p>
          </div>
        </Card>

        {/* Submit */}
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
            <p style={{ fontSize: 12, color: "var(--text-muted)", margin: 0, lineHeight: 1.5 }}>
              On submit: enquiry created → AI draft generated → email sent to{" "}
              <strong style={{ color: "var(--text-secondary)" }}>
                {form.reply_email || DEFAULT_REPLY_EMAIL}
              </strong>
            </p>
            <Button type="submit" variant="primary" size="lg" loading={submitting}>
              {submitting && step ? step : "Send Enquiry"}
            </Button>
          </div>
        </Card>
      </div>
    </form>
  );
}

// ── Main export ────────────────────────────────────────────────────────────────

export function EnquiryWebform() {
  const [activeTab, setActiveTab] = useState<Tab>("structured");
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/restaurants?limit=100`)
      .then((r) => r.json())
      .then((d: RestaurantListOut) => setRestaurants(d.items ?? []))
      .catch(() => {});
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <TabBar active={activeTab} onChange={setActiveTab} />

      {activeTab === "structured" ? (
        <StructuredEnquiryForm restaurants={restaurants} />
      ) : (
        <FreeformEnquiryForm restaurants={restaurants} />
      )}
    </div>
  );
}
