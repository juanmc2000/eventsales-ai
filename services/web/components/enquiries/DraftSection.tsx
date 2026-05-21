"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/Button";
import { api, ApiError } from "@/lib/api";
import type { EnquiryDraft } from "@/lib/types/enquiry";

// ─── Icons ────────────────────────────────────────────────────────────────────
function SendIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z" />
    </svg>
  );
}
function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

// ─── Types ────────────────────────────────────────────────────────────────────
type SendState =
  | { kind: "idle" }
  | { kind: "sending" }
  | { kind: "sent" }
  | { kind: "failed"; message: string }
  | { kind: "gmail_disabled" };

// ─── DraftSection ─────────────────────────────────────────────────────────────
export function DraftSection({
  enquiryId,
  toEmail,
}: {
  enquiryId: string;
  toEmail: string;
}) {
  const [draft, setDraft] = useState<EnquiryDraft | null>(null);
  const [generating, setGenerating] = useState(false);
  const [sendState, setSendState] = useState<SendState>({ kind: "idle" });

  const fetchDraft = useCallback(async () => {
    try {
      const data = await api.get<EnquiryDraft>(
        `/api/v1/enquiries/${enquiryId}/draft`
      );
      if (data?.body) setDraft(data);
    } catch {
      // No draft found or endpoint unavailable — stay in no-draft state
    }
  }, [enquiryId]);

  useEffect(() => {
    fetchDraft();
  }, [fetchDraft]);

  async function handleGenerateDraft() {
    setGenerating(true);
    try {
      const data = await api.post<EnquiryDraft>(
        `/api/v1/enquiries/${enquiryId}/draft`
      );
      if (data?.body) setDraft(data);
    } catch {
      // Generation not available yet — no-op, stays in no_draft state
    } finally {
      setGenerating(false);
    }
  }

  async function handleSendDraft() {
    if (!draft) return;
    setSendState({ kind: "sending" });
    try {
      await api.post("/api/v1/email/send-draft", {
        enquiry_id: enquiryId,
        to_email: toEmail,
      });
      setSendState({ kind: "sent" });
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        setSendState({ kind: "gmail_disabled" });
      } else {
        const msg =
          err instanceof ApiError ? err.message : "Network error — could not reach server";
        setSendState({ kind: "failed", message: msg });
      }
    }
  }

  // ── No draft ────────────────────────────────────────────────────────────────
  if (!draft) {
    return (
      <div
        style={{
          padding: "16px",
          borderRadius: 10,
          background: "rgba(109,61,245,0.04)",
          border: "1px dashed rgba(109,61,245,0.3)",
          display: "flex",
          flexDirection: "column",
          gap: 10,
          alignItems: "flex-start",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              fontSize: 10,
              fontWeight: 700,
              color: "var(--brand-purple)",
              background: "rgba(109,61,245,0.12)",
              padding: "2px 7px",
              borderRadius: 4,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Coming Soon
          </span>
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
            AI-assisted draft response
          </span>
        </div>
        <p
          style={{
            fontSize: 13,
            color: "var(--text-secondary)",
            lineHeight: 1.6,
          }}
        >
          No draft generated yet. Generate a persona-aware response to proceed
          with email sending.
        </p>
        <Button
          variant="secondary"
          size="sm"
          onClick={handleGenerateDraft}
          loading={generating}
        >
          Generate Draft
        </Button>
      </div>
    );
  }

  // ── Has draft ───────────────────────────────────────────────────────────────
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Draft content */}
      <div>
        {draft.subject && (
          <p
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: "var(--text-secondary)",
              marginBottom: 6,
            }}
          >
            Subject: {draft.subject}
          </p>
        )}
        <div
          style={{
            padding: "12px 14px",
            borderRadius: 8,
            background: "rgba(109,61,245,0.04)",
            border: "1px solid rgba(109,61,245,0.15)",
            fontSize: 13,
            color: "var(--text-secondary)",
            lineHeight: 1.7,
            whiteSpace: "pre-wrap",
            maxHeight: 200,
            overflowY: "auto",
          }}
        >
          {draft.body}
        </div>
      </div>

      {/* Send action row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          flexWrap: "wrap",
        }}
      >
        {sendState.kind === "idle" && (
          <Button
            variant="primary"
            size="sm"
            onClick={handleSendDraft}
            icon={<SendIcon />}
          >
            Send Draft
          </Button>
        )}

        {sendState.kind === "sending" && (
          <Button variant="primary" size="sm" loading>
            Send Draft
          </Button>
        )}

        {sendState.kind === "sent" && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: 13,
              color: "var(--success)",
              fontWeight: 500,
            }}
          >
            <CheckIcon />
            <span>Sent — test email only</span>
          </div>
        )}

        {sendState.kind === "failed" && (
          <>
            <span
              style={{ fontSize: 12, color: "var(--danger)" }}
            >
              Send failed: {sendState.message}
            </span>
            <Button variant="secondary" size="sm" onClick={handleSendDraft}>
              Retry
            </Button>
          </>
        )}

        {sendState.kind === "gmail_disabled" && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 12px",
              borderRadius: 8,
              background: "rgba(109,61,245,0.04)",
              border: "1px dashed rgba(109,61,245,0.25)",
            }}
          >
            <span
              style={{
                fontSize: 10,
                fontWeight: 700,
                color: "var(--brand-purple)",
                background: "rgba(109,61,245,0.12)",
                padding: "2px 7px",
                borderRadius: 4,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              Coming Soon
            </span>
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              Gmail not configured — set SMTP credentials to activate email sending
            </span>
          </div>
        )}

        {/* Test-only disclaimer */}
        {(sendState.kind === "idle" || sendState.kind === "sending") && (
          <span
            style={{
              fontSize: 11,
              color: "var(--text-muted)",
              fontStyle: "italic",
            }}
          >
            Test email only — no real customers will be contacted
          </span>
        )}
      </div>
    </div>
  );
}
