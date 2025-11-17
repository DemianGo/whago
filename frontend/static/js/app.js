const API_BASE = "/api/v1";
const ACCESS_TOKEN_KEY = "whago_access_token";
const REFRESH_TOKEN_KEY = "whago_refresh_token";

const PUBLIC_PAGES = new Set(["login", "register", "home", ""]);

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

const CHIP_STATUS_LABELS = {
  WAITING_QR: "Aguardando QR",
  CONNECTING: "Conectando",
  CONNECTED: "Conectado",
  MATURING: "Em aquecimento",
  DISCONNECTED: "Desconectado",
  MAINTENANCE: "Em manutenção",
  BANNED: "Banido",
  ERROR: "Erro",
};

const chipState = {
  pollIntervalId: null,
  qrPollIntervalId: null,
  currentChipId: null,
  modalOpen: false,
  modal: {
    element: null,
    backdrop: null,
    form: null,
    aliasInput: null,
    submitButton: null,
  },
};

const campaignState = {
  campaignId: null,
  currentStep: 1,
  contactsSummary: null,
  createdCampaign: null,
  wizard: {
    element: null,
    backdrop: null,
    steps: [],
    panels: [],
  },
  selectedChips: new Set(),
  chipCache: [],
  variables: [],
  media: [],
  pendingMediaFile: null,
};

globalThis.__WHAGO_CAMPAIGN_STATE = campaignState;

function setCampaignFeedback(message, type = "info") {
  const feedback = document.getElementById("campaign-feedback");
  if (!feedback) return;
  feedback.textContent = message ?? "";
  feedback.classList.remove("text-emerald-600", "text-red-600", "text-amber-600", "text-slate-500");
  if (!message) {
    feedback.classList.add("text-slate-500");
    return;
  }
  const classMap = {
    success: "text-emerald-600",
    error: "text-red-600",
    warning: "text-amber-600",
    info: "text-slate-500",
  };
  feedback.classList.add(classMap[type] ?? "text-slate-500");
}

