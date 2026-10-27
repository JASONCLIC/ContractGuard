import { test, expect, registerViaApi, uniqueUser, loginViaUi, navigateInApp } from "../fixtures";

test.describe("auth flows", () => {
  test("register + sign in via UI", async ({ page, request }) => {
    const user = uniqueUser("auth");
    await page.goto("/login");
    await page.getByRole("button", { name: "Register" }).click();
    await page.getByPlaceholder("Enter your name (min. 2 characters)").fill(user.name);
    await page.getByPlaceholder("Enter your email address").fill(user.email);
    await page.getByPlaceholder("Enter your password (min. 6 characters)").fill(user.password);
    const [loginResp] = await Promise.all([
      page.waitForResponse(
        (resp) => resp.url().includes("/api/auth/login") && resp.request().method() === "POST"
      ),
      page.getByRole("button", { name: "Register & Sign In" }).click(),
    ]);
    expect(loginResp.ok()).toBeTruthy();
    await navigateInApp(page, "/analysis");
    await expect(page.getByRole("heading", { name: "Contract Analysis" })).toBeVisible();

    // keep user usable for future negative/admin checks if needed
    await registerViaApi(request, user);
  });

  test("signed-in user can logout from nav", async ({ page, seed }) => {
    await loginViaUi(page, seed.user.email, seed.user.password);
    await expect(page.getByRole("button", { name: "Sign Out" })).toBeVisible();
    await page.getByRole("button", { name: "Sign Out" }).click();
    await expect(page).toHaveURL(/\/login$/);
  });
});
