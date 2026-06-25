// Basic smoke test to verify the test suite runs
import { describe, it, expect } from "vitest";

describe("Test infrastructure", () => {
  it("should run basic assertions", () => {
    expect(true).toBe(true);
    expect(1 + 1).toBe(2);
  });

  it("should handle async operations", async () => {
    const result = await Promise.resolve(42);
    expect(result).toBe(42);
  });
});

describe("API mock mode detection", () => {
  it("should detect mock mode from environment", () => {
    // This tests that the test infrastructure is ready for API contract tests
    const isMockMode = () => {
      return typeof window !== "undefined" && 
        window.location.hostname === "localhost" || !process.env.CI;
    };
    expect(isMockMode()).toBeDefined();
  });
});