function setCampaignMediaFeedback(message, type = "info") {
  const feedback = document.getElementById("campaign-media-feedback");
  if (!feedback) return;
  const classMap = {
    success: "text-emerald-600",
    error: "text-red-600",
    warning: "text-amber-600",
    info: "text-slate-500",
  };
  feedback.textContent = message ?? "";
  feedback.classList.remove("text-emerald-600", "text-red-600", "text-amber-600", "text-slate-500");
  feedback.classList.add(classMap[type] ?? "text-slate-500");
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** index;
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

function renderCampaignMediaList() {
  const list = document.getElementById("campaign-media-list");
  if (!list) return;
  if (!campaignState.media.length) {
    list.classList.add("hidden");
    list.innerHTML = "";
    return;
  }
  list.classList.remove("hidden");
  list.innerHTML = campaignState.media
    .map((item) => `<li data-media-id="${item.id}">${item.original_name} (${formatBytes(item.size_bytes)})</li>`)
    .join("");
}

function renderCampaignVariables() {
  const container = document.getElementById("campaign-variables");
  const box = document.getElementById("campaign-variables-box");
  if (!container || !box) return;
  if (!campaignState.variables.length) {
    container.innerHTML = "";
    box.classList.add("hidden");
    return;
  }
  box.classList.remove("hidden");
  container.innerHTML = campaignState.variables
    .map((variable) => `<button type="button" class="badge" data-variable="${variable}">{{${variable}}}</button>`)
    .join("");
}

function renderCampaignVariablesSummary() {
  const summary = document.getElementById("campaign-variables-summary");
  if (!summary) return;
  if (!campaignState.variables.length) {
    summary.classList.add("hidden");
    summary.innerHTML = "";
    return;
  }
  summary.classList.remove("hidden");
  summary.innerHTML = `<strong>Variáveis detectadas:</strong> ${campaignState.variables
    .map((variable) => `{{${variable}}}`)
    .join(", ")}`;
}

function insertVariableAtCursor(target, value) {
  if (!(target instanceof HTMLTextAreaElement)) return;
  const start = target.selectionStart ?? target.value.length;
  const end = target.selectionEnd ?? target.value.length;
  const before = target.value.slice(0, start);
  const after = target.value.slice(end);
  target.value = `${before}${value}${after}`;
  const newPosition = start + value.length;
  target.focus();
  target.setSelectionRange(newPosition, newPosition);
  target.dispatchEvent(new Event("input", { bubbles: true }));
}

async function safeReadText(response) {
  try {
    const text = await response.text();
    if (!text) return null;
    try {
      const parsed = JSON.parse(text);
      if (parsed && typeof parsed.detail === "string") return parsed.detail;
      if (parsed && typeof parsed.message === "string") return parsed.message;
      return text;
    } catch (error) {
      return text;
    }
  } catch (error) {
    console.error(error);
    return null;
  }
}

async function uploadCampaignMedia(file) {
  if (!file) return false;
  if (!campaignState.campaignId) {
    campaignState.pendingMediaFile = file;
    setCampaignMediaFeedback("Crie a campanha antes de enviar a mídia.", "warning");
    return false;
  }
  setCampaignMediaFeedback(`Enviando ${file.name}...`, "info");
  const token = getAccessToken();
  const formData = new FormData();
  formData.append("file", file);
  try {
    const response = await fetch(`${API_BASE}/campaigns/${campaignState.campaignId}/media`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!response.ok) {
      const message = await safeReadText(response) ?? "Falha ao anexar o arquivo.";
      setCampaignMediaFeedback(message, "error");
      return false;
    }
    const media = await response.json();
    campaignState.media.push(media);
    if (campaignState.createdCampaign) {
      if (!Array.isArray(campaignState.createdCampaign.media)) {
        campaignState.createdCampaign.media = [];
      }
      campaignState.createdCampaign.media.push(media);
    }
    setCampaignMediaFeedback(`Arquivo ${media.original_name} anexado com sucesso.`, "success");
    renderCampaignMediaList();
    return true;
  } catch (error) {
    console.error(error);
    setCampaignMediaFeedback("Erro inesperado ao enviar o arquivo.", "error");
    return false;
  }
}

async function maybeUploadPendingMedia() {
  if (!campaignState.pendingMediaFile || !campaignState.campaignId) {
    return;
  }
  const file = campaignState.pendingMediaFile;
  campaignState.pendingMediaFile = null;
  await uploadCampaignMedia(file);
  const mediaInput = document.getElementById("campaign-media");
  if (mediaInput) {
    mediaInput.value = "";
  }
}

const CAMPAIGN_STATUS_LABELS = {
  draft: "Rascunho",
  scheduled: "Agendada",
  running: "Em andamento",
  paused: "Pausada",
  completed: "Concluída",
  cancelled: "Cancelada",
  error: "Erro",
};

function formatCampaignStatus(status) {
  if (!status) return "--";
  const key = String(status).toLowerCase();
  return CAMPAIGN_STATUS_LABELS[key] ?? status;
}

function getCampaignStatusClass(status) {
  const normalized = (status || "").toLowerCase();
  switch (normalized) {
    case "running":
      return "status status-running";
    case "paused":
      return "status status-paused";
    case "completed":
      return "status status-delivered";
    case "cancelled":
    case "error":
      return "status status-error";
    case "scheduled":
      return "status status-waiting";
    default:
      return "status";
  }
}

const statusMap = {
  draft: "Rascunho",
  scheduled: "Agendada",
  running: "Em andamento",
  paused: "Pausada",
  completed: "Concluída",
  cancelled: "Cancelada",
  error: "Erro",
};

const WEBHOOK_EVENTS = [
  { value: "campaign.started", label: "Campanha iniciada" },
  { value: "campaign.completed", label: "Campanha concluída" },
  { value: "campaign.paused", label: "Campanha pausada" },
  { value: "campaign.cancelled", label: "Campanha cancelada" },
  { value: "message.sent", label: "Mensagem enviada" },
  { value: "message.failed", label: "Mensagem com falha" },
  { value: "payment.succeeded", label: "Pagamento aprovado" },
];

const webhookState = {
  subscription: null,
  logs: [],
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
  const planName = data.plan ?? data.plan_name ?? "Plano Free";
  if (nameEl) nameEl.innerText = data.name;
  if (emailEl) emailEl.innerText = data.email;
  if (initialEl) initialEl.innerText = data.name?.[0]?.toUpperCase() ?? "U";
  if (planEl) planEl.innerText = planName;
  if (creditsEl) creditsEl.innerText = `${data.credits ?? 0} créditos`;
  const mobilePlanEl = document.getElementById("mobile-plan");
  if (mobilePlanEl) {
    mobilePlanEl.innerText = `Plano ${planName}`;
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

  window.whagoUser = data;
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
    const creditsEl = selectors.summaryCredits();
    if (creditsEl) {
      creditsEl.innerText = `${data.credits_available} créditos`;
    }
    const todayEl = selectors.summaryToday();
    if (todayEl) {
      todayEl.innerText = data.messages_today;
    }
    const todayVarEl = selectors.summaryTodayVariation();
    if (todayVarEl) {
      todayVarEl.innerText = displayVariation(data.messages_today_variation);
    }
    const monthEl = selectors.summaryMonth();
    if (monthEl) {
      monthEl.innerText = data.messages_month;
    }
    const monthVarEl = selectors.summaryMonthVariation();
    if (monthVarEl) {
      monthVarEl.innerText = displayVariation(data.messages_month_variation);
    }
    const successEl = selectors.summarySuccess();
    if (successEl) {
      successEl.innerText = `${data.success_rate.toFixed(2)}%`;
    }
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

async function loadProxyUsage() {
  try {
    const response = await apiFetch("/user/proxy/usage");
    if (response?.ok) {
      const data = await response.json();
      
      // Atualizar texto do limite
      const limitText = document.getElementById("proxy-limit-text");
      if (limitText) {
        limitText.textContent = `${data.gb_used} / ${parseFloat(data.limit_gb)} GB`;
      }
      
      // Atualizar barra de progresso
      const progressBar = document.getElementById("proxy-progress-bar");
      if (progressBar) {
        const percentage = Math.min(data.percentage_used, 100);
        progressBar.style.width = `${percentage}%`;
        
        // Mudar cor baseado no uso
        progressBar.classList.remove('bg-blue-500', 'bg-yellow-500', 'bg-red-500');
        if (percentage >= 90) {
          progressBar.classList.add('bg-red-500');
        } else if (percentage >= 70) {
          progressBar.classList.add('bg-yellow-500');
        } else {
          progressBar.classList.add('bg-blue-500');
        }
      }
      
      // Atualizar hint com custo
      const hint = document.getElementById("proxy-usage-hint");
      if (hint) {
        let message = `Proteção via proxy residencial. Custo: R$ ${parseFloat(data.cost).toFixed(2)}`;
        if (data.percentage_used >= 90) {
          message = `⚠️ Você está próximo do limite (${data.percentage_used.toFixed(1)}%)!`;
        } else if (data.percentage_used >= 100) {
          message = `🚫 Limite excedido! Faça upgrade ou aguarde dia 1.`;
        }
        hint.textContent = message;
      }
      
      // Ocultar card se não houver limite configurado
      if (parseFloat(data.limit_gb) <= 0) {
        const card = document.getElementById("proxy-usage-card");
        if (card) card.style.display = 'none';
      }
    }
  } catch (error) {
    console.error('Erro ao carregar uso de proxy:', error);
  }
}

function formatChipStatus(status) {
  if (!status) return "--";
  const key = String(status).toUpperCase();
  return CHIP_STATUS_LABELS[key] ?? String(status).replace(/_/g, " ");
}

function getChipStatusClass(status) {
  const normalized = (status || "").toLowerCase();
  switch (normalized) {
    case "waiting_qr":
    case "waiting-qr":
      return "status status-waiting";
    case "connecting":
      return "status status-waiting";
    case "connected":
      return "status status-connected";
    case "maturing":
      return "status status-maturing";
    case "disconnected":
      return "status status-disconnected";
    case "error":
      return "status status-error";
    default:
      return "status";
  }
}

function setChipFeedback(message, type = "info") {
  const feedback = document.getElementById("chip-feedback");
  if (!feedback) return;
  feedback.textContent = message ?? "";
  feedback.classList.remove("text-emerald-600", "text-red-600", "text-amber-600", "text-slate-500");
  if (!message) {
    feedback.classList.add("text-slate-500");
    return;
  }
  const classMap = {
    success: "text-emerald-600",
    error: "text-red-600",
    warning: "text-amber-600",
    info: "text-slate-500",
  };
  feedback.classList.add(classMap[type] ?? "text-slate-500");
}

function openChipModal() {
  const { element, backdrop, aliasInput, submitButton } = chipState.modal;
  if (!element || !backdrop) return;
  element.classList.remove("hidden");
  backdrop.classList.remove("hidden");
  chipState.modalOpen = true;
  submitButton?.removeAttribute("disabled");
  aliasInput?.focus({ preventScroll: true });
}

function closeChipModal() {
  const { element, backdrop, form } = chipState.modal;
  if (!element || !backdrop) return;
  element.classList.add("hidden");
  backdrop.classList.add("hidden");
  chipState.modalOpen = false;
  form?.reset();
}

async function handleChipFormSubmit(event) {
  event.preventDefault();
  const { aliasInput, submitButton } = chipState.modal;
  if (!aliasInput) return;
  const alias = aliasInput.value.trim();
  if (!alias) {
    setChipFeedback("Informe um apelido para o chip.", "warning");
    return;
  }
  submitButton?.setAttribute("disabled", "true");
  setChipFeedback("Criando chip...", "info");
  const response = await apiFetch("/chips", {
    method: "POST",
    body: JSON.stringify({ alias }),
  });
  if (response?.ok) {
    const chip = await response.json();
    setChipFeedback(`Chip ${chip.alias} criado com sucesso.`, "success");
    
    // Show QR Code section
    await showChipQrCode(chip.id);
    await loadChips({ silent: true });
  } else {
    let detail = "Não foi possível criar o chip.";
    try {
      const error = await response.json();
      if (typeof error?.detail === "string") {
        detail = error.detail;
      }
    } catch (err) {
      // Ignora falha ao ler corpo da resposta
    }
    setChipFeedback(detail, "error");
  }
  submitButton?.removeAttribute("disabled");
}

async function showChipQrCode(chipId) {
  console.log('[showChipQrCode] Iniciando para chip:', chipId);
  
  // Hide form, show QR section
  const form = document.getElementById("chip-form");
  const qrSection = document.getElementById("chip-qr-section");
  const qrLoading = document.getElementById("chip-qr-loading");
  const qrImage = document.getElementById("chip-qr-image");
  const qrStatus = document.getElementById("chip-qr-status");
  
  console.log('[showChipQrCode] Elementos encontrados:', { 
    form: !!form, 
    qrSection: !!qrSection, 
    qrImage: !!qrImage, 
    qrLoading: !!qrLoading 
  });
  
  if (!form || !qrSection || !qrImage || !qrLoading) {
    console.error('[showChipQrCode] Elementos faltando!');
    return;
  }
  
  form.classList.add("hidden");
  qrSection.classList.remove("hidden");
  qrLoading.classList.remove("hidden");
  qrImage.classList.add("hidden");
  
  console.log('[showChipQrCode] QR section exibida');
  
  chipState.currentChipId = chipId;
  chipState.qrPollIntervalId = setInterval(() => {
    void fetchAndDisplayQrCode(chipId);
  }, 5000); // Poll every 5 seconds
  
  // Initial fetch
  await fetchAndDisplayQrCode(chipId);
  
  // Bind close button
  const closeButton = document.getElementById("chip-qr-close");
  closeButton?.addEventListener("click", () => {
    closeChipQrModal();
  });
}

async function fetchAndDisplayQrCode(chipId) {
  const qrLoading = document.getElementById("chip-qr-loading");
  const qrImage = document.getElementById("chip-qr-image");
  const qrStatus = document.getElementById("chip-qr-status");
  
  if (!qrImage || !qrStatus) return;
  
  try {
    const response = await apiFetch(`/chips/${chipId}/qr`);
    
    if (!response?.ok) {
      if (qrStatus) {
        qrStatus.textContent = "Erro ao buscar QR Code. Tentando novamente...";
        qrStatus.className = "text-center text-sm text-red-600";
      }
      return;
    }
    
    const data = await response.json();
    console.log('[QR Code Debug]', { chipId, data, hasQrCode: !!(data.qr_code || data.qr) });
    
    // Backend retorna 'qr_code', não 'qr'
    const qrCode = data.qr_code || data.qr;
    
    if (qrCode) {
      // QR code is available
      if (qrLoading) qrLoading.classList.add("hidden");
      qrImage.src = qrCode;
      qrImage.classList.remove("hidden");
      
      if (qrStatus) {
        if (data.expires_at) {
          const expiresAt = new Date(data.expires_at);
          const now = new Date();
          const secondsLeft = Math.floor((expiresAt - now) / 1000);
          if (secondsLeft > 0) {
            qrStatus.textContent = `QR Code expira em ${secondsLeft} segundos`;
            qrStatus.className = "text-center text-sm text-slate-600";
          } else {
            qrStatus.textContent = "QR Code expirado. Gerando novo...";
            qrStatus.className = "text-center text-sm text-orange-600";
          }
        } else {
          qrStatus.textContent = "Escaneie o QR Code acima com seu WhatsApp";
          qrStatus.className = "text-center text-sm text-slate-600";
        }
      }
    } else {
      // No QR code yet
      if (qrLoading) qrLoading.classList.remove("hidden");
      qrImage.classList.add("hidden");
      if (qrStatus) {
        qrStatus.textContent = "Aguardando QR Code...";
        qrStatus.className = "text-center text-sm text-slate-600";
      }
    }
    
    // Check chip status
    const chipResponse = await apiFetch(`/chips/${chipId}`);
    if (chipResponse?.ok) {
      const chip = await chipResponse.json();
      if (chip.status === "connected") {
        // Chip connected, close modal
        if (qrStatus) {
          qrStatus.textContent = "✅ Chip conectado com sucesso!";
          qrStatus.className = "text-center text-sm text-green-600 font-semibold";
        }
        setTimeout(() => {
          closeChipQrModal();
        }, 2000);
      }
    }
  } catch (error) {
    console.error("Error fetching QR code:", error);
    if (qrStatus) {
      qrStatus.textContent = "Erro ao buscar QR Code. Tentando novamente...";
      qrStatus.className = "text-center text-sm text-red-600";
    }
  }
}

function closeChipQrModal() {
  const form = document.getElementById("chip-form");
  const qrSection = document.getElementById("chip-qr-section");
  
  if (chipState.qrPollIntervalId) {
    clearInterval(chipState.qrPollIntervalId);
    chipState.qrPollIntervalId = null;
  }
  
  if (form) form.classList.remove("hidden");
  if (qrSection) qrSection.classList.add("hidden");
  
  closeChipModal();
  chipState.currentChipId = null;
}

function bindChipModal() {
  chipState.modal.element = document.getElementById("chip-modal");
  chipState.modal.backdrop = document.getElementById("chip-modal-backdrop");
  chipState.modal.form = document.getElementById("chip-form");
  chipState.modal.aliasInput = document.getElementById("chip-alias");
  chipState.modal.submitButton = document.querySelector("[data-test=\"submit-chip\"]");

  const cancelButton = document.getElementById("chip-modal-cancel");
  const closeButton = document.getElementById("chip-modal-close");

  cancelButton?.addEventListener("click", (event) => {
    event.preventDefault();
    closeChipModal();
  });
  closeButton?.addEventListener("click", (event) => {
    event.preventDefault();
    closeChipModal();
  });
  chipState.modal.backdrop?.addEventListener("click", closeChipModal);
  chipState.modal.form?.addEventListener("submit", handleChipFormSubmit);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && chipState.modalOpen) {
      closeChipModal();
    }
  });
}

