"use client";

import { useEffect, useState } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/layout/Card";
import { StatBlock } from "@/components/ui/StatBlock";
import { Badge } from "@/components/ui/Badge";
import type { DashboardSummary } from "@/lib/types/dashboard";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Status colour map ──────────────────────────────────────────────────────
const STATUS_COLORS: Record<string, string> = {
  new: "#6D3DF5",
  open: "#2CC7C9",
  follow_up: "#F5B84B",
  proposal_sent: "#ED3D96",
  deposit_sent: "#FF7A1A",
  deposit_received: "#16A66A",
  closed_won: "#16A66A",
  closed_lost: "#E5484D",
  escalated: "#E99A1C",
};

const DEMAND_COLORS: Record<string, string> = {
  very_high: "#E5484D",
  high: "#E99A1C",
  medium: "#2CC7C9",
  low: "#9A94AD",
};

// ─── Horizontal bar chart ───────────────────────────────────────────────────
function HorizontalBar({
  items,
  maxValue,
}: {
  items: { label: string; value: number; color: string }[];
  maxValue: number;
}) {
  if (!items.length) return <p style={{ color: "var(--text-muted)", fontSize: 14 }}>No data</p>;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {items.map((item) => (
        <div key={item.label} style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span
            style={{
              width: 140,
              fontSize: 13,
              color: "var(--text-secondary)",
              flexShrink: 0,
              textAlign: "right",
              textTransform: "capitalize",
            }}
          >
            {item.label.replace(/_/g, " ")}
          </span>
          <div
            style={{
              flex: 1,
              background: "var(--border)",
              borderRadius: 4,
              height: 12,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${maxValue > 0 ? (item.value / maxValue) * 100 : 0}%`,
                height: "100%",
                background: item.color,
                borderRadius: 4,
                transition: "width 0.4s ease-out",
              }}
            />
          </div>
          <span
            style={{
              width: 32,
              fontSize: 13,
              fontWeight: 600,
              color: "var(--text-primary)",
              flexShrink: 0,
              textAlign: "right",
            }}
          >
            {item.value}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Status pill legend ──────────────────────────────────────────────────────
function SummaryPills({ items }: { items: { label: string; value: number; color: string }[] }) {
  const total = items.reduce((acc, i) => acc + i.value, 0);
  if (!total) return null;
  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 16 }}>
      {items.map((item) => (
        <div
          key={item.label}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "4px 10px",
            borderRadius: 20,
            background: `${item.color}18`,
            border: `1px solid ${item.color}40`,
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: item.color,
              flexShrink: 0,
            }}
          />
          <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", textTransform: "capitalize" }}>
            {item.label.replace(/_/g, " ")}
          </span>
          <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>
            {item.value}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Section title ───────────────────────────────────────────────────────────
function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2
      style={{
        fontSize: 16,
        fontWeight: 650,
        color: "var(--text-primary)",
        marginBottom: 16,
      }}
    >
      {children}
    </h2>
  );
}

// ─── Icons ───────────────────────────────────────────────────────────────────
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
function CalendarIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function InsightsPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/dashboard/summary?recent_limit=5&demand_days_ahead=60`)
      .then((r) => {
        if (!r.ok) throw new Error("fetch failed");
        return r.json();
      })
      .then((d: DashboardSummary) => setData(d))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  const enquiryTotal = data?.enquiry_totals.total ?? 0;
  const closedWon = data?.enquiry_totals.by_status.find((s) => s.status === "closed_won")?.count ?? 0;
  const conversionRate = enquiryTotal > 0 ? ((closedWon / enquiryTotal) * 100).toFixed(1) : "0.0";
  const avgSpend = data?.pricing_summary.average_minimum_spend;
  const avgSpendLabel = avgSpend != null ? `£${Math.round(avgSpend).toLocaleString()}` : "—";
  const demandSpikes = data?.upcoming_demand_spikes ?? [];
  const highDemandCount = demandSpikes.filter(
    (d) => d.demand_level === "very_high" || d.demand_level === "high"
  ).length;

  const byStatusItems = (data?.enquiry_totals.by_status ?? [])
    .map((s) => ({ label: s.status, value: s.count, color: STATUS_COLORS[s.status] ?? "#9A94AD" }))
    .sort((a, b) => b.value - a.value);

  const byRestaurantItems = (data?.enquiry_totals.by_restaurant ?? [])
    .map((r) => ({ label: r.restaurant_name, value: r.count, color: "#6D3DF5" }))
    .sort((a, b) => b.value - a.value);

  const byPersonaItems = (data?.enquiry_totals.by_persona ?? [])
    .map((p) => ({ label: p.persona_name ?? "Unassigned", value: p.count, color: "#ED3D96" }))
    .sort((a, b) => b.value - a.value);

  const demandByLevel = Object.entries(
    demandSpikes.reduce<Record<string, number>>((acc, d) => {
      acc[d.demand_level] = (acc[d.demand_level] ?? 0) + 1;
      return acc;
    }, {})
  ).map(([level, count]) => ({ label: level, value: count, color: DEMAND_COLORS[level] ?? "#9A94AD" }));

  const maxByStatus = Math.max(...byStatusItems.map((i) => i.value), 1);
  const maxByRestaurant = Math.max(...byRestaurantItems.map((i) => i.value), 1);
  const maxByPersona = Math.max(...byPersonaItems.map((i) => i.value), 1);
  const maxDemandByLevel = Math.max(...demandByLevel.map((i) => i.value), 1);

  if (loading) {
    return (
      <PageContainer>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: 300,
          }}
        >
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: "50%",
              border: "3px solid var(--border)",
              borderTopColor: "var(--brand-purple)",
              animation: "spin 0.8s linear infinite",
            }}
          />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      </PageContainer>
    );
  }

  if (error || !data) {
    return (
      <PageContainer>
        <PageHeader title="Insights" subtitle="Commercial intelligence across your operation" />
        <Card>
          <p style={{ color: "var(--text-muted)", fontSize: 14, textAlign: "center", padding: "40px 0" }}>
            Unable to load insights data. Ensure the API is running.
          </p>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Insights"
        subtitle="Commercial intelligence across your operation"
      />

      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
        <StatBlock label="Total Enquiries" value={enquiryTotal.toString()} accent="purple" icon={<EnquiryIcon />} />
        <StatBlock label="Conversion Rate" value={`${conversionRate}%`} accent="pink" icon={<EnquiryIcon />} />
        <StatBlock label="Avg Min. Spend" value={avgSpendLabel} accent="orange" icon={<PricingIcon />} />
        <StatBlock label="High-Demand Dates" value={highDemandCount.toString()} accent="teal" icon={<CalendarIcon />} />
      </div>

      {/* Enquiries by Status + by Venue */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card>
          <SectionTitle>Enquiries by Status</SectionTitle>
          <SummaryPills items={byStatusItems} />
          <HorizontalBar items={byStatusItems} maxValue={maxByStatus} />
        </Card>
        <Card>
          <SectionTitle>Enquiries by Venue</SectionTitle>
          <HorizontalBar items={byRestaurantItems} maxValue={maxByRestaurant} />
        </Card>
      </div>

      {/* Enquiries by Persona + Demand by Level */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card>
          <SectionTitle>Enquiries by Persona</SectionTitle>
          <HorizontalBar items={byPersonaItems} maxValue={maxByPersona} />
        </Card>
        <Card>
          <SectionTitle>Upcoming Demand — by Level</SectionTitle>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 16 }}>Next 60 days</p>
          <HorizontalBar items={demandByLevel} maxValue={maxDemandByLevel} />
        </Card>
      </div>

      {/* Pricing summary */}
      <Card>
        <SectionTitle>Pricing Rules Summary</SectionTitle>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
          {[
            {
              label: "Active Rules",
              value: data.pricing_summary.active_rule_count.toString(),
              color: "var(--brand-purple)",
            },
            {
              label: "Avg Min. Spend",
              value:
                data.pricing_summary.average_minimum_spend != null
                  ? `£${Math.round(data.pricing_summary.average_minimum_spend).toLocaleString()}`
                  : "—",
              color: "var(--brand-pink)",
            },
            {
              label: "Highest Min. Spend",
              value:
                data.pricing_summary.max_minimum_spend != null
                  ? `£${Math.round(data.pricing_summary.max_minimum_spend).toLocaleString()}`
                  : "—",
              color: "var(--brand-orange)",
            },
            {
              label: "Lowest Min. Spend",
              value:
                data.pricing_summary.min_minimum_spend != null
                  ? `£${Math.round(data.pricing_summary.min_minimum_spend).toLocaleString()}`
                  : "—",
              color: "var(--brand-teal)",
            },
          ].map((item) => (
            <div
              key={item.label}
              style={{
                padding: "16px 20px",
                borderRadius: 12,
                background: "var(--surface-soft)",
                border: "1px solid var(--border)",
              }}
            >
              <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 6 }}>{item.label}</p>
              <p style={{ fontSize: 22, fontWeight: 700, color: item.color }}>{item.value}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Upcoming high-demand dates */}
      <Card>
        <SectionTitle>Upcoming High-Demand Dates</SectionTitle>
        {demandSpikes.length === 0 ? (
          <p style={{ color: "var(--text-muted)", fontSize: 14 }}>No high-demand dates in the next 60 days.</p>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
              gap: 12,
            }}
          >
            {demandSpikes.slice(0, 12).map((spike) => {
              const color = DEMAND_COLORS[spike.demand_level] ?? "#9A94AD";
              const badgeVariant =
                spike.demand_level === "very_high"
                  ? "error"
                  : spike.demand_level === "high"
                  ? "warning"
                  : "neutral";
              return (
                <div
                  key={spike.id}
                  style={{
                    padding: "12px 16px",
                    borderRadius: 10,
                    border: `1px solid ${color}30`,
                    background: `${color}0a`,
                    display: "flex",
                    flexDirection: "column",
                    gap: 4,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                      {new Date(spike.event_date).toLocaleDateString("en-GB", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                    <Badge variant={badgeVariant as "error" | "warning" | "neutral"}>
                      {spike.demand_level.replace("_", " ")}
                    </Badge>
                  </div>
                  <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{spike.restaurant_name}</span>
                  <span style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "capitalize" }}>
                    {spike.meal_period}
                    {spike.demand_score != null && ` · score ${spike.demand_score}`}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </PageContainer>
  );
}
