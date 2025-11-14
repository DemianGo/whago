import { test, expect } from "@playwright/test";
import { createTestUser, loginUI } from "../utils/auth";
import { deleteUserByEmail } from "../utils/db";

type ChipRecord = {
  id: string;
  alias: string;
};

type CampaignRecord = {
  id: string;
  name: string;
  status: string;
  settings?: { chip_ids?: string[]; interval_seconds?: number };
};

function buildCsv(): Buffer {
  const rows = [
    "numero,nome",
    "+5511990001111,Cliente 1",
    "+5511990001112,Cliente 2",
    "+5511990001113,Cliente 3",
  ];
  return Buffer.from(rows.join("\n"), "utf8");
}

function buildPng(): Buffer {
  const base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAoMBgObeOusAAAAASUVORK5CYII=";
  return Buffer.from(base64, "base64");
}

async function createChip(request, token: string, aliasBase: string): Promise<string> {
  const uniqueAlias = `${aliasBase} ${Date.now()}-${Math.random().toString(16).slice(2, 6)}`;
  const response = await request.post("/api/v1/chips", {
    headers: { Authorization: `Bearer ${token}` },
    data: { alias: uniqueAlias },
  });
  expect(response.status(), `chip ${uniqueAlias} deve ser criado via API`).toBe(201);
  return uniqueAlias;
}

