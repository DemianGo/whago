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
  if (!response?.ok) return null;
  const data = await response.json();

  const nameEl = document.getElementById("user-name");
  const emailEl = document.getElementById("user-email");
  const initialEl = document.getElementById("user-initial");
  const planEl = document.getElementById("sidebar-plan");
  const creditsEl = document.getElementById("sidebar-credits");
  if (nameEl) nameEl.innerText = data.name;
  if (emailEl) emailEl.innerText = data.email;
  if (initialEl) initialEl.innerText = data.name?.[0]?.toUpperCase() ?? "U";
  if (planEl) planEl.innerText = data.plan_name ?? "Plano Free";
  if (creditsEl) creditsEl.innerText = `${data.credits ?? 0} créditos`;
  const mobilePlanEl = document.getElementById("mobile-plan");
  if (mobilePlanEl) {
    mobilePlanEl.innerText = data.plan_name ? `Plano ${data.plan_name}` : "Plano Free";
  }

  const profileName = document.getElementById("settings-name");
  if (profileName) {
    const phoneInput = document.getElementById("profile-phone");
    const companyInput = document.getElementById("profile-company");
    const documentInput = document.getElementById("profile-document");
    if (phoneInput) phoneInput.value = data.phone ?? "";
    if (companyInput) companyInput.value = data.company_name ?? "";
    if (documentInput) documentInput.value = data.document ?? "";
  }

  return data;
}

const notificationsState = {
  items: [],
  unread: 0,
  dropdownOpen: false,
  intervalId: null,
  pageUnreadOnly: false,
};

function renderNotificationsBadge() {
  const badge = document.getElementById("notifications-badge");
  if (!badge) return;
  if (notificationsState.unread > 0) {
    badge.classList.remove("hidden");
    badge.innerText = String(notificationsState.unread);
  } else {
    badge.classList.add("hidden");
  }
}

function notificationTypeLabel(type) {
  switch (type) {
    case "success":
      return "Sucesso";
    case "warning":
      return "Atenção";
    case "error":
      return "Erro";
    default:
      return "Informativo";
  }
}

function renderNotificationsDropdown() {
  const dropdown = document.getElementById("notifications-dropdown");
  const list = document.getElementById("notifications-list");
  if (!dropdown || !list) return;
  if (notificationsState.dropdownOpen) {
    dropdown.classList.remove("hidden");
    dropdown.setAttribute("aria-hidden", "false");
  } else {
    dropdown.classList.add("hidden");
    dropdown.setAttribute("aria-hidden", "true");
  }

  list.innerHTML = "";
  if (!notificationsState.items.length) {
    list.innerHTML = '<li class="text-sm text-slate-500">Nenhuma notificação até o momento.</li>';
    return;
  }

  notificationsState.items.forEach((item) => {
    const li = document.createElement("li");
    li.className = `notification__item ${item.is_read ? "" : "notification__item--unread"}`;
    li.dataset.notificationId = item.id;
    li.innerHTML = `
      <div class="notification__item-title">${notificationTypeLabel(item.type)}</div>
      <div class="notification__item-body">${item.title}${item.message ? ` — ${item.message}` : ""}</div>
      <div class="notification__item-time">${formatDate(item.created_at)}</div>
    `;
    list.appendChild(li);
  });
}

async function refreshNotificationsPreview() {
  const params = new URLSearchParams({ limit: "5" });
  const [listResp, countResp] = await Promise.all([
    apiFetch(`/notifications?${params.toString()}`),
    apiFetch("/notifications/unread-count"),
  ]);
  if (listResp?.ok) {
    notificationsState.items = await listResp.json();
  }
  if (countResp?.ok) {
    const data = await countResp.json();
    notificationsState.unread = data.unread ?? 0;
  }
  renderNotificationsBadge();
  renderNotificationsDropdown();
}

async function markNotifications(ids) {
  if (!ids.length) return;
  const response = await apiFetch("/notifications/mark-read", {
    method: "POST",
    body: JSON.stringify({ notification_ids: ids }),
  });
  if (response?.ok) {
    await refreshNotificationsPreview();
    if (currentPage === "notifications") {
      await loadNotificationsPage();
    }
  }
}

