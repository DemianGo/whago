const API_BASE = "/api/v1";
const ACCESS_TOKEN_KEY = "whago_access_token";
const REFRESH_TOKEN_KEY = "whago_refresh_token";

const PUBLIC_PAGES = new Set(["login", "register"]);

const selectors = {
  summaryCredits: () => document.getElementById("summary-credits"),
  summaryToday: () => document.getElementById("summary-today"),
  summaryTodayVariation: () => document.getElementById("summary-today-variation"),
  summaryMonth: () => document.getElementById("summary-month"),
  summaryMonthVariation: () => document.getElementById("summary-month-variation"),
  summarySuccess: () => document.getElementById("summary-success"),
  sidebarPlan: () => document.getElementById("sidebar-plan"),
  sidebarCredits: () => document.getElementById("sidebar-credits"),
  userName: () => document.getElementById("user-name"),
  userEmail: () => document.getElementById("user-email"),
  userInitial: () => document.getElementById("user-initial"),
  topbarTitle: () => document.getElementById("topbar-title"),
};

const statusMap = {
  draft: "Rascunho",
  scheduled: "Agendada",
  running: "Em andamento",
  paused: "Pausada",
  completed: "Concluída",
  cancelled: "Cancelada",
  error: "Erro",
};

function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

function setTokens(tokens) {
  if (!tokens) return;
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function apiFetch(path, options = {}) {
  const token = getAccessToken();
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && !PUBLIC_PAGES.has(currentPage)) {
    clearTokens();
    window.location.href = "/login";
    return null;
  }

  return response;
}