async function waitForMessages(request, token: string, campaignId: string, expected: number): Promise<any[]> {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    const response = await request.get(`/api/v1/messages?campaign_id=${campaignId}&limit=50`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(response.status()).toBe(200);
    const data = await response.json();
    if (Array.isArray(data) && data.length >= expected) {
      return data;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  return [];
}

function distributionIsBalanced(messages: any[], aliases: string[]): boolean {
  const counters = new Map<string, number>();
  aliases.forEach((alias) => counters.set(alias, 0));
  messages.forEach((msg) => {
    const alias = msg.chip_alias;
    if (counters.has(alias)) {
      counters.set(alias, (counters.get(alias) ?? 0) + 1);
    }
  });
  const values = Array.from(counters.values()).filter((count) => count > 0);
  if (values.length === 0) return false;
  const min = Math.min(...values);
  const max = Math.max(...values);
  return max - min <= 1;
}

async function listChips(request, token: string): Promise<ChipRecord[]> {
  const response = await request.get("/api/v1/chips", {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.status()).toBe(200);
  return response.json();
}

async function findChipByAlias(request, token: string, alias: string): Promise<ChipRecord> {
  const chips = await listChips(request, token);
  const chip = chips.find((item) => item.alias === alias);
  expect(chip, `chip ${alias} deve existir na API`).toBeTruthy();
  return chip as ChipRecord;
}

async function createCampaignDirect(
  request,
  token: string,
  payload: {
    name: string;
    message_template: string;
    message_template_b?: string | null;
    description?: string | null;
    settings?: Record<string, unknown>;
  },
): Promise<CampaignRecord> {
  const response = await request.post("/api/v1/campaigns", {
    headers: { Authorization: `Bearer ${token}` },
    data: payload,
  });
  expect(response.status()).toBe(201);
  return response.json();
}

async function updateCampaignSettings(
  request,
  token: string,
  campaignId: string,
  settings: { chip_ids?: string[]; interval_seconds?: number; randomize_interval?: boolean },
): Promise<CampaignRecord> {
  const response = await request.put(`/api/v1/campaigns/${campaignId}`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { settings },
  });
  expect(response.status()).toBe(200);
  return response.json();
}

async function uploadCampaignContactsCsv(
  request,
  token: string,
  campaignId: string,
  rows: string[],
) {
  const buffer = Buffer.from(rows.join("\n"), "utf8");
  return request.post(`/api/v1/campaigns/${campaignId}/contacts/upload`, {
    headers: { Authorization: `Bearer ${token}` },
    multipart: {
      file: {
        name: "contatos.csv",
        mimeType: "text/csv",
        buffer,
      },
    },
  });
}

async function getCampaignDetail(request, token: string, campaignId: string): Promise<CampaignRecord> {
  const response = await request.get(`/api/v1/campaigns/${campaignId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.status()).toBe(200);
  return response.json();
}

test.describe("TestSprite Campaigns Suite", () => {
  test("TC009 – Chip rotation distributes messages automaticamente", async ({ page, request }) => {
    test.setTimeout(120_000);
    const user = await createTestUser(request, { plan_slug: "business" });
    const chipAliases: string[] = [];
    try {
      chipAliases.push(await createChip(request, user.tokens.access_token, "Chip Rotação"));
      chipAliases.push(await createChip(request, user.tokens.access_token, "Chip Rotação"));

      await loginUI(page, { email: user.email, password: user.password }, { request });
      await page.goto("/campaigns");
      await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });

      await page.getByRole("button", { name: "Nova campanha" }).click();

      const campaignName = `Campanha Rotação ${Date.now()}`;
      await page.fill("#campaign-name", campaignName);
      await page.fill("#campaign-template", "Olá {{nome}}, esta é uma oferta exclusiva!");
      await page.locator("#campaign-basic-form button[type='submit']").click();

      await expect(page.locator("#campaign-chips-list input[type='checkbox']")).toHaveCount(2, {
        timeout: 10000,
      });
      for (const alias of chipAliases) {
        await page.locator("#campaign-chips-list label", { hasText: alias }).locator("input[type='checkbox']").check();
      }
      await page.fill("#campaign-interval", "5");
      await page.locator("#campaign-chips-form button[type='submit']").click();

      await page.setInputFiles("#campaign-contacts-file", {
        name: "contatos.csv",
        mimeType: "text/csv",
        buffer: buildCsv(),
      });
      await page.locator("#campaign-contacts-form button[type='submit']").click({ noWaitAfter: true });

      await expect(page.locator("#campaign-review")).toContainText(/contatos válidos/i, { timeout: 10000 });
      await page.locator("#campaign-start-button").click();
      await expect(page.locator("#campaign-feedback")).toContainText(/Campanha iniciada/i, { timeout: 15000 });

      const campaignsResponse = await request.get("/api/v1/campaigns", {
        headers: { Authorization: `Bearer ${user.tokens.access_token}` },
      });
      expect(campaignsResponse.status()).toBe(200);
      const campaigns = await campaignsResponse.json();
      const createdCampaign = campaigns.find((item) => item.name === campaignName);
      expect(createdCampaign, "Campanha criada deve existir na listagem").toBeTruthy();

      const dispatchResponse = await request.post(`/api/v1/campaigns/${createdCampaign.id}/dispatch-sync`, {
        headers: { Authorization: `Bearer ${user.tokens.access_token}` },
      });
      expect(dispatchResponse.status(), "Dispatch síncrono deve executar com sucesso").toBe(200);

      const messages = await waitForMessages(request, user.tokens.access_token, createdCampaign.id, 3);
      expect(messages.length).toBeGreaterThanOrEqual(3);

      const usedAliases = new Set(messages.map((msg) => msg.chip_alias).filter(Boolean));
      expect(usedAliases.size, "Deve usar múltiplos chips na rotação").toBeGreaterThanOrEqual(2);
      expect(distributionIsBalanced(messages, chipAliases)).toBeTruthy();
    } finally {
      await deleteUserByEmail(user.email);
    }
  });

  test("TC010 – Create campaign with contacts, variables and media", async ({ page, request }) => {
    test.setTimeout(120_000);
    const user = await createTestUser(request, { plan_slug: "enterprise" });
    const chipAlias = await createChip(request, user.tokens.access_token, "Chip Wizard");
    try {

      await loginUI(page, { email: user.email, password: user.password }, { request });
      await page.goto("/campaigns");
      await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });

      await page.getByRole("button", { name: "Nova campanha" }).click();
      const campaignName = `Campanha Completa ${Date.now()}`;
      await page.fill("#campaign-name", campaignName);
      await page.fill("#campaign-template", "Olá {{nome}}, confira nossa oferta em {{produto}}!");
      await page.locator("#campaign-basic-form button[type='submit']").click();

      await expect(page.locator("#campaign-chips-list input[type='checkbox']")).toHaveCount(1, { timeout: 10000 });
      await page.locator("#campaign-chips-list input[type='checkbox']").first().check();
      await page.locator("#campaign-chips-form button[type='submit']").click();

      await page.setInputFiles("#campaign-contacts-file", {
        name: "contatos.csv",
        mimeType: "text/csv",
        buffer: Buffer.from("numero,nome,produto\n+5511990002222,Ana,Widget\n", "utf8"),
      });
      await page.locator("#campaign-contacts-form button[type='submit']").click({ noWaitAfter: true });

      await expect(page.locator("#campaign-contacts-summary")).toContainText(/contatos válidos/i, { timeout: 10000 });
      await expect(page.locator("#campaign-review")).toBeVisible({ timeout: 10000 });
      await expect(page.locator("#campaign-review")).toContainText("{{produto}}");

      await page.locator("#campaign-start-button").click();
      await expect(page.locator("#campaign-feedback")).toContainText(/Campanha iniciada/i, { timeout: 15000 });

      const campaignsResponse = await request.get("/api/v1/campaigns", {
        headers: { Authorization: `Bearer ${user.tokens.access_token}` },
      });
      expect(campaignsResponse.status()).toBe(200);
      const campaigns = await campaignsResponse.json();
      const createdCampaign = campaigns.find((item) => item.name === campaignName) as CampaignRecord;
      expect(createdCampaign, "Campanha criada deve existir na listagem").toBeTruthy();

      const mediaUploadResponse = await request.post(`/api/v1/campaigns/${createdCampaign.id}/media`, {
        headers: { Authorization: `Bearer ${user.tokens.access_token}` },
        multipart: {
          file: {
            name: "banner.png",
            mimeType: "image/png",
            buffer: buildPng(),
          },
        },
      });
      expect(mediaUploadResponse.status()).toBe(201);
      const mediaPayload = await mediaUploadResponse.json();
      expect(mediaPayload.original_name).toBe("banner.png");

      const dispatchResponse = await request.post(`/api/v1/campaigns/${createdCampaign.id}/dispatch-sync`, {
        headers: { Authorization: `Bearer ${user.tokens.access_token}` },
      });
      expect(dispatchResponse.status()).toBe(200);

      const detailResponse = await request.get(`/api/v1/campaigns/${createdCampaign.id}`, {
        headers: { Authorization: `Bearer ${user.tokens.access_token}` },
      });
      expect(detailResponse.status()).toBe(200);
      const campaignDetail = await detailResponse.json();
      expect(campaignDetail.message_template).toContain("{{produto}}");
      expect(Array.isArray(campaignDetail.media)).toBeTruthy();
      expect(campaignDetail.media.length).toBeGreaterThan(0);
      expect(campaignDetail.media[0].original_name).toBe("banner.png");
      expect(campaignDetail.media[0].content_type).toBe("image/png");
    } finally {
      await deleteUserByEmail(user.email);
    }
  });

  test("TC011 – Campaign lifecycle: start, pause, resume and cancel", async ({ page, request }) => {
    test.setTimeout(120_000);
    const user = await createTestUser(request, { plan_slug: "business" });
    const chipAlias = await createChip(request, user.tokens.access_token, "Chip Ciclo");
    try {
      const chip = await findChipByAlias(request, user.tokens.access_token, chipAlias);
      const campaign = await createCampaignDirect(request, user.tokens.access_token, {
        name: `Campanha Ciclo ${Date.now()}`,
        message_template: "Oferta exclusiva para {{nome}}",
      });
      await updateCampaignSettings(request, user.tokens.access_token, campaign.id, {
        chip_ids: [chip.id],
        interval_seconds: 5,
        randomize_interval: false,
      });
      const uploadResponse = await uploadCampaignContactsCsv(request, user.tokens.access_token, campaign.id, [
        "numero,nome",
        "+5511990004444,Ciclo",
      ]);
      expect(uploadResponse.status()).toBe(200);

      await loginUI(page, { email: user.email, password: user.password }, { request });
      await page.goto("/campaigns");
      await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });

      const row = page.locator(`tr[data-campaign-id="${campaign.id}"]`);
      await expect(row).toBeVisible();

      await row.locator('[data-campaign-action="start"]').click();
      await expect(page.locator("#campaign-feedback")).toContainText(/Campanha atualizada/i, { timeout: 10000 });
      await expect(page.locator(`tr[data-campaign-id="${campaign.id}"] .status`)).toContainText(/Em andamento/i);

      const runningRow = page.locator(`tr[data-campaign-id="${campaign.id}"]`);
      await runningRow.locator('[data-campaign-action="pause"]').waitFor();
      await runningRow.locator('[data-campaign-action="pause"]').click();
      await expect(page.locator("#campaign-feedback")).toContainText(/Pausada/i, { timeout: 10000 });
      await expect(page.locator(`tr[data-campaign-id="${campaign.id}"] .status`)).toContainText(/Pausada/i);

      const pausedRow = page.locator(`tr[data-campaign-id="${campaign.id}"]`);
      await pausedRow.locator('[data-campaign-action="resume"]').waitFor();
      await pausedRow.locator('[data-campaign-action="resume"]').click();
      await expect(page.locator("#campaign-feedback")).toContainText(/Em andamento/i, { timeout: 10000 });
      await expect(page.locator(`tr[data-campaign-id="${campaign.id}"] .status`)).toContainText(/Em andamento/i);

      const resumedRow = page.locator(`tr[data-campaign-id="${campaign.id}"]`);
      await resumedRow.locator('[data-campaign-action="cancel"]').waitFor();
      await resumedRow.locator('[data-campaign-action="cancel"]').click();
      await expect(page.locator("#campaign-feedback")).toContainText(/Cancelada/i, { timeout: 10000 });
      await expect(page.locator(`tr[data-campaign-id="${campaign.id}"] .status`)).toContainText(/Cancelada/i);

      const finalDetail = await getCampaignDetail(request, user.tokens.access_token, campaign.id);
      expect(finalDetail.status).toBe("cancelled");
    } finally {
      await deleteUserByEmail(user.email);
    }
  });

  test("TC012 – Sending messages respeitando limites do plano", async ({ page, request }) => {
    test.setTimeout(120_000);
    const user = await createTestUser(request, { plan_slug: "free" });
    const chipAlias = await createChip(request, user.tokens.access_token, "Chip Limites");
    try {
      const chip = await findChipByAlias(request, user.tokens.access_token, chipAlias);
      const campaign = await createCampaignDirect(request, user.tokens.access_token, {
        name: `Campanha Limites ${Date.now()}`,
        message_template: "Olá {{nome}}, confira nossa oferta!",
      });
      const updated = await updateCampaignSettings(request, user.tokens.access_token, campaign.id, {
        chip_ids: [chip.id],
        interval_seconds: 1,
      });
      expect(updated.settings?.interval_seconds).toBeGreaterThanOrEqual(10);

      const rows = ["numero,nome"];
      for (let index = 0; index < 120; index += 1) {
        rows.push(`+551199${(1000000 + index).toString().padStart(7, "0")},Contato ${index}`);
      }
      const tooManyResponse = await uploadCampaignContactsCsv(request, user.tokens.access_token, campaign.id, rows);
      expect(tooManyResponse.status()).toBe(400);
      const tooManyPayload = await tooManyResponse.json();
      expect(String(tooManyPayload.detail || "")).toMatch(/Limite de 100 contatos/i);

      const validResponse = await uploadCampaignContactsCsv(request, user.tokens.access_token, campaign.id, [
        "numero,nome",
        "+5511991234567,Cliente",
        "+5511997654321,Outro",
      ]);
      expect(validResponse.status()).toBe(200);

      await loginUI(page, { email: user.email, password: user.password }, { request });
      await page.goto("/campaigns");
      await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });

      const row = page.locator(`tr[data-campaign-id="${campaign.id}"]`);
      await expect(row).toBeVisible();
      await row.locator('[data-campaign-action="start"]').click();
      await expect(page.locator("#campaign-feedback")).toContainText(/Em andamento/i, { timeout: 10000 });
      await expect(page.locator(`tr[data-campaign-id="${campaign.id}"] .status`)).toContainText(/Em andamento/i);

      const detail = await getCampaignDetail(request, user.tokens.access_token, campaign.id);
      expect(detail.settings?.interval_seconds).toBeGreaterThanOrEqual(10);
      expect(detail.total_contacts).toBeGreaterThan(0);
    } finally {
      await deleteUserByEmail(user.email);
    }
  });
});