function startChipPolling() {
  if (chipState.pollIntervalId) return;
  chipState.pollIntervalId = setInterval(() => {
    void loadChips({ silent: true });
  }, 5000);
}

function bindChipsPage() {
  bindChipModal();
  document.querySelector("[data-test=\"add-chip\"]")?.addEventListener("click", () => {
    openChipModal();
  });
  document.getElementById("refresh-chips")?.addEventListener("click", () => {
    void loadChips({ silent: true });
  });
}

async function initChipsPage() {
  bindChipsPage();
  await loadChips();
  startChipPolling();
}

async function loadChips(options = {}) {
  const { silent = false } = options;
  const response = await apiFetch("/chips");
  if (!response?.ok) {
    if (!silent) {
      setChipFeedback("Não foi possível carregar os chips.", "error");
    }
    return;
  }
  const chips = await response.json();
  const table = document.querySelector("#chip-table tbody");
  if (!table) return;
  table.innerHTML = "";
  chips.forEach((chip) => {
    const statusLabel = formatChipStatus(chip.status);
    const statusClass = getChipStatusClass(chip.status);
    const heatUpStatus = chip.extra_data?.heat_up?.status;
    const isHeatingUp = heatUpStatus === "in_progress";
    
    const row = document.createElement("tr");
    row.dataset.test = "chip-row";
    row.dataset.chipId = chip.id;
    row.dataset.alias = chip.alias;
    row.innerHTML = `
      <td class="py-2 font-medium text-slate-800">
        ${chip.alias}
        ${isHeatingUp ? '<span class="ml-2 text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">🔥 Aquecendo</span>' : ''}
      </td>
      <td class="py-2"><span data-test="chip-status" class="${statusClass}">${statusLabel}</span></td>
      <td class="py-2">${chip.health_score ?? "--"}</td>
      <td class="py-2">${formatDate(chip.created_at)}</td>
      <td class="py-2">${formatDate(chip.last_activity_at)}</td>
      <td class="py-2 text-right">
        <div class="flex gap-2 justify-end">
          <button class="btn-secondary btn-xs" type="button" data-test="chip-action-heatup" data-chip-id="${chip.id}">
            Iniciar heat-up
          </button>
          ${chip.status === 'connected' ? `
            <button class="btn-secondary btn-xs" type="button" data-action="disconnect" data-chip-id="${chip.id}">
              Desconectar
            </button>
          ` : ''}
          <button class="btn-secondary btn-xs text-red-600 hover:bg-red-50" type="button" data-action="delete" data-chip-id="${chip.id}">
            Deletar
          </button>
        </div>
      </td>
    `;
    table.appendChild(row);

    const heatUpButton = row.querySelector("[data-test=\"chip-action-heatup\"]");
    const heatUpInfo = chip.extra_data?.heat_up;
    if (heatUpInfo?.status === "in_progress") {
      heatUpButton?.setAttribute("disabled", "true");
      if (heatUpButton) heatUpButton.textContent = "Heat-up em andamento";
    } else {
      heatUpButton?.addEventListener("click", async () => {
        await handleChipHeatUp(heatUpButton);
      });
    }
    
    // Disconnect button
    const disconnectButton = row.querySelector("[data-action=\"disconnect\"]");
    disconnectButton?.addEventListener("click", async () => {
      if (confirm(`Deseja desconectar o chip "${chip.alias}"?`)) {
        await handleChipDisconnect(chip.id);
      }
    });
    
    // Delete button
    const deleteButton = row.querySelector("[data-action=\"delete\"]");
    deleteButton?.addEventListener("click", async (e) => {
      // Prevenir múltiplos cliques
      if (deleteButton.disabled) return;
      
      const heatUpStatus = chip.extra_data?.heat_up?.status;
      let confirmMsg = `Tem certeza que deseja DELETAR o chip "${chip.alias}"?`;
      
      if (heatUpStatus === "in_progress") {
        confirmMsg = `⚠️ ATENÇÃO: O chip "${chip.alias}" está EM AQUECIMENTO!\n\nDeletar agora interromperá o processo de aquecimento.\n\nTem certeza que deseja DELETAR?`;
      } else if (chip.status === "connected") {
        confirmMsg = `⚠️ ATENÇÃO: O chip "${chip.alias}" está CONECTADO!\n\nDeletar desconectará o WhatsApp.\n\nTem certeza que deseja DELETAR?`;
      }
      
      confirmMsg += "\n\nEsta ação não pode ser desfeita.";
      
      if (confirm(confirmMsg)) {
        deleteButton.disabled = true;
        deleteButton.textContent = "Deletando...";
        await handleChipDelete(chip.id);
        // Não precisa re-habilitar pois a linha será removida após reload
      }
    });
  });

  if (!silent) {
    const activePlan = chips.find((chip) => chip.extra_data?.heat_up?.plan?.length);
    if (activePlan) {
      const planPayload = activePlan.extra_data.heat_up;
      renderHeatUpPlan({
        chip_id: activePlan.id,
        stages: planPayload.plan,
        recommended_total_hours: planPayload.plan.reduce(
          (total, stage) => total + (stage.duration_hours ?? 0),
          0,
        ),
        message: "Plano de aquecimento em andamento.",
      });
    } else {
      renderHeatUpPlan(null);
    }
  }

  if (!silent) {
    if (!chips.length) {
      setChipFeedback("Nenhum chip cadastrado até o momento.", "info");
    } else {
      setChipFeedback("", "info");
    }
  }
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
    document.getElementById("billing-current-plan").innerText = data.plan_name ?? data.plan ?? "--";
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
  if (creditFeedback) {
    creditFeedback.dataset.state = creditFeedback.dataset.state || "idle";
  }
  if (creditForm) {
    creditForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (creditFeedback) {
        creditFeedback.dataset.state = "loading";
      }
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
        if (creditFeedback) {
          creditFeedback.dataset.state = "success";
        }
        await loadBilling();
        await loadProfile();
      } else {
        creditFeedback.innerText = "Falha ao registrar compra. Tente novamente.";
        if (creditFeedback) {
          creditFeedback.dataset.state = "error";
        }
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

function ensureWebhookEventsRendered() {
  const container = document.getElementById("webhook-events-container");
  if (!container || container.dataset.bound === "true") return;
  container.innerHTML = "";
  WEBHOOK_EVENTS.forEach((event) => {
    const safeId = event.value.replace(/\./g, "-");
    const wrapper = document.createElement("label");
    wrapper.className = "inline-flex items-center gap-2 rounded border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600";
    wrapper.innerHTML = `
      <input type="checkbox" value="${event.value}" id="webhook-event-${safeId}" class="h-4 w-4 rounded border-slate-300" />
      <span>${event.label}</span>
    `;
    container.appendChild(wrapper);
  });
  container.dataset.bound = "true";
}

function getSelectedWebhookEvents() {
  const container = document.getElementById("webhook-events-container");
  if (!container) return [];
  return Array.from(container.querySelectorAll('input[type="checkbox"]:checked')).map((checkbox) => checkbox.value);
}

function setSelectedWebhookEvents(events) {
  const container = document.getElementById("webhook-events-container");
  if (!container) return;
  const selected = new Set(events);
  container.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
    checkbox.checked = selected.has(checkbox.value);
  });
}

function setWebhookFeedback(message, type = "info") {
  const feedback = document.getElementById("webhook-feedback");
  if (!feedback) return;
  feedback.innerText = message;
  feedback.classList.remove("text-red-500", "text-emerald-600", "text-slate-500");
  if (type === "error") {
    feedback.classList.add("text-red-500");
  } else if (type === "success") {
    feedback.classList.add("text-emerald-600");
  } else {
    feedback.classList.add("text-slate-500");
  }
}

function renderWebhookLogs(logs) {
  const section = document.getElementById("webhook-logs");
  const list = document.getElementById("webhook-logs-list");
  if (!section || !list) return;
  if (!logs.length) {
    section.classList.add("hidden");
    list.innerHTML = "";
    return;
  }
  section.classList.remove("hidden");
  list.innerHTML = "";
  logs.forEach((log) => {
    const item = document.createElement("li");
    item.className = "rounded border border-slate-200 bg-slate-50 p-3";
    item.innerHTML = `
      <div class="flex items-center justify-between text-xs text-slate-500">
        <span>${log.event}</span>
        <span>${formatDate(log.created_at)}</span>
      </div>
      <div class="mt-1 text-sm text-slate-600">
        Status: ${log.success ? "Entregue" : "Falha"} ${log.status_code ? `(HTTP ${log.status_code})` : ""}
      </div>
    `;
    list.appendChild(item);
  });
}

async function loadWebhookSettings() {
  const form = document.getElementById("webhook-form");
  if (!form) return;
  const disabledBox = document.getElementById("webhook-disabled");
  const deleteButton = document.getElementById("webhook-delete");
  const testButton = document.getElementById("webhook-test");
  ensureWebhookEventsRendered();

  const features = window.whagoUser?.plan_features || {};
  if (!features.webhooks) {
    disabledBox?.classList.remove("hidden");
    form.classList.add("hidden");
    deleteButton?.classList.add("hidden");
    testButton?.setAttribute("disabled", "disabled");
    renderWebhookLogs([]);
    return;
  }

  disabledBox?.classList.add("hidden");
  form.classList.remove("hidden");
  testButton?.removeAttribute("disabled");

  try {
    const [subscriptionResp, logsResp] = await Promise.all([
      apiFetch("/webhooks"),
      apiFetch("/webhooks/logs"),
    ]);
    if (!subscriptionResp?.ok) {
      setWebhookFeedback("Não foi possível carregar o webhook configurado.", "error");
      return;
    }
    const subscriptions = await subscriptionResp.json();
    webhookState.subscription = subscriptions[0] ?? null;
    if (webhookState.subscription) {
      document.getElementById("webhook-url").value = webhookState.subscription.url;
      document.getElementById("webhook-secret").value = webhookState.subscription.secret ?? "";
      document.getElementById("webhook-active").checked = webhookState.subscription.is_active;
      setSelectedWebhookEvents(webhookState.subscription.events || []);
      deleteButton?.classList.remove("hidden");
    } else {
      document.getElementById("webhook-url").value = "";
      document.getElementById("webhook-secret").value = "";
      document.getElementById("webhook-active").checked = true;
      setSelectedWebhookEvents([]);
      deleteButton?.classList.add("hidden");
    }
    if (logsResp?.ok) {
      webhookState.logs = await logsResp.json();
      renderWebhookLogs(webhookState.logs);
    }
    setWebhookFeedback("Configurações carregadas.", "success");
  } catch (error) {
    setWebhookFeedback("Erro ao carregar webhooks.", "error");
    console.error(error); // eslint-disable-line no-console
  }
}

