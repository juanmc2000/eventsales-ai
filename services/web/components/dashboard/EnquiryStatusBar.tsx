import type { EnquiryStatusCount } from "@/lib/types/dashboard";

type Props = {
  items: EnquiryStatusCount[];
  total: number;
};

// Status display mapping
const STATUS_LABELS: Record<string, string> = {
  new: "New",
  open: "Open",
  follow_up: "Follow Up",
  proposal_sent: "Proposal Sent",
  confirmed: "Confirmed",
  cancelled: "Cancelled",
  lost: "Lost",
};

const STATUS_COLORS: Record<string, string> = {
  new: "var(--brand-purple)",
  open: "var(--brand-teal)",
  follow_up: "var(--brand-orange)",
  proposal_sent: "var(--brand-pink)",
  confirmed: "var(--success)",
  cancelled: "var(--text-muted)",
  lost: "var(--danger)",
};

export function EnquiryStatusBar({ items, total }: Props) {
  if (total === 0) {
    return (
      <p className="text-sm" style={{ color: "var(--text-muted)" }}>
        No enquiries yet.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Stacked bar */}
      <div className="flex h-2.5 rounded-full overflow-hidden gap-0.5">
        {items.map((item) => {
          const pct = (item.count / total) * 100;
          if (pct < 1) return null;
          return (
            <div
              key={item.status}
              className="h-full rounded-full"
              style={{
                width: `${pct}%`,
                backgroundColor: STATUS_COLORS[item.status] ?? "var(--border)",
              }}
            />
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-5 gap-y-2">
        {items.map((item) => (
          <div key={item.status} className="flex items-center gap-1.5">
            <span
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{
                backgroundColor: STATUS_COLORS[item.status] ?? "var(--border)",
              }}
            />
            <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
              {STATUS_LABELS[item.status] ?? item.status}{" "}
              <span className="font-semibold" style={{ color: "var(--text-primary)" }}>
                {item.count}
              </span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
