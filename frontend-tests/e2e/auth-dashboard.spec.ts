import { test, expect } from "@playwright/test";
import { createTestUser, loginUI } from "../utils/auth";
import { deleteUserByEmail } from "../utils/db";

test.describe("Fluxos de autenticação e dashboard", () => {
  test("usuário consegue autenticar e visualizar KPIs do dashboard", async ({ page, request }) => {
    const user = await createTestUser(request);
    try {
      await loginUI(page, user);

      await expect(page.locator("#topbar-title")).toHaveText(/Painel WHAGO/i);
      await expect(page.locator("#sidebar-plan")).toContainText("Plano");
      await expect(page.locator("#sidebar-credits")).toHaveText(/\d+ créditos/);

      // garante que cards principais renderizaram
      await expect(page.locator("#summary-credits")).toBeVisible();
      await expect(page.locator("#summary-today")).toBeVisible();

      // navegação básica
      await page.getByRole("link", { name: "Campanhas" }).click();
      await expect(page).toHaveURL(/\/campaigns$/);
      await expect(page.locator("h2.page-title")).toHaveText(/Campanhas/);

      await page.getByRole("link", { name: "Configurações" }).click();
      await expect(page).toHaveURL(/\/settings$/);
      await expect(page.locator("h2.card__title").first()).toHaveText(/Perfil/);
    } finally {
      await deleteUserByEmail(user.email);
    }
  });
});

