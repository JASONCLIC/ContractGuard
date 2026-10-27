import { test, expect, loginViaUi, sharedUrl, navigateInApp } from "../fixtures";

test.describe("negative and security paths", () => {
  test("unauthenticated user is redirected to login", async ({ page }) => {
    await page.goto("/analysis");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("heading", { name: "Welcome" })).toBeVisible();
  });

  test("shared link with wrong password is rejected", async ({ page, seed }) => {
    await page.goto(sharedUrl(seed.share.token));
    await expect(page.getByText("Password Required")).toBeVisible();
    await page.getByPlaceholder("Enter access password").fill("wrong-pass");
    await page.getByRole("button", { name: "Access" }).click();
    await expect(page.getByText("Incorrect password. Please try again.")).toBeVisible();
  });

  test("normal user cannot access /admin", async ({ page, seed }) => {
    await loginViaUi(page, seed.user.email, seed.user.password);
    await navigateInApp(page, "/admin");
    await expect(page).not.toHaveURL(/\/admin$/);
  });
});
