"use client";

import { useState, useEffect, useCallback } from "react";
import type { EmailEventRecord } from "@/lib/types/enquiry";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Status display config ─────────────────────────────────────────────────────

type StatusConfig = {
  label: string;
  color: string;
  bgColor: string;
  dotColor: string;
  description: string;
};

const STATUS_CONFIG: Record<string, StatusConfig> = {
  sent: {
    label: "Sent",
    color: "var(--success)",
    bgColor: "rgba(22,166,106,0.08)",
    dotColor: "var(--success)",
    description: "Email delivered via Gmail",
  },
  received: {
    label: "Received",
    color: "var(--brand-teal)",
    bgColor: "rgba(44,199,201,0.08)",
    dotColor: "var(--brand-teal)",
    description: "Inbound email received",
  },
  failed: {
    label: "Failed",
    color: "var(--danger)",
    bgColor: "rgba(229,72,77,0.08)",
    dotColor: "var(--danger)",
    description: "Send attempt failed",
  },
  disabled: {
    label: "Not Sent",
    color: "var(--text-muted)",
    bgColor: "rgba(154,148,173,0.08)",
    dotColor: "var(--text-muted)",
    description: "Gmail not configured",
  },
  queued: {
    label: "Queued",
    color: "var(--brand-orange)",
    bgColor: "rgba(255,122,26,0.08)",
    dotColor: "var(--brand-orange)",
    description: "Waiting to send",
  },
  sending: {
    label: "Sending",
    color: "var(--brand-purple)",
    bgColor: "rgba(109,61,245,0.08)",
    dotColor: "var(--brand-purple)",
    description: "Sending via Gmail",
  },
};

const DEFAULT_STATUS: StatusConfig = {
  label: "Unknown",
  color: "var(--text-muted)",
  bgColor: "rgba(154,148,173,0.08)",
  dotColor: "var(--text-muted)",
  description: "",
};

// ── Icons ─────────────────────────────────────────────────────────────────────

function OutboundIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z" />
    </svg>
  );
}
function InboundIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
      <polyline points="22,6 12,13 2,6" />
    </svg>
  );
}

// ── Timeline entry ────────────────────────────────────────────────────────────

function TimelineEntry({ event }: { event: EmailEventRecord }) {
  const cfg = STATUS_CONFIG[event.status] ?? DEFAULT_STATUS;
  const isOutbound = event.direction === "outbound";

  return (
    <div
      style={{
        display: "flex",
        gap: 12,
        alignItems: "flex-start",
      }}
    >
      {/* Timeline dot + line */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          paddingTop: 4,
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: cfg.dotColor,
            flexShrink: 0,
          }}
        />
      </div>

      {/* Content */}
      <div
        style={{
          flex: 1,
          padding: "8px 10px",
          borderRadius: 8,
          background: cfg.bgColor,
          border: `1px solid ${cfg.color}26`,
          minWidth: 0,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 8,
            flexWrap: "wrap",
            marginBottom: 4,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ color: cfg.color, display: "flex", alignItems: "center" }}>
              {isOutbound ? <OutboundIcon /> : <InboundIcon />}
            </span>
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                color: cfg.color,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              {cfg.label}
            </span>
            {cfg.description && (
              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                — {cfg.description}
              </span>
            )}
          </div>
          <time
            style={{
              fontSize: 11,
              color: "var(--text-muted)",
              whiteSpace: "nowrap",
              flexShrink: 0,
            }}
          >
            {new Date(event.created_at).toLocaleDateString("en-GB", {
              day: "numeric",
              month: "short",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </time>
        </div>

        {event.subject && (
          <p
            style={{
              fontSize: 12,
              color: "var(--text-secondary)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {event.subject}
          </p>
        )}

        {/* Show error summary for failed sends — no raw SMTP details */}
        {event.status === "failed" && event.error && (
          <p style={{ fontSize: 11, color: "var(--danger)", marginTop: 2 }}>
            {event.error.length > 80
              ? event.error.slice(0, 80) + "…"
              : event.error}
          </p>
        )}
      </div>
    </div>
  );
}

// ── EmailActivityTimeline ─────────────────────────────────────────────────────

export function EmailActivityTimeline({ enquiryId }: { enquiryId: string }) {
  const [events, setEvents] = useState<EmailEventRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/enquiries/${enquiryId}/email-events`
      );
      if (res.ok) {
        const data = await res.json();
        setEvents(Array.isArray(data) ? data : []);
      } else {
        // Endpoint not yet available — show empty state gracefully
        setEvents([]);
      }
    } catch {
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [enquiryId]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  if (loading) {
    return (
      <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
        Loading email activity…
      </p>
    );
  }

  if (events.length === 0) {
    return (
      <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
        No email activity recorded yet.
      </p>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {events.map((ev) => (
        <TimelineEntry key={ev.id} event={ev} />
      ))}
    </div>
  );
}
