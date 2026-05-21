"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/layout/Card";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Drawer } from "@/components/ui/Drawer";
import { api } from "@/lib/api";
import type { CalendarRangeOut, DayDemandSummary, DemandEventListOut, DemandEvent } from "@/lib/types/calendar";
import type { RestaurantListOut } from "@/lib/types/restaurant";

// ── Demand level design ────────────────────────────────────────────────────────

const DEMAND_CONFIG: Record<string, { bg: string; border: string; dot: string; label: string }> = {
  very_high: {
    bg: "rgba(229,72,77,0.08)",
    border: "rgba(229,72,77,0.35)",
    dot: "var(--danger)",
    label: "Very High",
  },
  high: {
    bg: "rgba(233,154,28,0.08)",
    border: "rgba(233,154,28,0.35)",
    dot: "var(--warning)",
    label: "High",
  },
  medium: {
    bg: "rgba(44,199,201,0.08)",
    border: "rgba(44,199,201,0.35)",
    dot: "var(--brand-teal)",
    label: "Medium",
  },
  low: {
    bg: "transparent",
    border: "var(--border)",
    dot: "var(--text-muted)",
    label: "Low",
  },
};

function getDemandConfig(level: string) {
  return DEMAND_CONFIG[level] ?? DEMAND_CONFIG.low;
}

// ── Calendar helpers ──────────────────────────────────────────────────────────

const MONTH_NAMES = [
  "January","February","March","April","May","June",
  "July","August","September","October","November","December",
];
const DAY_NAMES = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];

function getMonthStart(year: number, month: number): Date {
  return new Date(year, month, 1);
}

function getMonthEnd(year: number, month: number): Date {
  return new Date(year, month + 1, 0);
}

function toISODate(d: Date): string {
  return d.toISOString().split("T")[0];
}

function buildMonthGrid(year: number, month: number): (Date | null)[][] {
  const start = getMonthStart(year, month);
  const end = getMonthEnd(year, month);

  // ISO day: Mon=1 … Sun=7; JS: Sun=0 Mon=1 … Sat=6
  // Convert to ISO-style offset (Mon=0)
  const startOffset = (start.getDay() + 6) % 7;

  const days: (Date | null)[] = [
    ...Array(startOffset).fill(null),
  ];
  for (let d = 1; d <= end.getDate(); d++) {
    days.push(new Date(year, month, d));
  }
  // Pad to complete last week
  while (days.length % 7 !== 0) days.push(null);

  const weeks: (Date | null)[][] = [];
  for (let i = 0; i < days.length; i += 7) {
    weeks.push(days.slice(i, i + 7));
  }
  return weeks;
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function ChevronLeft() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function ChevronRight() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 18l6-6-6-6" />
    </svg>
  );
}

// ── Day detail drawer ─────────────────────────────────────────────────────────

type DayDetailProps = {
  date: Date | null;
  summary: DayDemandSummary | null;
  events: DemandEvent[];
  open: boolean;
  onClose: () => void;
};

