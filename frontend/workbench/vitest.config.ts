import { defineConfig } from "vitest/config";

// Unit tests run in plain node: they cover the pure formatting/label helpers.
// Playwright owns everything DOM-facing (see playwright.config.ts), so keep
// e2e/ out of vitest's include list.
export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.{ts,tsx}"]
  }
});
