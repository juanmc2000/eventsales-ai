/**
 * TypeScript types for the Insights Analytics page.
 * Data sourced from the dashboard summary endpoint.
 * Source of truth: services/api/app/modules/dashboard/
 */

export type InsightBarItem = {
  label: string;
  value: number;
  color: string;
};
