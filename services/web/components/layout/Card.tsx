import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  className?: string;
  padding?: "none" | "sm" | "md" | "lg";
};

const PADDING = {
  none: "",
  sm: "p-4",
  md: "p-5",
  lg: "p-6",
};

/**
 * White rounded card — the standard content surface across all pages.
 * Uses design token --surface, --border, --shadow-card.
 */
export function Card({ children, className = "", padding = "md" }: Props) {
  return (
    <div
      className={`rounded-2xl border ${PADDING[padding]} ${className}`}
      style={{
        backgroundColor: "var(--surface)",
        borderColor: "var(--border)",
        boxShadow: "var(--shadow-card)",
      }}
    >
      {children}
    </div>
  );
}