function bindWebhookForm() {
  const form = document.getElementById("webhook-form");
  if (!form || form.dataset.bound === "true") return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setWebhookFeedback("Salvando configuração...");
    const payload = {
      url: document.getElementById("webhook-url").value,
      secret: document.getElementById("webhook-secret").value || null,
      events: getSelectedWebhookEvents(),
      is_active: document.getElementById("webhook-active").checked,
    };
    const response = await apiFetch("/webhooks", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (response?.ok) {
      setWebhookFeedback("Webhook salvo com sucesso.", "success");
      await loadWebhookSettings();
    } else {
      setWebhookFeedback("Não foi possível salvar o webhook.", "error");
    }
  });

  const testButton = document.getElementById("webhook-test");
  if (testButton) {
    testButton.addEventListener("click", async () => {
      if (!webhookState.subscription) {
        setWebhookFeedback("Configure um webhook antes de enviar testes.", "error");
        return;
      }
      setWebhookFeedback("Disparando evento de teste...");
      const response = await apiFetch("/webhooks/test", {
        method: "POST",
        body: JSON.stringify({
          subscription_id: webhookState.subscription.id,
          event: "campaign.started",
          payload: { origin: "settings.test" },
        }),
      });
      if (response?.ok) {
        setWebhookFeedback("Evento de teste enviado.", "success");
        await loadWebhookSettings();
      } else {
        setWebhookFeedback("Falha ao enviar evento de teste.", "error");
      }
    });
  }

  const deleteButton = document.getElementById("webhook-delete");
  if (deleteButton) {
    deleteButton.addEventListener("click", async () => {
      if (!webhookState.subscription) {
        setWebhookFeedback("Nenhum webhook configurado.", "error");
        return;
      }
      setWebhookFeedback("Removendo webhook...");
      const response = await apiFetch(`/webhooks/${webhookState.subscription.id}`, {
        method: "DELETE",
      });
      if (response?.ok) {
        webhookState.subscription = null;
        setWebhookFeedback("Webhook removido.", "success");
        await loadWebhookSettings();
      } else {
        setWebhookFeedback("Erro ao remover webhook.", "error");
      }
    });
  }

  form.dataset.bound = "true";
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
      const documentValue = document.getElementById("reg-document").value.trim();
      const companyValue = document.getElementById("reg-company").value.trim();
      
      const payload = {
        name: document.getElementById("reg-name").value,
        email: document.getElementById("reg-email").value,
        phone: document.getElementById("reg-phone").value,
        password: document.getElementById("reg-password").value,
        company_name: companyValue || null,
        document: documentValue || null,
        plan_slug: document.getElementById("reg-plan").value,
      };
      const response = await apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (response?.ok) {
        const data = await response.json();
        setTokens(data.tokens);
        
        // Check if there's a pending subscription from home page
        const pendingSubscription = sessionStorage.getItem('pending_subscription');
        if (pendingSubscription) {
          try {
            const subscriptionData = JSON.parse(pendingSubscription);
            feedback.innerText = "Conta criada! Redirecionando para pagamento...";
            
            // Store subscription intent for after login
            sessionStorage.setItem('subscription_intent', JSON.stringify({
              plan_id: parseInt(subscriptionData.plan_id),
              payment_method: subscriptionData.payment_method
            }));
            sessionStorage.removeItem('pending_subscription');
            
            // Redirect to billing page to complete payment
            window.location.href = "/billing?action=subscribe";
            return;
          } catch (error) {
            console.error("Erro ao processar assinatura pendente:", error);
            sessionStorage.removeItem('pending_subscription');
          }
        }
        
        window.location.href = "/dashboard";
      } else {
        // Try to get detailed error message
        try {
          const errorData = await response.json();
          if (errorData.detail && Array.isArray(errorData.detail)) {
            // Pydantic validation errors
            const errors = errorData.detail.map(err => {
              const field = err.loc[err.loc.length - 1];
              const fieldNames = {
                'phone': 'Telefone',
                'document': 'CPF/CNPJ',
                'password': 'Senha',
                'email': 'Email',
                'name': 'Nome'
              };
              const friendlyField = fieldNames[field] || field;
              return `${friendlyField}: ${err.msg.replace('Value error, ', '')}`;
            });
            feedback.innerText = errors.join(' | ');
          } else if (typeof errorData.detail === 'string') {
            feedback.innerText = errorData.detail;
          } else {
            feedback.innerText = "Não foi possível criar a conta. Verifique os dados.";
          }
        } catch (e) {
          feedback.innerText = "Não foi possível criar a conta. Verifique os dados.";
        }
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
    const profile = await loadProfile();
    bindNotificationDropdown();
    await refreshNotificationsPreview();
    if (!notificationsState.intervalId) {
      notificationsState.intervalId = setInterval(refreshNotificationsPreview, 60000);
    }

    if (currentPage === "dashboard") {
      await loadDashboard();
      await loadProxyUsage();
    }
    if (currentPage === "chips") {
      await initChipsPage();
    }
    if (currentPage === "campaigns") {
      await initCampaignsPage();
    }
    if (currentPage === "billing") {
      await loadBilling();
      bindBillingForms();
    }
    if (currentPage === "settings") {
      bindProfileForm();
      bindWebhookForm();
      bindApiKeysSection(profile);
      if (profile?.plan_features?.webhooks) {
        await loadWebhookSettings();
      } else {
        document.getElementById("webhook-disabled")?.classList.remove("hidden");
        document.getElementById("webhook-form")?.classList.add("hidden");
        renderWebhookLogs([]);
      }
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

  globalThis.__WHAGO_READY = true;
});

async function handleChipHeatUp(button) {
  const chipId = button?.dataset?.chipId;
  if (!chipId) return;
  button.setAttribute("disabled", "true");
  setChipFeedback("Configurando plano de aquecimento...", "info");
  const response = await apiFetch(`/chips/${chipId}/heat-up`, { method: "POST" });
  if (!response?.ok) {
    let detail = "Não foi possível iniciar o aquecimento do chip.";
    try {
      const error = await response.json();
      if (typeof error?.detail === "string") {
        detail = error.detail;
      }
    } catch (err) {
      // Ignora erro ao ler resposta
    }
    setChipFeedback(detail, "error");
    button.removeAttribute("disabled");
    return;
  }

  const payload = await response.json();
  renderHeatUpPlan(payload);
  setChipFeedback(payload.message ?? "Plano de aquecimento iniciado.", "success");
  await loadChips({ silent: true });
  button.removeAttribute("disabled");
}

async function handleChipDisconnect(chipId) {
  setChipFeedback("Desconectando chip...", "info");
  const response = await apiFetch(`/chips/${chipId}/disconnect`, { method: "POST" });
  if (!response?.ok) {
    let detail = "Não foi possível desconectar o chip.";
    try {
      const error = await response.json();
      if (typeof error?.detail === "string") {
        detail = error.detail;
      }
    } catch (err) {
      // Ignora erro ao ler resposta
    }
    setChipFeedback(detail, "error");
    return;
  }
  setChipFeedback("Chip desconectado com sucesso.", "success");
  await loadChips({ silent: true });
}

async function handleChipDelete(chipId) {
  console.log('[handleChipDelete] Deletando chip:', chipId);
  setChipFeedback("Deletando chip...", "info");
  
  try {
    const response = await apiFetch(`/chips/${chipId}`, { method: "DELETE" });
    console.log('[handleChipDelete] Response:', response?.status);
    
    if (!response?.ok) {
      let detail = "Não foi possível deletar o chip.";
      try {
        const error = await response.json();
        if (typeof error?.detail === "string") {
          detail = error.detail;
        }
      } catch (err) {
        console.error('[handleChipDelete] Erro ao ler resposta:', err);
      }
      setChipFeedback(detail, "error");
      return;
    }
    
    setChipFeedback("Chip deletado com sucesso.", "success");
    await loadChips({ silent: true });
  } catch (err) {
    console.error('[handleChipDelete] Erro ao deletar:', err);
    setChipFeedback("Erro ao deletar chip: " + err.message, "error");
  }
}

function renderHeatUpPlan(payload) {
  const container = document.getElementById("chip-events");
  if (!container) return;
  container.innerHTML = "";

  const stages = payload?.stages ?? [];
  if (!stages.length) {
    const card = document.createElement("article");
    card.className = "card";
    card.innerHTML = '<p class="text-sm text-slate-500">Nenhum plano de aquecimento disponível no momento.</p>';
    container.appendChild(card);
    return;
  }

  const totalHours = payload.recommended_total_hours ?? stages.reduce((acc, stage) => acc + (stage.duration_hours ?? 0), 0);
  const card = document.createElement("article");
  card.className = "card space-y-4";
  card.innerHTML = `
    <div class="card__header">
      <h3 class="card__title">Plano de aquecimento</h3>
      <p class="card__subtitle">${totalHours}h totais recomendados para completar todas as fases.</p>
    </div>
  `;

  const list = document.createElement("ol");
  list.className = "space-y-3 text-sm text-slate-600";
  stages.forEach((stage) => {
    const item = document.createElement("li");
    item.dataset.test = "chip-heatup-stage";
    item.innerHTML = `
      <div class="font-medium text-slate-700">Fase ${stage.stage}</div>
      <p>${stage.messages_per_hour} mensagens por hora · ${stage.duration_hours}h</p>
      <p class="text-xs text-slate-500">${stage.description}</p>
    `;
    list.appendChild(item);
  });

  card.appendChild(list);
  container.appendChild(card);
}

