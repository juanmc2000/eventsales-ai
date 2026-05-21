/**
 * TypeScript types mirroring the backend enquiry schemas.
 * Source of truth: services/api/app/modules/enquiries/schemas.py
 */

export type Enquiry = {
  id: string;
  restaurant_id: string;
  persona_id: string | null;
  reference: string;
  status: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  company_name: string | null;
  party_size: number | null;
  event_date: string | null;
  event_type: string | null;
  budget_indication: string | null;
  preferred_area: string | null;
  dietary_requirements: string | null;
  special_requests: string | null;
  message: string | null;
  source: string;
  recommended_minimum_spend: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type EnquiryListOut = {
  items: Enquiry[];
  total: number;
};

export type EnquiryMessage = {
  id: string;
  enquiry_id: string;
  direction: string; // inbound | outbound
  channel: string;
  subject: string | null;
  body: string;
  sent_at: string | null;
  created_at: string;
};

/** Mirrors DraftResponseOut from services/api/app/modules/enquiries/schemas.py */
export type DraftResponseOut = {
  enquiry_id: string;
  message_id: string;
  subject: string | null;
  body: string;
  persona_name: string | null;
  recommended_minimum_spend: number | null;
  pricing_explanation: string | null;
  is_fallback: boolean | null;
  model: string | null;
  generated_at: string;
};
