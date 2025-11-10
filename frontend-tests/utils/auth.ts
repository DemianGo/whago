import { APIRequestContext, Page, expect } from "@playwright/test";

export type TestUser = {
  email: string;
  password: string;
  userId: string;
  tokens: { access_token: string; refresh_token: string };
};

export async function createTestUser(
  request: APIRequestContext,
  overrides: Partial<{ email: string; password: string; plan_slug: string }> = {},
): Promise<TestUser> {
  const suffix = Math.random().toString(16).slice(2, 10);
  const email = overrides.email ?? `playwright+${Date.now()}-${suffix}@example.com`;
  const phoneSuffix = Math.floor(Math.random() * 10 ** 8);
  const phone = overrides.phone ?? `+55119${phoneSuffix.toString().padStart(8, "0")}`;
  const document = overrides.document ?? "11144477735"; // CPF válido
  const password = overrides.password ?? "SenhaForte!1";
  const payload = {
    name: "Usuário Playwright",
    email,
    password,
    phone,
    company_name: "Empresa Playwright",
    document,
    plan_slug: overrides.plan_slug ?? "free",
  };

  const response = await request.post("/api/v1/auth/register", {
    data: payload,
  });
  expect(response.status(), "registro deve retornar 201").toBe(201);
  const body = await response.json();
  return {
    email,
    password,
    userId: body.user.id,
    tokens: body.tokens,
  };
}

export async function loginUI(page: Page, credentials: { email: string; password: string }): Promise<void> {
  await page.goto("/login");
  await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 15000 });
  await page.getByLabel("E-mail").fill(credentials.email);
  await page.getByLabel("Senha").fill(credentials.password);
  await Promise.all([
    page.waitForURL("**/dashboard", { timeout: 15_000 }),
    page.getByRole("button", { name: "Entrar" }).click(),
  ]);
}

