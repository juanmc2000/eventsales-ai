import type { DemandSpikeItem } from "@/lib/types/dashboard";
import { Badge } from "@/components/ui/Badge";
import Link from "next/link";

type Props = {
  spikes: DemandSpikeItem[];
};

const DEMAND_BADGE: Record<string, "warning" | "error" | "neutral"> = {
  high: "warning",
  very_high: "error",
};

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

export function DemandSpikesList({ spikes }: Props) {
  if (spikes.length === 0) {
    return (
      <p className="text-sm py-4" style={{ color: "var(--text-muted)" }}>
        No high-demand events in the next 30 days.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {spikes.slice(0, 5).map((spike) => (
        <div
          key={spike.id}
          className="flex items-center gap-3 px-3 py-2.5 rounded-xl"
          style={{ backgroundColor: "var(--surface-soft)", border: "1px solid var(--border)" }}
        >
          {/* Demand indicator dot */}
          <span
            className="w-2.5 h-2.5 rounded-full flex-shrink-0"
            style={{
              backgroundColor:
                spike.demand_level === "very_high"
                  ? "var(--danger)"
                  : "var(--warning)",
            }}
          />

          {/* Date */}
          <p
            className="text-xs font-medium flex-shrink-0 w-24"
            style={{ color: "var(--text-secondary)" }}
          >
            {formatDate(spike.event_date)}
          </p>

          {/* Restaurant */}
          <p
            className="text-sm font-medium flex-1 truncate"
            style={{ color: "var(--text-primary)" }}
          >
            {spike.restaurant_name}
          </p>

          {/* Meal period */}
          <p
            className="text-xs capitalize flex-shrink-0 hidden sm:block"
            style={{ color: "var(--text-muted)" }}
          >
            {spike.meal_period}
          </p>

          {/* Demand badge */}
          <Badge variant={DEMAND_BADGE[spike.demand_level] ?? "neutral"}>
            {spike.demand_level.replace("_", " ")}
          </Badge>
        </div>
      ))}

      {spikes.length > 0 && (
        <Link
          href="/calendar"
          className="text-sm font-medium mt-1 transition-colors duration-150"
          style={{ color: "var(--brand-purple)" }}
        >
          View full calendar →
        </Link>
      )}
    </div>
  );
}
