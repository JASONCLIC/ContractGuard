import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";

async function waitForHealth(url, timeoutMs = 60_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url);
      if (res.ok) return;
    } catch {
      // ignore and retry
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`Backend health check timeout: ${url}`);
}

export default async function globalSetup() {
  const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
  const repoRoot = path.resolve(frontendRoot, "..");
  const stateDir = path.join(frontendRoot, "e2e", ".state");
  const seedPath = path.join(stateDir, "seed.json");
  const dbPath = path.join(repoRoot, "backend", "e2e.sqlite3");

  fs.mkdirSync(stateDir, { recursive: true });
  if (fs.existsSync(dbPath)) fs.rmSync(dbPath, { force: true });

  await waitForHealth("http://localhost:5000/health", 90_000);

  const cmd = [
    `cd "${repoRoot}"`,
    `. ".venv/bin/activate"`,
    `DATABASE_URL="sqlite:///${dbPath}" LLM_ENABLED=false python "backend/scripts/e2e_seed.py" --output "${seedPath}"`,
  ].join(" && ");

  execSync(cmd, { stdio: "inherit" });
}
