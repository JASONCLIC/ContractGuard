import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test as base, expect } from "@playwright/test";

const seedPath = path.join(path.dirname(fileURLToPath(import.meta.url)), ".state", "seed.json");

function readSeed() {
  const raw = fs.readFileSync(seedPath, "utf-8");
  return JSON.parse(raw);
}

async function loginViaUi(page, email, password) {
  await page.goto("/login");
  await page.getByPlaceholder("Enter your email address").fill(email);
  await page.getByPlaceholder("Enter your password (min. 6 characters)").fill(password);
  const [loginResp] = await Promise.all([
    page.waitForResponse((resp) => resp.url().includes("/api/auth/login") && resp.request().method() === "POST"),
    page.locator("form").getByRole("button", { name: "Sign In" }).click(),
  ]);
  const payload = await loginResp.json();
  await page.evaluate(async (user) => {
    const mod = await import("/src/store/useAuthStore.js");
    mod.default.getState().setUser(user);
  }, payload?.data || null);
  await page.evaluate(() => {
    window.history.pushState({}, "", "/analysis");
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
  await expect(page.getByRole("heading", { name: "Contract Analysis" })).toBeVisible();
}

async function navigateInApp(page, pathName) {
  await page.evaluate((to) => {
    window.history.pushState({}, "", to);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, pathName);
}

async function loginViaApi(request, email, password) {
  const res = await request.post("http://localhost:5000/api/auth/login", {
    data: { email, password },
  });
  expect(res.ok()).toBeTruthy();
}

async function setContractStore(page, contractId, jobId = null) {
  await page.evaluate(
    async ({ contractId: cid, jobId: jid }) => {
      const mod = await import("/src/store/useContractStore.js");
      mod.default.getState().setContract(cid, jid);
    },
    { contractId, jobId }
  );
}

async function registerViaApi(request, { name, email, password }) {
  const res = await request.post("http://localhost:5000/api/auth/register", {
    data: { name, email, password },
  });
  expect([200, 400]).toContain(res.status());
}

function uniqueUser(prefix = "pw") {
  const n = Date.now();
  return {
    name: `${prefix}-${n}`,
    email: `${prefix}.${n}@test.local`,
    password: "Strong#1234",
  };
}

function sharedUrl(token) {
  return `/shared/${token}`;
}

export const test = base.extend({
  seed: async ({}, use) => {
    await use(readSeed());
  },
});

export {
  expect,
  loginViaUi,
  loginViaApi,
  setContractStore,
  registerViaApi,
  uniqueUser,
  sharedUrl,
  navigateInApp,
};
