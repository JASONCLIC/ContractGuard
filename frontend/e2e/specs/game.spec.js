import { test, expect, loginViaUi, navigateInApp } from "../fixtures";

test.describe("risk quiz game", () => {
  test("can answer one question and see feedback", async ({ page, seed }) => {
    await loginViaUi(page, seed.user.email, seed.user.password);
    await navigateInApp(page, "/game");

    await expect(page.getByText("Risk Clause Quiz")).toBeVisible();
    await page.getByRole("button", { name: "Safe Clause" }).click();

    await expect(page.getByText(/Correct!|Incorrect/)).toBeVisible();
    await expect(page.getByRole("button", { name: /Next|See Results/ })).toBeVisible();
  });
});