function bindCampaignWizardElements() {
  if (campaignState.wizard.element) {
    return;
  }
  const wizard = document.getElementById("campaign-wizard");
  const backdrop = document.getElementById("campaign-wizard-backdrop");
  if (!wizard || !backdrop) return;

  campaignState.wizard.element = wizard;
  campaignState.wizard.backdrop = backdrop;
  campaignState.wizard.steps = Array.from(document.querySelectorAll("#campaign-steps .wizard__step"));
  campaignState.wizard.panels = Array.from(document.querySelectorAll("#campaign-wizard .wizard__panel"));

  document.getElementById("campaign-wizard-close")?.addEventListener("click", closeCampaignWizard);
  backdrop.addEventListener("click", closeCampaignWizard);
  document.getElementById("campaign-basic-form")?.addEventListener("submit", handleCampaignBasicSubmit);
  document.getElementById("campaign-chips-form")?.addEventListener("submit", handleCampaignChipsSubmit);
  document.getElementById("campaign-contacts-form")?.addEventListener("submit", handleCampaignContactsSubmit);
  document.getElementById("campaign-start-button")?.addEventListener("click", handleCampaignStart);
  document.getElementById("campaign-basic-cancel")?.addEventListener("click", (event) => {
    event.preventDefault();
    closeCampaignWizard();
  });

  const scheduleToggle = document.getElementById("campaign-schedule-toggle");
  scheduleToggle?.addEventListener("change", (event) => {
    const fields = document.getElementById("campaign-schedule-fields");
    if (!fields) return;
    fields.classList.toggle("hidden", !event.target.checked);
  });

  wizard.addEventListener("click", (event) => {
    const backButton = event.target.closest("[data-step-back]");
    if (backButton) {
      const target = Number(backButton.dataset.stepBack);
      goToCampaignStep(target);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && wizard.classList.contains("hidden") === false) {
      closeCampaignWizard();
    }
  });

  const variableContainer = document.getElementById("campaign-variables");
  variableContainer?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-variable]");
    if (!button) return;
    const variable = button.dataset.variable;
    if (!variable) return;
    const textarea = document.getElementById("campaign-template");
    insertVariableAtCursor(textarea, `{{${variable}}}`);
  });

  const mediaInput = document.getElementById("campaign-media");
  mediaInput?.addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!campaignState.campaignId) {
      campaignState.pendingMediaFile = file;
      setCampaignMediaFeedback("Arquivo pronto para envio. Salve as informações básicas para anexar.", "info");
      return;
    }
    await uploadCampaignMedia(file);
    event.target.value = "";
  });
}

function resetCampaignWizard() {
  campaignState.campaignId = null;
  campaignState.currentStep = 1;
  campaignState.contactsSummary = null;
  campaignState.createdCampaign = null;
  campaignState.selectedChips.clear();
  campaignState.variables = [];
  campaignState.media = [];
  campaignState.pendingMediaFile = null;

  document.getElementById("campaign-basic-form")?.reset();
  document.getElementById("campaign-chips-form")?.reset();
  document.getElementById("campaign-contacts-form")?.reset();
  document.getElementById("campaign-contacts-summary")?.classList.add("hidden");
  document.getElementById("campaign-variables-summary")?.classList.add("hidden");
  document.getElementById("campaign-schedule-fields")?.classList.add("hidden");
  document.getElementById("campaign-review")?.replaceChildren();
  document.getElementById("campaign-wizard-subtitle").textContent = "Preencha as etapas abaixo para concluir sua campanha.";
  renderCampaignVariables();
  renderCampaignVariablesSummary();
  renderCampaignMediaList();
  setCampaignMediaFeedback("Formatos aceitos: imagens, PDF, áudio (MP3/OGG) e vídeo MP4 até 10MB.", "info");
  campaignState.wizard.panels.forEach((panel) => panel.classList.add("hidden"));
  campaignState.wizard.steps.forEach((step) => step.classList.remove("wizard__step--active"));
  goToCampaignStep(1, true);
}

function updateCampaignSteps(step) {
  campaignState.wizard.steps.forEach((item) => {
    const itemStep = Number(item.dataset.step);
    if (Number.isNaN(itemStep)) return;
    item.classList.toggle("wizard__step--active", itemStep === step);
  });
}

function goToCampaignStep(step, initial = false) {
  campaignState.currentStep = step;
  campaignState.wizard.panels.forEach((panel) => {
    const panelStep = Number(panel.id.split("-").pop());
    panel.classList.toggle("hidden", panelStep !== step);
  });
  updateCampaignSteps(step);
  if (!initial) {
    const titles = {
      1: "Informe os detalhes principais da campanha",
      2: "Selecione quais chips participarão da rotação",
      3: "Importe a base de contatos da campanha",
      4: "Revise e dispare sua campanha",
    };
    const subtitle = document.getElementById("campaign-wizard-subtitle");
    if (subtitle && titles[step]) {
      subtitle.textContent = titles[step];
    }
  }
}

function openCampaignWizard() {
  bindCampaignWizardElements();
  resetCampaignWizard();
  campaignState.wizard.element?.classList.remove("hidden");
  campaignState.wizard.backdrop?.classList.remove("hidden");
}

function closeCampaignWizard() {
  campaignState.wizard.element?.classList.add("hidden");
  campaignState.wizard.backdrop?.classList.add("hidden");
  resetCampaignWizard();
}

async function handleCampaignBasicSubmit(event) {
  event.preventDefault();
  if (campaignState.campaignId) {
    goToCampaignStep(2);
    await loadCampaignWizardChips();
    return;
  }
  const nameInput = document.getElementById("campaign-name");
  const templateInput = document.getElementById("campaign-template");
  if (!nameInput?.value || !templateInput?.value) {
    setCampaignFeedback("Informe nome e mensagem principal para continuar.", "warning");
    return;
  }
  const payload = {
    name: nameInput.value.trim(),
    description: document.getElementById("campaign-description")?.value?.trim() || null,
    message_template: templateInput.value,
    message_template_b: document.getElementById("campaign-template-b")?.value?.trim() || null,
    settings: {
      chip_ids: [],
      interval_seconds: 10,
      randomize_interval: false,
    },
  };
  const scheduleToggle = document.getElementById("campaign-schedule-toggle");
  const scheduleDatetime = document.getElementById("campaign-schedule-datetime");
  if (scheduleToggle?.checked) {
    if (!scheduleDatetime?.value) {
      setCampaignFeedback("Informe a data e hora para agendamento ou desmarque o agendamento.", "warning");
      return;
    }
    const date = new Date(scheduleDatetime.value);
    if (Number.isNaN(date.getTime())) {
      setCampaignFeedback("Data de agendamento inválida.", "error");
      return;
    }
    payload.scheduled_for = date.toISOString();
  }

  const mediaInput = document.getElementById("campaign-media");
  const pendingFile = mediaInput?.files?.[0] ?? null;
  if (pendingFile) {
    campaignState.pendingMediaFile = pendingFile;
  }

  const response = await apiFetch("/campaigns", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!response?.ok) {
    const message = await response.text();
    setCampaignFeedback(message || "Não foi possível criar a campanha.", "error");
    return;
  }
  const data = await response.json();
  campaignState.campaignId = data.id;
  campaignState.createdCampaign = data;
  campaignState.media = Array.isArray(data.media) ? data.media : [];
  setCampaignFeedback("Campanha criada como rascunho. Continue para selecionar chips.", "success");
  renderCampaignMediaList();
  await maybeUploadPendingMedia();
  if (mediaInput) {
    mediaInput.value = "";
  }
  await loadCampaignWizardChips();
  goToCampaignStep(2);
}

async function loadCampaignWizardChips() {
  const response = await apiFetch("/chips");
  if (!response?.ok) {
    setCampaignFeedback("Não foi possível carregar a lista de chips.", "error");
    return;
  }
  const chips = await response.json();
  campaignState.chipCache = chips;
  renderCampaignChips(chips);
}

function renderCampaignChips(chips) {
  const container = document.getElementById("campaign-chips-list");
  if (!container) return;
  container.innerHTML = "";
  if (!chips.length) {
    container.innerHTML = '<p class="text-sm text-slate-500">Nenhum chip disponível. Cadastre chips antes de prosseguir.</p>';
    return;
  }
  chips.forEach((chip) => {
    const card = document.createElement("label");
    const disabled = !["connected", "maturing", "waiting_qr"].includes((chip.status || "").toLowerCase());
    card.className = `card space-y-2 ${disabled ? "opacity-60" : ""}`;
    card.innerHTML = `
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="font-medium text-slate-700">${chip.alias}</p>
          <p class="text-xs text-slate-500">Status: ${formatChipStatus(chip.status)}</p>
        </div>
        <input type="checkbox" value="${chip.id}" ${disabled ? "disabled" : ""} class="rounded border-slate-300" data-test="campaign-chip" />
      </div>
      <p class="text-xs text-slate-500">Saúde: ${chip.health_score ?? "--"}</p>
    `;
    container.appendChild(card);
  });
}