function formatDate(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function displayVariation(value) {
  if (value === null || value === undefined) return "Sem histórico";
  const formatted = `${value > 0 ? "+" : ""}${value.toFixed(2)}% vs período anterior`;
  return value >= 0 ? formatted : `${formatted} ↓`;
}

function setActiveNavigation() {
  const links = document.querySelectorAll(".sidebar__link");
  links.forEach((link) => {
    const nav = link.dataset.nav;
    if (nav === currentPage) {
      link.classList.add("bg-primary/20", "text-white");
    } else {
      link.classList.remove("bg-primary/20", "text-white");
    }
  });
}

async function loadProfile() {
  const response = await apiFetch("/users/me");
  if (!response || !response.ok) return null;
  const data = await response.json();

  selectors.userName()?.innerText = data.name;
  selectors.userEmail()?.innerText = data.email;
  selectors.userInitial()?.innerText = data.name?.[0]?.toUpperCase() ?? "U";
  selectors.sidebarCredits()?.innerText = `${data.credits} créditos`;
  selectors.sidebarPlan()?.innerText = data.plan ? `Plano ${data.plan}` : "Sem plano";

  const nameInput = document.getElementById("profile-name");
  if (nameInput) {
    nameInput.value = data.name ?? "";
    const phoneInput = document.getElementById("profile-phone");
    const companyInput = document.getElementById("profile-company");
    const documentInput = document.getElementById("profile-document");
    if (phoneInput) phoneInput.value = data.phone ?? "";
    if (companyInput) companyInput.value = data.company_name ?? "";
    if (documentInput) documentInput.value = data.document ?? "";
  }

  return data;
}

async function loadDashboard() {
  const summaryResp = await apiFetch("/dashboard/summary");
  if (summaryResp?.ok) {
    const data = await summaryResp.json();
    selectors.summaryCredits()?.innerText = `${data.credits_available} créditos`;
    selectors.summaryToday()?.innerText = data.messages_today;
    selectors.summaryTodayVariation()?.innerText = displayVariation(data.messages_today_variation);
    selectors.summaryMonth()?.innerText = data.messages_month;
    selectors.summaryMonthVariation()?.innerText = displayVariation(data.messages_month_variation);
    selectors.summarySuccess()?.innerText = `${data.success_rate.toFixed(2)}%`;
  }

  const trendResp = await apiFetch("/dashboard/messages-trend");
  if (trendResp?.ok) {
    const trend = await trendResp.json();
    const tbody = document.getElementById("trend-body");
    if (tbody) {
      tbody.innerHTML = "";
      trend.points.slice(-15).forEach((point) => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td class="py-2">${formatDate(point.date).split(" ")[0]}</td>
          <td class="py-2">${point.sent}</td>
          <td class="py-2">${point.delivered}</td>
          <td class="py-2">${point.read}</td>
          <td class="py-2">${point.failed}</td>
        `;
        tbody.appendChild(row);
      });
    }
  }

  const activityResp = await apiFetch("/dashboard/activity");
  if (activityResp?.ok) {
    const activity = await activityResp.json();
    const list = document.getElementById("activity-feed");
    if (list) {
      list.innerHTML = "";
      if (!activity.items.length) {
        list.innerHTML = "<li class=\"text-slate-500\">Sem eventos registrados.</li>";
      } else {
        activity.items.slice(0, 10).forEach((item) => {
          const li = document.createElement("li");
          li.innerHTML = `
            <div class="font-medium text-slate-800">${item.title}</div>
            <div class="text-xs text-slate-500">${formatDate(item.timestamp)}</div>
            <p class="text-sm text-slate-600">${item.description}</p>
          `;
          list.appendChild(li);
        });
      }
    }
  }
}

async function loadChips() {
  const response = await apiFetch("/chips");
  if (!response?.ok) return;
  const chips = await response.json();
  const table = document.querySelector("#chip-table tbody");
  if (!table) return;
  table.innerHTML = "";
  chips.forEach((chip) => {
    const statusText = (chip.status || "--").replace(/_/g, " ");
    const statusClass = (chip.status || "").toLowerCase();
    const row = document.createElement("tr");
    row.innerHTML = `
      <td class="py-2 font-medium text-slate-800">${chip.alias}</td>
      <td class="py-2"><span class="status status-${statusClass}">${statusText}</span></td>
      <td class="py-2">${chip.health_score ?? "--"}</td>
      <td class="py-2">${formatDate(chip.created_at)}</td>
      <td class="py-2">${formatDate(chip.last_activity_at)}</td>
    `;
    table.appendChild(row);
  });
}

async function loadCampaigns() {
  const response = await apiFetch("/campaigns");
  if (!response?.ok) return;
  const campaigns = await response.json();
  const table = document.querySelector("#campaign-table tbody");
  if (!table) return;
  table.innerHTML = "";
  campaigns.forEach((campaign) => {
    const statusKey = (campaign.status || "").toLowerCase();
    const status = statusMap[statusKey] ?? campaign.status ?? "--";
    const progress = campaign.total_contacts
      ? Math.round((campaign.sent_count / campaign.total_contacts) * 100)
      : 0;
    const success = typeof campaign.success_rate === "number"
      ? campaign.success_rate.toFixed(2)
      : "--";
    const row = document.createElement("tr");
    row.innerHTML = `
      <td class="py-2 font-medium text-slate-800">${campaign.name}</td>
      <td class="py-2">${status}</td>
      <td class="py-2">${progress}%</td>
      <td class="py-2">${success}%</td>
      <td class="py-2">${formatDate(campaign.created_at)}</td>
      <td class="py-2 text-primary">Detalhes</td>
    `;
    table.appendChild(row);
  });
}

async function loadBilling() {
  const statusResp = await apiFetch("/billing/subscription");
  if (statusResp?.ok) {
    const data = await statusResp.json();
    document.getElementById("billing-current-plan").innerText = data.plan_name ?? "--";
    document.getElementById("billing-renewal").innerText = formatDate(data.renewal_at);
    document.getElementById("billing-pending-plan").innerText = data.pending_plan_name ?? "--";
    document.getElementById("billing-failures").innerText = data.failed_payment_attempts ?? 0;
    const cancelBtn = document.getElementById("cancel-downgrade");
    if (cancelBtn) {
      cancelBtn.classList.toggle("hidden", !data.pending_plan);
    }
  }

  const transactionsResp = await apiFetch("/billing/transactions");
  if (transactionsResp?.ok) {
    const transactions = await transactionsResp.json();
    const list = document.getElementById("transaction-list");
    if (list) {
      list.innerHTML = "";
      if (!transactions.length) {
        list.innerHTML = "<li>Sem registros.</li>";
      } else {
        transactions.slice(0, 5).forEach((tx) => {
          const li = document.createElement("li");
          li.innerHTML = `
            <div class="font-medium text-slate-700">${tx.type} • ${tx.status}</div>
            <div class="text-xs text-slate-500">${formatDate(tx.created_at)} — R$ ${tx.amount.toFixed(2)}</div>
          `;
          list.appendChild(li);
        });
      }
    }
  }

  const creditResp = await apiFetch("/billing/credits/history");
  if (creditResp?.ok) {
    const entries = await creditResp.json();
    const list = document.getElementById("credit-history");
    if (list) {
      list.innerHTML = "";
      if (!entries.length) {
        list.innerHTML = "<li>Sem movimentações.</li>";
      } else {
        entries.slice(0, 5).forEach((entry) => {
          const li = document.createElement("li");
          li.innerHTML = `
            <div class="font-medium text-slate-700">${entry.source}</div>
            <div class="text-xs text-slate-500">${formatDate(entry.created_at)} • saldo: ${entry.balance_after}</div>
            <p class="text-sm text-slate-600">${entry.description ?? "--"}</p>
          `;
          list.appendChild(li);
        });
      }
    }
  }
}

function bindBillingForms() {
  const planForm = document.getElementById("plan-change-form");
  const planFeedback = document.getElementById("plan-change-feedback");
  if (planForm) {
    planForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      planFeedback.innerText = "Processando alteração...";
      const payload = {
        plan_slug: document.getElementById("plan-select").value,
        payment_method: document.getElementById("plan-payment-method").value,
      };
      const response = await apiFetch("/billing/plan/change", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (response?.ok) {
        const data = await response.json();
        planFeedback.innerText = data.message;
        await loadBilling();
      } else {
        planFeedback.innerText = "Não foi possível alterar o plano agora.";
      }
    });
  }

  const cancelBtn = document.getElementById("cancel-downgrade");
  if (cancelBtn) {
    cancelBtn.addEventListener("click", async () => {
      cancelBtn.disabled = true;
      const response = await apiFetch("/billing/plan/downgrade/cancel", {
        method: "POST",
      });
      cancelBtn.disabled = false;
      if (response?.ok) {
        await loadBilling();
      }
    });
  }

  const creditForm = document.getElementById("credit-purchase-form");
  const creditFeedback = document.getElementById("credit-purchase-feedback");
  if (creditForm) {
    creditForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      creditFeedback.innerText = "Gerando compra...";
      const payload = {
        package_code: document.getElementById("credit-package").value,
        payment_method: document.getElementById("credit-method").value,
        payment_reference: `auto-${randomReference()}`,
      };
      const response = await apiFetch("/billing/credits/purchase", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (response?.ok) {
        const data = await response.json();
        creditFeedback.innerText = `Compra registrada! Novos créditos: ${data.new_balance}.`;
        await loadBilling();
        await loadProfile();
      } else {
        creditFeedback.innerText = "Falha ao registrar compra. Tente novamente.";
      }
    });
  }
}

function bindProfileForm() {
  const profileForm = document.getElementById("profile-form");
  const feedback = document.getElementById("profile-feedback");
  if (!profileForm) return;
  profileForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      name: document.getElementById("profile-name").value,
      phone: document.getElementById("profile-phone").value,
      company_name: document.getElementById("profile-company").value,
      document: document.getElementById("profile-document").value,
    };
    const response = await apiFetch("/users/me", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    if (response?.ok) {
      feedback.innerText = "Perfil atualizado com sucesso.";
      await loadProfile();
    } else {
      feedback.innerText = "Não foi possível atualizar o perfil.";
    }
  });

  const passwordForm = document.getElementById("password-form");
  const passwordFeedback = document.getElementById("password-feedback");
  if (passwordForm) {
    passwordForm.addEventListener("submit", (event) => {
      event.preventDefault();
      passwordFeedback.innerText = "Fluxo de alteração de senha será implementado em breve.";
    });
  }
}

function bindLoginForms() {
  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    const feedback = document.getElementById("login-feedback");
    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      feedback.innerText = "Autenticando...";
      const payload = {
        email: document.getElementById("login-email").value,
        password: document.getElementById("login-password").value,
      };
      const response = await apiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (response?.ok) {
        const data = await response.json();
        setTokens(data.tokens);
        window.location.href = "/dashboard";
      } else {
        feedback.innerText = "Credenciais inválidas.";
      }
    });
  }

  const registerForm = document.getElementById("register-form");
  if (registerForm) {
    const feedback = document.getElementById("register-feedback");
    registerForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      feedback.innerText = "Criando conta...";
      const payload = {
        name: document.getElementById("reg-name").value,
        email: document.getElementById("reg-email").value,
        phone: document.getElementById("reg-phone").value,
        password: document.getElementById("reg-password").value,
        company_name: document.getElementById("reg-company").value,
        document: document.getElementById("reg-document").value,
        plan_slug: document.getElementById("reg-plan").value,
      };
      const response = await apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (response?.ok) {
        const data = await response.json();
        setTokens(data.tokens);
        window.location.href = "/dashboard";
      } else {
        feedback.innerText = "Não foi possível criar a conta. Verifique os dados.";
      }
    });
  }
}

function randomReference() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(16).slice(2)}`;
}

let currentPage = "";

document.addEventListener("DOMContentLoaded", async () => {
  const main = document.querySelector("[data-page]");
  currentPage = main?.dataset.page ?? "dashboard";

  bindLoginForms();

  if (!PUBLIC_PAGES.has(currentPage)) {
    if (!getAccessToken()) {
      window.location.href = "/login";
      return;
    }

    setActiveNavigation();
    await loadProfile();

    if (currentPage === "dashboard") {
      await loadDashboard();
    }
    if (currentPage === "chips") {
      await loadChips();
      document.getElementById("refresh-chips")?.addEventListener("click", loadChips);
    }
    if (currentPage === "campaigns") {
      await loadCampaigns();
    }
    if (currentPage === "billing") {
      await loadBilling();
      bindBillingForms();
    }
    if (currentPage === "settings") {
      bindProfileForm();
    }

    document.getElementById("logout-btn")?.addEventListener("click", () => {
      clearTokens();
      window.location.href = "/login";
    });
  } else {
    clearTokens();
  }
});
