import { test, expect } from "@playwright/test";
import { createTestUser, loginUI } from "../utils/auth";
import { deleteUserByEmail, insertCampaignWithMessage } from "../utils/db";

test.describe("Campanhas e mensagens", () => {
  test("listagens apresentam dados da campanha e mensagens enviadas", async ({ page, request }) => {
    const user = await createTestUser(request);
    try {
      await insertCampaignWithMessage({ userId: user.userId });
      await loginUI(page, user, { request });

      await page.getByRole("link", { name: "Campanhas" }).click();
      await expect(page).toHaveURL(/\/campaigns$/);
      const campaignRow = page.locator("#campaign-table tbody tr").first();
      await expect(campaignRow).toContainText("Campanha Playwright");

      await page.getByRole("link", { name: "Mensagens" }).click();
      await expect(page).toHaveURL(/\/messages$/);
      const messageRow = page.locator("#messages-table-body tr").first();
      await expect(messageRow).toContainText("+5511987654321");
      await expect(messageRow).toContainText("sent");
    } finally {
      await deleteUserByEmail(user.email);
    }
  });
});

