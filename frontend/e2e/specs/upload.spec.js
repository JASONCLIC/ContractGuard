import path from "node:path";
import { fileURLToPath } from "node:url";
import { test, expect, loginViaUi } from "../fixtures";

const fixturePdf = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "fixtures", "contract.pdf");

test.describe("upload flow", () => {
  test("upload a valid pdf and enter analysis loading/result route", async ({ page, seed }) => {
    await loginViaUi(page, seed.user.email, seed.user.password);

    const fileInput = page.locator("input[type='file']");
    await fileInput.setInputFiles(fixturePdf);

    // Upload success can route to loading (new analysis) or result (deduplicated done).
    await expect
      .poll(() => page.url(), { timeout: 20_000 })
      .toMatch(/\/analysis\/(loading|result)$/);
  });

  test("reject non-pdf uploads", async ({ page, seed }) => {
    await loginViaUi(page, seed.user.email, seed.user.password);
    await page.locator("input[type='file']").setInputFiles({
      name: "not-pdf.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("hello"),
    });
    await expect(page.getByText("Only PDF files are allowed.")).toBeVisible();
  });
});
