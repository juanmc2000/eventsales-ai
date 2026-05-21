/**
 * TypeScript types mirroring the backend restaurant schemas.
 * Source of truth: services/api/app/modules/restaurants/schemas.py
 */

export type Restaurant = {
  id: string;
  tenant_id: string;
  name: string;
  slug: string;
  description: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  settings: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type RestaurantListOut = {
  items: Restaurant[];
  total: number;
};

export type RestaurantCreate = {
  name: string;
  slug: string;
  description?: string;
  address?: string;
  phone?: string;
  email?: string;
};

export type RestaurantUpdate = {
  name?: string;
  description?: string;
  address?: string;
  phone?: string;
  email?: string;
};

export type Room = {
  id: string;
  tenant_id: string;
  restaurant_id: string;
  name: string;
  slug: string;
  description: string | null;
  room_type: string | null;
  seated_capacity: number | null;
  standing_capacity: number | null;
  min_capacity: number | null;
  max_capacity: number | null;
  layouts: string[] | null;
  amenities: string[] | null;
  asset_links: Array<{ type: string; label?: string; url: string }> | null;
  room_hire_fee: string | null;
  minimum_spend_notes: string | null;
  suitability_notes: string | null;
  booking_url: string | null;
  is_private_dining: boolean;
  is_active: boolean;
  display_order: number;
  created_at: string;
  updated_at: string;
};

export type RoomListOut = {
  items: Room[];
  total: number;
};

export type PersonaContext = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  tone: string;
  style: string;
  is_default: boolean;
};

export type PricingRuleContext = {
  name: string;
  meal_period: string;
  day_of_week: number | null;
  minimum_spend: string;
  minimum_covers: number | null;
  notes: string | null;
};

export type RoomContext = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  room_type: string | null;
  seated_capacity: number | null;
  standing_capacity: number | null;
  min_capacity: number | null;
  max_capacity: number | null;
  layouts: string[] | null;
  amenities: string[] | null;
  asset_links: Array<{ type: string; label?: string; url: string }> | null;
  room_hire_fee: string | null;
  minimum_spend_notes: string | null;
  suitability_notes: string | null;
  booking_url: string | null;
  is_private_dining: boolean;
  display_order: number;
};

export type RestaurantContext = {
  id: string;
  tenant_id: string;
  name: string;
  slug: string;
  description: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  personas: PersonaContext[];
  default_persona: PersonaContext | null;
  rooms: RoomContext[];
  pricing_rules: PricingRuleContext[];
};
