import { defineConfig } from "@playwright/test";

// Parcours de bout en bout : vraie API (base SQLite temporaire), LLM et recherche simulés
// (Backend/tests/e2e_server.py), frontend construit servi par `vite preview`.
//   npm run build && npm run test:e2e
// PLAYWRIGHT_CHROMIUM_PATH : navigateur déjà installé (sinon `npx playwright install chromium`).
const API_PORT = 8765;
const WEB_PORT = 4173;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    trace: "retain-on-failure",
    launchOptions: {
      executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH || undefined,
      args: ["--no-sandbox"],
    },
  },
  webServer: [
    {
      command: `uv run python -m tests.e2e_server ${API_PORT}`,
      cwd: "../Backend",
      url: `http://127.0.0.1:${API_PORT}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: `npx vite preview --port ${WEB_PORT} --strictPort --host 127.0.0.1`,
      url: `http://127.0.0.1:${WEB_PORT}`,
      env: { VITE_PROXY_TARGET: `http://127.0.0.1:${API_PORT}` },
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
