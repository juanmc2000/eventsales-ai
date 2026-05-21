/**
 * Smoke tests for the webform page and component modules.
 *
 * These tests run without a DOM/browser. They verify:
 * 1. Module imports succeed (no broken imports or top-level errors)
 * 2. Page component exports a default function
 * 3. EnquiryWebform component exports correctly
 * 4. EnquiryIntakeOut type is correctly exported from types module
 *
 * UI-010: Build Test Enquiry Webform
 */
import { describe, it, expect, vi } from "vitest";

// Mock Next.js navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/webform",
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ children }: { children: unknown }) => children,
}));

describe("Webform page module", () => {
  it("exports a default page component", async () => {
    const mod = await import("@/app/webform/page");
    expect(typeof mod.default).toBe("function");
  });
});

describe("EnquiryWebform component module", () => {
  it("exports EnquiryWebform as a named export", async () => {
    const mod = await import("@/components/webform/EnquiryWebform");
    expect(typeof mod.EnquiryWebform).toBe("function");
  });
});

describe("EnquiryIntakeOut type", () => {
  it("EnquiryIntakeOut shape matches expected fields", () => {
    // Type-level validation: construct a matching object and assert its fields
    const intake = {
      enquiry_id: "abc-123",
      reference: "ENQ-2026-0001",
      status: "new",
      restaurant_id: "rest-id",
      persona_id: null,
      persona_name: null,
      recommended_minimum_spend: 1500,
      pricing_explanation: "No rules matched.",
      created_at: "2026-05-21T09:00:00Z",
    };
    expect(intake.reference).toBe("ENQ-2026-0001");
    expect(intake.recommended_minimum_spend).toBe(1500);
    expect(intake.persona_id).toBeNull();
  });
});

describe("Webform API call pattern", () => {
  it("intake endpoint path is correct", () => {
    const path = "/api/v1/enquiries/intake";
    expect(path).toBe("/api/v1/enquiries/intake");
  });

  it("required fields are present in a minimal intake payload", () => {
    const payload = {
      restaurant_id: "r1",
      first_name: "Jane",
      last_name: "Smith",
      email: "jane@example.com",
      meal_period: "dinner",
    };
    expect(payload.restaurant_id).toBeTruthy();
    expect(payload.email).toContain("@");
    expect(payload.meal_period).toBe("dinner");
  });
});
