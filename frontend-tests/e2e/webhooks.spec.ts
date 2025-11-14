import { test, expect } from "@playwright/test";
import { createTestUser, loginUI } from "../utils/auth";
import { deleteUserByEmail } from "../utils/db";

async function createChip(request, token: string, alias: string): Promise<string> {
  const response = await request.post("/api/v1/chips", {
    headers: { Authorization: `Bearer ${token}` },
    data: { alias },
  });
  expect(response.status(), "Chip deve ser criado com sucesso").toBe(201);
  const payload = await response.json();
  return payload.id as string;
}

async function createCampaignWithChip(request, token: string, chipId: string) {
  const campaignResponse = await request.post("/api/v1/campaigns", {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      name: `Webhook Campaign ${Date.now()}`,
      description: "Campanha para validar webhooks",
      message_template: "Olá {{nome}}",
    },
  });
  expect(campaignResponse.status()).toBe(201);
  const campaign = await campaignResponse.json();

  const settingsResponse = await request.put(`/api/v1/campaigns/${campaign.id}`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { settings: { chip_ids: [chipId], interval_seconds: 5 } },
  });
  expect(settingsResponse.status()).toBe(200);

  const contactsCsv = Buffer.from("numero,nome\n+5511999999999,Webhook QA\n", "utf8");
  const uploadResponse = await request.post(`/api/v1/campaigns/${campaign.id}/contacts/upload`, {
    headers: { Authorization: `Bearer ${token}` },
    multipart: {
      file: {
        name: "contatos.csv",
        mimeType: "text/csv",
        buffer: contactsCsv,
      },
    },
  });
  expect(uploadResponse.status()).toBe(200);

  return campaign;
}

test.describe("Configuração de webhooks", () => {
  test("usuário Enterprise configura e testa webhook com sucesso", async ({ page, request }) => {
    const user = await createTestUser(request, { plan_slug: "enterprise" });
    try {
      await loginUI(page, user, { request });
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

  test("TC015 – Webhook Integration for ENTERPRISE Plan", async ({ page, request }) => {
    const user = await createTestUser(request, { plan_slug: "enterprise" });
    try {
      await request.delete("/api/v1/webhooks/test-receiver/events");
      await loginUI(page, user, { request });
      await page.goto("/settings");
      await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });

      await page.fill("#webhook-url", "http://localhost:8000/api/v1/webhooks/test-receiver");
      await page.fill("#webhook-secret", "enterprise-secret");
      await page.getByLabel("Campanha iniciada").check();
      await page.locator('#webhook-form button[type="submit"]').click();
      await expect(page.locator("#webhook-feedback")).toContainText(/configurações carregadas/i);

      const chipId = await createChip(request, user.tokens.access_token, "Chip Webhook");
      const campaign = await createCampaignWithChip(request, user.tokens.access_token, chipId);

      const startResponse = await request.post(`/api/v1/campaigns/${campaign.id}/start`, {
        headers: { Authorization: `Bearer ${user.tokens.access_token}` },
      });
      expect(startResponse.status()).toBe(200);
      const dispatchResponse = await request.post(`/api/v1/campaigns/${campaign.id}/dispatch-sync`, {
        headers: { Authorization: `Bearer ${user.tokens.access_token}` },
      });
      expect(dispatchResponse.status(), "Dispatch sincronizado deve concluir").toBe(200);

      await page.reload();
      await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });

      const logs = page.locator("#webhook-logs-list li");
      await expect(logs.first()).toContainText(/campaign.(started|completed)/i, { timeout: 15000 });
      await expect(logs.first()).toContainText(/HTTP 200/i);

      const eventsResponse = await request.get("/api/v1/webhooks/test-receiver/events");
      expect(eventsResponse.status()).toBe(200);
      const events = await eventsResponse.json();
      expect(events.length).toBeGreaterThan(0);
      expect(events[0].payload?.event).toBe("campaign.started");
    } finally {
      await deleteUserByEmail(user.email);
      await request.delete("/api/v1/webhooks/test-receiver/events");
    }
  });
});