async function handleCampaignChipsSubmit(event) {
  event.preventDefault();
  if (!campaignState.campaignId) {
    setCampaignFeedback("Crie a campanha antes de selecionar os chips.", "warning");
    return;
  }
  const checkboxes = Array.from(document.querySelectorAll("#campaign-chips-list input[type='checkbox']:checked"));
  if (!checkboxes.length) {
    setCampaignFeedback("Selecione ao menos um chip para continuar.", "warning");
    return;
  }
  const chipIds = checkboxes.map((input) => input.value);
  campaignState.selectedChips = new Set(chipIds);
  const intervalSeconds = Number(document.getElementById("campaign-interval")?.value || "10");
  const randomize = Boolean(document.getElementById("campaign-randomize")?.checked);
  const response = await apiFetch(`/campaigns/${campaignState.campaignId}`, {
    method: "PUT",
    body: JSON.stringify({
      settings: {
        chip_ids: chipIds,
        interval_seconds: Number.isFinite(intervalSeconds) && intervalSeconds > 0 ? intervalSeconds : 10,
        randomize_interval: randomize,
      },
    }),
  });
  if (!response?.ok) {
    const message = await response.text();
    setCampaignFeedback(message || "Não foi possível salvar as configurações de chips.", "error");
    return;
  }
  const data = await response.json();
  campaignState.createdCampaign = data;
  campaignState.media = Array.isArray(data.media) ? data.media : campaignState.media;
  setCampaignFeedback("Chips configurados com sucesso. Importe os contatos.", "success");
  renderCampaignMediaList();
  goToCampaignStep(3);
}

async function handleCampaignContactsSubmit(event) {
  event.preventDefault();
  if (!campaignState.campaignId) {
    setCampaignFeedback("Crie a campanha antes de importar contatos.", "warning");
    return;
  }
  const fileInput = document.getElementById("campaign-contacts-file");
  const file = fileInput?.files?.[0];
  if (!file) {
    setCampaignFeedback("Selecione um arquivo CSV para importar.", "warning");
    return;
  }
  const token = getAccessToken();
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE}/campaigns/${campaignState.campaignId}/contacts/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!response.ok) {
    const message = await response.text();
    setCampaignFeedback(message || "Falha ao importar contatos.", "error");
    return;
  }
  const summary = await response.json();
  campaignState.contactsSummary = summary;
  campaignState.variables = Array.isArray(summary.variables) ? summary.variables : [];
  renderCampaignVariables();
  renderCampaignVariablesSummary();
  const summaryElement = document.getElementById("campaign-contacts-summary");
  if (summaryElement) {
    summaryElement.classList.remove("hidden");
    summaryElement.innerHTML = `
      <p><strong>${summary.valid_contacts}</strong> contatos válidos (Total processado: ${summary.total_processed}).</p>
      <p>Inválidos: ${summary.invalid_contacts} · Duplicados: ${summary.duplicated}</p>
    `;
  }
  setCampaignFeedback("Contatos importados! Revise e finalize o disparo.", "success");
  await populateCampaignReview();
  goToCampaignStep(4);
}

async function populateCampaignReview() {
  if (!campaignState.campaignId) return;
  const response = await apiFetch(`/campaigns/${campaignState.campaignId}`);
  if (!response?.ok) return;
  const data = await response.json();
  campaignState.createdCampaign = data;
  campaignState.media = Array.isArray(data.media) ? data.media : campaignState.media;
  renderCampaignMediaList();
  renderCampaignReview();
}

function renderCampaignReview() {
  const container = document.getElementById("campaign-review");
  if (!container || !campaignState.createdCampaign) return;
  const campaign = campaignState.createdCampaign;
  const chipsSelected = Array.from(campaignState.selectedChips);
  const chipAliasMap = new Map(campaignState.chipCache.map((chip) => [chip.id, chip.alias]));
  const chipList = chipsSelected
    .map((id) => `<li>${chipAliasMap.get(id) || id}</li>`)
    .join("");
  const summary = campaignState.contactsSummary;
  const variablesSection = campaignState.variables.length
    ? `<div class="space-y-2">
        <h4 class="font-medium text-slate-700">Variáveis detectadas</h4>
        <p class="text-sm text-slate-600">${campaignState.variables.map((variable) => `{{${variable}}}`).join(", ")}</p>
      </div>`
    : "";
  const mediaSection = campaignState.media.length
    ? `<div class="space-y-2">
        <h4 class="font-medium text-slate-700">Arquivos anexados (${campaignState.media.length})</h4>
        <ul class="list-disc space-y-1 pl-5 text-sm text-slate-600">
          ${campaignState.media
            .map((item) => `<li>${item.original_name} · ${formatBytes(item.size_bytes)}</li>`)
            .join("")}
        </ul>
      </div>`
    : `<div class="space-y-2">
        <h4 class="font-medium text-slate-700">Arquivos anexados</h4>
        <p class="text-sm text-slate-600">Nenhum anexo enviado.</p>
      </div>`;
  container.innerHTML = `
    <div class="space-y-2">
      <h4 class="font-medium text-slate-700">Informações principais</h4>
      <p class="text-sm text-slate-600"><strong>Nome:</strong> ${campaign.name}</p>
      <p class="text-sm text-slate-600"><strong>Status:</strong> ${formatCampaignStatus(campaign.status)}</p>
      <p class="text-sm text-slate-600"><strong>Agendamento:</strong> ${campaign.scheduled_for ? formatDate(campaign.scheduled_for) : "Envio imediato"}</p>
    </div>
    <div class="space-y-2">
      <h4 class="font-medium text-slate-700">Mensagem principal</h4>
      <pre class="rounded-xl bg-slate-900/90 p-4 text-xs text-slate-100">${campaign.message_template}</pre>
      ${campaign.message_template_b ? `<p class="text-xs text-slate-500">Mensagem B configurada para testes A/B.</p>` : ""}
    </div>
    ${variablesSection}
    <div class="space-y-2">
      <h4 class="font-medium text-slate-700">Chips selecionados (${chipsSelected.length})</h4>
      <ul class="list-disc space-y-1 pl-5 text-sm text-slate-600">${chipList || "<li>Nenhum chip selecionado.</li>"}</ul>
    </div>
    <div class="space-y-2">
      <h4 class="font-medium text-slate-700">Contatos importados</h4>
      ${summary
        ? `<p class="text-sm text-slate-600">${summary.valid_contacts} contatos válidos · ${summary.invalid_contacts} inválidos · ${summary.duplicated} duplicados.</p>`
        : '<p class="text-sm text-slate-600">Importe os contatos antes de iniciar.</p>'}
    </div>
    ${mediaSection}
  `;
}

async function handleCampaignStart() {
  if (!campaignState.campaignId) return;
  const response = await apiFetch(`/campaigns/${campaignState.campaignId}/start`, {
    method: "POST",
  });
  if (!response?.ok) {
    const message = await response.text();
    setCampaignFeedback(message || "Não foi possível iniciar a campanha.", "error");
    return;
  }
  const data = await response.json();
  setCampaignFeedback(`Campanha iniciada com status ${formatCampaignStatus(data.status)}.`, "success");
  closeCampaignWizard();
  await loadCampaigns({ silent: true });
}

function bindCampaignsPage() {
  document.querySelector("[data-test='campaign-wizard-open']")?.addEventListener("click", () => {
    openCampaignWizard();
  });
  document.getElementById("campaigns-refresh")?.addEventListener("click", () => {
    void loadCampaigns({ toast: "Lista de campanhas atualizada." });
  });
  const table = document.querySelector("#campaign-table tbody");
  table?.addEventListener("click", (event) => {
    const actionButton = event.target.closest("[data-campaign-action]");
    if (!actionButton) return;
    const campaignId = actionButton.dataset.campaignId;
    const action = actionButton.dataset.campaignAction;
    void handleCampaignRowAction(campaignId, action);
  });
}

function buildCampaignActionButtons(campaign) {
  const status = (campaign.status || "").toLowerCase();
  const buttons = [];
  if (status === "draft" || status === "scheduled") {
    buttons.push(`<button data-campaign-action="start" data-campaign-id="${campaign.id}" class="btn-primary btn-xs" type="button">Iniciar</button>`);
  }
  if (status === "running") {
    buttons.push(`<button data-campaign-action="pause" data-campaign-id="${campaign.id}" class="btn-secondary btn-xs" type="button">Pausar</button>`);
    buttons.push(`<button data-campaign-action="cancel" data-campaign-id="${campaign.id}" class="btn-secondary btn-xs" type="button">Cancelar</button>`);
  }
  if (status === "paused") {
    buttons.push(`<button data-campaign-action="resume" data-campaign-id="${campaign.id}" class="btn-primary btn-xs" type="button">Retomar</button>`);
    buttons.push(`<button data-campaign-action="cancel" data-campaign-id="${campaign.id}" class="btn-secondary btn-xs" type="button">Cancelar</button>`);
  }
  return buttons.join(" ");
}

async function handleCampaignRowAction(campaignId, action) {
  if (!campaignId || !action) return;
  let endpoint;
  if (action === "start" || action === "resume") {
    endpoint = `/campaigns/${campaignId}/start`;
  } else if (action === "pause") {
    endpoint = `/campaigns/${campaignId}/pause`;
  } else if (action === "cancel") {
    endpoint = `/campaigns/${campaignId}/cancel`;
  } else {
    return;
  }
  const response = await apiFetch(endpoint, { method: "POST" });
  if (!response?.ok) {
    const message = await response.text();
    setCampaignFeedback(message || "Não foi possível executar a ação na campanha.", "error");
    return;
  }
  const data = await response.json();
  setCampaignFeedback(`Campanha atualizada: ${formatCampaignStatus(data.status)}.`, "success");
  await loadCampaigns({ silent: true });
}

function renderCampaignInsights(campaigns) {
  const container = document.getElementById("campaign-insights-body");
  const emptyState = document.getElementById("campaign-insights-empty");
  if (!container) return;
  container.innerHTML = "";
  if (!campaigns.length) {
    emptyState?.classList.remove("hidden");
    return;
  }
  emptyState?.classList.add("hidden");
  const total = campaigns.length;
  const running = campaigns.filter((c) => c.status === "running").length;
  const scheduled = campaigns.filter((c) => c.status === "scheduled").length;
  const drafts = campaigns.filter((c) => c.status === "draft").length;
  const completed = campaigns.filter((c) => c.status === "completed").length;
  container.innerHTML = `
    <div>
      <dt class="card__label">Campanhas totais</dt>
      <dd class="card__value">${total}</dd>
    </div>
    <div>
      <dt class="card__label">Em andamento</dt>
      <dd class="card__value">${running}</dd>
    </div>
    <div>
      <dt class="card__label">Agendadas</dt>
      <dd class="card__value">${scheduled}</dd>
    </div>
    <div>
      <dt class="card__label">Rascunhos</dt>
      <dd class="card__value">${drafts}</dd>
    </div>
    <div>
      <dt class="card__label">Concluídas</dt>
      <dd class="card__value">${completed}</dd>
    </div>
  `;
}

