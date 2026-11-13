import { defineConfig } from "@playwright/test";

/**
 * End-to-end accessibility and keyboard tests. Both servers are started automatically
 * (and re-used if you already have them running locally). CI re-seeds the database first.
 */
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false, // tests share one seeded database
  workers: 1,
  retries: 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: { baseURL: "http://localhost:3210", trace: "retain-on-failure" },
  // Ports 3210/8210 rather than 3000/8000, which are often taken by other local projects.
  webServer: [
    {
      name: "API",
      command: "uv run python -m app.seed && uv run uvicorn app.main:app --port 8210",
      cwd: "../backend",
      url: "http://localhost:8210/health",
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
    },
    {
      name: "Web",
      command: "pnpm dev",
      url: "http://localhost:3210",
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
