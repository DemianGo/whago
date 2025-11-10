import { test, expect } from "@playwright/test";
import { createTestUser, loginUI } from "../utils/auth";
import { deleteUserByEmail } from "../utils/db";

test.describe("Formulários e responsividade", () => {
  test("atualização de perfil exibe feedback positivo", async ({ page, request }) => {
    const user = await createTestUser(request);
    try {
      await loginUI(page, user);
      await expect(page).toHaveURL(/\/dashboard$/);
      await page.goto("/settings");
      await expect(page).toHaveURL(/\/settings$/);

      await page.fill("#profile-name", "Usuário Atualizado");
      await page.fill("#profile-phone", "+5511988887777");
      await page.fill("#profile-company", "Playwright Corp");
      await page.fill("#profile-document", "52998224725");

      await page.locator("#profile-form button[type='submit']").click();
      await expect(page.locator("#profile-feedback")).toHaveText(/Perfil atualizado com sucesso/);
    } finally {
      await deleteUserByEmail(user.email);
    }
  });

  test.use({ viewport: { width: 414, height: 896 } });
  test("navegação móvel permite abrir e fechar o menu lateral", async ({ page, request }) => {
    const user = await createTestUser(request);
    try {
      await loginUI(page, user);
      await expect(page.locator("#sidebar-toggle")).toBeVisible();

      await page.click("#sidebar-toggle");
      const overlay = page.locator("#sidebar-overlay");
      await expect(overlay).toBeVisible();

      await page.evaluate(() => {
        document.getElementById("sidebar-overlay")?.click();
      });
      await expect(overlay).toBeHidden();
    } finally {
      await deleteUserByEmail(user.email);
    }
  });
});

