"use client";

/**
 * PromptRunReviewPanel — collapsed quality review form for a prompt run.
 *
 * Renders only when a prompt_run_id is available (i.e. the draft was produced
 * by the live LLM, not the fallback provider).  Collapsed by default so it
 * stays out of the main enquiry workflow.
 *
 * UI-021: Add Prompt Run Quality Review Panel
 */

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/Button";
import type { PromptRunReviewOut, PromptRunReviewCreate } from "@/lib/types/enquiry";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Score field config ────────────────────────────────────────────────────────

const SCORE_FIELDS: Array<{ key: keyof PromptRunReviewCreate; label: string }> = [
  { key: "accuracy_score",           label: "Accuracy" },
  { key: "tone_fit_score",           label: "Tone Fit" },
  { key: "persona_fit_score",        label: "Persona Fit" },
  { key: "commercial_quality_score", label: "Commercial Quality" },
  { key: "completeness_score",       label: "Completeness" },
  { key: "hallucination_risk_score", label: "Hallucination Risk" },
];

// ─── Score input ───────────────────────────────────────────────────────────────

function ScoreInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label
        style={{
          display: "block",
          fontSize: 11,
          fontWeight: 600,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          marginBottom: 4,
        }}
      >
        {label}
      </label>
      <input
        type="number"
        min={0}
        max={5}
        step={0.5}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="—"
        style={{
          width: "100%",
          padding: "6px 10px",
          fontSize: 13,
          borderRadius: 6,
          border: "1px solid var(--border)",
          background: "var(--surface)",
          color: "var(--text-primary)",
          outline: "none",
        }}
      />
    </div>
  );
}

// ─── Saved review summary ─────────────────────────────────────────────────────

function SavedReviewSummary({ review }: { review: PromptRunReviewOut }) {
  const scored = SCORE_FIELDS.filter(({ key }) => review[key as keyof PromptRunReviewOut] != null);
  return (
    <div
      style={{
        padding: "10px 14px",
        borderRadius: 8,
        background: "rgba(22,166,106,0.06)",
        border: "1px solid rgba(22,166,106,0.2)",
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <span
          style={{
            fontSize: 11,
            fontWeight: 700,
            color: "#16A66A",
            background: "rgba(22,166,106,0.12)",
            padding: "2px 7px",
            borderRadius: 4,
            textTransform: "uppercase",
            letterSpacing: "0.06em",
          }}
        >
          Review saved
        </span>
        {review.ready_to_send != null && (
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: 4,
              background: review.ready_to_send
                ? "rgba(22,166,106,0.1)"
                : "rgba(239,68,68,0.08)",
              color: review.ready_to_send ? "#16A66A" : "#dc2626",
            }}
          >
            {review.ready_to_send ? "Ready to send" : "Not ready to send"}
          </span>
        )}
      </div>
      {scored.length > 0 && (
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {scored.map(({ key, label }) => (
            <span key={key} style={{ fontSize: 12, color: "var(--text-secondary)" }}>
              <span style={{ color: "var(--text-muted)" }}>{label}:</span>{" "}
              <strong>{String(review[key as keyof PromptRunReviewOut])}</strong>/5
            </span>
          ))}
        </div>
      )}
      {review.reviewer_notes && (
        <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
          {review.reviewer_notes}
        </p>
      )}
    </div>
  );
}

// ─── Panel ────────────────────────────────────────────────────────────────────

