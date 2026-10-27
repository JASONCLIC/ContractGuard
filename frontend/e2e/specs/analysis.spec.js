import { test, expect, loginViaUi, setContractStore, navigateInApp } from "../fixtures";

test.describe("analysis result views", () => {
  test("open summary / structure / risks / missing tabs", async ({ page, seed }) => {
    await loginViaUi(page, seed.user.email, seed.user.password);
    await setContractStore(page, seed.contract.id, null);
    await navigateInApp(page, "/analysis/result");

    await expect(page.getByRole("heading", { name: "Analysis Results" })).toBeVisible();
    await expect(page.getByText(`Contract ID #${seed.contract.id}`)).toBeVisible();

    await page.getByRole("button", { name: "Clause Structure" }).click();
    await expect(page.getByPlaceholder("Search clauses (keyword, clause name…)")).toBeVisible();
    await expect(page.getByText("Article 1 Term")).toBeVisible();

    await page.getByRole("button", { name: "Risk Clauses" }).click();
    await expect(page.getByRole("button", { name: "High Risk" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Medium Risk" })).toBeVisible();

    await page.getByRole("button", { name: "Missing Items" }).click();
    await expect(page.getByText("Dispute Resolution", { exact: true })).toBeVisible();
  });
});
