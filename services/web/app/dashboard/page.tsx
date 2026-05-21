import { PageContainer } from "@/components/layout/PageContainer";
import { Card } from "@/components/layout/Card";
import { StatBlock } from "@/components/ui/StatBlock";
import { EnquiryStatusBar } from "@/components/dashboard/EnquiryStatusBar";
import { RecentEnquiriesTable } from "@/components/dashboard/RecentEnquiriesTable";
import { DemandSpikesList } from "@/components/dashboard/DemandSpikesList";
import type { DashboardSummary } from "@/lib/types/dashboard";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Server component — fetches data at render time
async function fetchDashboardSummary(): Promise<DashboardSummary | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/dashboard/summary?recent_limit=8`, {
      next: { revalidate: 30 }, // revalidate every 30s
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

function PlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

function EnquiryIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  );
}

function PricingIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </svg>
  );
}

// Quick action links
const QUICK_LINKS = [
  { label: "New Enquiry", href: "/enquiries", accent: "var(--brand-purple)" },
  { label: "Pricing Rules", href: "/pricing-rules", accent: "var(--brand-pink)" },
  { label: "Calendar", href: "/calendar", accent: "var(--brand-orange)" },
  { label: "Personas", href: "/personas", accent: "var(--brand-teal)" },
];

export default async function DashboardPage() {
  const summary = await fetchDashboardSummary();

  const totalEnquiries = summary?.enquiry_totals.total ?? 0;
  const pendingCount = summary?.pending_follow_ups.length ?? 0;
  const demandSpikeCount = summary?.upcoming_demand_spikes.length ?? 0;
  const avgSpend = summary?.pricing_summary.average_minimum_spend;

  return (
    <PageContainer>
      {/* Welcome header */}
      <div>
        <h2
          className="text-2xl font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          Welcome back
        </h2>
        <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>
          {"Here's what's happening across your portfolio today."}
        </p>
      </div>

      {/* KPI stat cards — purple → pink → orange → teal */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatBlock
          label="Total Enquiries"
          value={totalEnquiries}
          accent="purple"
          icon={<EnquiryIcon />}
        />
        <StatBlock
          label="Pending Follow-ups"
          value={pendingCount}
          accent="pink"
          icon={<ClockIcon />}
        />
        <StatBlock
          label="Demand Spikes (30d)"
          value={demandSpikeCount}
          accent="orange"
          icon={<AlertIcon />}
        />
        <StatBlock
          label="Avg. Min. Spend"
          value={avgSpend != null ? `£${avgSpend.toFixed(0)}` : "—"}
          accent="teal"
          icon={<PricingIcon />}
        />
      </div>

      {/* Main grid — 2 columns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Pipeline overview — span 2 */}
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3
              className="text-sm font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
              Enquiry Pipeline
            </h3>
            <Link
              href="/enquiries"
              className="text-xs font-medium transition-colors duration-150"
              style={{ color: "var(--brand-purple)" }}
            >
              View all
            </Link>
          </div>
          {summary ? (
            <EnquiryStatusBar
              items={summary.enquiry_totals.by_status}
              total={totalEnquiries}
            />
          ) : (
            <div className="h-8 rounded animate-pulse" style={{ backgroundColor: "var(--border)" }} />
          )}
        </Card>

        {/* Quick links — span 1 */}
        <Card>
          <h3
            className="text-sm font-semibold mb-4"
            style={{ color: "var(--text-primary)" }}
          >
            Quick Actions
          </h3>
          <div className="flex flex-col gap-2">
            {QUICK_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors duration-150"
                style={{ backgroundColor: "var(--surface-soft)", border: "1px solid var(--border)" }}
              >
                <span
                  className="w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ backgroundColor: link.accent + "20", color: link.accent }}
                >
                  <PlusIcon />
                </span>
                <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  {link.label}
                </span>
              </Link>
            ))}
          </div>
        </Card>
      </div>

      {/* Bottom grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Recent enquiries */}
        <Card>
          <h3
            className="text-sm font-semibold mb-4"
            style={{ color: "var(--text-primary)" }}
          >
            Recent Enquiries
          </h3>
          {summary ? (
            <RecentEnquiriesTable enquiries={summary.recent_enquiries} />
          ) : (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className="h-10 rounded-lg animate-pulse"
                  style={{ backgroundColor: "var(--border)" }}
                />
              ))}
            </div>
          )}
        </Card>

        {/* Upcoming demand spikes */}
        <Card>
          <h3
            className="text-sm font-semibold mb-4"
            style={{ color: "var(--text-primary)" }}
          >
            Upcoming Demand Spikes
          </h3>
          {summary ? (
            <DemandSpikesList spikes={summary.upcoming_demand_spikes} />
          ) : (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div
                  key={i}
                  className="h-10 rounded-xl animate-pulse"
                  style={{ backgroundColor: "var(--border)" }}
                />
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* By restaurant breakdown */}
      {summary && summary.enquiry_totals.by_restaurant.length > 0 && (
        <Card>
          <h3
            className="text-sm font-semibold mb-4"
            style={{ color: "var(--text-primary)" }}
          >
            Enquiries by Restaurant
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {summary.enquiry_totals.by_restaurant.map((r) => (
              <div
                key={r.restaurant_id}
                className="flex flex-col gap-1 px-4 py-3 rounded-xl"
                style={{
                  backgroundColor: "var(--surface-soft)",
                  border: "1px solid var(--border)",
                }}
              >
                <p
                  className="text-xl font-semibold tabular-nums"
                  style={{ color: "var(--text-primary)" }}
                >
                  {r.count}
                </p>
                <p
                  className="text-xs truncate"
                  style={{ color: "var(--text-secondary)" }}
                >
                  {r.restaurant_name}
                </p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* API unavailable fallback */}
      {!summary && (
        <Card>
          <p className="text-sm text-center py-6" style={{ color: "var(--text-muted)" }}>
            Dashboard data unavailable. Start the backend API to load live data.
          </p>
        </Card>
      )}
    </PageContainer>
  );
}