export function PromptRunReviewPanel({ promptRunId }: { promptRunId: string }) {
  const [open, setOpen] = useState(false);
  const [savedReview, setSavedReview] = useState<PromptRunReviewOut | null>(null);
  const [loadingReview, setLoadingReview] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Form state — all strings so inputs are controlled; parsed to numbers on submit
  const [scores, setScores] = useState<Record<string, string>>({});
  const [readyToSend, setReadyToSend] = useState<boolean | null>(null);
  const [notes, setNotes] = useState("");

  // Load the most recent review for this run
  const loadReview = useCallback(async () => {
    setLoadingReview(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/ai/prompt-runs/${promptRunId}/reviews?limit=1`
      );
      if (res.ok) {
        const data = await res.json();
        const latest: PromptRunReviewOut | null = data.items?.[0] ?? null;
        setSavedReview(latest);
        if (latest) {
          const loaded: Record<string, string> = {};
          for (const { key } of SCORE_FIELDS) {
            const v = latest[key as keyof PromptRunReviewOut];
            loaded[key] = v != null ? String(v) : "";
          }
          setScores(loaded);
          setReadyToSend(latest.ready_to_send ?? null);
          setNotes(latest.reviewer_notes ?? "");
        }
      }
    } catch {
      // Non-fatal — no review yet
    } finally {
      setLoadingReview(false);
    }
  }, [promptRunId]);

  useEffect(() => {
    loadReview();
  }, [loadReview]);

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    try {
      const payload: PromptRunReviewCreate = { prompt_run_id: promptRunId };
      for (const { key } of SCORE_FIELDS) {
        const raw = scores[key] ?? "";
        if (raw !== "") {
          const parsed = parseFloat(raw);
          if (!isNaN(parsed)) {
            (payload as Record<string, unknown>)[key] = parsed;
          }
        }
      }
      if (readyToSend !== null) payload.ready_to_send = readyToSend;
      if (notes.trim()) payload.reviewer_notes = notes.trim();

      const res = await fetch(
        `${API_BASE}/api/v1/ai/prompt-runs/${promptRunId}/reviews`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        setSaveError(detail?.detail ?? `Save failed (${res.status})`);
        return;
      }
      const saved: PromptRunReviewOut = await res.json();
      setSavedReview(saved);
    } catch {
      setSaveError("Network error — could not reach server");
    } finally {
      setSaving(false);
    }
  }

  function setScore(key: string, value: string) {
    setScores((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <div
      style={{
        borderRadius: 10,
        border: "1px solid var(--border)",
        overflow: "hidden",
        background: "var(--surface-soft)",
      }}
    >
      {/* Collapsed header */}
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 14px",
          background: "none",
          border: "none",
          cursor: "pointer",
          gap: 8,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              fontSize: 10,
              fontWeight: 700,
              color: "var(--brand-purple)",
              background: "rgba(109,61,245,0.1)",
              padding: "2px 7px",
              borderRadius: 4,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Quality Review
          </span>
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
            {savedReview ? "Review saved" : "Rate this draft"}
          </span>
        </div>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--text-muted)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ transform: open ? "rotate(180deg)" : "none", flexShrink: 0 }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {/* Expanded body */}
      {open && (
        <div
          style={{
            borderTop: "1px solid var(--border)",
            padding: "14px",
            display: "flex",
            flexDirection: "column",
            gap: 14,
          }}
        >
          {loadingReview ? (
            <p style={{ fontSize: 12, color: "var(--text-muted)" }}>Loading…</p>
          ) : (
            <>
              {/* Saved review summary */}
              {savedReview && <SavedReviewSummary review={savedReview} />}

              {/* Score grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {SCORE_FIELDS.map(({ key, label }) => (
                  <ScoreInput
                    key={key}
                    label={label}
                    value={scores[key] ?? ""}
                    onChange={(v) => setScore(key, v)}
                  />
                ))}
              </div>

              {/* Ready to send */}
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  cursor: "pointer",
                  fontSize: 13,
                  color: "var(--text-secondary)",
                }}
              >
                <input
                  type="checkbox"
                  checked={readyToSend === true}
                  onChange={(e) => setReadyToSend(e.target.checked ? true : null)}
                  style={{ width: 15, height: 15, accentColor: "var(--brand-purple)" }}
                />
                Ready to send
              </label>

              {/* Notes */}
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: 11,
                    fontWeight: 600,
                    color: "var(--text-muted)",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    marginBottom: 4,
                  }}
                >
                  Reviewer Notes
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Optional notes…"
                  rows={3}
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    fontSize: 13,
                    borderRadius: 6,
                    border: "1px solid var(--border)",
                    background: "var(--surface)",
                    color: "var(--text-primary)",
                    resize: "vertical",
                    outline: "none",
                    fontFamily: "inherit",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              {/* Save action */}
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <Button variant="primary" size="sm" onClick={handleSave} loading={saving}>
                  Save Review
                </Button>
                {saveError && (
                  <span style={{ fontSize: 12, color: "var(--danger)" }}>{saveError}</span>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
