"use client";

import { useEffect, useState, useCallback } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/layout/Card";
import { Badge, StatusPill } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { Enquiry, EnquiryListOut } from "@/lib/types/enquiry";
import type { Restaurant, RestaurantListOut } from "@/lib/types/restaurant";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ALL_STATUSES = [
  "new",
  "open",
  "follow_up",
  "proposal_sent",
  "deposit_sent",
  "deposit_received",
  "closed_won",
  "closed_lost",
  "escalated",
];

// ─── Icons ───────────────────────────────────────────────────────────────────
function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
    </svg>
  );
}
function ChevronRightIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m9 18 6-6-6-6" />
    </svg>
  );
}
function UserIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
    </svg>
  );
}

// ─── Status to badge variant mapping ─────────────────────────────────────────
function statusVariant(status: string): string {
  const map: Record<string, string> = {
    new: "new",
    open: "active",
    follow_up: "warning",
    proposal_sent: "proposal-sent",
    deposit_sent: "deposit-sent",
    deposit_received: "deposit-received",
    closed_won: "closed-won",
    closed_lost: "closed-lost",
    escalated: "escalated",
  };
  return map[status] ?? "neutral";
}

// ─── Guest avatar initials ────────────────────────────────────────────────────
function GuestAvatar({ firstName, lastName }: { firstName: string; lastName: string }) {
  const initials = `${firstName[0] ?? ""}${lastName[0] ?? ""}`.toUpperCase();
  const colors = ["#6D3DF5", "#ED3D96", "#FF7A1A", "#2CC7C9"];
  const colorIndex = (firstName.charCodeAt(0) + lastName.charCodeAt(0)) % colors.length;
  return (
    <div
      style={{
        width: 32,
        height: 32,
        borderRadius: "50%",
        background: colors[colorIndex],
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 12,
        fontWeight: 700,
        color: "#fff",
        flexShrink: 0,
      }}
    >
      {initials}
    </div>
  );
}

// ─── Enquiry detail drawer (stub — expanded in UI-009) ────────────────────────
function EnquiryDetailDrawer({
  enquiry,
  restaurantName,
  onClose,
}: {
  enquiry: Enquiry;
  restaurantName: string;
  onClose: () => void;
}) {
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(7,10,31,0.45)",
          zIndex: 40,
        }}
      />
      {/* Drawer */}
      <div
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          bottom: 0,
          width: 520,
          background: "var(--surface)",
          zIndex: 50,
          display: "flex",
          flexDirection: "column",
          boxShadow: "var(--shadow-hover)",
          overflowY: "auto",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 12,
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
                {enquiry.first_name} {enquiry.last_name}
              </h2>
              <StatusPill status={enquiry.status} />
            </div>
            <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
              {enquiry.reference} · {restaurantName}
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--text-muted)",
              padding: 4,
              borderRadius: 6,
              fontSize: 20,
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Key details grid */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {[
              { label: "Email", value: enquiry.email },
              { label: "Phone", value: enquiry.phone ?? "—" },
              { label: "Company", value: enquiry.company_name ?? "—" },
              { label: "Party Size", value: enquiry.party_size?.toString() ?? "—" },
              {
                label: "Event Date",
                value: enquiry.event_date
                  ? new Date(enquiry.event_date).toLocaleDateString("en-GB", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    })
                  : "—",
              },
              { label: "Event Type", value: enquiry.event_type ?? "—" },
              { label: "Preferred Area", value: enquiry.preferred_area ?? "—" },
              { label: "Source", value: enquiry.source },
            ].map((row) => (
              <div key={row.label}>
                <p style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 2 }}>{row.label}</p>
                <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>{row.value}</p>
              </div>
            ))}
          </div>

          {/* Recommended min spend */}
          {enquiry.recommended_minimum_spend != null && (
            <div
              style={{
                padding: "14px 16px",
                borderRadius: 10,
                background: "rgba(109,61,245,0.06)",
                border: "1px solid rgba(109,61,245,0.2)",
              }}
            >
              <p style={{ fontSize: 11, color: "var(--brand-purple)", fontWeight: 600, marginBottom: 4 }}>
                RECOMMENDED MINIMUM SPEND
              </p>
              <p style={{ fontSize: 22, fontWeight: 700, color: "var(--brand-purple)" }}>
                £{Math.round(enquiry.recommended_minimum_spend).toLocaleString()}
              </p>
            </div>
          )}

          {/* Budget indication */}
          {enquiry.budget_indication && (
            <div>
              <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 4 }}>Budget Indication</p>
              <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>{enquiry.budget_indication}</p>
            </div>
          )}

          {/* Message */}
          {enquiry.message && (
            <div>
              <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 6 }}>Initial Message</p>
              <div
                style={{
                  padding: "12px 14px",
                  borderRadius: 8,
                  background: "var(--surface-soft)",
                  border: "1px solid var(--border)",
                  fontSize: 13,
                  color: "var(--text-secondary)",
                  lineHeight: 1.6,
                  whiteSpace: "pre-wrap",
                }}
              >
                {enquiry.message}
              </div>
            </div>
          )}

          {/* Dietary / special requests */}
          {(enquiry.dietary_requirements || enquiry.special_requests) && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {enquiry.dietary_requirements && (
                <div>
                  <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 4 }}>Dietary Requirements</p>
                  <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>{enquiry.dietary_requirements}</p>
                </div>
              )}
              {enquiry.special_requests && (
                <div>
                  <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 4 }}>Special Requests</p>
                  <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>{enquiry.special_requests}</p>
                </div>
              )}
            </div>
          )}

          {/* Notes */}
          {enquiry.notes && (
            <div>
              <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 4 }}>Notes</p>
              <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>{enquiry.notes}</p>
            </div>
          )}

          <div
            style={{
              padding: "10px 0 0",
              borderTop: "1px solid var(--border)",
              display: "flex",
              gap: 12,
              fontSize: 12,
              color: "var(--text-muted)",
            }}
          >
            <span>Created {new Date(enquiry.created_at).toLocaleDateString("en-GB")}</span>
            <span>·</span>
            <span>Updated {new Date(enquiry.updated_at).toLocaleDateString("en-GB")}</span>
          </div>
        </div>
      </div>
    </>
  );
}