async function markAllNotifications() {
  const response = await apiFetch("/notifications/mark-all-read", { method: "POST" });
  if (response?.ok) {
    notificationsState.unread = 0;
    await refreshNotificationsPreview();
    if (currentPage === "notifications") {
      await loadNotificationsPage();
    }
  }
}

function bindNotificationDropdown() {
  const toggle = document.getElementById("notifications-toggle");
  const dropdown = document.getElementById("notifications-dropdown");
  const list = document.getElementById("notifications-list");
  if (!toggle || !dropdown || !list) return;

  toggle.addEventListener("click", async (event) => {
    event.stopPropagation();
    notificationsState.dropdownOpen = !notificationsState.dropdownOpen;
    renderNotificationsDropdown();
    if (notificationsState.dropdownOpen) {
      await refreshNotificationsPreview();
    }
  });

  document.getElementById("notifications-mark-all")?.addEventListener("click", async (event) => {
    event.preventDefault();
    await markAllNotifications();
  });

  list.addEventListener("click", async (event) => {
    const item = event.target.closest("[data-notification-id]");
    if (!item) return;
    const id = item.dataset.notificationId;
    await markNotifications([id]);
  });

  document.addEventListener("click", (event) => {
    if (notificationsState.dropdownOpen) {
      const target = event.target;
      if (!dropdown.contains(target) && target !== toggle) {
        notificationsState.dropdownOpen = false;
        renderNotificationsDropdown();
      }
    }
  });
}

async function loadNotificationsPage() {
  const list = document.getElementById("notifications-page-list");
  const empty = document.getElementById("notifications-page-empty");
  const counter = document.getElementById("notifications-page-counter");
  if (!list || !counter) return;

  const params = new URLSearchParams({ limit: "100" });
  if (notificationsState.pageUnreadOnly) {
    params.set("unread_only", "true");
  }
  const response = await apiFetch(`/notifications?${params.toString()}`);
  if (!response?.ok) return;
  const data = await response.json();

  list.innerHTML = "";
  if (!data.length) {
    empty?.classList.remove("hidden");
  } else {
    empty?.classList.add("hidden");
  }
  counter.innerText = `${data.length} notificações`;

  data.forEach((item) => {
    const li = document.createElement("li");
    li.className = `notification__item ${item.is_read ? "" : "notification__item--unread"}`;
    li.dataset.notificationId = item.id;
    li.innerHTML = `
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div class="notification__item-title">${item.title}</div>
          <div class="notification__item-body">${item.message ?? ""}</div>
        </div>
        <div class="flex flex-col items-end gap-2 text-right">
          <span class="notification__item-time">${formatDate(item.created_at)}</span>
          ${item.is_read ? "" : '<button type="button" class="btn-secondary notification__page-mark">Marcar como lida</button>'}
        </div>
      </div>
    `;
    list.appendChild(li);
  });
}

function bindNotificationsPage() {
  const filter = document.getElementById("notifications-filter-unread");
  const markAllButton = document.getElementById("notifications-page-mark-all");
  const list = document.getElementById("notifications-page-list");
  if (filter) {
    filter.addEventListener("change", async (event) => {
      notificationsState.pageUnreadOnly = event.target.checked;
      await loadNotificationsPage();
    });
  }
  if (markAllButton) {
    markAllButton.addEventListener("click", async () => {
      await markAllNotifications();
      await loadNotificationsPage();
    });
  }
  if (list) {
    list.addEventListener("click", async (event) => {
      const button = event.target.closest(".notification__page-mark");
      if (!button) return;
      const item = event.target.closest("[data-notification-id]");
      if (!item) return;
      await markNotifications([item.dataset.notificationId]);
      await loadNotificationsPage();
    });
  }
}

