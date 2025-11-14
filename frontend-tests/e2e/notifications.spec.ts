import { test, expect } from "@playwright/test";
import { createTestUser, loginUI } from "../utils/auth";
import { deleteUserByEmail, insertNotification } from "../utils/db";

test.describe("Notificações in-app", () => {
  test("usuário visualiza notificações e marca como lidas", async ({ page, request }) => {
    const user = await createTestUser(request);
    try {
      await insertNotification({
        userId: user.userId,
        title: "Campanha concluída",
        message: "Sua campanha de boas-vindas finalizou com sucesso.",
        type: "success",
      });
      await insertNotification({
        userId: user.userId,
        title: "Saldo baixo",
        message: "Adicione créditos para continuar enviando mensagens.",
        type: "warning",
      });

      await loginUI(page, user, { request });
      await page.reload(); // garante que o preview busque notificações recém criadas

      await page.click("#notifications-toggle");
      const listItems = page.locator("#notifications-list li");
      await expect(listItems).toHaveCount(2);
      const itemTexts = await listItems.allTextContents();
      expect(itemTexts.some((text) => text.includes("Campanha concluída"))).toBeTruthy();
      expect(itemTexts.some((text) => text.includes("Saldo baixo"))).toBeTruthy();

      await page.click("#notifications-mark-all");
      const badge = page.locator("#notifications-badge");
      await expect(badge).toHaveClass(/hidden/);
    } finally {
      await deleteUserByEmail(user.email);
    }
  });

  test("TC014 – compra de créditos gera notificações e histórico", async ({ page, request }) => {
    test.setTimeout(120_000);
    const user = await createTestUser(request, { plan_slug: "business" });
    try {
      await loginUI(page, user, { request });
      await page.goto("/billing");
      await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });

      const beforeResponse = await request.get("/api/v1/notifications", {
        headers: { Authorization: `Bearer ${user.tokens.access_token}` },
      });
      expect(beforeResponse.status()).toBe(200);
      const beforeNotifications = await beforeResponse.json();

      const feedback = page.locator("#credit-purchase-feedback");
      await page.locator("#credit-purchase-form button[type='submit']").click();
      await expect(feedback).toContainText(/Compra registrada/i, { timeout: 15000 });

      const transactionItem = page.locator("#transaction-list li").first();
      await expect(transactionItem).not.toHaveText(/Sem registros/i, { timeout: 15000 });
      await expect(transactionItem).toContainText(/credit_purchase/i);

      await page.waitForTimeout(500);

      const notificationResponse = await request.get("/api/v1/notifications", {
        headers: { Authorization: `Bearer ${user.tokens.access_token}` },
      });
      expect(notificationResponse.status()).toBe(200);
      const notifications = await notificationResponse.json();
      expect(notifications.length).toBeGreaterThan(beforeNotifications.length);
      const latest = notifications[0];
      expect(latest.title || "").toMatch(/Créditos adicionados/i);

      await page.click("#notifications-toggle");
      const latestNotification = page.locator("#notifications-list li").first();
      await expect(latestNotification).toContainText(/Créditos adicionados/i);
    } finally {
      await deleteUserByEmail(user.email);
    }
  });
});

