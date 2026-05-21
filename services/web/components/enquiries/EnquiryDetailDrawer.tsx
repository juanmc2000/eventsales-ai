"use client";

import { useEffect, useState, useCallback } from "react";
import { StatusPill } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import type { Enquiry, EnquiryMessage, DraftResponseOut } from "@/lib/types/enquiry";
import type { Persona, PersonaListOut } from "@/lib/types/persona";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ALL_STATUSES = [
  "new",
  "open",
  "follow_up",
  "proposal_sent",
  "deposit_sent",
  "deposit_received",
  "closed_won",
  "closed_lost",
  "escalated",
];

// ─── Icons ───────────────────────────────────────────────────────────────────
function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}
function InboundIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  );
}
function OutboundIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z" />
    </svg>
  );
}
function PersonaIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

// ─── Field row ────────────────────────────────────────────────────────────────
function FieldRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 2, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</p>
      <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>{value || "—"}</p>
    </div>
  );
}

// ─── Section header ───────────────────────────────────────────────────────────
function DrawerSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3
        style={{
          fontSize: 12,
          fontWeight: 700,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          marginBottom: 12,
          paddingBottom: 8,
          borderBottom: "1px solid var(--border)",
        }}
      >
        {title}
      </h3>
      {children}
    </div>
  );
}

// ─── Message bubble ───────────────────────────────────────────────────────────
function MessageBubble({ message }: { message: EnquiryMessage }) {
  const isOutbound = message.direction === "outbound";
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: isOutbound ? "flex-end" : "flex-start",
        gap: 4,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--text-muted)" }}>
        {isOutbound ? <OutboundIcon /> : <InboundIcon />}
        <span style={{ fontSize: 11 }}>
          {isOutbound ? "Outbound" : "Inbound"} · {message.channel}
          {message.sent_at
            ? ` · ${new Date(message.sent_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}`
            : ""}
        </span>
      </div>
      {message.subject && (
        <p style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>{message.subject}</p>
      )}
      <div
        style={{
          maxWidth: "85%",
          padding: "10px 14px",
          borderRadius: isOutbound ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
          background: isOutbound ? "rgba(109,61,245,0.08)" : "var(--surface-soft)",
          border: `1px solid ${isOutbound ? "rgba(109,61,245,0.2)" : "var(--border)"}`,
          fontSize: 13,
          color: "var(--text-secondary)",
          lineHeight: 1.6,
          whiteSpace: "pre-wrap",
        }}
      >
        {message.body}
      </div>
    </div>
  );
}

// ─── Icons ───────────────────────────────────────────────────────────────────
function SparkleIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z" />
    </svg>
  );
}
function RefreshIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" /><path d="M21 3v5h-5" /><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" /><path d="M8 16H3v5" />
    </svg>
  );
}

// ─── Draft response section ────────────────────────────────────────────────────
type DraftState = "idle" | "loading" | "ready" | "error";

