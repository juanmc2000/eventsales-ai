/**
 * TypeScript types mirroring the backend calendar schemas.
 * Source of truth: services/api/app/modules/calendar/schemas.py
 */

export type DayDemandSummary = {
  event_date: string;
  peak_demand_level: string; // low / medium / high / very_high
  avg_demand_score: number | null;
  breakfast_level: string | null;
  lunch_level: string | null;
  dinner_level: string | null;
};

export type CalendarRangeOut = {
  restaurant_id: string;
  date_from: string;
  date_to: string;
  days: DayDemandSummary[];
};

export type DemandEvent = {
  id: string;
  restaurant_id: string;
  event_date: string;
  meal_period: string;
  demand_level: string;
  demand_score: number | null;
  source: string;
  notes: string | null;
  created_at: string;
};

export type DemandEventListOut = {
  items: DemandEvent[];
  total: number;
};
