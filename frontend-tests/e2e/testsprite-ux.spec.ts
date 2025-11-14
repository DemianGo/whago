import { test, expect } from "@playwright/test";
import { createTestUser, loginUI } from "../utils/auth";
import { deleteUserByEmail } from "../utils/db";

test.describe("TestSprite UX Suite", () => {
  test("TC018 – Frontend responsivo e acessível", async ({ page, request }) => {
    const user = await createTestUser(request, { plan_slug: "business" });
    try {
      await loginUI(page, user, { request });
      await page.goto("/dashboard");
      await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });

      await page.setViewportSize({ width: 1280, height: 720 });
      await expect(page.locator("aside.sidebar")).toBeVisible();

      await page.setViewportSize({ width: 820, height: 1180 });
      await expect(page.locator("#sidebar-toggle")).toBeVisible();

      await page.setViewportSize({ width: 390, height: 844 });
      await expect(page.locator("#sidebar-toggle")).toBeVisible();
      await page.keyboard.press("Tab");
      const focusedElement = await page.evaluate(() => document.activeElement?.id ?? document.activeElement?.getAttribute("aria-label") ?? "");
      expect(focusedElement).toContain("sidebar");
      await page.keyboard.press("Enter");
      await expect(page.locator(".sidebar.sidebar--open")).toBeVisible();
      await page.dispatchEvent("#sidebar-overlay", "click");
      await expect(page.locator(".sidebar.sidebar--open")).toHaveCount(0);

      await expect(page.locator("#notifications-toggle")).toHaveAttribute("aria-label", /notificações/i);

      await page.goto("/campaigns");
      await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });
      await expect(page.locator("#campaign-feedback")).toHaveAttribute("aria-live", "polite");
      await expect(page.locator("#campaign-feedback")).toHaveAttribute("role", "status");

      await page.goto("/billing");
      await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });
      await expect(page.locator("#credit-purchase-feedback")).toHaveAttribute("aria-live", "polite");
      await expect(page.locator("#credit-purchase-feedback")).toHaveAttribute("role", "status");
    } finally {
      await deleteUserByEmail(user.email);
    }
  });

  test("TC019 – Estados de loading, sucesso e erro visíveis", async ({ page, request }) => {
    const user = await createTestUser(request, { plan_slug: "business" });
    try {
      await loginUI(page, user, { request });
      await page.goto("/billing");
      await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });

      const feedback = page.locator("#credit-purchase-feedback");
      await page.selectOption("#credit-package", "credits_1000");
      await page.selectOption("#credit-method", "pix");
      const waitLoadingSuccess = page.evaluate(() => {
        const el = document.getElementById("credit-purchase-feedback");
        if (!el) return false;
        if (el.getAttribute("data-state") === "loading") return true;
        return new Promise((resolve) => {
          const observer = new MutationObserver(() => {
            if (el.getAttribute("data-state") === "loading") {
              observer.disconnect();
              resolve(true);
            }
          });
          observer.observe(el, { attributes: true, attributeFilter: ["data-state"] });
        });
      });
      await page.locator('#credit-purchase-form button[type="submit"]').click();
      await waitLoadingSuccess;
      await expect(feedback).toHaveAttribute("data-state", "success", { timeout: 15000 });
      await expect(feedback).toContainText(/Compra registrada/i, { timeout: 15000 });

      await page.route("**/api/v1/billing/credits/purchase", async (route) => {
        await route.fulfill({ status: 500, body: JSON.stringify({ detail: "Falha simulada" }) });
      });
      const waitLoadingError = page.evaluate(() => {
        const el = document.getElementById("credit-purchase-feedback");
        if (!el) return false;
        if (el.getAttribute("data-state") === "loading") return true;
        return new Promise((resolve) => {
          const observer = new MutationObserver(() => {
            if (el.getAttribute("data-state") === "loading") {
              observer.disconnect();
              resolve(true);
            }
          });
          observer.observe(el, { attributes: true, attributeFilter: ["data-state"] });
        });
      });
      await page.locator('#credit-purchase-form button[type="submit"]').click();
      await waitLoadingError;
      await expect(feedback).toHaveAttribute("data-state", "error", { timeout: 5000 });
      await expect(feedback).toContainText(/Falha ao registrar compra/i, { timeout: 5000 });
      await page.unroute("**/api/v1/billing/credits/purchase");
    } finally {
      await deleteUserByEmail(user.email);
    }
  });
});
