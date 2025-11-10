import { test, expect } from "@playwright/test";
import { createTestUser, loginUI } from "../utils/auth";
import { deleteUserByEmail } from "../utils/db";

test.describe("Configuração de webhooks", () => {
  test("usuário Enterprise configura e testa webhook com sucesso", async ({ page, request }) => {
    const user = await createTestUser(request, { plan_slug: "enterprise" });
    try {
      await loginUI(page, user);
      await page.goto("/settings");

      const card = page.locator("#webhook-card");
      await expect(card).toBeVisible();
      const form = card.locator("#webhook-form");
      await expect(form).toBeVisible();

      await page.fill("#webhook-url", "https://webhooks.example.com/whago");
      await page.fill("#webhook-secret", "playwright-secret");
      await page.getByLabel("Campanha iniciada").check();
      await page.getByLabel("Pagamento aprovado").check();

      await form.locator('button[type="submit"]').click();
      await expect(page.locator("#webhook-feedback")).toHaveText(/configurações carregadas/i);

      await page.click("#webhook-test");
      await expect(page.locator("#webhook-feedback")).toHaveText(/configurações carregadas/i);

      const logs = page.locator("#webhook-logs-list li");
      await expect(logs.first()).toContainText("campaign.started");
    } finally {
      await deleteUserByEmail(user.email);
    }
  });
});

