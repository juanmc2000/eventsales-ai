/**
 * TypeScript types mirroring the backend DashboardSummaryOut schema.
 * Source of truth: services/api/app/modules/dashboard/schemas.py
 */

export type EnquiryStatusCount = {
  status: string;
  count: number;
};

export type EnquiryRestaurantCount = {
  restaurant_id: string;
  restaurant_name: string;
  count: number;
};

export type EnquiryPersonaCount = {
  persona_id: string | null;
  persona_name: string | null;
  count: number;
};

export type EnquiryTotals = {
  total: number;
  by_status: EnquiryStatusCount[];
  by_restaurant: EnquiryRestaurantCount[];
  by_persona: EnquiryPersonaCount[];
};

export type RecentEnquiryItem = {
  id: string;
  reference: string;
  status: string;
  first_name: string;
  last_name: string;
  email: string;
  restaurant_id: string;
  event_date: string | null;
  created_at: string;
};

export type PendingFollowUpItem = {
  id: string;
  reference: string;
  status: string;
  first_name: string;
  last_name: string;
  email: string;
  restaurant_id: string;
  event_date: string | null;
  created_at: string;
};

export type DemandSpikeItem = {
  id: string;
  restaurant_id: string;
  restaurant_name: string;
  event_date: string;
  meal_period: string;
  demand_level: string;
  demand_score: number | null;
};

export type PricingSummary = {
  active_rule_count: number;
  average_minimum_spend: number | null;
  max_minimum_spend: number | null;
  min_minimum_spend: number | null;
};

export type DashboardSummary = {
  enquiry_totals: EnquiryTotals;
  recent_enquiries: RecentEnquiryItem[];
  pending_follow_ups: PendingFollowUpItem[];
  upcoming_demand_spikes: DemandSpikeItem[];
  pricing_summary: PricingSummary;
  email_activity: Record<string, unknown>[];
};
