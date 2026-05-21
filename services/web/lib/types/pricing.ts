/**
 * TypeScript types mirroring the backend pricing schemas.
 * Source of truth: services/api/app/modules/pricing/schemas.py
 */

export type PricingRule = {
  id: string;
  restaurant_id: string;
  name: string;
  day_of_week: number | null; // 0=Mon … 6=Sun; null=every day
  meal_period: string; // breakfast / lunch / dinner / all
  minimum_spend: number;
  minimum_covers: number | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type PricingRuleListOut = {
  items: PricingRule[];
  total: number;
};

export type PricingRuleCreate = {
  name: string;
  restaurant_id: string;
  day_of_week?: number | null;
  meal_period: string;
  minimum_spend: number;
  minimum_covers?: number | null;
  notes?: string;
};

export type PricingRuleUpdate = {
  name?: string;
  day_of_week?: number | null;
  meal_period?: string;
  minimum_spend?: number;
  minimum_covers?: number | null;
  notes?: string;
};

export type AppliedRule = {
  rule_id: string;
  rule_name: string;
  minimum_spend: number;
  reason: string;
};

export type PricingRecommendationOut = {
  recommended_minimum_spend: number;
  applied_rules: AppliedRule[];
  explanation: string;
  confidence: number;
};
