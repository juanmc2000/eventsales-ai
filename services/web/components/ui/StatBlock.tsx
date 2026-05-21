import type { ReactNode } from "react";

// Accent color sequence per UI_COMPONENT_RULES.md: purple → pink → orange → teal
type Accent = "purple" | "pink" | "orange" | "teal";

type Props = {
  label: string;
  value: string | number;
  delta?: string;
  deltaPositive?: boolean;
  accent?: Accent;
  icon?: ReactNode;
};

const ACCENT_STYLES: Record<Accent, { bg: string; text: string; gradient: string }> = {
  purple: {
    bg: "rgba(109,61,245,0.1)",
    text: "var(--brand-purple)",
    gradient: "var(--gradient-purple)",
  },
  pink: {
    bg: "rgba(237,61,150,0.1)",
    text: "var(--brand-pink)",
    gradient: "linear-gradient(135deg, #ED3D96 0%, #FF7A1A 100%)",
  },
  orange: {
    bg: "rgba(255,122,26,0.1)",
    text: "var(--brand-orange)",
    gradient: "linear-gradient(135deg, #FF7A1A 0%, #F5B84B 100%)",
  },
  teal: {
    bg: "rgba(44,199,201,0.1)",
    text: "var(--brand-teal)",
    gradient: "var(--gradient-teal)",
  },
};

export function StatBlock({
  label,
  value,
  delta,
  deltaPositive,
  accent = "purple",
  icon,
}: Props) {
  const accentStyle = ACCENT_STYLES[accent];

  return (
    <div
      className="rounded-2xl border p-5 flex flex-col gap-3"
      style={{
        backgroundColor: "var(--surface)",
        borderColor: "var(--border)",
        boxShadow: "var(--shadow-card)",
      }}
    >
      {/* Accent icon tile */}
      {icon && (
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: accentStyle.bg }}
        >
          <span style={{ color: accentStyle.text }}>{icon}</span>
        </div>
      )}

      {/* Metric */}
      <div className="flex flex-col gap-0.5">
        <p
          className="text-xs font-medium uppercase tracking-wider"
          style={{ color: "var(--text-muted)" }}
        >
          {label}
        </p>
        <p
          className="text-2xl font-semibold tabular-nums"
          style={{ color: "var(--text-primary)" }}
        >
          {value}
        </p>
      </div>

      {/* Delta */}
      {delta && (
        <div className="flex items-center gap-1">
          <span
            className="text-xs font-medium"
            style={{
              color:
                deltaPositive === true
                  ? "var(--success)"
                  : deltaPositive === false
                    ? "var(--danger)"
                    : "var(--text-muted)",
            }}
          >
            {deltaPositive === true ? "▲" : deltaPositive === false ? "▼" : ""}{" "}
            {delta}
          </span>
        </div>
      )}
    </div>
  );
}
