/**
 * Route module smoke tests — verifies every Sprint 3 page module:
 *  1. can be imported without throwing
 *  2. exports a default function (the page component)
 *
 * These tests run without a DOM/browser. They catch broken imports,
 * missing exports, and top-level module errors early.
 *
 * TEST-003: Frontend Smoke Test Baseline
 */
import { describe, it, expect, vi } from "vitest";

// Mock Next.js navigation so page modules that import it don't fail.
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ children }: { children: unknown }) => children,
}));

// ─── Route exports ────────────────────────────────────────────────────────────

describe("Route module exports", () => {
  it("dashboard page exports a default component", async () => {
    const mod = await import("@/app/dashboard/page");
    expect(typeof mod.default).toBe("function");
  });

  it("restaurants page exports a default component", async () => {
    const mod = await import("@/app/restaurants/page");
    expect(typeof mod.default).toBe("function");
  });

  it("personas page exports a default component", async () => {
    const mod = await import("@/app/personas/page");
    expect(typeof mod.default).toBe("function");
  });

  it("pricing-rules page exports a default component", async () => {
    const mod = await import("@/app/pricing-rules/page");
    expect(typeof mod.default).toBe("function");
  });

  it("calendar page exports a default component", async () => {
    const mod = await import("@/app/calendar/page");
    expect(typeof mod.default).toBe("function");
  });

  it("insights page exports a default component", async () => {
    const mod = await import("@/app/insights/page");
    expect(typeof mod.default).toBe("function");
  });

  it("enquiries page exports a default component", async () => {
    const mod = await import("@/app/enquiries/page");
    expect(typeof mod.default).toBe("function");
  });
});

// ─── Layout module ────────────────────────────────────────────────────────────

describe("Root layout", () => {
  it("exports a default component", async () => {
    const mod = await import("@/app/layout");
    expect(typeof mod.default).toBe("function");
  });
});

// ─── Shared component exports ─────────────────────────────────────────────────

describe("Shared UI components", () => {
  it("Button exports a default component", async () => {
    const mod = await import("@/components/ui/Button");
    expect(typeof mod.Button).toBe("function");
  });

  it("Badge exports Badge and StatusPill", async () => {
    const mod = await import("@/components/ui/Badge");
    expect(typeof mod.Badge).toBe("function");
    expect(typeof mod.StatusPill).toBe("function");
  });

  it("Card exports a default component", async () => {
    const mod = await import("@/components/layout/Card");
    expect(typeof mod.Card).toBe("function");
  });

  it("StatBlock exports a default component", async () => {
    const mod = await import("@/components/ui/StatBlock");
    expect(typeof mod.StatBlock).toBe("function");
  });

  it("EnquiryDetailDrawer exports the drawer component", async () => {
    const mod = await import("@/components/enquiries/EnquiryDetailDrawer");
    expect(typeof mod.EnquiryDetailDrawer).toBe("function");
  });
});
