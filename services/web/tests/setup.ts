/**
 * Vitest global test setup.
 * Runs before each test file.
 */
import "@testing-library/jest-dom";

// ── Default fetch mock ────────────────────────────────────────────────────────
// Tests that don't override fetch get a sensible default (empty list responses).
// Individual tests should vi.stubGlobal("fetch", ...) for specific payloads.
globalThis.fetch = vi.fn().mockResolvedValue({
  ok: true,
  json: async () => ({ items: [], total: 0 }),
}) as unknown as typeof fetch;

// Reset all mocks between tests so spy counts don't bleed across.
afterEach(() => {
  vi.clearAllMocks();
});
