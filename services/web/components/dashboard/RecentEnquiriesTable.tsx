import Link from "next/link";
import type { RecentEnquiryItem } from "@/lib/types/dashboard";
import { Badge } from "@/components/ui/Badge";
import type { StatusVariant } from "@/components/ui/Badge";

type Props = {
  enquiries: RecentEnquiryItem[];
};

const STATUS_MAP: Record<string, StatusVariant> = {
  new: "new",
  open: "active",
  follow_up: "info-requested",
  proposal_sent: "proposal-sent",
  confirmed: "closed-won",
  cancelled: "closed-lost",
  lost: "closed-lost",
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

function formatDateTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

export function RecentEnquiriesTable({ enquiries }: Props) {
  if (enquiries.length === 0) {
    return (
      <p className="text-sm py-4" style={{ color: "var(--text-muted)" }}>
        No recent enquiries.
      </p>
    );
  }

  return (
    <div className="flex flex-col divide-y" style={{ borderColor: "var(--border)" }}>
      {enquiries.map((e) => (
        <div
          key={e.id}
          className="flex items-center gap-4 py-3"
        >
          {/* Avatar initial */}
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-semibold flex-shrink-0"
            style={{ background: "var(--gradient-purple)" }}
          >
            {e.first_name.charAt(0)}
          </div>

          {/* Name + reference */}
          <div className="flex-1 min-w-0">
            <p
              className="text-sm font-medium truncate"
              style={{ color: "var(--text-primary)" }}
            >
              {e.first_name} {e.last_name}
            </p>
            <p className="text-xs truncate" style={{ color: "var(--text-muted)" }}>
              {e.reference}
            </p>
          </div>

          {/* Event date */}
          <p className="text-xs flex-shrink-0" style={{ color: "var(--text-muted)" }}>
            {formatDate(e.event_date)}
          </p>

          {/* Created */}
          <p className="text-xs flex-shrink-0 hidden sm:block" style={{ color: "var(--text-muted)" }}>
            {formatDateTime(e.created_at)}
          </p>

          {/* Status */}
          <div className="flex-shrink-0">
            <Badge variant={STATUS_MAP[e.status] ?? "neutral"}>
              {e.status.replace(/_/g, " ")}
            </Badge>
          </div>
        </div>
      ))}

      <div className="pt-3">
        <Link
          href="/enquiries"
          className="text-sm font-medium transition-colors duration-150"
          style={{ color: "var(--brand-purple)" }}
        >
          View all enquiries →
        </Link>
      </div>
    </div>
  );
}
