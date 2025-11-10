import { test, expect } from "@playwright/test";
import { createTestUser, loginUI } from "../utils/auth";
import { deleteUserByEmail } from "../utils/db";

async function navigateToReports(page) {
  await page.getByRole("link", { name: "Relatórios" }).click();
  await expect(page).toHaveURL(/\/reports$/);
  await page.waitForSelector("#plan-comparison-table tbody tr", { timeout: 10_000 });
}

test.describe("Relatórios e exportações", () => {
  test("usuário consegue baixar comparativo de planos e visualizar prévias em JSON", async ({ page, request }) => {
    const user = await createTestUser(request);
    try {
      await loginUI(page, user);
      await navigateToReports(page);

      const downloadButton = page.locator("#download-plan-comparison");
      await expect(downloadButton).toBeVisible();

      const [download] = await Promise.all([
        page.waitForEvent("download"),
        downloadButton.click(),
      ]);
      const suggestedName = download.suggestedFilename();
      expect(suggestedName).toContain("plan-comparison");
      await download.delete(); // evita acúmulo em disco

      // executa relatório de chips em JSON
      await page.fill("#chips-start", "2025-01-01T00:00");
      await page.fill("#chips-end", "2025-01-31T23:59");
      await page.locator("#chips-report-form button[type='submit']").click();
      const chipsPreview = page.locator("#chips-report-preview");
      await expect(chipsPreview).toBeVisible();

      // relatório financeiro em CSV
      await page.fill("#financial-start", "2025-02-01T00:00");
      await page.fill("#financial-end", "2025-02-28T23:59");
      await page.selectOption("#financial-report-format", "csv");
      const [financialDownload] = await Promise.all([
        page.waitForEvent("download"),
        page.locator("#financial-report-form button[type='submit']").click(),
      ]);
      expect(financialDownload.suggestedFilename()).toContain("financial-report.csv");
      await financialDownload.delete();
    } finally {
      await deleteUserByEmail(user.email);
    }
  });
});

