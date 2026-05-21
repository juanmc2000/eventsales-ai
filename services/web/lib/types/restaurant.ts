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
