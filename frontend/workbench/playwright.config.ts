import { defineConfig, devices } from "@playwright/test";

// E2E runs against the real backend in deterministic fake-AI mode.
// serve-workbench serves the built SPA from src/hardwise/workbench/static,
// so run `npm run build` first (or use `npm run test:e2e`, which chains it).
const HOST = "127.0.0.1";
const PORT = 4399;

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://${HOST}:${PORT}`,
    ...devices["Desktop Chrome"],
    viewport: { width: 1440, height: 900 }
  },
  webServer: {
    command:
      "uv run hardwise serve-workbench " +
      "tests/fixtures/allegro/mixed_controller_power_stage.net " +
      "tests/fixtures/allegro/mixed_controller_power_stage_bom.csv " +
      `--fake-ai --host ${HOST} --port ${PORT}`,
    cwd: "../..",
    url: `http://${HOST}:${PORT}/`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000
  }
});
