/**
 * TypeScript types mirroring the backend persona schemas.
 * Source of truth: services/api/app/modules/personas/schemas.py
 */

export type Persona = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  tone: string;
  style: string;
  // system_prompt is backend-only; we do not display raw prompts in the UI
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type PersonaListOut = {
  items: Persona[];
  total: number;
};

export type PersonaCreate = {
  name: string;
  slug: string;
  description?: string;
  tone: string;
  style: string;
  system_prompt: string;
};

export type PersonaUpdate = {
  name?: string;
  description?: string;
  tone?: string;
  style?: string;
};

export type RestaurantPersonaOut = {
  id: string;
  restaurant_id: string;
  persona_id: string;
  is_default: boolean;
  created_at: string;
};
