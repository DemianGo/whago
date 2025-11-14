import { test, expect, request as playwrightRequest } from "@playwright/test";
import { createTestUser, loginUI } from "../utils/auth";
import { deleteUserByEmail } from "../utils/db";

test.describe("TestSprite Security Suite", () => {
  test("TC016 – API REST Authentication and Rate Limiting", async ({ page, request }) => {
    const user = await createTestUser(request, { plan_slug: "enterprise" });
    const apiContext = await playwrightRequest.newContext({ baseURL: "http://localhost:8000" });
    try {
      await loginUI(page, user, { request });
      await page.goto("/settings");
      await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });

      const manager = page.locator("#api-key-manager");
      await expect(manager).toBeVisible();

      await page.fill("#api-key-name", "Key TC016");
      await Promise.all([
        page.waitForSelector("#api-key-modal:not(.hidden)", { timeout: 10000 }),
        page.locator('#api-key-form button[type="submit"]').click(),
      ]);

      const rawKey = await page.locator("#api-key-modal-value code").innerText();
      expect(rawKey).toMatch(/^whago_[a-f0-9]{8}_[a-f0-9]{64}$/i);
      await page.click("#api-key-modal-close");

      const validResponse = await apiContext.get("/api/v1/campaigns", {
        headers: { "X-API-Key": rawKey },
      });
      expect(validResponse.status()).toBe(200);

      const invalidResponse = await apiContext.get("/api/v1/campaigns", {
        headers: { "X-API-Key": "whago_deadbeef_invalid" },
      });
      expect(invalidResponse.status()).toBe(401);

      let rateLimited = false;
      for (let attempt = 0; attempt < 50; attempt += 1) {
        const response = await apiContext.get("/api/v1/campaigns", {
          headers: { "X-API-Key": rawKey },
        });
        if (response.status() === 429) {
          rateLimited = true;
          break;
        }
      }
      expect(rateLimited).toBeTruthy();
    } finally {
      await apiContext.dispose();
      await deleteUserByEmail(user.email);
    }
  });
});
