import { test, expect, Page } from "@playwright/test";
import { createTestUser } from "../utils/auth";
import { deleteUserByEmail } from "../utils/db";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

function randomEmail(prefix: string): string {
  const suffix = Math.random().toString(16).slice(2, 10);
  return `${prefix}+${Date.now()}-${suffix}@example.com`;
}

const strongPassword = "SenhaForte!1";
const validPhone = "+5511987654321";

async function fillRegistrationForm(page: Page, data: {
  name: string;
  email: string;
  phone: string;
  password: string;
  company: string;
  document: string;
  planSlug: string;
}): Promise<void> {
  await page.fill("#reg-name", data.name);
  await page.fill("#reg-email", data.email);
  await page.fill("#reg-phone", data.phone);
  await page.fill("#reg-password", data.password);
  await page.fill("#reg-company", data.company);
  await page.fill("#reg-document", data.document);
  await page.selectOption("#reg-plan", data.planSlug);
  await page.locator("#reg-terms").check();
}

const validRegistrationData = () => ({
  name: "Empresária QA",
  email: randomEmail("testsprite"),
  phone: validPhone,
  password: strongPassword,
  company: "Empresa QA",
  document: "11144477735",
  planSlug: "business",
});

const invalidEmailData = () => ({
  ...validRegistrationData(),
  email: "usuario.invalido@",
});

function readEnvVarFromFile(key: string): string | undefined {
  if (process.env[key]) {
    return process.env[key];
  }
  const envPath = path.resolve(__dirname, "../../backend/.env");
  if (!fs.existsSync(envPath)) {
    return undefined;
  }
  const content = fs.readFileSync(envPath, "utf8");
  for (const line of content.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }
    const [envKey, ...rest] = trimmed.split("=");
    if (envKey === key) {
      return rest.join("=");
    }
  }
  return undefined;
}

function signJwt(payload: Record<string, unknown>): string {
  const secret = readEnvVarFromFile("JWT_SECRET_KEY");
  if (!secret) {
    throw new Error("JWT_SECRET_KEY não encontrado para testes");
  }
  const header = { alg: "HS256", typ: "JWT" };
  const encode = (value: unknown) => Buffer.from(JSON.stringify(value)).toString("base64url");
  const headerEncoded = encode(header);
  const payloadEncoded = encode(payload);
  const signature = crypto
    .createHmac("sha256", secret)
    .update(`${headerEncoded}.${payloadEncoded}`)
    .digest("base64url");
  return `${headerEncoded}.${payloadEncoded}.${signature}`;
}

function buildExpiredToken(token: string): string {
  const [, payloadSegment] = token.split(".");
  const payload: Record<string, unknown> = JSON.parse(Buffer.from(payloadSegment, "base64url").toString("utf8"));
  payload.exp = Math.floor(Date.now() / 1000) - 60;
  payload.iat = Math.floor(Date.now() / 1000) - 120;
  return signJwt(payload);
}

test.describe("TestSprite Auth Suite", () => {
  test("TC001 – User Registration with Valid Data", async ({ page }) => {
    const data = validRegistrationData();

    await page.goto("/register");
    await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });
    await fillRegistrationForm(page, data);

    await Promise.all([
      page.waitForURL("**/dashboard", { timeout: 20000 }),
      page.click("button[type='submit']"),
    ]);

    await expect(page.locator("#sidebar-plan")).toContainText(/Business/i);
    await expect(page.locator("#sidebar-credits")).toContainText(/100/);

    await deleteUserByEmail(data.email);
  });

  test("TC002 – User Registration with Invalid Email", async ({ page }) => {
    const data = invalidEmailData();

    await page.goto("/register");
    await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });
    await fillRegistrationForm(page, data);

    await page.click("button[type='submit']");

    const emailValidity = await page.evaluate(() => {
      const input = document.querySelector("#reg-email") as HTMLInputElement;
      return input.validity.valid;
    });
    expect(emailValidity).toBeFalsy();

    const validationMessage = await page.evaluate(() => {
      const input = document.querySelector("#reg-email") as HTMLInputElement;
      return input.validationMessage;
    });
    expect(validationMessage).not.toBe("");
  });

  test("TC003 – User Login with Valid Credentials", async ({ page, request }) => {
    const user = await createTestUser(request, { plan_slug: "business" });

    await page.goto("/login");
    await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });
    await page.fill("#login-email", user.email);
    await page.fill("#login-password", user.password);

    await Promise.all([
      page.waitForURL("**/dashboard", { timeout: 15000 }),
      page.click("button[type='submit']"),
    ]);

    const accessToken = await page.evaluate(() => localStorage.getItem("whago_access_token"));
    expect(accessToken).toBeTruthy();

    await deleteUserByEmail(user.email);
  });

  test("TC004 – User Login with Invalid Credentials", async ({ page }) => {
    await page.goto("/login");
    await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });

    await page.fill("#login-email", "naoexiste@example.com");
    await page.fill("#login-password", "SenhaErrada!1");
    await page.click("button[type='submit']");

    await expect(page.locator("#login-feedback")).toHaveText(/Credenciais inválidas/i);
  });

  test("TC005 – JWT Token Expiry and Refresh", async ({ request }) => {
    const user = await createTestUser(request, { plan_slug: "business" });

    const protectedResponse = await request.get("/api/v1/users/me", {
      headers: { Authorization: `Bearer ${user.tokens.access_token}` },
    });
    expect(protectedResponse.status()).toBe(200);

    const expiredToken = buildExpiredToken(user.tokens.access_token);
    const invalidTokenResponse = await request.get("/api/v1/users/me", {
      headers: {
        Authorization: `Bearer ${expiredToken}`,
        Cookie: "",
      },
    });
    expect(invalidTokenResponse.status(), "token expirado deve ser rejeitado").toBe(401);

    const refreshResponse = await request.post("/api/v1/auth/refresh");
    expect(refreshResponse.status()).toBe(200);

    const refreshed = await refreshResponse.json();
    const protectedWithNewToken = await request.get("/api/v1/users/me", {
      headers: { Authorization: `Bearer ${refreshed.tokens.access_token}` },
    });
    expect(protectedWithNewToken.status()).toBe(200);

    await deleteUserByEmail(user.email);
  });
});
