import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:8000";

export default defineConfig({
  testDir: "./frontend-tests/e2e",
  fullyParallel: false,
  reporter: [["list"], ["html", { outputFolder: "frontend-tests/report", open: "never" }]],
  retries: 0,
  timeout: 60_000,
  expect: {
    timeout: 5_000,
  },
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    headless: true,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  outputDir: "frontend-tests/.artifacts",
});

