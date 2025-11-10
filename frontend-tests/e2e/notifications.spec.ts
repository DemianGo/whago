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

      await loginUI(page, user);
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
});

