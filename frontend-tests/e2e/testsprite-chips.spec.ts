import { test, expect, Page } from "@playwright/test";
import { createTestUser, loginUI } from "../utils/auth";
import { deleteUserByEmail } from "../utils/db";

async function openAddChipModal(page: Page): Promise<void> {
  await page.click('[data-test="add-chip"]');
  await expect(page.locator('#chip-alias')).toBeVisible();
}

async function submitChip(page: Page, alias: string): Promise<void> {
  await page.fill('#chip-alias', alias);
  await page.click('[data-test="submit-chip"]');
}

test.describe("TestSprite Chips Suite", () => {
  test("TC006 – Add Chip via QR Code Scan respecting Business plan limit", async ({ page, request }) => {
    const user = await createTestUser(request, { plan_slug: "business" });
    try {
      await loginUI(page, { email: user.email, password: user.password }, { request });
      await page.goto("/chips");
      await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });

      for (let index = 1; index <= 3; index += 1) {
        await openAddChipModal(page);
        const alias = `Chip QA ${index}`;
        await submitChip(page, alias);
        await expect(
          page.locator('[data-test="chip-row"]').filter({ hasText: alias }),
          `chip ${alias} deve aparecer na lista`,
        ).toBeVisible();
      }

      await openAddChipModal(page);
      await submitChip(page, "Chip QA 4");
      await expect(page.locator('#chip-feedback')).toContainText(/Limite de chips do plano atingido/i);
      await expect(page.locator('[data-test="chip-row"]')).toHaveCount(3);
    } finally {
      await deleteUserByEmail(user.email);
    }
  });

  test("TC007 – Chip status updates reflected in real time", async ({ page, request }) => {
    const user = await createTestUser(request, { plan_slug: "business" });
    try {
      await loginUI(page, { email: user.email, password: user.password }, { request });
      await page.goto("/chips");
      await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });

      const alias = "Chip Status QA";
      await openAddChipModal(page);
      await submitChip(page, alias);
      await expect(
        page.locator('[data-test="chip-row"]').filter({ hasText: alias }),
        "chip deve aparecer na lista após criação",
      ).toBeVisible();

      const listResponse = await request.get("/api/v1/chips", {
        headers: { Authorization: `Bearer ${user.tokens.access_token}` },
      });
      expect(listResponse.status()).toBe(200);
      const chips = await listResponse.json();
      const createdChip = chips.find((chip: any) => chip.alias === alias);
      expect(createdChip, "chip criado deve existir na API").toBeTruthy();

      const row = page.locator(`[data-chip-id="${createdChip.id}"]`);
      await expect(row.locator('[data-test="chip-status"]')).toContainText(/Aguardando/i);

      const disconnectResponse = await request.post(`/api/v1/chips/${createdChip.id}/disconnect`, {
        headers: { Authorization: `Bearer ${user.tokens.access_token}` },
      });
      expect(disconnectResponse.status()).toBe(200);

      await expect(row.locator('[data-test="chip-status"]')).toContainText(/Desconectado/i, {
        timeout: 10000,
      });
    } finally {
      await deleteUserByEmail(user.email);
    }
  });

  test("TC008 – Chip maturation automatic heat-up process", async ({ page, request }) => {
    const user = await createTestUser(request, { plan_slug: "business" });
    try {
      await loginUI(page, { email: user.email, password: user.password }, { request });
      await page.goto("/chips");
      await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });

      const alias = "Chip HeatUp QA";
      await openAddChipModal(page);
      await submitChip(page, alias);
      const chipRow = page.locator('[data-test="chip-row"]').filter({ hasText: alias });
      await expect(chipRow).toBeVisible();

      const heatUpButton = chipRow.locator('[data-test="chip-action-heatup"]');
      await heatUpButton.click();

      await expect(page.locator('#chip-feedback')).toContainText(/Plano de aquecimento iniciado/i);
      await expect(page.locator('[data-test="chip-heatup-stage"]')).toHaveCount(4);
      await expect(page.locator('[data-test="chip-heatup-stage"]').first()).toContainText(/Fase 1/i);

      const listResponse = await request.get("/api/v1/chips", {
        headers: { Authorization: `Bearer ${user.tokens.access_token}` },
      });
      expect(listResponse.status()).toBe(200);
      const chips = await listResponse.json();
      const createdChip = chips.find((chip: any) => chip.alias === alias);
      expect(createdChip?.status).toBe("maturing");
      expect(createdChip?.extra_data?.heat_up?.status).toBe("in_progress");
    } finally {
      await deleteUserByEmail(user.email);
    }
  });
});
