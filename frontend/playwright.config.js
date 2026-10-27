import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..");
const e2eDbPath = path.join(repoRoot, "backend", "e2e.sqlite3");
const seedOutput = path.join(__dirname, "e2e", ".state", "seed.json");

export default defineConfig({
  testDir: "./e2e/specs",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  globalSetup: "./e2e/global-setup.js",
  webServer: [
    {
      command: `. ".venv/bin/activate" && DATABASE_URL="sqlite:///${e2eDbPath}" LLM_ENABLED=false python -c "from app import app; app.run(host='127.0.0.1', port=5000, debug=False)"`,
      cwd: repoRoot,
      url: "http://localhost:5000/health",
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      command: "VITE_API_BASE_URL=http://localhost:5000/api npm run dev -- --host localhost --port 5173",
      cwd: __dirname,
      url: "http://localhost:5173",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  metadata: {
    e2eDbPath,
    seedOutput,
  },
});