// ─── Main page ─────────────────────────────────────────────────────────────────
export default function EnquiriesPage() {
  const [enquiries, setEnquiries] = useState<Enquiry[]>([]);
  const [total, setTotal] = useState(0);
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState("");
  const [restaurantId, setRestaurantId] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Selected enquiry for detail drawer
  const [selected, setSelected] = useState<Enquiry | null>(null);

  // Load restaurants once
  useEffect(() => {
    fetch(`${API_BASE}/api/v1/restaurants`)
      .then((r) => r.json())
      .then((d: RestaurantListOut) => setRestaurants(d.items ?? []))
      .catch(() => {});
  }, []);

  const loadEnquiries = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams({ limit: "200" });
    if (restaurantId) params.set("restaurant_id", restaurantId);
    if (statusFilter) params.set("status", statusFilter);

    fetch(`${API_BASE}/api/v1/enquiries?${params}`)
      .then((r) => r.json())
      .then((d: EnquiryListOut) => {
        setEnquiries(d.items ?? []);
        setTotal(d.total ?? 0);
      })
      .catch(() => {
        setEnquiries([]);
        setTotal(0);
      })
      .finally(() => setLoading(false));
  }, [restaurantId, statusFilter]);

  useEffect(() => {
    loadEnquiries();
  }, [loadEnquiries]);

  // Client-side search filter
  const filtered = search.trim()
    ? enquiries.filter((e) => {
        const q = search.toLowerCase();
        return (
          e.reference.toLowerCase().includes(q) ||
          e.first_name.toLowerCase().includes(q) ||
          e.last_name.toLowerCase().includes(q) ||
          e.email.toLowerCase().includes(q) ||
          (e.company_name?.toLowerCase().includes(q) ?? false)
        );
      })
    : enquiries;

  // Build restaurant name lookup
  const restaurantMap: Record<string, string> = {};
  for (const r of restaurants) restaurantMap[r.id] = r.name;

  const restaurantOptions = [
    { value: "", label: "All Venues" },
    ...restaurants.map((r) => ({ value: r.id, label: r.name })),
  ];
  const statusOptions = [
    { value: "", label: "All Statuses" },
    ...ALL_STATUSES.map((s) => ({ value: s, label: s.replace(/_/g, " ") })),
  ];

  return (
    <PageContainer>
      <PageHeader
        title="Enquiries"
        subtitle={`${total} total enquiry${total !== 1 ? "ies" : "y"} · ${filtered.length} shown`}
      />

      {/* ── Filters ──────────────────────────────────────────────────────── */}
      <Card padding="sm">
        <div style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
          <div style={{ flex: "1 1 240px" }}>
            <Input
              label=""
              placeholder="Search name, email, reference, company…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              leadingIcon={<SearchIcon />}
            />
          </div>
          <div style={{ width: 200 }}>
            <Select
              label=""
              value={restaurantId}
              onChange={(e) => setRestaurantId(e.target.value)}
              options={restaurantOptions}
            />
          </div>
          <div style={{ width: 180 }}>
            <Select
              label=""
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              options={statusOptions}
            />
          </div>
          {(search || restaurantId || statusFilter) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSearch("");
                setRestaurantId("");
                setStatusFilter("");
              }}
            >
              Clear
            </Button>
          )}
        </div>
      </Card>

      {/* ── Table ────────────────────────────────────────────────────────── */}
      <Card padding="none">
        {loading ? (
          <div style={{ padding: 40, display: "flex", justifyContent: "center" }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: "50%",
                border: "3px solid var(--border)",
                borderTopColor: "var(--brand-purple)",
                animation: "spin 0.8s linear infinite",
              }}
            />
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: "60px 24px", textAlign: "center" }}>
            <p style={{ color: "var(--text-muted)", fontSize: 14 }}>No enquiries match your filters.</p>
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["Guest", "Reference", "Venue", "Event Date", "Party", "Min. Spend", "Status", "Created", ""].map(
                  (col) => (
                    <th
                      key={col}
                      style={{
                        padding: "12px 16px",
                        textAlign: "left",
                        fontSize: 12,
                        fontWeight: 600,
                        color: "var(--text-muted)",
                        letterSpacing: "0.04em",
                        textTransform: "uppercase",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {col}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {filtered.map((enq, idx) => (
                <tr
                  key={enq.id}
                  onClick={() => setSelected(enq)}
                  style={{
                    borderBottom: idx < filtered.length - 1 ? "1px solid var(--border)" : "none",
                    cursor: "pointer",
                    transition: "background 0.12s ease",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLTableRowElement).style.background = "var(--surface-soft)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLTableRowElement).style.background = "transparent";
                  }}
                >
                  {/* Guest */}
                  <td style={{ padding: "12px 16px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <GuestAvatar firstName={enq.first_name} lastName={enq.last_name} />
                      <div>
                        <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                          {enq.first_name} {enq.last_name}
                        </p>
                        <p style={{ fontSize: 12, color: "var(--text-muted)" }}>{enq.email}</p>
                      </div>
                    </div>
                  </td>

                  {/* Reference */}
                  <td style={{ padding: "12px 16px" }}>
                    <span
                      style={{
                        fontSize: 12,
                        fontFamily: "monospace",
                        color: "var(--brand-purple)",
                        background: "rgba(109,61,245,0.08)",
                        padding: "2px 6px",
                        borderRadius: 4,
                      }}
                    >
                      {enq.reference}
                    </span>
                  </td>

                  {/* Venue */}
                  <td style={{ padding: "12px 16px" }}>
                    <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                      {restaurantMap[enq.restaurant_id] ?? "—"}
                    </p>
                  </td>

                  {/* Event Date */}
                  <td style={{ padding: "12px 16px" }}>
                    <p style={{ fontSize: 13, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
                      {enq.event_date
                        ? new Date(enq.event_date).toLocaleDateString("en-GB", {
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                          })
                        : "—"}
                    </p>
                  </td>

                  {/* Party size */}
                  <td style={{ padding: "12px 16px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--text-secondary)" }}>
                      <UserIcon />
                      <span style={{ fontSize: 13 }}>{enq.party_size ?? "—"}</span>
                    </div>
                  </td>

                  {/* Min spend */}
                  <td style={{ padding: "12px 16px" }}>
                    {enq.recommended_minimum_spend != null ? (
                      <span style={{ fontSize: 13, fontWeight: 600, color: "var(--brand-purple)" }}>
                        £{Math.round(enq.recommended_minimum_spend).toLocaleString()}
                      </span>
                    ) : (
                      <span style={{ fontSize: 13, color: "var(--text-muted)" }}>—</span>
                    )}
                  </td>

                  {/* Status */}
                  <td style={{ padding: "12px 16px" }}>
                    <StatusPill status={enq.status} />
                  </td>

                  {/* Created */}
                  <td style={{ padding: "12px 16px" }}>
                    <p style={{ fontSize: 12, color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                      {new Date(enq.created_at).toLocaleDateString("en-GB", {
                        day: "numeric",
                        month: "short",
                      })}
                    </p>
                  </td>

                  {/* Open action */}
                  <td style={{ padding: "12px 16px", textAlign: "right" }}>
                    <span style={{ color: "var(--text-muted)" }}>
                      <ChevronRightIcon />
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* ── Detail drawer ─────────────────────────────────────────────────── */}
      {selected && (
        <EnquiryDetailDrawer
          enquiry={selected}
          restaurantName={restaurantMap[selected.restaurant_id] ?? "—"}
          onClose={() => setSelected(null)}
        />
      )}
    </PageContainer>
  );
}
