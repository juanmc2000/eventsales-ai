/**
 * Shell smoke tests — verifies the fixed sidebar and topbar render
 * without crashing and contain the expected navigation structure.
 *
 * TEST-003: Frontend Smoke Test Baseline
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

// Next.js navigation hooks used by Sidebar/Topbar must be mocked in Vitest.
vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

import { Sidebar } from "@/components/shell/Sidebar";
import { Topbar } from "@/components/shell/Topbar";

// ─── Sidebar ──────────────────────────────────────────────────────────────────

describe("Sidebar", () => {
  it("renders without crashing", () => {
    const { container } = render(<Sidebar />);
    expect(container.firstChild).not.toBeNull();
  });

  it("renders the main navigation section", () => {
    render(<Sidebar />);
    // At minimum the Home link should exist
    expect(screen.getByText(/home/i)).toBeInTheDocument();
  });

  it("renders the Enquiries nav item", () => {
    render(<Sidebar />);
    expect(screen.getByText(/enquiries/i)).toBeInTheDocument();
  });

  it("renders the Calendar nav item", () => {
    render(<Sidebar />);
    expect(screen.getByText(/calendar/i)).toBeInTheDocument();
  });

  it("renders the Configuration section", () => {
    render(<Sidebar />);
    expect(screen.getByText(/pricing rules/i)).toBeInTheDocument();
  });

  it("renders the Insights section", () => {
    render(<Sidebar />);
    expect(screen.getByText(/insights/i)).toBeInTheDocument();
  });

  it("does not expose any system_prompt content", () => {
    const { container } = render(<Sidebar />);
    expect(container.textContent).not.toContain("system_prompt");
  });
});

// ─── Topbar ───────────────────────────────────────────────────────────────────

describe("Topbar", () => {
  it("renders without crashing", () => {
    const { container } = render(<Topbar />);
    expect(container.firstChild).not.toBeNull();
  });

  it("renders the global search input", () => {
    render(<Topbar />);
    const input = screen.getByPlaceholderText(/search/i);
    expect(input).toBeInTheDocument();
  });
});