function renderCampaignMessages(messages) {
  const tableBody = document.querySelector("#campaign-messages-table tbody");
  const empty = document.getElementById("campaign-messages-empty");
  if (!tableBody) return;
  tableBody.innerHTML = "";
  if (!messages || !messages.length) {
    empty?.classList.remove("hidden");
    return;
  }
  empty?.classList.add("hidden");
  messages.forEach((message) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td class="py-2 font-medium text-slate-700">${message.phone_number}</td>
      <td class="py-2 text-slate-600">${message.chip_alias ?? "--"}</td>
      <td class="py-2"><span class="status status-${(message.status || "").toLowerCase()}">${message.status}</span></td>
      <td class="py-2 text-slate-500">${formatDate(message.sent_at)}</td>
    `;
    tableBody.appendChild(row);
  });
}

async function loadCampaignMessagesPreview(campaignId) {
  const response = await apiFetch(`/campaigns/${campaignId}/messages?limit=8`);
  if (!response?.ok) {
    renderCampaignMessages([]);
    return;
  }
  const data = await response.json();
  renderCampaignMessages(data);
}

async function loadCampaigns(options = {}) {
  const response = await apiFetch("/campaigns");
  if (!response?.ok) {
    setCampaignFeedback("Não foi possível carregar campanhas.", "error");
    return;
  }
  const campaigns = await response.json();
  const table = document.querySelector("#campaign-table tbody");
  if (table) {
    table.innerHTML = "";
    campaigns.forEach((campaign) => {
      const chipsSelected = Array.isArray(campaign.settings?.chip_ids) ? campaign.settings.chip_ids.length : 0;
      const total = campaign.total_contacts ?? 0;
      const sent = campaign.sent_count ?? 0;
      const progress = total > 0 ? `${sent}/${total}` : "--";
      const row = document.createElement("tr");
      row.dataset.campaignId = campaign.id;
      row.innerHTML = `
        <td class="py-2 font-medium text-slate-800">${campaign.name}</td>
        <td class="py-2"><span class="${getCampaignStatusClass(campaign.status)}">${formatCampaignStatus(campaign.status)}</span></td>
        <td class="py-2">${progress}</td>
        <td class="py-2">${chipsSelected} chips</td>
        <td class="py-2">${formatDate(campaign.created_at)}</td>
        <td class="py-2 text-right">${buildCampaignActionButtons(campaign)}</td>
      `;
      table.appendChild(row);
    });
  }
  renderCampaignInsights(campaigns);
  const previewTarget = campaigns.find((c) => c.status === "running") || campaigns[0];
  if (previewTarget) {
    await loadCampaignMessagesPreview(previewTarget.id);
  } else {
    renderCampaignMessages([]);
  }
  if (options.toast) {
    setCampaignFeedback(options.toast, "success");
  } else if (!options.silent) {
    setCampaignFeedback("Campanhas carregadas com sucesso.", "success");
  }
}

async function initCampaignsPage() {
  bindCampaignWizardElements();
  bindCampaignsPage();
  await loadCampaigns();
}

const apiKeyState = {
  items: [],
  bound: false,
};

function setApiKeyFeedback(message, variant = "info") {
  const feedback = document.getElementById("api-key-feedback");
  if (!feedback) return;
  feedback.classList.remove("text-slate-500", "text-red-600", "text-emerald-600", "text-amber-600");
  if (variant === "error") {
    feedback.classList.add("text-red-600");
  } else if (variant === "success") {
    feedback.classList.add("text-emerald-600");
  } else if (variant === "warning") {
    feedback.classList.add("text-amber-600");
  } else {
    feedback.classList.add("text-slate-500");
  }
  feedback.innerText = message;
}

function renderApiKeys(keys) {
  const tbody = document.getElementById("api-key-list");
  if (!tbody) return;
  tbody.innerHTML = "";
  if (!keys.length) {
    const emptyRow = document.createElement("tr");
    emptyRow.innerHTML = '<td class="py-3 text-center text-slate-500" colspan="6">Nenhuma chave cadastrada.</td>';
    tbody.appendChild(emptyRow);
    return;
  }
  keys.forEach((key) => {
    const tr = document.createElement("tr");
    const statusLabel = key.revoked_at ? "Revogada" : "Ativa";
    const statusClass = key.revoked_at ? "text-red-600" : "text-emerald-600";
    tr.innerHTML = `
      <td class="py-2 font-medium text-slate-800">${key.name}</td>
      <td class="py-2 text-slate-600">${key.prefix}</td>
      <td class="py-2 text-slate-600">${formatDate(key.created_at)}</td>
      <td class="py-2 text-slate-600">${key.last_used_at ? formatDate(key.last_used_at) : "Nunca"}</td>
      <td class="py-2 ${statusClass}">${statusLabel}</td>
      <td class="py-2 text-right">
        ${key.revoked_at ? "" : `<button type="button" class="btn-secondary btn-xs" data-api-key-revoke="${key.id}">Revogar</button>`}
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function openApiKeyModal(value) {
  const modal = document.getElementById("api-key-modal");
  const backdrop = document.getElementById("api-key-modal-backdrop");
  if (!modal) return;
  const container = document.getElementById("api-key-modal-value");
  const code = container?.querySelector("code");
  if (container && code) {
    container.dataset.keyValue = value;
    code.innerText = value;
  }
  modal.classList.remove("hidden");
  backdrop?.classList.remove("hidden");
  document.body.classList.add("overflow-hidden");
}

function closeApiKeyModal() {
  const modal = document.getElementById("api-key-modal");
  const backdrop = document.getElementById("api-key-modal-backdrop");
  if (!modal) return;
  modal.classList.add("hidden");
  backdrop?.classList.add("hidden");
  document.body.classList.remove("overflow-hidden");
}

function bindApiKeyModal() {
  const modal = document.getElementById("api-key-modal");
  if (!modal || modal.dataset.bound === "true") return;
  modal.dataset.bound = "true";
  const backdrop = document.getElementById("api-key-modal-backdrop");
  document.getElementById("api-key-modal-close")?.addEventListener("click", closeApiKeyModal);
  backdrop?.addEventListener("click", closeApiKeyModal);
  document.getElementById("api-key-copy")?.addEventListener("click", async () => {
    const container = document.getElementById("api-key-modal-value");
    if (!container) return;
    const key = container.dataset.keyValue;
    if (!key) return;
    try {
      await navigator.clipboard.writeText(key);
      setApiKeyFeedback("Chave copiada para a área de transferência.", "success");
    } catch (error) {
      console.error(error);
      setApiKeyFeedback("Não foi possível copiar automaticamente. Copie manualmente.", "warning");
    }
  });
}

async function refreshApiKeys() {
  const response = await apiFetch("/api-keys");
  if (!response) return;
  if (response.status === 403) {
    setApiKeyFeedback("Seu plano não possui acesso à API externa.", "error");
    return;
  }
  if (!response.ok) {
    const message = (await safeReadText(response)) ?? "Não foi possível carregar as chaves de API.";
    setApiKeyFeedback(message, "error");
    return;
  }
  apiKeyState.items = await response.json();
  renderApiKeys(apiKeyState.items);
  if (apiKeyState.items.length) {
    setApiKeyFeedback(`Você possui ${apiKeyState.items.length} chave(s) ativa(s).`, "success");
  } else {
    setApiKeyFeedback("Sem chaves cadastradas. Gere uma nova para iniciar uma integração.", "info");
  }
}

async function handleApiKeyCreate(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const input = form.querySelector("#api-key-name");
  const name = input?.value.trim();
  if (!name) {
    setApiKeyFeedback("Informe um nome para a chave.", "error");
    return;
  }
  setApiKeyFeedback("Gerando chave...");
  const response = await apiFetch("/api-keys", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  if (!response) return;
  if (response.status === 403) {
    setApiKeyFeedback("Seu plano não possui acesso à API externa.", "error");
    return;
  }
  if (!response.ok) {
    const message = (await safeReadText(response)) ?? "Não foi possível gerar a chave. Tente novamente.";
    setApiKeyFeedback(message, "error");
    return;
  }
  const data = await response.json();
  input.value = "";
  await refreshApiKeys();
  openApiKeyModal(data.key);
  setApiKeyFeedback("Nova chave criada com sucesso.", "success");
}

async function handleApiKeyRevoke(keyId) {
  setApiKeyFeedback("Revogando chave...");
  const response = await apiFetch(`/api-keys/${keyId}`, { method: "DELETE" });
  if (!response) return;
  if (!response.ok) {
    const message = (await safeReadText(response)) ?? "Não foi possível revogar a chave.";
    setApiKeyFeedback(message, "error");
    return;
  }
  await refreshApiKeys();
  setApiKeyFeedback("Chave revogada com sucesso.", "success");
}

function bindApiKeysSection(profile) {
  const manager = document.getElementById("api-key-manager");
  const upgrade = document.getElementById("api-key-upgrade");
  if (!manager || !upgrade) return;
  bindApiKeyModal();
  const hasAccess = Boolean(profile?.plan_features?.api_access);
  if (!hasAccess) {
    upgrade.classList.remove("hidden");
    manager.classList.add("hidden");
    setApiKeyFeedback("");
    return;
  }
  upgrade.classList.add("hidden");
  manager.classList.remove("hidden");
  if (!apiKeyState.bound) {
    apiKeyState.bound = true;
    const form = document.getElementById("api-key-form");
    form?.addEventListener("submit", handleApiKeyCreate);
    document.getElementById("api-key-list")?.addEventListener("click", async (event) => {
      const button = event.target.closest("[data-api-key-revoke]");
      if (!button) return;
      const keyId = button.getAttribute("data-api-key-revoke");
      button.setAttribute("disabled", "true");
      await handleApiKeyRevoke(keyId);
      button.removeAttribute("disabled");
    });
  }
  void refreshApiKeys();
}
// ========================================
// BILLING & PAYMENTS
// ========================================

async function loadSubscriptionInfo() {
  try {
    const profile = await apiFetch(`${API_BASE}/users/profile`);
    
    const planName = profile.plan?.name || "Free";
    const subscriptionStatus = profile.subscription_status || null;
    const subscriptionGateway = profile.subscription_gateway || null;
    const nextBillingDate = profile.next_billing_date || null;
    const subscriptionStartedAt = profile.subscription_started_at || null;
    
    document.getElementById("billing-current-plan").textContent = planName;
    
    // Status badge
    const statusEl = document.getElementById("billing-subscription-status");
    if (subscriptionStatus) {
      const statusMap = {
        active: { text: "Ativa", class: "bg-green-100 text-green-800" },
        paused: { text: "Pausada", class: "bg-yellow-100 text-yellow-800" },
        cancelled: { text: "Cancelada", class: "bg-red-100 text-red-800" },
        pending: { text: "Pendente", class: "bg-blue-100 text-blue-800" },
      };
      const status = statusMap[subscriptionStatus] || { text: subscriptionStatus, class: "bg-gray-100 text-gray-800" };
      statusEl.innerHTML = `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${status.class}">${status.text}</span>`;
    }
    
    // Gateway
    if (subscriptionGateway) {
      const gatewayNames = {
        mercadopago: "Mercado Pago",
        paypal: "PayPal",
        stripe: "Stripe",
      };
      document.getElementById("billing-gateway").textContent = gatewayNames[subscriptionGateway] || subscriptionGateway;
    }
    
    // Next billing
    if (nextBillingDate) {
      const date = new Date(nextBillingDate);
      document.getElementById("billing-renewal").textContent = date.toLocaleDateString("pt-BR");
    }
    
    // Started at
    if (subscriptionStartedAt) {
      const date = new Date(subscriptionStartedAt);
      document.getElementById("billing-started-at").textContent = date.toLocaleDateString("pt-BR");
      document.getElementById("subscription-dates-container").style.display = "block";
    }
    
    // Show/hide buttons
    const cancelBtn = document.getElementById("cancel-subscription-btn");
    const changeBtn = document.getElementById("change-payment-method-btn");
    
    if (subscriptionStatus === "active") {
      cancelBtn.classList.remove("hidden");
      changeBtn.classList.remove("hidden");
    } else {
      cancelBtn.classList.add("hidden");
      changeBtn.classList.add("hidden");
    }
    
  } catch (error) {
    console.error("Erro ao carregar informações de assinatura:", error);
  }
}

async function handleCancelSubscription() {
  const confirmed = confirm(
    "Tem certeza que deseja cancelar sua assinatura?\n\n" +
    "Você manterá acesso ao plano até o fim do período já pago."
  );
  
  if (!confirmed) return;
  
  const feedbackEl = document.getElementById("subscription-feedback");
  const btn = document.getElementById("cancel-subscription-btn");
  
  try {
    btn.setAttribute("disabled", "true");
    btn.textContent = "Cancelando...";
    feedbackEl.textContent = "Processando cancelamento...";
    feedbackEl.className = "mt-4 text-sm text-blue-600";
    
    await apiFetch(`${API_BASE}/payments/subscriptions`, { method: "DELETE" });
    
    feedbackEl.textContent = "Assinatura cancelada com sucesso!";
    feedbackEl.className = "mt-4 text-sm text-green-600";
    
    setTimeout(() => {
      window.location.reload();
    }, 2000);
    
  } catch (error) {
    console.error("Erro ao cancelar assinatura:", error);
    feedbackEl.textContent = "Erro ao cancelar assinatura. Tente novamente.";
    feedbackEl.className = "mt-4 text-sm text-red-600";
    btn.removeAttribute("disabled");
    btn.textContent = "Cancelar Assinatura";
  }
}

async function loadPaymentMethods() {
  try {
    const response = await fetch(`${API_BASE}/payments/methods`);
    if (!response.ok) {
      throw new Error("Erro ao carregar métodos de pagamento");
    }
    const data = await response.json();
    const methods = data.methods.filter(m => m.enabled);
    
    const select = document.getElementById("credit-payment-method");
    if (select) {
      select.innerHTML = methods.map(m => 
        `<option value="${m.id}">${m.name}</option>`
      ).join("");
    }
  } catch (error) {
    console.error("Erro ao carregar métodos de pagamento:", error);
  }
}

function updateCreditPrice() {
  const amountInput = document.getElementById("credit-amount");
  const priceEl = document.getElementById("credit-price");
  
  if (!amountInput || !priceEl) return;
  
  const amount = parseInt(amountInput.value) || 0;
  const price = (amount * 0.10).toFixed(2);
  priceEl.textContent = price;
}

async function handleCreditPurchase(event) {
  event.preventDefault();
  
  const amountInput = document.getElementById("credit-amount");
  const methodSelect = document.getElementById("credit-payment-method");
  const feedbackEl = document.getElementById("credit-purchase-feedback");
  const submitBtn = event.target.querySelector('button[type="submit"]');
  
  const amount = parseInt(amountInput.value);
  const paymentMethod = methodSelect.value;
  
  if (!amount || amount < 100) {
    feedbackEl.textContent = "Quantidade mínima: 100 créditos";
    feedbackEl.className = "text-sm text-red-600";
    return;
  }
  
  try {
    submitBtn.setAttribute("disabled", "true");
    submitBtn.textContent = "Processando...";
    feedbackEl.textContent = "Gerando pagamento...";
    feedbackEl.className = "text-sm text-blue-600";
    
    const response = await apiFetch("/payments/credits", {
      method: "POST",
      body: JSON.stringify({
        credits: amount,
        payment_method: paymentMethod,
      }),
    });
    
    if (!response?.ok) {
      throw new Error("Erro ao gerar pagamento");
    }
    
    const data = await response.json();
    
    feedbackEl.textContent = "Redirecionando para pagamento...";
    
    // Redirect to payment URL
    if (data.payment_url) {
      window.location.href = data.payment_url;
    } else {
      throw new Error("URL de pagamento não recebida");
    }
    
  } catch (error) {
    console.error("Erro ao comprar créditos:", error);
    feedbackEl.textContent = error.message || "Erro ao processar compra. Tente novamente.";
    feedbackEl.className = "text-sm text-red-600";
    submitBtn.removeAttribute("disabled");
    submitBtn.textContent = "Comprar Créditos";
  }
}

function bindBillingPage() {
  // Cancel subscription button
  const cancelBtn = document.getElementById("cancel-subscription-btn");
  if (cancelBtn) {
    cancelBtn.addEventListener("click", handleCancelSubscription);
  }
  
  // Credit purchase form
  const creditForm = document.getElementById("credit-purchase-form");
  if (creditForm) {
    creditForm.addEventListener("submit", handleCreditPurchase);
    
    const amountInput = document.getElementById("credit-amount");
    if (amountInput) {
      amountInput.addEventListener("input", updateCreditPrice);
      updateCreditPrice(); // Initial update
    }
  }
  
  // Load data
  loadSubscriptionInfo();
  loadPaymentMethods();
  
  // Check for subscription intent from registration
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('action') === 'subscribe') {
    processSubscriptionIntent();
  }
}

async function processSubscriptionIntent() {
  const subscriptionIntent = sessionStorage.getItem('subscription_intent');
  if (!subscriptionIntent) {
    return;
  }
  
  try {
    const intentData = JSON.parse(subscriptionIntent);
    
    // Show loading message
    const feedbackEl = document.getElementById("subscription-feedback");
    if (feedbackEl) {
      feedbackEl.textContent = "Gerando link de pagamento...";
      feedbackEl.className = "mt-4 text-sm text-blue-600";
    }
    
    // Create subscription (which generates payment link but doesn't activate)
    const response = await apiFetch("/payments/subscriptions", {
      method: "POST",
      body: JSON.stringify({
        plan_id: intentData.plan_id,
        payment_method: intentData.payment_method
      }),
    });
    
    if (response?.ok) {
      const data = await response.json();
      sessionStorage.removeItem('subscription_intent');
      
      // Redirect to payment gateway
      window.location.href = data.payment_url;
    } else {
      const error = await response.text();
      if (feedbackEl) {
        feedbackEl.textContent = error || "Erro ao gerar pagamento. Tente novamente.";
        feedbackEl.className = "mt-4 text-sm text-red-600";
      }
      sessionStorage.removeItem('subscription_intent');
    }
  } catch (error) {
    console.error("Erro ao processar intenção de assinatura:", error);
    sessionStorage.removeItem('subscription_intent');
  }
}

// ========================================
// PAGE INITIALIZATION
// ========================================

// Bind billing page if on billing route
if (window.location.pathname.includes("/billing")) {
  document.addEventListener("DOMContentLoaded", bindBillingPage);
}

// Cache bust: 1763061975
// Cache bust: 1763065043 - Deletar e Desconectar chips
// Cache bust: 1763065236 - Fix deletar chips + aviso aquecimento
// Cache bust: 1763075987 - Billing & Payments UI
// Cache bust: 1763076543 - Fix home page redirect
// Cache bust: 1763077234 - Auto subscription after register
// Cache bust: 1763077890 - Subscription only after payment confirmed
// Cache bust: 1763078456 - Better registration error messages
// Cache bust: 1763082962 - Mercado Pago Sandbox working 100%
// Cache bust: 1763083452 - Fix credit purchase redirect
