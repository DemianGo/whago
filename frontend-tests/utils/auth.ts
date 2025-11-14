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

export type LoginOptions = {
  request?: APIRequestContext;
  waitForDashboardTimeout?: number;
};

export async function loginUI(
  page: Page,
  credentials: { email: string; password: string },
  options: LoginOptions = {},
): Promise<void> {
  const { request: apiRequest, waitForDashboardTimeout = 15_000 } = options;
  const { email, password } = credentials;

  if (!email || !password) {
    throw new Error("loginUI requer email e senha válidos");
  }

  await page.goto("/login");

  const ensureReady = async () => {
    await page.waitForSelector("#login-form", { timeout: 10_000 });
    try {
      await page.waitForFunction(() => window.__WHAGO_READY === true, null, { timeout: 10_000 });
    } catch (error) {
      console.warn("loginUI: __WHAGO_READY não sinalizado dentro do tempo limite");
    }
  };

  await ensureReady();

  const attemptUiLogin = async () => {
    await page.getByLabel("E-mail").fill(email);
    await page.getByLabel("Senha").fill(password);
    await Promise.all([
      page.waitForURL("**/dashboard", { timeout: waitForDashboardTimeout }),
      page.getByRole("button", { name: "Entrar" }).click(),
    ]);
  };

  try {
    await attemptUiLogin();
    return;
  } catch (error) {
    console.warn("loginUI: tentativa de login via UI falhou", error);
    if (!apiRequest) {
      throw error;
    }
  }

  console.warn("loginUI: aplicando fallback via API");
  const response = await apiRequest.post("/api/v1/auth/login", {
    data: { email, password },
  });
  expect(response.status(), "login API deve retornar 200").toBe(200);
  const data = await response.json();

  await page.evaluate(
    ({ tokens }) => {
      if (!tokens?.access_token || !tokens?.refresh_token) {
        throw new Error("Tokens inválidos no fallback de login");
      }
      localStorage.setItem("whago_access_token", tokens.access_token);
      localStorage.setItem("whago_refresh_token", tokens.refresh_token);
    },
    { tokens: data.tokens },
  );

  await page.goto("/dashboard");
  await page.waitForFunction(() => window.__WHAGO_READY === true, null, {
    timeout: waitForDashboardTimeout,
  });
}

