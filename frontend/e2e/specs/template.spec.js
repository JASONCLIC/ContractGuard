import { test, expect, loginViaUi, navigateInApp } from "../fixtures";

test.describe("template library", () => {
  test("browse categories and expand template entry", async ({ page, seed }) => {
    await loginViaUi(page, seed.user.email, seed.user.password);
    await navigateInApp(page, "/templates");

    await expect(page.getByText("Clause Template Library")).toBeVisible();
    await expect(page.locator("button", { hasText: /Salary|Pay|Termination|General/i }).first()).toBeVisible();

    const firstExpandButton = page.locator("button", { hasText: "+" }).first();
    await firstExpandButton.click();
    await expect(page.getByRole("button", { name: "Copy Template Text" })).toBeVisible();
  });
});
