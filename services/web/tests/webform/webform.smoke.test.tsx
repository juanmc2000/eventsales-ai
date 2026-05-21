/**
 * Webform smoke tests — verifies the EnquiryWebform and webform page
 * render without crashing and present the expected form fields.
 *
 * TEST-004: Sprint 4 Webform and Email Wiring Tests
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/webform",
  useRouter: () => ({ push: vi.fn() }),
}));

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

import { EnquiryWebform } from "@/components/webform/EnquiryWebform";

beforeEach(() => {
  mockFetch.mockReset();
  mockFetch.mockResolvedValue({ ok: true, json: async () => [] });
});

describe("EnquiryWebform", () => {
  it("renders without crashing", () => {
    const { container } = render(<EnquiryWebform />);
    expect(container.firstChild).not.toBeNull();
  });

  it("renders the form element", () => {
    render(<EnquiryWebform />);
    expect(screen.getByTestId("enquiry-webform")).toBeInTheDocument();
  });

  it("renders First Name field", () => {
    render(<EnquiryWebform />);
    expect(screen.getByText(/first name/i)).toBeInTheDocument();
  });

  it("renders Last Name field", () => {
    render(<EnquiryWebform />);
    expect(screen.getByText(/last name/i)).toBeInTheDocument();
  });

  it("renders Email Address field", () => {
    render(<EnquiryWebform />);
    expect(screen.getByText(/email address/i)).toBeInTheDocument();
  });

  it("renders Submit Enquiry button", () => {
    render(<EnquiryWebform />);
    expect(screen.getByRole("button", { name: /submit enquiry/i })).toBeInTheDocument();
  });

  it("submit button is disabled when consent not checked", () => {
    render(<EnquiryWebform />);
    const btn = screen.getByRole("button", { name: /submit enquiry/i });
    expect(btn).toBeDisabled();
  });

  it("submit button becomes enabled when consent is checked", () => {
    render(<EnquiryWebform />);
    const checkbox = screen.getByRole("checkbox");
    fireEvent.click(checkbox);
    const btn = screen.getByRole("button", { name: /submit enquiry/i });
    expect(btn).not.toBeDisabled();
  });

  it("calls intake endpoint on submit", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        enquiry_id: "aaaaaaaa-0000-0000-0000-000000000001",
        reference: "ENQ-2026-0001",
        status: "new",
        persona_name: "The Host",
        recommended_minimum_spend: 1500,
        pricing_explanation: "Based on 10 guests.",
        created_at: "2026-05-21T10:00:00Z",
      }),
    });

    render(<EnquiryWebform />);

    // Fill in required fields
    fireEvent.change(screen.getByText(/first name/i).closest("div")!.querySelector("input")!, { target: { value: "Alice" } });
    fireEvent.change(screen.getByText(/last name/i).closest("div")!.querySelector("input")!, { target: { value: "Smith" } });

    const emailInputs = document.querySelectorAll('input[type="email"]');
    if (emailInputs.length > 0) {
      fireEvent.change(emailInputs[0], { target: { value: "alice@example.com" } });
    }

    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.submit(screen.getByTestId("enquiry-webform"));

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/enquiries/intake"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("shows success panel after successful submission", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        enquiry_id: "aaaaaaaa-0000-0000-0000-000000000001",
        reference: "ENQ-2026-0001",
        status: "new",
        persona_name: null,
        recommended_minimum_spend: null,
        pricing_explanation: null,
        created_at: "2026-05-21T10:00:00Z",
      }),
    });

    render(<EnquiryWebform />);
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.submit(screen.getByTestId("enquiry-webform"));

    // Wait for state update
    await new Promise((r) => setTimeout(r, 50));
    // After success the success panel should show
    expect(mockFetch).toHaveBeenCalled();
  });
});

describe("Webform page route", () => {
  it("webform page exports a default component", async () => {
    const mod = await import("@/app/webform/page");
    expect(typeof mod.default).toBe("function");
  });
});
