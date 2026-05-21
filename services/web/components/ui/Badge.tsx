import type { ReactNode } from "react";

// ── Status language per UI_COMPONENT_RULES.md ──────────────────────────────
export type StatusVariant =
  | "new"
  | "hot-lead"
  | "info-requested"
  | "proposal-sent"
  | "viewed"
  | "deposit-sent"
  | "deposit-received"
  | "closed-won"
  | "closed-lost"
  | "escalated"
  | "active"
  | "inactive"
  | "healthy"
  | "warning"
  | "error"
  | "neutral";

type BadgeProps = {
  variant?: StatusVariant | "purple" | "pink" | "orange" | "teal" | "gold";
  children: ReactNode;
  dot?: boolean;
};

const STATUS_LABELS: Record<StatusVariant, string> = {
  "new": "New",
  "hot-lead": "Hot Lead",
  "info-requested": "Information Requested",
  "proposal-sent": "Proposal Sent",
  "viewed": "Viewed",
  "deposit-sent": "Deposit Link Sent",
  "deposit-received": "Deposit Received",
  "closed-won": "Closed Won",
  "closed-lost": "Closed Lost",
  "escalated": "Escalated",
  "active": "Active",
  "inactive": "Inactive",
  "healthy": "Healthy",
  "warning": "Warning",
  "error": "Error",
  "neutral": "—",
};

const VARIANT_STYLES: Record<string, React.CSSProperties> = {
  new: { backgroundColor: "rgba(109,61,245,0.12)", color: "var(--brand-purple)" },
  "hot-lead": { backgroundColor: "rgba(237,61,150,0.12)", color: "var(--brand-pink)" },
  "info-requested": { backgroundColor: "rgba(255,122,26,0.12)", color: "var(--brand-orange)" },
  "proposal-sent": { backgroundColor: "rgba(44,199,201,0.12)", color: "var(--brand-teal)" },
  viewed: { backgroundColor: "rgba(245,184,75,0.12)", color: "var(--brand-gold)" },
  "deposit-sent": { backgroundColor: "rgba(109,61,245,0.12)", color: "var(--brand-purple)" },
  "deposit-received": { backgroundColor: "rgba(22,166,106,0.12)", color: "var(--success)" },
  "closed-won": { backgroundColor: "rgba(22,166,106,0.12)", color: "var(--success)" },
  "closed-lost": { backgroundColor: "rgba(229,72,77,0.12)", color: "var(--danger)" },
  escalated: { backgroundColor: "rgba(229,72,77,0.12)", color: "var(--danger)" },
  active: { backgroundColor: "rgba(22,166,106,0.12)", color: "var(--success)" },
  inactive: { backgroundColor: "rgba(107,102,128,0.12)", color: "var(--text-secondary)" },
  healthy: { backgroundColor: "rgba(22,166,106,0.12)", color: "var(--success)" },
  warning: { backgroundColor: "rgba(233,154,28,0.12)", color: "var(--warning)" },
  error: { backgroundColor: "rgba(229,72,77,0.12)", color: "var(--danger)" },
  neutral: { backgroundColor: "rgba(107,102,128,0.1)", color: "var(--text-muted)" },
  purple: { backgroundColor: "rgba(109,61,245,0.12)", color: "var(--brand-purple)" },
  pink: { backgroundColor: "rgba(237,61,150,0.12)", color: "var(--brand-pink)" },
  orange: { backgroundColor: "rgba(255,122,26,0.12)", color: "var(--brand-orange)" },
  teal: { backgroundColor: "rgba(44,199,201,0.12)", color: "var(--brand-teal)" },
  gold: { backgroundColor: "rgba(245,184,75,0.12)", color: "var(--brand-gold)" },
};

export function Badge({ variant = "neutral", children, dot = false }: BadgeProps) {
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium"
      style={VARIANT_STYLES[variant] ?? VARIANT_STYLES.neutral}
    >
      {dot && (
        <span
          className="w-1.5 h-1.5 rounded-full flex-shrink-0"
          style={{ backgroundColor: "currentColor" }}
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  );
}

/** Convenience: render a badge for a known StatusVariant with the canonical label. */
export function StatusPill({ status }: { status: StatusVariant }) {
  return (
    <Badge variant={status} dot>
      {STATUS_LABELS[status]}
    </Badge>
  );
}
