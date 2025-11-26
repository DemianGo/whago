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
  // Verificar se o wizard está aberto
  const wizard = document.getElementById("campaign-wizard");
  const isWizardOpen = wizard && !wizard.classList.contains("hidden");
  
  // Usar feedback do wizard se estiver aberto, senão usar o da página
  const feedbackId = isWizardOpen ? "campaign-wizard-feedback" : "campaign-feedback";
  const feedback = document.getElementById(feedbackId);
  if (!feedback) return;
  
  // Fazer scroll para o topo do wizard para mostrar a mensagem
  if (isWizardOpen) {
    const wizardContent = wizard.querySelector(".modal__content");
    if (wizardContent) {
      wizardContent.scrollTop = 0;
    }
  }
  
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

async function openConnectModal(chipId) {
  openChipModal();
  const form = document.getElementById("chip-form");
  if (form) form.classList.add("hidden");
  
  const modalTitle = document.querySelector("#chip-modal h3");
  if (modalTitle) modalTitle.textContent = "Conectar WhatsApp";
  
  await showChipQrCode(chipId);
}

async function showChipQrCode(chipId) {
  console.log('[showChipQrCode] Iniciando para chip:', chipId);
  
  // Garantir que o modal está visível
  const modal = document.getElementById("chip-modal");
  const backdrop = document.getElementById("chip-modal-backdrop");
  if (modal && modal.classList.contains("hidden")) {
      modal.classList.remove("hidden");
      backdrop.classList.remove("hidden");
  }

  // Hide form, show QR section
  const form = document.getElementById("chip-form");
  const qrSection = document.getElementById("chip-qr-section");
  const qrLoading = document.getElementById("chip-qr-loading");
  const qrImage = document.getElementById("chip-qr-image");
  const qrStatus = document.getElementById("chip-qr-status");
  const modalTitle = document.querySelector("#chip-modal h3");

  if (modalTitle) {
      modalTitle.textContent = "Conectar WhatsApp";
  }
  
  // Resetar estado visual
  if (form) form.classList.add("hidden");
  if (qrSection) qrSection.classList.remove("hidden");
  if (qrLoading) qrLoading.classList.remove("hidden");
  if (qrImage) {
      qrImage.classList.add("hidden");
      qrImage.src = ""; // Limpar imagem anterior
  }
  if (qrStatus) {
      qrStatus.textContent = "Aguardando QR Code...";
      qrStatus.className = "text-center text-sm text-slate-500 animate-pulse";
  }
  
  console.log('[showChipQrCode] QR section ativada');
  
  chipState.currentChipId = chipId;
  
  // Limpar intervalo anterior se existir
  if (chipState.qrPollIntervalId) {
      clearInterval(chipState.qrPollIntervalId);
  }

  // Poll a cada 3 segundos
  chipState.qrPollIntervalId = setInterval(() => {
    void fetchAndDisplayQrCode(chipId);
  }, 3000); 
  
  // Initial fetch imediato
  await fetchAndDisplayQrCode(chipId);
  
  // Bind close button
  const closeButton = document.getElementById("chip-qr-close");
  // Remover listeners antigos para evitar duplicação (cloneNode)
  if (closeButton) {
      const newBtn = closeButton.cloneNode(true);
      closeButton.parentNode.replaceChild(newBtn, closeButton);
      newBtn.addEventListener("click", () => {
        closeChipQrModal();
      });
  }
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
        qrStatus.textContent = "Aguardando inicialização do sistema...";
        qrStatus.className = "text-center text-sm text-amber-600 animate-pulse";
      }
      return;
    }
    
    const data = await response.json();
    // console.log('[QR Code Debug]', { status: data.status, hasQr: !!data.qr_code });
    
    const qrCode = data.qr_code || data.qr;
    
    if (qrCode && qrCode.startsWith("data:image")) {
      // QR code válido encontrado
      if (qrLoading) qrLoading.classList.add("hidden");
      
      qrImage.src = qrCode;
      qrImage.classList.remove("hidden");
      
      // Forçar display block para garantir centralização se necessário
      qrImage.style.display = "block"; 
      
      if (qrStatus) {
          qrStatus.textContent = "Escaneie o QR Code com seu WhatsApp";
          qrStatus.className = "text-center text-sm text-slate-600 font-medium";
      }
    } else {
      // Sem QR code ainda
      if (qrLoading) qrLoading.classList.remove("hidden");
      qrImage.classList.add("hidden");
      
      if (qrStatus) {
        let statusMsg = data.message || (data.status ? `Status: ${data.status}` : "Aguardando...");
        
        // Traduções amigáveis
        if (data.status === "STARTING") statusMsg = "Iniciando WhatsApp... Aguarde.";
        if (data.status === "SCAN_QR_CODE") statusMsg = "Gerando QR Code...";
        
        qrStatus.textContent = statusMsg;
        
        if (data.status === "CONNECTED" || data.status === "WORKING") {
             qrStatus.textContent = "✅ Conectado com sucesso!";
             qrStatus.className = "text-center text-sm text-green-600 font-bold";
             setTimeout(() => closeChipQrModal(), 2000);
        } else if (data.status === "FAILED" || data.status === "STOPPED") {
             qrStatus.className = "text-center text-sm text-red-600 font-bold";
             statusMsg = "Erro na conexão. Tentando reiniciar...";
             qrStatus.textContent = statusMsg;
        } else {
             qrStatus.className = "text-center text-sm text-slate-500 animate-pulse";
        }
      }
    }
    
    // Check chip status final para fechar modal se conectar via outro meio
    const chipResponse = await apiFetch(`/chips/${chipId}`);
    if (chipResponse?.ok) {
      const chip = await chipResponse.json();
      if (chip.status === "connected") {
        if (qrStatus) {
          qrStatus.textContent = "✅ Chip conectado com sucesso!";
          qrStatus.className = "text-center text-sm text-green-600 font-bold";
        }
        setTimeout(() => closeChipQrModal(), 2000);
      }
    }
            
  } catch (err) {
    console.error("Erro no poll de QR:", err);
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
  document.getElementById("open-group-heatup")?.addEventListener("click", () => {
    openGroupHeatUpModal();
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
    const heatUpStatus = chip.extra_data?.heat_up?.status;
    const isHeatingUp = heatUpStatus === "in_progress";
    
    let statusLabel = formatChipStatus(chip.status);
    let statusClass = getChipStatusClass(chip.status);
    
    // Sobrescrever status visual se estiver em aquecimento, mas apenas se conectado
    if (isHeatingUp) {
      if (!["waiting_qr", "disconnected", "banned", "error"].includes(chip.status)) {
        statusLabel = "Em Aquecimento";
        statusClass = "inline-flex items-center rounded-full bg-sky-100 px-2.5 py-0.5 text-xs font-medium text-sky-800";
      } else {
        // Se estiver desconectado mas com heatup ativo
        // Não mudamos o statusLabel principal (fica "Desconectado"), mas podemos adicionar um indicador extra no nome ou badge
      }
    }

    const row = document.createElement("tr");
    row.dataset.test = "chip-row";
    row.dataset.chipId = chip.id;
    row.dataset.alias = chip.alias;
    
    // Badge ao lado do nome
    let nameBadge = "";
    if (isHeatingUp && !["waiting_qr", "disconnected", "banned", "error"].includes(chip.status)) {
      nameBadge = '<span class="ml-2 text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">🔥 Aquecendo</span>';
    }

    row.innerHTML = `
      <td class="py-2 font-medium text-slate-800">
        ${chip.alias}
        ${nameBadge}
      </td>
      <td class="py-2"><span data-test="chip-status" class="${statusClass}">${statusLabel}</span></td>
      <td class="py-2">${chip.health_score ?? "--"}</td>
      <td class="py-2">${formatDate(chip.created_at)}</td>
      <td class="py-2">${formatDate(chip.last_activity_at)}</td>
      <td class="py-2 text-right">
        <div class="flex gap-2 justify-end">
          ${(isHeatingUp && !["waiting_qr", "disconnected", "banned", "error"].includes(chip.status)) ? `
            <button class="btn-xs bg-orange-100 text-orange-700 hover:bg-orange-200" type="button" data-action="view-stats" data-chip-id="${chip.id}">
              📊 Stats
            </button>
            <button class="btn-xs bg-red-100 text-red-700 hover:bg-red-200" type="button" data-action="stop-heatup" data-chip-id="${chip.id}">
              ⏸ Parar
            </button>
          ` : chip.status === 'connected' ? `
            <button class="btn-secondary btn-xs" type="button" data-action="heat-up" data-chip-id="${chip.id}">
              🔥 Heat-up
            </button>
            <button class="btn-secondary btn-xs" type="button" data-action="view-stats" data-chip-id="${chip.id}">
              📊 Stats
            </button>
            <button class="btn-secondary btn-xs" type="button" data-action="disconnect" data-chip-id="${chip.id}">
              Desconectar
            </button>
          ` : (chip.status === 'waiting_qr' || chip.status === 'disconnected') ? `
             <button class="btn-primary btn-xs" type="button" data-action="connect" data-chip-id="${chip.id}">
               🔌 Conectar
             </button>
          ` : ''}
          <button class="btn-secondary btn-xs text-red-600 hover:bg-red-50" type="button" data-action="delete" data-chip-id="${chip.id}">
            Deletar
          </button>
        </div>
      </td>
    `;
    table.appendChild(row);

    // Heat-up button (individual)
    const heatUpButton = row.querySelector("[data-action=\"heat-up\"]");
    if (heatUpButton) {
      heatUpButton.addEventListener("click", async () => {
        await openHeatUpModalForChip(chip.id);
      });
    }

    // Connect button
    const connectButton = row.querySelector("[data-action=\"connect\"]");
    if (connectButton) {
      connectButton.addEventListener("click", async () => {
        await openConnectModal(chip.id);
      });
    }

    // View Stats button
    const viewStatsButton = row.querySelector("[data-action=\"view-stats\"]");
    if (viewStatsButton) {
      viewStatsButton.addEventListener("click", async () => {
        await openMaturationStatsModal(chip.id);
      });
    }
    
    // Stop heat-up button
    const stopHeatUpButton = row.querySelector("[data-action=\"stop-heatup\"]");
    if (stopHeatUpButton) {
      stopHeatUpButton.addEventListener("click", async () => {
        if (confirm(`Deseja parar o aquecimento do chip "${chip.alias}"?`)) {
          await handleStopHeatUp(chip.id);
        }
      });
    }
    
    // Disconnect button
    const disconnectButton = row.querySelector("[data-action=\"disconnect\"]");
    if (disconnectButton) {
      disconnectButton.addEventListener("click", async () => {
        if (confirm(`Deseja desconectar o chip "${chip.alias}"?`)) {
          await handleChipDisconnect(chip.id);
        }
      });
    }
    
    // Delete button
    const deleteButton = row.querySelector("[data-action=\"delete\"]");
    if (deleteButton) {
      deleteButton.addEventListener("click", async (e) => {
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
    }
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
  document.getElementById("campaign-save-button")?.addEventListener("click", handleCampaignSave);
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

function openCampaignWizard(skipReset = false) {
  bindCampaignWizardElements();
  if (!skipReset) {
    resetCampaignWizard();
  }
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
  
  const nameInput = document.getElementById("campaign-name");
  const templateInput = document.getElementById("campaign-template");
  if (!nameInput?.value || !templateInput?.value) {
    setCampaignFeedback("Informe nome e mensagem principal para continuar.", "warning");
    return;
  }
  
  const payload = {
    name: nameInput.value.trim(),
    description: document.getElementById("campaign-description")?.value?.trim() || null,
    message_template: templateInput.value.trim(),
    message_template_b: document.getElementById("campaign-template-b")?.value?.trim() || null,
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
  } else {
    payload.scheduled_for = null;
  }

  const mediaInput = document.getElementById("campaign-media");
  const pendingFile = mediaInput?.files?.[0] ?? null;
  if (pendingFile) {
    campaignState.pendingMediaFile = pendingFile;
  }

  // Modo de EDIÇÃO
  if (campaignState.campaignId) {
    // NÃO enviar settings no passo 1, apenas informações básicas
    // Settings (chips, intervalo, etc) são enviados no passo 2
    
    console.log("📤 Enviando PUT para editar campanha (passo 1 - SEM settings):", payload);
    
    const response = await apiFetch(`/campaigns/${campaignState.campaignId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    if (!response?.ok) {
      const errorText = await response.text();
      console.error("❌ Erro no PUT:", errorText);
      setCampaignFeedback(errorText || "Não foi possível atualizar a campanha.", "error");
      return;
    }
    const data = await response.json();
    campaignState.createdCampaign = data;
    campaignState.media = Array.isArray(data.media) ? data.media : [];
    setCampaignFeedback("Informações atualizadas! Continue para os próximos passos.", "success");
    renderCampaignMediaList();
    await maybeUploadPendingMedia();
    if (mediaInput) {
      mediaInput.value = "";
    }
    
    // Ir para o passo 2 (chips) - NÃO fechar o wizard
    await loadCampaignWizardChips();
    goToCampaignStep(2);
    return;
  }
  
  // Modo de CRIAÇÃO
  payload.settings = {
    chip_ids: [],
    interval_seconds: 10,
    randomize_interval: false,
  };
  
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
  
  // Buscar chips em uso por outras campanhas ATIVAS (draft, scheduled, running, paused)
  const campaignsResponse = await apiFetch("/campaigns");
  let chipsInUse = new Set();
  if (campaignsResponse?.ok) {
    const campaigns = await campaignsResponse.json();
    const activeCampaigns = campaigns.filter(c => 
      ["draft", "scheduled", "running", "paused"].includes(c.status) && 
      c.id !== campaignState.campaignId // Excluir campanha atual se estiver editando
    );
    activeCampaigns.forEach(campaign => {
      const chipIds = campaign.settings?.chip_ids || [];
      chipIds.forEach(id => chipsInUse.add(id));
    });
  }
  
  renderCampaignChips(chips, chipsInUse);
}

function renderCampaignChips(chips, chipsInUse = new Set()) {
  const container = document.getElementById("campaign-chips-list");
  if (!container) return;
  container.innerHTML = "";
  if (!chips.length) {
    container.innerHTML = '<p class="text-sm text-slate-500">Nenhum chip disponível. Cadastre chips antes de prosseguir.</p>';
    return;
  }
  
  // Verificar se chip está em maturação
  const isMaturing = (chip) => {
    if ((chip.status || "").toLowerCase() === "maturing") return true;
    if (chip.extra_data?.heat_up?.status === "in_progress") return true;
    return false;
  };
  
  // Contar chips disponíveis (conectados E não em uso E não em maturação)
  const availableChips = chips.filter(c => 
    (c.status || "").toLowerCase() === "connected" && 
    !chipsInUse.has(c.id) &&
    !isMaturing(c)
  );
  
  // Mostrar aviso se não houver chips disponíveis
  if (availableChips.length === 0) {
    const warning = document.createElement("div");
    warning.className = "bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4";
    warning.innerHTML = `
      <p class="text-sm text-yellow-800">
        ⚠️ <strong>Nenhum chip disponível!</strong> 
        ${chips.some(isMaturing)
          ? "Seus chips estão em processo de aquecimento (maturação). Pare o aquecimento para usá-los."
          : chips.some(c => (c.status || "").toLowerCase() === "connected") 
          ? "Todos os chips conectados estão sendo usados por outras campanhas." 
          : "Conecte pelo menos um chip antes de iniciar a campanha."}
      </p>
    `;
    container.appendChild(warning);
  }
  
  // Pegar o chip selecionado (apenas 1)
  const selectedChipId = campaignState.selectedChips.size > 0 ? Array.from(campaignState.selectedChips)[0] : null;
  
  chips.forEach((chip) => {
    const card = document.createElement("label");
    const isConnected = (chip.status || "").toLowerCase() === "connected";
    const isInUse = chipsInUse.has(chip.id);
    const maturing = isMaturing(chip);
    
    // Desabilitado se: Não conectado OU Em uso OU Em Maturação
    const disabled = !isConnected || isInUse || maturing;
    const isSelected = selectedChipId === chip.id;
    
    // Se está desabilitado e estava selecionado, remover da seleção
    if (disabled && isSelected) {
      campaignState.selectedChips.clear();
    }
    
    let statusLabel = "";
    if (maturing) {
      statusLabel = '<span class="text-xs text-amber-600 ml-2 font-bold">🔥 Em Aquecimento</span>';
    } else if (!isConnected) {
      statusLabel = '<span class="text-xs text-red-600 ml-2">(Desconectado)</span>';
    } else if (isInUse) {
      statusLabel = '<span class="text-xs text-orange-600 ml-2">(Em uso por outra campanha)</span>';
    }
    
    card.className = `card space-y-2 ${disabled ? "opacity-50 cursor-not-allowed bg-slate-50" : "cursor-pointer hover:bg-slate-50"}`;
    card.innerHTML = `
      <div class="flex items-center justify-between gap-3">
        <div class="flex-1">
          <p class="font-medium ${disabled ? "text-slate-400" : "text-slate-700"}">
            ${chip.alias}
            ${statusLabel}
          </p>
          <p class="text-xs text-slate-500">Status: ${formatChipStatus(chip.status)}</p>
        </div>
        <input type="radio" name="campaign-chip" value="${chip.id}" ${disabled ? "disabled" : ""} ${isSelected && !disabled ? "checked" : ""} class="border-slate-300" data-test="campaign-chip" />
      </div>
      <p class="text-xs text-slate-500">Saúde: ${chip.health_score ?? "--"}</p>
    `;
    container.appendChild(card);
  });
}

async function handleCampaignChipsSubmit(event) {
  event.preventDefault();
  if (!campaignState.campaignId) {
    setCampaignFeedback("Crie a campanha antes de selecionar o chip.", "warning");
    return;
  }
  const selectedRadio = document.querySelector("#campaign-chips-list input[type='radio']:checked");
  if (!selectedRadio) {
    setCampaignFeedback("Selecione um chip para continuar.", "warning");
    return;
  }
  const chipId = selectedRadio.value;
  campaignState.selectedChips = new Set([chipId]);
  const intervalSeconds = Number(document.getElementById("campaign-interval")?.value || "10");
  const randomize = Boolean(document.getElementById("campaign-randomize")?.checked);
  const response = await apiFetch(`/campaigns/${campaignState.campaignId}`, {
    method: "PUT",
    body: JSON.stringify({
      settings: {
        chip_ids: [chipId],
        interval_seconds: Number.isFinite(intervalSeconds) && intervalSeconds > 0 ? intervalSeconds : 10,
        randomize_interval: randomize,
      },
    }),
  });
  if (!response?.ok) {
    let message = "Não foi possível salvar as configurações de chips.";
    try {
      const errorData = await response.json();
      message = errorData.detail || errorData.message || message;
    } catch {
      const text = await response.text();
      if (text) {
        try {
          const parsed = JSON.parse(text);
          message = parsed.detail || parsed.message || text;
        } catch {
          message = text;
        }
      }
    }
    setCampaignFeedback(message, "error");
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
  
  // Se não tem arquivo, mas já tem contatos importados, permitir continuar
  if (!file) {
    if (campaignState.contactsSummary && campaignState.contactsSummary.valid_contacts > 0) {
      // Já tem contatos, pode pular para revisão
      setCampaignFeedback("Usando contatos já importados. Revise e finalize o disparo.", "info");
      await populateCampaignReview();
      goToCampaignStep(4);
      return;
    } else {
      // Não tem arquivo e não tem contatos
      setCampaignFeedback("Selecione um arquivo CSV para importar contatos.", "warning");
      return;
    }
  }
  
  // Tem arquivo, fazer upload (substituir contatos antigos)
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

async function handleCampaignSave() {
  if (!campaignState.campaignId) {
    setCampaignFeedback("Nenhuma campanha para salvar.", "warning");
    return;
  }
  
  // Fechar wizard e atualizar lista
  closeCampaignWizard();
  await loadCampaigns({ toast: "Campanha salva com sucesso!" });
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
  
  // DRAFT: Editar, Iniciar, Deletar
  if (status === "draft") {
    buttons.push(`<button data-campaign-action="edit" data-campaign-id="${campaign.id}" class="btn-secondary btn-xs" type="button" title="Editar campanha">✏️ Editar</button>`);
    buttons.push(`<button data-campaign-action="start" data-campaign-id="${campaign.id}" class="btn-primary btn-xs" type="button">Iniciar</button>`);
    buttons.push(`<button data-campaign-action="delete" data-campaign-id="${campaign.id}" class="btn-xs px-2 py-1 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded transition-colors" type="button" title="Deletar campanha">🗑️</button>`);
  }
  
  // SCHEDULED: Editar, Cancelar, Deletar
  if (status === "scheduled") {
    buttons.push(`<button data-campaign-action="edit" data-campaign-id="${campaign.id}" class="btn-secondary btn-xs" type="button" title="Editar campanha">✏️ Editar</button>`);
    buttons.push(`<button data-campaign-action="cancel" data-campaign-id="${campaign.id}" class="btn-xs px-2 py-1 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded transition-colors" type="button">Cancelar</button>`);
    buttons.push(`<button data-campaign-action="delete" data-campaign-id="${campaign.id}" class="btn-xs px-2 py-1 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded transition-colors" type="button" title="Deletar campanha">🗑️</button>`);
  }
  
  // RUNNING: Pausar, Cancelar (SEM Editar)
  if (status === "running") {
    buttons.push(`<button data-campaign-action="pause" data-campaign-id="${campaign.id}" class="btn-secondary btn-xs" type="button">Pausar</button>`);
    buttons.push(`<button data-campaign-action="cancel" data-campaign-id="${campaign.id}" class="btn-xs px-2 py-1 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded transition-colors" type="button">Cancelar</button>`);
  }
  
  // PAUSED: Editar, Retomar, Cancelar
  if (status === "paused") {
    buttons.push(`<button data-campaign-action="edit" data-campaign-id="${campaign.id}" class="btn-secondary btn-xs" type="button" title="Editar campanha">✏️ Editar</button>`);
    buttons.push(`<button data-campaign-action="resume" data-campaign-id="${campaign.id}" class="btn-primary btn-xs" type="button">Retomar</button>`);
    buttons.push(`<button data-campaign-action="cancel" data-campaign-id="${campaign.id}" class="btn-xs px-2 py-1 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded transition-colors" type="button">Cancelar</button>`);
  }
  
  // CANCELLED e COMPLETED: Apenas Deletar
  if (status === "cancelled" || status === "completed") {
    buttons.push(`<button data-campaign-action="delete" data-campaign-id="${campaign.id}" class="btn-xs px-2 py-1 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded transition-colors" type="button" title="Deletar campanha">🗑️ Deletar</button>`);
  }
  
  return buttons.join(" ");
}

async function loadCampaignForEdit(campaignId) {
  // Buscar dados da campanha
  const response = await apiFetch(`/campaigns/${campaignId}`);
  if (!response?.ok) {
    setCampaignFeedback("Erro ao carregar campanha para edição.", "error");
    return;
  }
  
  const campaign = await response.json();
  console.log("🔍 Campanha carregada para edição:", campaign);
  
  // Validar se pode editar (permitir apenas DRAFT, SCHEDULED, PAUSED)
  if (campaign.status === "running") {
    setCampaignFeedback("Pause a campanha antes de editá-la.", "warning");
    return;
  }
  
  if (campaign.status === "completed" || campaign.status === "cancelled") {
    setCampaignFeedback("Não é possível editar campanhas completas ou canceladas.", "warning");
    return;
  }
  
  // Abrir wizard SEM resetar (modo edição)
  bindCampaignWizardElements();
  campaignState.wizard.element?.classList.remove("hidden");
  campaignState.wizard.backdrop?.classList.remove("hidden");
  
  // Armazenar ID para modo de edição
  campaignState.campaignId = campaignId;
  campaignState.createdCampaign = campaign;
  
  // Aguardar renderização do DOM
  await new Promise(resolve => setTimeout(resolve, 100));
  
  // Preencher formulário básico
  const nameInput = document.getElementById("campaign-name");
  const descInput = document.getElementById("campaign-description");
  const templateInput = document.getElementById("campaign-template");
  const templateBInput = document.getElementById("campaign-template-b");
  
  if (nameInput) nameInput.value = campaign.name || "";
  if (descInput) descInput.value = campaign.description || "";
  if (templateInput) templateInput.value = campaign.message_template || "";
  if (templateBInput) templateBInput.value = campaign.message_template_b || "";
  
  console.log("✅ Campos preenchidos:", {
    name: nameInput?.value,
    desc: descInput?.value,
    template: templateInput?.value,
  });
  
  // Agendamento
  if (campaign.scheduled_for) {
    const scheduleToggle = document.getElementById("campaign-schedule-toggle");
    const scheduleDatetime = document.getElementById("campaign-schedule-datetime");
    const scheduleFields = document.getElementById("campaign-schedule-fields");
    
    if (scheduleToggle) scheduleToggle.checked = true;
    if (scheduleDatetime) {
      // Converter para formato datetime-local
      const date = new Date(campaign.scheduled_for);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      scheduleDatetime.value = `${year}-${month}-${day}T${hours}:${minutes}`;
    }
    if (scheduleFields) scheduleFields.classList.remove("hidden");
  }
  
  // Carregar chips selecionados e configurações
  const settings = campaign.settings || {};
  if (Array.isArray(settings.chip_ids)) {
    campaignState.selectedChips = new Set(settings.chip_ids);
  }
  
  // Preencher intervalo e randomização (quando carregar o passo 2)
  const intervalInput = document.getElementById("campaign-interval");
  const randomizeInput = document.getElementById("campaign-randomize");
  if (intervalInput && settings.interval_seconds) {
    intervalInput.value = settings.interval_seconds;
  }
  if (randomizeInput && typeof settings.randomize_interval === "boolean") {
    randomizeInput.checked = settings.randomize_interval;
  }
  
  // Carregar resumo de contatos (se existem)
  if (campaign.total_contacts > 0) {
    campaignState.contactsSummary = {
      valid_contacts: campaign.total_contacts,
      total_processed: campaign.total_contacts,
      invalid_contacts: 0,
      duplicated: 0,
      variables: []
    };
    
    // Mostrar resumo de contatos
    const summaryElement = document.getElementById("campaign-contacts-summary");
    if (summaryElement) {
      summaryElement.classList.remove("hidden");
      summaryElement.innerHTML = `
        <p><strong>${campaign.total_contacts}</strong> contatos já importados.</p>
        <p class="text-xs text-slate-500 mt-2">💡 Você pode deixar como está ou fazer upload de um novo CSV para substituir.</p>
      `;
    }
  }
  
  // Atualizar título
  const wizardTitle = document.getElementById("campaign-wizard-title");
  const wizardSubtitle = document.getElementById("campaign-wizard-subtitle");
  if (wizardTitle) wizardTitle.textContent = "Editar campanha";
  if (wizardSubtitle) wizardSubtitle.textContent = "Modifique as informações da campanha e salve.";
  
  setCampaignFeedback(`Editando campanha: ${campaign.name}`, "info");
}

async function handleCampaignRowAction(campaignId, action) {
  if (!campaignId || !action) return;
  
  // Ação: EDITAR
  if (action === "edit") {
    await loadCampaignForEdit(campaignId);
    return;
  }
  
  // Ação: DELETAR
  if (action === "delete") {
    const confirmed = confirm("Deseja realmente deletar esta campanha?\n\nEsta ação é irreversível e irá remover:\n- Todos os contatos\n- Todas as mensagens\n- Todas as mídias\n\nChips e proxies não serão afetados.");
    if (!confirmed) return;
    
    const response = await apiFetch(`/campaigns/${campaignId}`, { method: "DELETE" });
    if (!response?.ok) {
      const message = await response.text();
      setCampaignFeedback(message || "Não foi possível deletar a campanha.", "error");
      return;
    }
    setCampaignFeedback("Campanha deletada com sucesso. Recursos liberados.", "success");
    await loadCampaigns({ silent: true });
    return;
  }
  
  // Ações: START, RESUME, PAUSE, CANCEL
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
  
  // Mensagem customizada por ação
  let message = "";
  if (action === "start") {
    message = "Campanha iniciada! Mensagens sendo enviadas.";
  } else if (action === "resume") {
    message = "Campanha retomada! Continuando envios.";
  } else if (action === "pause") {
    message = "Campanha pausada. Mensagens pendentes preservadas.";
  } else if (action === "cancel") {
    message = "Campanha cancelada. Mensagens pendentes marcadas como falhas.";
  }
  
  setCampaignFeedback(message || `Status: ${formatCampaignStatus(data.status)}`, "success");
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
      let errorMessage = "Erro ao gerar pagamento";
      try {
        const errorData = await response.json();
        if (errorData.detail) errorMessage = errorData.detail;
      } catch (e) {
        // Ignorar
      }
      throw new Error(errorMessage);
    }
    
    const data = await response.json();
    
    feedbackEl.textContent = "Redirecionando para pagamento...";
    
    // Se for Mercado Pago e tivermos Public Key e Payment ID (Preference ID), usar SDK
    if (paymentMethod === "mercadopago" && data.public_key && data.payment_id && window.MercadoPago) {
      try {
        const mp = new MercadoPago(data.public_key);
        mp.checkout({
          preference: {
            id: data.payment_id
          },
          autoOpen: true
        });
        feedbackEl.textContent = "Aguardando pagamento...";
        submitBtn.removeAttribute("disabled");
        submitBtn.textContent = "Comprar Créditos";
        return; // Não redirecionar via URL, o modal vai abrir
      } catch (e) {
        console.error("Erro ao abrir Mercado Pago SDK:", e);
        // Fallback para redirect
      }
    }
    
    // Redirect to payment URL (Fallback ou outros gateways)
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

// ========================================
// HEAT-UP EM GRUPO
// ========================================

// Abrir modal de heat-up para um chip específico
async function openHeatUpModalForChip(chipId) {
  await openGroupHeatUpModal(chipId);
}

async function openGroupHeatUpModal(preselectedChipId = null) {
  const modal = document.getElementById("group-heatup-modal");
  const backdrop = document.getElementById("group-heatup-backdrop");
  if (!modal || !backdrop) return;

  // Carregar chips conectados
  const response = await apiFetch("/chips");
  if (!response?.ok) {
    setChipFeedback("Não foi possível carregar os chips.", "error");
    return;
  }

  const chips = await response.json();
  const connectedChips = chips.filter(chip => chip.status === "connected");

  if (connectedChips.length < 1) {
    setChipFeedback("Você precisa de pelo menos 1 chip conectado.", "warning");
    return;
  }

  const container = document.getElementById("group-heatup-chips");
  if (!container) return;

  container.innerHTML = "";
  connectedChips.forEach(chip => {
    const isPreselected = chip.id === preselectedChipId;
    const div = document.createElement("div");
    div.className = "flex items-center gap-3 p-2 border rounded hover:bg-slate-50 cursor-pointer transition-colors";
    div.innerHTML = `
      <input type="checkbox" id="chip-${chip.id}" name="group_chips" value="${chip.id}" ${isPreselected ? 'checked' : ''} class="cursor-pointer chip-checkbox" />
      <label for="chip-${chip.id}" class="flex-1 cursor-pointer text-sm font-medium text-slate-700">
        ${chip.alias} <span class="text-xs text-slate-500">(Saúde: ${chip.health_score ?? "--"})</span>
      </label>
    `;
    container.appendChild(div);
  });

  // Atualizar contador ao mudar seleção
  updateSelectedChipsCount();
  document.querySelectorAll('.chip-checkbox').forEach(cb => {
    cb.addEventListener('change', updateSelectedChipsCount);
  });
  
  // Carregar mensagens padrão no textarea
  const messagesTextarea = document.getElementById("group-heatup-messages");
  if (messagesTextarea) {
    // Só preencher se estiver vazio
    if (!messagesTextarea.value.trim()) {
      messagesTextarea.value = getDefaultHeatUpMessages();
    }
    messagesTextarea.addEventListener('input', updateMessagesPreview);
    updateMessagesPreview(); // Inicial
  }

  modal.classList.remove("hidden");
  backdrop.classList.remove("hidden");
}

function getDefaultHeatUpMessages() {
  return `Oi! Tudo bem?
Bom dia! Como vai?
Boa tarde! E aí?
Boa noite! Tudo certo?
Olá! Tudo bem com você?
E aí, tudo tranquilo?
Oi, tudo certinho aí?
Bom dia! Tudo ok?
Boa tarde! Beleza?
Boa noite! Como foi o dia?
Ok, entendido!
Perfeito, obrigado!
Beleza, valeu!
Combinado então!
Pode deixar!
Sim, recebi sim!
Ok, vou verificar
Tudo certo, obrigado
Entendi, valeu!
Perfeito! Obrigado
Conseguiu ver?
Recebeu o documento?
Viu a mensagem?
Tudo certo aí?
Precisa de alguma coisa?
Posso ajudar em algo?
Tem alguma dúvida?
Quer que eu explique melhor?
Precisa de mais informações?
Alguma outra coisa?
Sim, recebi!
Tudo ok por aqui
Não precisa, obrigado
Já resolvi, valeu!
Tudo certo, pode seguir
Vou dar uma olhada
Deixa eu verificar aqui
Vou checar e te retorno
Já estou vendo
Olhando aqui agora
Deu tudo certo!
Funcionou perfeitamente
Consegui sim, obrigado
Resolvido, valeu!
Problema resolvido
Show! Obrigado
Maravilha! Valeu
Excelente! Obrigado
Legal! Funcionou
Perfeito! Deu certo
Quanto tempo! Como anda?
Há quanto tempo! Tudo bem?
Que bom te ver por aqui
Legal saber que está bem
Fico feliz em ajudar
Qualquer coisa é só falar
Estou à disposição
Pode contar comigo
Sem problemas!
De nada!
Disponha sempre
Por nada!
Sempre às ordens
Fico no aguardo
Aguardo seu retorno
Qualquer novidade me avisa
Me avisa se precisar
Estou aqui
Bom final de semana!
Ótima semana!
Bom descanso!
Até mais!
Até breve!
Abraço!
Falamos depois
Combinado! Até mais
Fechado então! Até`;
}

function updateSelectedChipsCount() {
  const selected = document.querySelectorAll("[name='group_chips']:checked").length;
  const countSpan = document.getElementById("selected-chips-count");
  if (countSpan) {
    countSpan.textContent = `${selected} selecionado${selected !== 1 ? 's' : ''}`;
    countSpan.className = selected >= 2 ? "text-xs text-green-600 font-medium" : "text-xs text-amber-600";
  }
}

function updateMessagesPreview() {
  const textarea = document.getElementById("group-heatup-messages");
  const preview = document.getElementById("messages-preview");
  const count = document.getElementById("messages-count");
  
  if (!textarea || !preview) return;
  
  const text = textarea.value.trim();
  const messages = text ? text.split('\n').filter(msg => msg.trim()) : [];
  
  if (count) {
    count.textContent = `${messages.length} mensagen${messages.length !== 1 ? 's' : 'm'}`;
  }
  
  if (messages.length === 0) {
    preview.innerHTML = '<p class="text-slate-400 italic">Nenhuma mensagem ainda...</p>';
    return;
  }
  
  preview.innerHTML = messages.slice(0, 10).map((msg, i) => 
    `<p class="text-slate-600">${i + 1}. ${msg.substring(0, 60)}${msg.length > 60 ? '...' : ''}</p>`
  ).join('');
  
  if (messages.length > 10) {
    preview.innerHTML += `<p class="text-slate-400 italic">... e mais ${messages.length - 10} mensagens</p>`;
  }
}

// Upload de arquivo de mensagens
document.getElementById("heatup-messages-file")?.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  
  try {
    const text = await file.text();
    const textarea = document.getElementById("group-heatup-messages");
    if (textarea) {
      textarea.value = text;
      updateMessagesPreview();
    }
    setChipFeedback(`Arquivo "${file.name}" carregado com ${text.split('\n').filter(l => l.trim()).length} mensagens.`, "success");
  } catch (err) {
    setChipFeedback("Erro ao ler arquivo: " + err.message, "error");
  }
});

// Limpar mensagens
document.getElementById("clear-messages")?.addEventListener('click', () => {
  if (confirm("Deseja limpar todas as mensagens?")) {
    const textarea = document.getElementById("group-heatup-messages");
    if (textarea) {
      textarea.value = "";
      updateMessagesPreview();
    }
    setChipFeedback("Mensagens limpas. Digite suas próprias mensagens ou feche e abra o modal novamente para recarregar as padrão.", "info");
  }
});

function closeGroupHeatUpModal() {
  const modal = document.getElementById("group-heatup-modal");
  const backdrop = document.getElementById("group-heatup-backdrop");
  modal?.classList.add("hidden");
  backdrop?.classList.add("hidden");
  
  // Limpar seleção
  document.querySelectorAll("[name='group_chips']:checked").forEach(el => el.checked = false);
  
  // Limpar textarea
  const textarea = document.getElementById("group-heatup-messages");
  if (textarea) textarea.value = "";
  
  // Limpar file input
  const fileInput = document.getElementById("heatup-messages-file");
  if (fileInput) fileInput.value = "";
  
  // Resetar preview
  updateMessagesPreview();
  updateSelectedChipsCount();
}

async function handleGroupHeatUpStart() {
  const selectedChips = Array.from(document.querySelectorAll("[name='group_chips']:checked")).map(el => el.value);
  
  if (selectedChips.length < 2) {
    setChipFeedback("⚠️ Selecione pelo menos 2 chips para iniciar o aquecimento.", "warning");
    return;
  }
  
  if (selectedChips.length > 10) {
    setChipFeedback("⚠️ Você pode selecionar no máximo 10 chips.", "warning");
    return;
  }

  const customMessagesText = document.getElementById("group-heatup-messages")?.value?.trim();
  
  if (!customMessagesText) {
    setChipFeedback("⚠️ Adicione pelo menos uma mensagem. Feche e abra o modal novamente para recarregar as mensagens padrão.", "warning");
    return;
  }
  
  const customMessages = customMessagesText.split("\n").filter(msg => msg.trim());
  
  if (customMessages.length < 10) {
    setChipFeedback("⚠️ Adicione pelo menos 10 mensagens para variar as conversas. Atualmente: " + customMessages.length + " mensagens.", "warning");
    return;
  }

  const startButton = document.getElementById("group-heatup-start");
  if (startButton) {
    startButton.disabled = true;
    startButton.textContent = "Iniciando...";
  }

  const response = await apiFetch("/chips/heat-up/group", {
    method: "POST",
    body: JSON.stringify({
      chip_ids: selectedChips,
      custom_messages: customMessages,
    }),
  });

  if (!response?.ok) {
    let detail = "Não foi possível iniciar o aquecimento em grupo.";
    try {
      const error = await response.json();
      if (typeof error?.detail === "string") {
        detail = error.detail;
      }
    } catch (err) {
      // Ignora erro ao ler resposta
    }
    setChipFeedback(detail, "error");
    if (startButton) {
      startButton.disabled = false;
      startButton.textContent = "🔥 Iniciar Aquecimento";
    }
    return;
  }

  const result = await response.json();
  setChipFeedback(`✅ Aquecimento iniciado! ${selectedChips.length} chips estão aquecendo com ${customMessages.length} mensagens configuradas.`, "success");
  closeGroupHeatUpModal();
  await loadChips({ silent: true });
  if (startButton) {
    startButton.disabled = false;
    startButton.textContent = "🔥 Iniciar Aquecimento";
  }
}

document.getElementById("group-heatup-start")?.addEventListener("click", handleGroupHeatUpStart);
document.getElementById("group-heatup-close")?.addEventListener("click", closeGroupHeatUpModal);
document.getElementById("group-heatup-cancel")?.addEventListener("click", closeGroupHeatUpModal);
document.getElementById("group-heatup-backdrop")?.addEventListener("click", closeGroupHeatUpModal);

async function handleStopHeatUp(chipId) {
  setChipFeedback("Parando aquecimento...", "info");
  
  const response = await apiFetch(`/chips/${chipId}/stop-heat-up`, {
    method: "POST",
  });
  
  if (!response?.ok) {
    let detail = "Não foi possível parar o aquecimento.";
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
  
  const result = await response.json();
  setChipFeedback(result.message ?? "Aquecimento parado com sucesso.", "success");
  await loadChips({ silent: true });
}

async function openMaturationStatsModal(chipId) {
  const modal = document.getElementById("maturation-stats-modal");
  const backdrop = document.getElementById("maturation-stats-backdrop");
  if (!modal || !backdrop) return;

  modal.classList.remove("hidden");
  backdrop.classList.remove("hidden");
  
  // Carregar estatísticas
  await loadMaturationStats(chipId);
  
  // Bind refresh button
  const refreshButton = document.getElementById("maturation-stats-refresh");
  if (refreshButton) {
    refreshButton.onclick = () => loadMaturationStats(chipId);
  }
}

async function loadMaturationStats(chipId) {
  const contentDiv = document.getElementById("maturation-stats-content");
  if (!contentDiv) return;
  
  contentDiv.innerHTML = '<p class="text-center text-slate-500">Carregando...</p>';
  
  const response = await apiFetch(`/chips/${chipId}/maturation-stats`);
  
  if (!response?.ok) {
    contentDiv.innerHTML = '<p class="text-center text-red-600">Erro ao carregar estatísticas.</p>';
    return;
  }
  
  const stats = await response.json();
  
  if (stats.status === "never_started") {
    contentDiv.innerHTML = `
      <div class="text-center space-y-3 py-8">
        <p class="text-6xl">😴</p>
        <p class="text-lg font-medium text-slate-700">${stats.alias}</p>
        <p class="text-sm text-slate-500">${stats.message}</p>
      </div>
    `;
    return;
  }
  
  const statusEmoji = {
    in_progress: "🔥",
    completed: "✅",
    stopped: "⏸️"
  }[stats.status] || "📊";
  
  const statusText = {
    in_progress: "Em andamento",
    completed: "Concluído",
    stopped: "Parado"
  }[stats.status] || stats.status;
  
  const isReady = stats.is_ready_for_campaign;
  const readyClass = isReady ? "text-emerald-600" : "text-amber-600";
  const readyEmoji = isReady ? "✅" : "⏳";
  
  contentDiv.innerHTML = `
    <div class="space-y-4">
      <div class="text-center pb-4 border-b">
        <p class="text-5xl mb-2">${statusEmoji}</p>
        <p class="text-xl font-bold text-slate-800">${stats.alias}</p>
        <p class="text-sm text-slate-500">${statusText}</p>
      </div>
      
      <div class="grid grid-cols-2 gap-4">
        <div class="bg-slate-50 p-3 rounded-lg">
          <p class="text-xs text-slate-500 uppercase">Fase Atual</p>
          <p class="text-2xl font-bold text-slate-800">${stats.current_phase}/${stats.total_phases}</p>
        </div>
        
        <div class="bg-slate-50 p-3 rounded-lg">
          <p class="text-xs text-slate-500 uppercase">Mensagens na Fase</p>
          <p class="text-2xl font-bold text-slate-800">${stats.messages_sent_in_phase ?? 0}</p>
        </div>
        
        <div class="bg-slate-50 p-3 rounded-lg">
          <p class="text-xs text-slate-500 uppercase">Tempo Decorrido</p>
          <p class="text-2xl font-bold text-slate-800">${stats.elapsed_hours}h</p>
        </div>
        
        <div class="bg-slate-50 p-3 rounded-lg">
          <p class="text-xs text-slate-500 uppercase">Tempo Total</p>
          <p class="text-2xl font-bold text-slate-800">${stats.total_hours}h</p>
        </div>
      </div>
      
      <div class="bg-slate-50 p-4 rounded-lg">
        <div class="flex justify-between items-center mb-2">
          <p class="text-xs font-medium text-slate-700 uppercase">Progresso</p>
          <p class="text-xs font-bold text-slate-700">${stats.progress_percent}%</p>
        </div>
        <div class="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
          <div class="h-full bg-gradient-to-r from-orange-400 to-emerald-500 transition-all duration-500" style="width: ${stats.progress_percent}%"></div>
        </div>
      </div>
      
      <div class="bg-gradient-to-r from-slate-50 to-slate-100 p-4 rounded-lg border-l-4 ${isReady ? 'border-emerald-500' : 'border-amber-500'}">
        <div class="flex justify-between items-start">
          <div>
            <p class="text-sm font-medium ${readyClass} flex items-center gap-2">
              <span class="text-xl">${readyEmoji}</span>
              ${stats.recommendation}
            </p>
          </div>
          ${stats.next_execution ? `
            <div class="text-right">
              <p class="text-xs text-slate-500 uppercase">Próxima mensagem</p>
              <p class="text-sm font-bold text-blue-600">${stats.next_execution}</p>
            </div>
          ` : ''}
        </div>
      </div>
      
      ${stats.recent_messages && stats.recent_messages.length > 0 ? `
        <div class="bg-white p-4 rounded-lg border">
          <p class="text-sm font-medium text-slate-700 mb-3 flex justify-between">
            <span>📨 Conversas Recentes</span>
            <span class="text-xs text-slate-400">${stats.total_messages_sent || 0} msgs total</span>
          </p>
          <div class="space-y-3 max-h-64 overflow-y-auto px-1">
            ${stats.recent_messages.map(msg => {
               const isSent = msg.type !== 'reply';
               return `
              <div class="flex flex-col ${isSent ? 'items-end' : 'items-start'}">
                <div class="max-w-[85%] ${isSent ? 'bg-blue-50 border-blue-100' : 'bg-slate-50 border-slate-100'} border p-2 rounded-lg relative">
                  <div class="flex justify-between items-center gap-4 mb-1">
                    <span class="text-[10px] font-bold ${isSent ? 'text-blue-700' : 'text-slate-700'}">
                      ${isSent ? '📤 Enviada' : '↩️ Resposta'}
                    </span>
                    <span class="text-[10px] text-slate-400">${msg.time}</span>
                  </div>
                  <p class="text-xs text-slate-600 mb-1">Para/De: <strong>${msg.to}</strong></p>
                  <p class="text-xs text-slate-800 italic">"${msg.message}"</p>
                </div>
              </div>
            `}).join('')}
          </div>
          <p class="text-xs text-slate-400 mt-2 text-center">Últimas interações</p>
        </div>
      ` : ''}
      
      ${stats.group_id ? `
        <div class="text-xs text-slate-500 text-center pt-2 border-t">
          Grupo: <code class="bg-slate-100 px-2 py-1 rounded">${stats.group_id}</code>
        </div>
      ` : ''}
      
      <div class="text-xs text-slate-400 space-y-1 pt-2 border-t">
        ${stats.started_at ? `<p>Iniciado: ${formatDate(stats.started_at)}</p>` : ''}
        ${stats.completed_at ? `<p>Concluído: ${formatDate(stats.completed_at)}</p>` : ''}
        ${stats.stopped_at ? `<p>Parado: ${formatDate(stats.stopped_at)}</p>` : ''}
      </div>
    </div>
  `;
}

function closeMaturationStatsModal() {
  const modal = document.getElementById("maturation-stats-modal");
  const backdrop = document.getElementById("maturation-stats-backdrop");
  modal?.classList.add("hidden");
  backdrop?.classList.add("hidden");
}

document.getElementById("maturation-stats-close")?.addEventListener("click", closeMaturationStatsModal);
document.getElementById("maturation-stats-cancel")?.addEventListener("click", closeMaturationStatsModal);
document.getElementById("maturation-stats-backdrop")?.addEventListener("click", closeMaturationStatsModal);

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
// Cache bust: 1731876543 - Group heat-up + maturation stats
// Cache bust: 1731877890 - Fix event listeners for stats buttons
// Cache bust: 1731889234 - Individual heat-up button with messages upload
// Cache bust: 1731889567 - Auto-fill with 75 default messages
// Cache bust: 1731891234 - REAL message sending + history display
// Cache bust: 1732023456 - 5 phases maturation system fully operational
// Cache bust: 1732024567 - Fixed @c.us suffix for real message sending

// ============================================================================
// GLOBAL HEATUP STATS
// ============================================================================

async function openGlobalStatsModal() {
  const modal = document.getElementById("global-stats-modal");
  const backdrop = document.getElementById("global-stats-backdrop");
  if (!modal || !backdrop) return;

  // Garantir que está limpo antes de abrir
  modal.classList.remove("hidden");
  backdrop.classList.remove("hidden");
  
  // Limpar conteúdo anterior para evitar confusão visual
  const contentDiv = document.getElementById("global-stats-content");
  if (contentDiv) {
      contentDiv.innerHTML = '<div class="flex flex-col items-center justify-center py-10"><div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div><p class="mt-4 text-slate-500">Carregando dados em tempo real...</p></div>';
  }
  
  await loadGlobalStats();
}

async function closeGlobalStatsModal() {
  const modal = document.getElementById("global-stats-modal");
  const backdrop = document.getElementById("global-stats-backdrop");
  
  if (modal) modal.classList.add("hidden");
  if (backdrop) backdrop.classList.add("hidden");
}

async function loadGlobalStats() {
  const contentDiv = document.getElementById("global-stats-content");
  if (!contentDiv) return;
  
  contentDiv.innerHTML = '<div class="flex flex-col items-center justify-center py-10"><div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div><p class="mt-4 text-slate-500">Carregando dados em tempo real...</p></div>';
  
  try {
    const response = await apiFetch("/chips/heat-up/global-stats");
    
    if (!response.ok) throw new Error("Falha ao carregar dados");
    
    const stats = await response.json();
    
    if (stats.total_active_chips === 0) {
      contentDiv.innerHTML = `
        <div class="text-center py-10 space-y-4">
          <p class="text-6xl">😴</p>
          <p class="text-xl font-medium text-slate-700">Nenhum aquecimento ativo</p>
          <p class="text-sm text-slate-500 max-w-md mx-auto">
            Selecione chips na lista e clique em "Aquecer em Grupo" para iniciar o processo de maturação.
          </p>
        </div>
      `;
      return;
    }
    
    contentDiv.innerHTML = `
      <!-- Resumo -->
      <div class="grid grid-cols-3 gap-4 mb-6">
        <div class="bg-blue-50 p-4 rounded-lg border border-blue-100 text-center">
          <p class="text-xs text-blue-600 font-bold uppercase">Chips Ativos</p>
          <p class="text-3xl font-bold text-blue-800">${stats.total_active_chips}</p>
        </div>
        <div class="bg-orange-50 p-4 rounded-lg border border-orange-100 text-center">
          <p class="text-xs text-orange-600 font-bold uppercase">Grupos</p>
          <p class="text-3xl font-bold text-orange-800">${stats.total_groups}</p>
        </div>
        <div class="bg-emerald-50 p-4 rounded-lg border border-emerald-100 text-center">
          <p class="text-xs text-emerald-600 font-bold uppercase">Msgs Hoje</p>
          <p class="text-3xl font-bold text-emerald-800">${stats.total_messages_sent}</p>
        </div>
      </div>
      
      <!-- Lista de Chips -->
      <div class="bg-white border rounded-lg overflow-hidden">
        <div class="bg-slate-50 px-4 py-2 border-b flex justify-between items-center">
          <span class="text-sm font-bold text-slate-700">Detalhes por Chip</span>
          <span class="text-xs text-slate-500">Atualizado agora</span>
        </div>
        <div class="divide-y divide-slate-100 max-h-[50vh] overflow-y-auto">
          ${stats.chips.map(chip => `
            <div class="p-4 hover:bg-slate-50 transition-colors flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="h-10 w-10 rounded-full bg-slate-200 flex items-center justify-center text-lg">
                  🤖
                </div>
                <div>
                  <p class="font-bold text-slate-800 text-sm">${chip.alias}</p>
                  <p class="text-xs text-slate-500">${chip.phone || 'Sem número'}</p>
                </div>
              </div>
              
              <div class="flex items-center gap-6">
                 <div class="text-center">
                    <p class="text-[10px] text-slate-400 uppercase">Fase</p>
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                      ${chip.phase}/5
                    </span>
                 </div>
                 
                 <div class="text-center">
                    <p class="text-[10px] text-slate-400 uppercase">Total Msgs</p>
                    <p class="text-sm font-bold text-slate-700">${chip.total_messages}</p>
                 </div>
                 
                 <div class="text-right">
                    <p class="text-[10px] text-slate-400 uppercase">Última Atividade</p>
                    <p class="text-xs text-slate-600">${chip.last_activity ? formatDate(chip.last_activity) : '-'}</p>
                 </div>
                 
                 <button onclick="openMaturationStatsModal('${chip.id}')" class="text-blue-600 hover:text-blue-800 text-xs font-medium underline">
                   Ver Detalhes
                 </button>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
    
  } catch (error) {
    console.error(error);
    contentDiv.innerHTML = '<div class="bg-red-50 p-4 rounded text-red-600 text-center">Erro ao carregar dados. Tente novamente.</div>';
  }
}

// Event Listeners
document.getElementById("open-global-stats")?.addEventListener("click", openGlobalStatsModal);
document.getElementById("global-stats-close")?.addEventListener("click", closeGlobalStatsModal);
document.getElementById("global-stats-ok")?.addEventListener("click", closeGlobalStatsModal);
document.getElementById("global-stats-backdrop")?.addEventListener("click", closeGlobalStatsModal);
document.getElementById("global-stats-refresh")?.addEventListener("click", loadGlobalStats);