function bindSidebarToggle() {
  const toggle = document.getElementById("sidebar-toggle");
  const sidebar = document.querySelector(".sidebar");
  const overlay = document.getElementById("sidebar-overlay");
  if (!toggle || !sidebar || !overlay) return;

  const closeSidebar = () => {
    sidebar.classList.remove("sidebar--open");
    overlay.classList.add("hidden");
    document.body.classList.remove("overflow-hidden");
  };

  toggle.addEventListener("click", (event) => {
    event.preventDefault();
    sidebar.classList.add("sidebar--open");
    overlay.classList.remove("hidden");
    document.body.classList.add("overflow-hidden");
  });

  overlay.addEventListener("click", closeSidebar);
  window.addEventListener("resize", () => {
    if (window.innerWidth >= 1024) {
      closeSidebar();
    }
  });
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

async function loadMessagesPageData() {
  const tbody = document.getElementById("messages-table-body");
  const empty = document.getElementById("messages-empty");
  if (!tbody) return;
  const statusSelect = document.getElementById("messages-filter-status");
  const campaignInput = document.getElementById("messages-filter-campaign");
  const recipientInput = document.getElementById("messages-filter-recipient");
  const params = new URLSearchParams({ limit: "100" });
  if (statusSelect?.value) params.set("status", statusSelect.value);
  if (campaignInput?.value) params.set("campaign_id", campaignInput.value.trim());
  if (recipientInput?.value) params.set("recipient", recipientInput.value.trim());

  const response = await apiFetch(`/messages?${params.toString()}`);
  if (!response?.ok) return;
  const data = await response.json();

  tbody.innerHTML = "";
  if (!data.length) {
    empty?.classList.remove("hidden");
    return;
  }
  empty?.classList.add("hidden");

  data.forEach((item) => {
    const tr = document.createElement("tr");
    tr.className = "align-top";
    tr.innerHTML = `
      <td class="py-3">
        <div class="font-medium text-slate-700">${item.recipient}</div>
        <div class="text-xs text-slate-500">${item.failure_reason ?? ""}</div>
      </td>
      <td class="py-3 text-slate-600">${item.campaign_name}</td>
      <td class="py-3 text-slate-600">${item.chip_alias ?? "--"}</td>
      <td class="py-3"><span class="status status-${item.status.toLowerCase()}">${item.status}</span></td>
      <td class="py-3 text-slate-500">${formatDate(item.sent_at)}</td>
      <td class="py-3 text-slate-500">${formatDate(item.delivered_at)}</td>
      <td class="py-3 text-slate-500">${formatDate(item.read_at)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function bindMessagesPage() {
  const applyBtn = document.getElementById("messages-filter-apply");
  if (applyBtn) {
    applyBtn.addEventListener("click", loadMessagesPageData);
  }
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

function parseDateInput(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

async function downloadBlob(response, fallbackName) {
  const contentDisposition = response.headers.get("Content-Disposition");
  let filename = fallbackName;
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^";]+)"?/i);
    if (match) {
      filename = match[1];
    }
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

function renderJsonPreview(previewElement, data) {
  if (!previewElement) return;
  previewElement.classList.remove("hidden");
  previewElement.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

async function handleReportRequest({
  endpoint,
  format,
  params,
  previewElement,
  fallbackFilename,
}) {
  const search = new URLSearchParams({ ...params, format });
  const response = await apiFetch(`${endpoint}?${search.toString()}`);
  if (!response) return;

  if (!response.ok) {
    const errorText = await response.text();
    renderJsonPreview(previewElement, errorText || "Não foi possível gerar o relatório.");
    return;
  }

  if (format === "json") {
    const data = await response.json();
    renderJsonPreview(previewElement, data);
  } else {
    if (previewElement) {
      previewElement.classList.add("hidden");
    }
    await downloadBlob(response, `${fallbackFilename}.${format}`);
  }
}

async function loadPlanComparison() {
  const tableBody = document.querySelector("#plan-comparison-table tbody");
  if (!tableBody) return;
  const response = await apiFetch("/reports/plans/comparison?format=json");
  if (!response?.ok) {
    tableBody.innerHTML = "<tr><td class=\"py-4\" colspan=\"3\">Não foi possível carregar o comparativo de planos.</td></tr>";
    return;
  }
  const data = await response.json();
  tableBody.innerHTML = "";
  data.plans.forEach((plan) => {
    const tr = document.createElement("tr");
    const features = Object.entries(plan.features || {})
      .map(([key, value]) => `<strong>${key}:</strong> ${value}`)
      .join("<br />");
    tr.innerHTML = `
      <td class="py-3 font-medium text-slate-800">${plan.name}</td>
      <td class="py-3">R$ ${plan.price.toFixed(2)}</td>
      <td class="py-3">${features || "-"}</td>
    `;
    tableBody.appendChild(tr);
  });
}

function bindReportsPage() {
  loadPlanComparison();

  const campaignForm = document.getElementById("campaign-report-form");
  if (campaignForm) {
    campaignForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const campaignId = document.getElementById("campaign-report-id").value.trim();
      if (!campaignId) return;
      const format = document.getElementById("campaign-report-format").value;
      const preview = document.getElementById("campaign-report-preview");
      await handleReportRequest({
        endpoint: `/reports/campaign/${campaignId}`,
        format,
        params: {},
        previewElement: preview,
        fallbackFilename: `campaign-${campaignId}`,
      });
    });
  }

  const chipsForm = document.getElementById("chips-report-form");
  if (chipsForm) {
    chipsForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const format = document.getElementById("chips-report-format").value;
      const preview = document.getElementById("chips-report-preview");
      const params = {
        start_date: parseDateInput(document.getElementById("chips-start").value),
        end_date: parseDateInput(document.getElementById("chips-end").value),
      };
      await handleReportRequest({
        endpoint: "/reports/chips",
        format,
        params,
        previewElement: preview,
        fallbackFilename: "chips-report",
      });
    });
  }

  const financialForm = document.getElementById("financial-report-form");
  if (financialForm) {
    financialForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const format = document.getElementById("financial-report-format").value;
      const preview = document.getElementById("financial-report-preview");
      const params = {
        start_date: parseDateInput(document.getElementById("financial-start").value),
        end_date: parseDateInput(document.getElementById("financial-end").value),
      };
      await handleReportRequest({
        endpoint: "/reports/financial",
        format,
        params,
        previewElement: preview,
        fallbackFilename: "financial-report",
      });
    });
  }

  const executiveForm = document.getElementById("executive-report-form");
  if (executiveForm) {
    executiveForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const format = document.getElementById("executive-report-format").value;
      const preview = document.getElementById("executive-report-preview");
      const params = {
        start_date: parseDateInput(document.getElementById("executive-start").value),
        end_date: parseDateInput(document.getElementById("executive-end").value),
      };
      await handleReportRequest({
        endpoint: "/reports/executive",
        format,
        params,
        previewElement: preview,
        fallbackFilename: "executive-report",
      });
    });
  }

  const downloadButtons = document.querySelectorAll("#download-plan-comparison, #download-plan-comparison-pdf");
  downloadButtons.forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      const format = button.dataset.format || "xlsx";
      const response = await apiFetch(`/reports/plans/comparison?format=${format}`);
      if (!response?.ok) return;
      await downloadBlob(response, `plan-comparison.${format}`);
    });
  });
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
    bindSidebarToggle();
    await loadProfile();
    bindNotificationDropdown();
    await refreshNotificationsPreview();
    if (!notificationsState.intervalId) {
      notificationsState.intervalId = setInterval(refreshNotificationsPreview, 60000);
    }

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
    if (currentPage === "executive") {
      bindProfileForm();
    }
    if (currentPage === "reports") {
      bindReportsPage();
    }
    if (currentPage === "notifications") {
      await loadNotificationsPage();
      bindNotificationsPage();
    }
    if (currentPage === "messages") {
      await loadMessagesPageData();
      bindMessagesPage();
    }

    document.getElementById("logout-btn")?.addEventListener("click", () => {
      clearTokens();
      window.location.href = "/login";
    });
  } else {
    clearTokens();
  }
});
