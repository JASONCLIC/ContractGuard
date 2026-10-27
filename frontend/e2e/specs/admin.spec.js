import { test, expect, loginViaUi, navigateInApp } from "../fixtures";

test.describe("admin console", () => {
  test("admin can access dashboard and switch tabs", async ({ page, seed }) => {
    await loginViaUi(page, seed.admin.email, seed.admin.password);
    await navigateInApp(page, "/admin");

    await expect(page.getByText("Admin Console")).toBeVisible();
    await expect(page.getByText("Total Users")).toBeVisible();

    await page.getByRole("tab", { name: "Identity" }).click();
    await expect(page.getByText("admin@contractguard.local")).toBeVisible();

    await page.getByRole("tab", { name: "Repository" }).click();
    await expect(page.getByPlaceholder("Search title, owner, or email...")).toBeVisible();

    await page.getByRole("tab", { name: "Security Logs" }).click();
    await expect(page.getByText("System Audit Logs")).toBeVisible();
  });
});