function DayDetailDrawer({ date, summary, events, open, onClose }: DayDetailProps) {
  if (!date) return null;

  const label = date.toLocaleDateString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <Drawer open={open} onClose={onClose} title={label}>
      <div className="flex flex-col gap-5">
        {/* Peak demand */}
        {summary ? (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--text-muted)" }}>
              Demand Overview
            </p>
            <div className="flex items-center gap-3 mb-3">
              <span
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: getDemandConfig(summary.peak_demand_level).dot }}
              />
              <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                {getDemandConfig(summary.peak_demand_level).label} demand
              </span>
              {summary.avg_demand_score != null && (
                <span className="text-xs ml-auto" style={{ color: "var(--text-muted)" }}>
                  Score: {(summary.avg_demand_score * 100).toFixed(0)}%
                </span>
              )}
            </div>

            {/* Meal period breakdown */}
            <div className="grid grid-cols-3 gap-2">
              {[
                ["Breakfast", summary.breakfast_level],
                ["Lunch", summary.lunch_level],
                ["Dinner", summary.dinner_level],
              ].map(([meal, level]) => (
                <div
                  key={meal}
                  className="flex flex-col items-center gap-1 py-2.5 rounded-xl"
                  style={{
                    backgroundColor: level
                      ? getDemandConfig(level).bg
                      : "var(--surface-soft)",
                    border: `1px solid ${level ? getDemandConfig(level).border : "var(--border)"}`,
                  }}
                >
                  <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>{meal}</p>
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{
                      backgroundColor: level
                        ? getDemandConfig(level).dot
                        : "var(--border)",
                    }}
                  />
                  <p className="text-xs capitalize" style={{ color: "var(--text-secondary)" }}>
                    {level ? getDemandConfig(level).label : "—"}
                  </p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            No demand data for this date.
          </p>
        )}

        {/* Demand events */}
        {events.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--text-muted)" }}>
              Demand Events ({events.length})
            </p>
            <div className="flex flex-col gap-2">
              {events.map((evt) => {
                const cfg = getDemandConfig(evt.demand_level);
                return (
                  <div
                    key={evt.id}
                    className="flex items-start gap-3 px-3 py-2.5 rounded-xl"
                    style={{ backgroundColor: cfg.bg, border: `1px solid ${cfg.border}` }}
                  >
                    <span className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0" style={{ backgroundColor: cfg.dot }} />
                    <div>
                      <p className="text-sm font-medium capitalize" style={{ color: "var(--text-primary)" }}>
                        {evt.meal_period === "all" ? "All periods" : evt.meal_period} — {cfg.label}
                      </p>
                      {evt.notes && (
                        <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{evt.notes}</p>
                      )}
                      <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                        Source: {evt.source}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </Drawer>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CalendarPage() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());

  const [restaurants, setRestaurants] = useState<{ id: string; name: string }[]>([]);
  const [restaurantId, setRestaurantId] = useState("");
  const [calendarData, setCalendarData] = useState<CalendarRangeOut | null>(null);
  const [dayEvents, setDayEvents] = useState<Record<string, DemandEvent[]>>({});
  const [loading, setLoading] = useState(false);

  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const grid = useMemo(() => buildMonthGrid(year, month), [year, month]);

  const demandByDate = useMemo(() => {
    if (!calendarData) return {};
    return Object.fromEntries(calendarData.days.map((d) => [d.event_date, d]));
  }, [calendarData]);

  const restaurantOptions = useMemo(
    () => restaurants.map((r) => ({ value: r.id, label: r.name })),
    [restaurants]
  );

  useEffect(() => {
    api
      .get<RestaurantListOut>("/api/v1/restaurants?limit=500")
      .then((d) => {
        setRestaurants(d.items.map((r) => ({ id: r.id, name: r.name })));
        if (d.items.length > 0) setRestaurantId(d.items[0].id);
      })
      .catch(() => {});
  }, []);

  const loadCalendar = useCallback(async () => {
    if (!restaurantId) return;
    setLoading(true);
    try {
      const start = getMonthStart(year, month);
      const end = getMonthEnd(year, month);
      const params = new URLSearchParams({
        restaurant_id: restaurantId,
        date_from: toISODate(start),
        date_to: toISODate(end),
      });
      const [rangeData, eventsData] = await Promise.all([
        api.get<CalendarRangeOut>(`/api/v1/calendar/range?${params}`),
        api.get<DemandEventListOut>(
          `/api/v1/demand-events?restaurant_id=${restaurantId}&date_from=${toISODate(start)}&date_to=${toISODate(end)}&limit=2000`
        ),
      ]);
      setCalendarData(rangeData);

      // Group events by date
      const grouped: Record<string, DemandEvent[]> = {};
      for (const evt of eventsData.items) {
        if (!grouped[evt.event_date]) grouped[evt.event_date] = [];
        grouped[evt.event_date].push(evt);
      }
      setDayEvents(grouped);
    } catch {
      setCalendarData(null);
    } finally {
      setLoading(false);
    }
  }, [restaurantId, year, month]);

  useEffect(() => {
    loadCalendar();
  }, [loadCalendar]);

  function navigate(delta: number) {
    setMonth((m) => {
      const next = m + delta;
      if (next < 0) { setYear((y) => y - 1); return 11; }
      if (next > 11) { setYear((y) => y + 1); return 0; }
      return next;
    });
  }

  function openDayDetail(date: Date) {
    setSelectedDate(date);
    setDrawerOpen(true);
  }

  const selectedDateStr = selectedDate ? toISODate(selectedDate) : null;
  const selectedSummary = selectedDateStr ? demandByDate[selectedDateStr] ?? null : null;
  const selectedEvents = selectedDateStr ? dayEvents[selectedDateStr] ?? [] : [];

  const todayStr = toISODate(today);

  return (
    <PageContainer>
      <PageHeader
        title="Commercial Calendar"
        subtitle="Demand signals and pricing indicators across your portfolio."
      />

      {/* Controls */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="w-56">
          <Select
            options={[{ value: "", label: "Select restaurant..." }, ...restaurantOptions]}
            value={restaurantId}
            onChange={(e) => setRestaurantId(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-2 ml-auto">
          <Button variant="secondary" size="sm" onClick={() => navigate(-1)} icon={<ChevronLeft />}>
            Prev
          </Button>
          <span className="text-sm font-semibold px-3" style={{ color: "var(--text-primary)" }}>
            {MONTH_NAMES[month]} {year}
          </span>
          <Button variant="secondary" size="sm" onClick={() => navigate(1)}>
            Next <ChevronRight />
          </Button>
        </div>

        {/* Demand legend */}
        <div className="flex items-center gap-3 flex-wrap">
          {(["very_high", "high", "medium", "low"] as const).map((level) => (
            <div key={level} className="flex items-center gap-1.5">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: getDemandConfig(level).dot }}
              />
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                {getDemandConfig(level).label}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Calendar grid */}
      <Card padding="none">
        {/* Day headers */}
        <div className="grid grid-cols-7 border-b" style={{ borderColor: "var(--border)" }}>
          {DAY_NAMES.map((d) => (
            <div
              key={d}
              className="py-2.5 text-center text-xs font-semibold uppercase tracking-wider"
              style={{
                color: "var(--text-muted)",
                backgroundColor: "var(--surface-soft)",
              }}
            >
              {d}
            </div>
          ))}
        </div>

        {/* Grid rows */}
        {loading ? (
          <div className="p-8 flex items-center justify-center">
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>Loading calendar…</span>
          </div>
        ) : (
          grid.map((week, wi) => (
            <div
              key={wi}
              className="grid grid-cols-7 border-b"
              style={{ borderColor: "var(--border)" }}
            >
              {week.map((date, di) => {
                const dateStr = date ? toISODate(date) : null;
                const summary = dateStr ? demandByDate[dateStr] : null;
                const isToday = dateStr === todayStr;
                const cfg = summary ? getDemandConfig(summary.peak_demand_level) : null;
                const evtCount = dateStr ? (dayEvents[dateStr]?.length ?? 0) : 0;

                return (
                  <div
                    key={di}
                    className="min-h-[80px] p-2 border-r cursor-pointer transition-all duration-100"
                    style={{
                      borderColor: "var(--border)",
                      backgroundColor: date
                        ? cfg
                          ? cfg.bg
                          : "transparent"
                        : "var(--surface-soft)",
                    }}
                    onClick={() => date && restaurantId && openDayDetail(date)}
                    onMouseEnter={(e) => {
                      if (date) e.currentTarget.style.opacity = "0.8";
                    }}
                    onMouseLeave={(e) => {
                      if (date) e.currentTarget.style.opacity = "1";
                    }}
                  >
                    {date && (
                      <>
                        {/* Date number */}
                        <div className="flex items-center justify-between mb-1">
                          <span
                            className="text-xs font-semibold w-6 h-6 flex items-center justify-center rounded-full"
                            style={{
                              color: isToday ? "#ffffff" : "var(--text-primary)",
                              backgroundColor: isToday
                                ? "var(--brand-purple)"
                                : "transparent",
                            }}
                          >
                            {date.getDate()}
                          </span>
                          {cfg && summary && (
                            <span
                              className="w-2 h-2 rounded-full"
                              style={{ backgroundColor: cfg.dot }}
                            />
                          )}
                        </div>

                        {/* Demand label */}
                        {summary && (
                          <p
                            className="text-xs font-medium leading-tight"
                            style={{ color: cfg?.dot ?? "var(--text-muted)" }}
                          >
                            {cfg?.label}
                          </p>
                        )}

                        {/* Event count */}
                        {evtCount > 0 && (
                          <p
                            className="text-xs mt-1"
                            style={{ color: "var(--text-muted)" }}
                          >
                            {evtCount} event{evtCount !== 1 ? "s" : ""}
                          </p>
                        )}
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          ))
        )}
      </Card>

      {/* No restaurant selected */}
      {!restaurantId && !loading && (
        <Card>
          <p className="text-sm text-center py-4" style={{ color: "var(--text-muted)" }}>
            Select a restaurant to load demand data.
          </p>
        </Card>
      )}

      {/* Day detail drawer */}
      <DayDetailDrawer
        date={selectedDate}
        summary={selectedSummary}
        events={selectedEvents}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </PageContainer>
  );
}
