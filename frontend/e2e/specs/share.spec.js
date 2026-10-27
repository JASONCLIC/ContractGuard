import { test, expect, loginViaUi, setContractStore, navigateInApp } from "../fixtures";

test.describe("share flow", () => {
  test("create password protected link and open shared page", async ({ page, seed }) => {
    await loginViaUi(page, seed.user.email, seed.user.password);
    await setContractStore(page, seed.contract.id, null);
    await navigateInApp(page, "/share");

    await page.getByLabel("Set Access Password").check();
    await page.getByPlaceholder("Enter share password (leave blank for no password)").fill("Share#5678");
    await page.getByRole("button", { name: "Generate Share Link" }).click();

    await expect(page.getByText("Share Link Generated")).toBeVisible();
    const urlBox = page.locator("text=/\\/shared\\//").first();
    await expect(urlBox).toBeVisible();
    const shareUrl = (await urlBox.textContent())?.trim();
    expect(shareUrl).toBeTruthy();

    const shared = await page.context().newPage();
    await shared.goto(shareUrl);
    await shared.getByPlaceholder("Enter access password").fill("Share#5678");
    await shared.getByRole("button", { name: "Access" }).click();
    await expect(shared.getByText("ContractGuard Shared Contract")).toBeVisible();
    await shared.close();
  });
});