function DraftSection({ enquiryId }: { enquiryId: string }) {
  const [draftState, setDraftState] = useState<DraftState>("idle");
  const [draft, setDraft] = useState<DraftResponseOut | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  async function handleGenerate() {
    setDraftState("loading");
    setErrorMsg(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/enquiries/${enquiryId}/draft`, { method: "POST" });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `HTTP ${res.status}`);
      }
      const data: DraftResponseOut = await res.json();
      setDraft(data);
      setDraftState("ready");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to generate draft.");
      setDraftState("error");
    }
  }

  if (draftState === "idle") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "flex-start" }}>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
          Generate a persona-based draft response using this enquiry's assigned persona, event details, and pricing recommendation.
        </p>
        <Button variant="primary" size="sm" icon={<SparkleIcon />} onClick={handleGenerate}>
          Generate Draft
        </Button>
      </div>
    );
  }

  if (draftState === "loading") {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "16px 0" }}>
        <div style={{ width: 16, height: 16, border: "2px solid rgba(109,61,245,0.3)", borderTopColor: "var(--brand-purple)", borderRadius: "50%", animation: "spin 0.8s linear infinite", flexShrink: 0 }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        <span style={{ fontSize: 13, color: "var(--text-muted)" }}>Generating draft response…</span>
      </div>
    );
  }

  if (draftState === "error") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <p style={{ fontSize: 13, color: "#dc2626" }}>{errorMsg}</p>
        <Button variant="secondary" size="sm" onClick={handleGenerate}>Retry</Button>
      </div>
    );
  }

  if (draftState === "ready" && draft) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          {draft.persona_name && (
            <span style={{ fontSize: 11, fontWeight: 700, color: "var(--brand-purple)", background: "rgba(109,61,245,0.1)", padding: "2px 8px", borderRadius: 4 }}>
              {draft.persona_name}
            </span>
          )}
          <span style={{ fontSize: 11, color: "var(--brand-orange)", background: "rgba(251,146,60,0.1)", padding: "2px 8px", borderRadius: 4, fontWeight: 600 }}>
            Draft — Not Sent
          </span>
          {draft.is_fallback && (
            <span style={{ fontSize: 11, color: "var(--text-muted)", background: "var(--surface-soft)", padding: "2px 8px", borderRadius: 4 }}>
              Template fallback
            </span>
          )}
        </div>
        {draft.subject && (
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{draft.subject}</p>
        )}
        <div style={{ padding: "12px 14px", borderRadius: 8, background: "var(--surface-soft)", border: "1px solid var(--border)", fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
          {draft.body}
        </div>
        {(draft.recommended_minimum_spend != null || draft.pricing_explanation) && (
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
            {draft.pricing_explanation ?? `Recommended minimum spend: £${draft.recommended_minimum_spend?.toLocaleString()}`}
          </p>
        )}
        <Button variant="secondary" size="sm" icon={<RefreshIcon />} onClick={handleGenerate}>
          Regenerate
        </Button>
      </div>
    );
  }

  return null;
}

// ─── Drawer component ─────────────────────────────────────────────────────────
export function EnquiryDetailDrawer({
  enquiry: initialEnquiry,
  restaurantName,
  onClose,
  onStatusUpdated,
}: {
  enquiry: Enquiry;
  restaurantName: string;
  onClose: () => void;
  onStatusUpdated?: (updated: Enquiry) => void;
}) {
  const [enquiry, setEnquiry] = useState<Enquiry>(initialEnquiry);
  const [messages, setMessages] = useState<EnquiryMessage[]>([]);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(true);
  const [statusValue, setStatusValue] = useState(enquiry.status);
  const [updatingStatus, setUpdatingStatus] = useState(false);

  // Escape to close
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  // Load messages and personas in parallel
  const loadDetails = useCallback(() => {
    setLoadingMessages(true);
    Promise.all([
      fetch(`${API_BASE}/api/v1/enquiries/${enquiry.id}/messages`)
        .then((r) => (r.ok ? r.json() : []))
        .catch(() => []),
      fetch(`${API_BASE}/api/v1/personas`)
        .then((r) => (r.ok ? r.json() : { items: [] }))
        .then((d: PersonaListOut) => d.items ?? [])
        .catch(() => []),
    ]).then(([msgs, ps]) => {
      setMessages(msgs);
      setPersonas(ps);
    }).finally(() => setLoadingMessages(false));
  }, [enquiry.id]);

  useEffect(() => {
    loadDetails();
  }, [loadDetails]);

  const assignedPersona = personas.find((p) => p.id === enquiry.persona_id);

  // Status update
  async function handleStatusUpdate() {
    if (statusValue === enquiry.status) return;
    setUpdatingStatus(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/enquiries/${enquiry.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: statusValue }),
      });
      if (res.ok) {
        const updated: Enquiry = await res.json();
        setEnquiry(updated);
        onStatusUpdated?.(updated);
      }
    } finally {
      setUpdatingStatus(false);
    }
  }

  const statusOptions = ALL_STATUSES.map((s) => ({
    value: s,
    label: s.replace(/_/g, " "),
  }));

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(7,10,31,0.45)",
          zIndex: 40,
        }}
      />

      {/* Drawer panel */}
      <div
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          bottom: 0,
          width: 580,
          background: "var(--surface)",
          zIndex: 50,
          display: "flex",
          flexDirection: "column",
          boxShadow: "var(--shadow-hover)",
        }}
      >
        {/* ── Header ──────────────────────────────────────────────────── */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid var(--border)",
            flexShrink: 0,
          }}
        >
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4, flexWrap: "wrap" }}>
                <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
                  {enquiry.first_name} {enquiry.last_name}
                </h2>
                <StatusPill status={enquiry.status as import("@/components/ui/Badge").StatusVariant} />
              </div>
              <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
                <span
                  style={{
                    fontFamily: "monospace",
                    color: "var(--brand-purple)",
                    background: "rgba(109,61,245,0.08)",
                    padding: "1px 5px",
                    borderRadius: 3,
                    marginRight: 8,
                  }}
                >
                  {enquiry.reference}
                </span>
                {restaurantName}
              </p>
            </div>
            <button
              onClick={onClose}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "var(--text-muted)",
                padding: 4,
                borderRadius: 6,
                display: "flex",
                alignItems: "center",
              }}
            >
              <CloseIcon />
            </button>
          </div>
        </div>

        {/* ── Scrollable body ─────────────────────────────────────────── */}
        <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px", display: "flex", flexDirection: "column", gap: 20 }}>

          {/* Status update control */}
          <DrawerSection title="Status">
            <div style={{ display: "flex", gap: 10, alignItems: "flex-end" }}>
              <div style={{ flex: 1 }}>
                <Select
                  label=""
                  value={statusValue}
                  onChange={(e) => setStatusValue(e.target.value)}
                  options={statusOptions}
                />
              </div>
              <Button
                variant="primary"
                size="sm"
                onClick={handleStatusUpdate}
                loading={updatingStatus}
                disabled={statusValue === enquiry.status}
              >
                Update
              </Button>
            </div>
          </DrawerSection>

          {/* Customer & event details */}
          <DrawerSection title="Customer & Event">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <FieldRow label="Email" value={enquiry.email} />
              <FieldRow label="Phone" value={enquiry.phone ?? ""} />
              <FieldRow label="Company" value={enquiry.company_name ?? ""} />
              <FieldRow label="Party Size" value={enquiry.party_size?.toString() ?? ""} />
              <FieldRow
                label="Event Date"
                value={
                  enquiry.event_date
                    ? new Date(enquiry.event_date).toLocaleDateString("en-GB", {
                        weekday: "short",
                        day: "numeric",
                        month: "long",
                        year: "numeric",
                      })
                    : ""
                }
              />
              <FieldRow label="Event Type" value={enquiry.event_type ?? ""} />
              <FieldRow label="Preferred Area" value={enquiry.preferred_area ?? ""} />
              <FieldRow label="Source" value={enquiry.source} />
            </div>
          </DrawerSection>

          {/* Pricing recommendation */}
          <DrawerSection title="Pricing Recommendation">
            {enquiry.recommended_minimum_spend != null ? (
              <div
                style={{
                  padding: "14px 18px",
                  borderRadius: 10,
                  background: "rgba(109,61,245,0.06)",
                  border: "1px solid rgba(109,61,245,0.2)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <div>
                  <p style={{ fontSize: 11, color: "var(--brand-purple)", fontWeight: 600, marginBottom: 2, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    Recommended Minimum Spend
                  </p>
                  <p style={{ fontSize: 26, fontWeight: 700, color: "var(--brand-purple)" }}>
                    £{Math.round(enquiry.recommended_minimum_spend).toLocaleString()}
                  </p>
                  <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
                    Determined by active pricing rules · confidence 100%
                  </p>
                </div>
              </div>
            ) : (
              <p style={{ fontSize: 13, color: "var(--text-muted)" }}>No recommendation generated yet.</p>
            )}
            {enquiry.budget_indication && (
              <div style={{ marginTop: 10 }}>
                <p style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 2, textTransform: "uppercase", letterSpacing: "0.05em" }}>Guest Budget Indication</p>
                <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>{enquiry.budget_indication}</p>
              </div>
            )}
          </DrawerSection>

          {/* Assigned persona */}
          <DrawerSection title="Assigned Persona">
            {assignedPersona ? (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "12px 14px",
                  borderRadius: 10,
                  background: "var(--surface-soft)",
                  border: "1px solid var(--border)",
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: "50%",
                    background: "var(--gradient-purple)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#fff",
                    flexShrink: 0,
                  }}
                >
                  <PersonaIcon />
                </div>
                <div>
                  <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{assignedPersona.name}</p>
                  <p style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "capitalize" }}>
                    {assignedPersona.tone} · {assignedPersona.style}
                  </p>
                </div>
              </div>
            ) : (
              <p style={{ fontSize: 13, color: "var(--text-muted)" }}>No persona assigned.</p>
            )}
          </DrawerSection>

          {/* Initial message */}
          {enquiry.message && (
            <DrawerSection title="Initial Request">
              <div
                style={{
                  padding: "12px 14px",
                  borderRadius: 8,
                  background: "var(--surface-soft)",
                  border: "1px solid var(--border)",
                  fontSize: 13,
                  color: "var(--text-secondary)",
                  lineHeight: 1.7,
                  whiteSpace: "pre-wrap",
                }}
              >
                {enquiry.message}
              </div>
            </DrawerSection>
          )}

          {/* Dietary / special requests */}
          {(enquiry.dietary_requirements || enquiry.special_requests) && (
            <DrawerSection title="Additional Requirements">
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                {enquiry.dietary_requirements && (
                  <FieldRow label="Dietary Requirements" value={enquiry.dietary_requirements} />
                )}
                {enquiry.special_requests && (
                  <FieldRow label="Special Requests" value={enquiry.special_requests} />
                )}
              </div>
            </DrawerSection>
          )}

          {/* Message thread */}
          <DrawerSection title={`Message Thread (${messages.length})`}>
            {loadingMessages ? (
              <p style={{ fontSize: 13, color: "var(--text-muted)" }}>Loading messages…</p>
            ) : messages.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--text-muted)" }}>No messages yet.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}
              </div>
            )}
          </DrawerSection>

          {/* Draft response */}
          <DrawerSection title="Draft Response">
            <DraftSection enquiryId={enquiry.id} />
          </DrawerSection>

          {/* Notes */}
          {enquiry.notes && (
            <DrawerSection title="Notes">
              <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>{enquiry.notes}</p>
            </DrawerSection>
          )}

          {/* Timestamps */}
          <div
            style={{
              paddingTop: 10,
              borderTop: "1px solid var(--border)",
              display: "flex",
              gap: 16,
              fontSize: 12,
              color: "var(--text-muted)",
            }}
          >
            <span>Created {new Date(enquiry.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}</span>
            <span>·</span>
            <span>Updated {new Date(enquiry.updated_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}</span>
          </div>
        </div>
      </div>
    </>
  );
}
