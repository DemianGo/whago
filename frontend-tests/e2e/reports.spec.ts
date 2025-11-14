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
};

async function navigateToReports(page) {
  await page.getByRole("link", { name: "Relatórios" }).click();
  await expect(page).toHaveURL(/\/reports$/);
  await page.waitForSelector("#plan-comparison-table tbody tr", { timeout: 10_000 });
}

async function listChips(request, token: string): Promise<ChipRecord[]> {
  const response = await request.get("/api/v1/chips", {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.status()).toBe(200);
  return response.json();
}

async function createChipRecord(request, token: string, aliasBase: string): Promise<ChipRecord> {
  const alias = `${aliasBase} ${Date.now()}-${Math.random().toString(16).slice(2, 6)}`;
  const response = await request.post("/api/v1/chips", {
    headers: { Authorization: `Bearer ${token}` },
    data: { alias },
  });
  expect(response.status()).toBe(201);
  const chips = await listChips(request, token);
  const chip = chips.find((item) => item.alias === alias);
  expect(chip, "chip criado deve existir na API").toBeTruthy();
  return chip as ChipRecord;
}

async function createCampaignRecord(request, token: string, payload: { name: string; message_template: string }): Promise<CampaignRecord> {
  const response = await request.post("/api/v1/campaigns", {
    headers: { Authorization: `Bearer ${token}` },
    data: payload,
  });
  expect(response.status()).toBe(201);
  return response.json();
}

async function updateCampaignSettings(request, token: string, campaignId: string, settings: Record<string, unknown>) {
  const response = await request.put(`/api/v1/campaigns/${campaignId}`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { settings },
  });
  expect(response.status()).toBe(200);
  return response.json();
}

async function uploadContacts(request, token: string, campaignId: string, rows: string[]) {
  const buffer = Buffer.from(rows.join("\n"), "utf8");
  const response = await request.post(`/api/v1/campaigns/${campaignId}/contacts/upload`, {
    headers: { Authorization: `Bearer ${token}` },
    multipart: {
      file: {
        name: "contatos.csv",
        mimeType: "text/csv",
        buffer,
      },
    },
  });
  expect(response.status()).toBe(200);
  return response.json();
}

async function seedCampaignForReports(request, token: string) {
  const chip = await createChipRecord(request, token, "Chip Reports");
  const campaign = await createCampaignRecord(request, token, {
    name: `Campanha Reports ${Date.now()}`,
    message_template: "Olá {{nome}}, relatórios em andamento.",
  });
  await updateCampaignSettings(request, token, campaign.id, {
    chip_ids: [chip.id],
    interval_seconds: 5,
  });
  await uploadContacts(request, token, campaign.id, [
    "numero,nome",
    "+5511998887777,Report QA",
  ]);
  await request.post(`/api/v1/campaigns/${campaign.id}/start`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return { campaign, chip };
}

test.describe("Relatórios e exportações", () => {
  test("usuário consegue baixar comparativo de planos e visualizar prévias em JSON", async ({ page, request }) => {
    const user = await createTestUser(request);
    try {
      await loginUI(page, user, { request });
      await navigateToReports(page);

      const downloadButton = page.locator("#download-plan-comparison");
      await expect(downloadButton).toBeVisible();

      const [download] = await Promise.all([
        page.waitForEvent("download"),
        downloadButton.click(),
      ]);
      const suggestedName = download.suggestedFilename();
      expect(suggestedName).toContain("plan-comparison");
      await download.delete(); // evita acúmulo em disco

      // executa relatório de chips em JSON
      await page.fill("#chips-start", "2025-01-01T00:00");
      await page.fill("#chips-end", "2025-01-31T23:59");
      await page.locator("#chips-report-form button[type='submit']").click();
      const chipsPreview = page.locator("#chips-report-preview");
      await expect(chipsPreview).toBeVisible();

      // relatório financeiro em CSV
      await page.fill("#financial-start", "2025-02-01T00:00");
      await page.fill("#financial-end", "2025-02-28T23:59");
      await page.selectOption("#financial-report-format", "csv");
      const [financialDownload] = await Promise.all([
        page.waitForEvent("download"),
        page.locator("#financial-report-form button[type='submit']").click(),
      ]);
      expect(financialDownload.suggestedFilename()).toContain("financial-report.csv");
      await financialDownload.delete();
    } finally {
      await deleteUserByEmail(user.email);
    }
  });

  test("TC013 – relatórios exportam dados em múltiplos formatos", async ({ page, request }) => {
    test.setTimeout(120_000);
    const user = await createTestUser(request, { plan_slug: "enterprise" });
    try {
      const { campaign } = await seedCampaignForReports(request, user.tokens.access_token);

      await loginUI(page, user, { request });
      await navigateToReports(page);

      await page.fill("#campaign-report-id", campaign.id);
      await page.selectOption("#campaign-report-format", "json");
      await page.locator("#campaign-report-form button[type='submit']").click();
      await expect(page.locator("#campaign-report-preview")).toBeVisible();

      await page.selectOption("#campaign-report-format", "pdf");
      const [campaignPdf] = await Promise.all([
        page.waitForEvent("download"),
        page.locator("#campaign-report-form button[type='submit']").click(),
      ]);
      expect(campaignPdf.suggestedFilename()).toContain("campaign-");
      await campaignPdf.delete();

      await page.fill("#chips-start", "2025-03-01T00:00");
      await page.fill("#chips-end", "2025-03-31T23:59");
      await page.selectOption("#chips-report-format", "xlsx");
      const [chipsXlsx] = await Promise.all([
        page.waitForEvent("download"),
        page.locator("#chips-report-form button[type='submit']").click(),
      ]);
      expect(chipsXlsx.suggestedFilename()).toContain("chips-report.xlsx");
      await chipsXlsx.delete();

      await page.fill("#financial-start", "2025-04-01T00:00");
      await page.fill("#financial-end", "2025-04-30T23:59");
      await page.selectOption("#financial-report-format", "pdf");
      const [financialPdf] = await Promise.all([
        page.waitForEvent("download"),
        page.locator("#financial-report-form button[type='submit']").click(),
      ]);
      expect(financialPdf.suggestedFilename()).toContain("financial-report.pdf");
      await financialPdf.delete();
    } finally {
      await deleteUserByEmail(user.email);
    }
  });
});

