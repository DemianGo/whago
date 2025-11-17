// Admin Proxies Management

let providers = [];
let proxies = [];

// Tab switching
function switchTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(content => content.classList.add('hidden'));
  
  document.getElementById(`tab-${tab}`).classList.add('active');
  document.getElementById(`content-${tab}`).classList.remove('hidden');
  
  if (tab === 'providers') loadProviders();
  else if (tab === 'pool') loadProxies();
  else if (tab === 'stats') loadStats();
}

// ========== PROVIDERS ==========

async function loadProviders() {
  try {
    const response = await adminFetch('/admin/proxies/providers');
    providers = response;
    
    const tbody = document.getElementById('providers-table');
    if (providers.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4">Nenhum provedor cadastrado</td></tr>';
      return;
    }
    
    tbody.innerHTML = providers.map(p => `
      <tr>
        <td class="font-medium">${p.name}</td>
        <td><span class="badge badge-blue">${p.provider_type}</span></td>
        <td>${p.region}</td>
        <td>R$ ${parseFloat(p.cost_per_gb).toFixed(2)}</td>
        <td>
          <span class="badge ${p.is_active ? 'badge-green' : 'badge-gray'}">
            ${p.is_active ? 'Ativo' : 'Inativo'}
          </span>
        </td>
        <td>
          <button onclick="testProvider('${p.id}')" class="btn-sm btn-secondary" title="Testar">🔌</button>
          <button onclick="editProvider('${p.id}')" class="btn-sm btn-secondary">Editar</button>
          <button onclick="deleteProvider('${p.id}')" class="btn-sm btn-danger">Excluir</button>
        </td>
      </tr>
    `).join('');
  } catch (error) {
    showAlert('Erro ao carregar provedores: ' + error.message, 'error');
  }
}

function openProviderModal(providerId = null) {
  const modal = document.getElementById('providerModal');
  const form = document.getElementById('providerForm');
  form.reset();
  
  if (providerId) {
    const provider = providers.find(p => p.id === providerId);
    document.getElementById('providerModalTitle').textContent = 'Editar Provedor';
    document.getElementById('provider_id').value = provider.id;
    document.getElementById('provider_name').value = provider.name;
    document.getElementById('provider_type').value = provider.provider_type;
    document.getElementById('provider_region').value = provider.region;
    document.getElementById('provider_cost').value = parseFloat(provider.cost_per_gb);
    document.getElementById('provider_active').checked = provider.is_active;
    
    // Credenciais
    document.getElementById('cred_server').value = provider.credentials.server || '';
    document.getElementById('cred_port').value = provider.credentials.port || '';
    document.getElementById('cred_username').value = provider.credentials.username || '';
    document.getElementById('cred_password').value = provider.credentials.password || '';
    document.getElementById('cred_api_key').value = provider.credentials.api_key || '';
  } else {
    document.getElementById('providerModalTitle').textContent = 'Novo Provedor';
    document.getElementById('provider_cost').value = '25.00';
    document.getElementById('cred_port').value = '3120';
  }
  
  modal.style.display = 'flex';
}

function closeProviderModal() {
  document.getElementById('providerModal').style.display = 'none';
}

async function handleProviderSubmit(event) {
  event.preventDefault();
  
  const providerId = document.getElementById('provider_id').value;
  const data = {
    name: document.getElementById('provider_name').value,
    provider_type: document.getElementById('provider_type').value,
    region: document.getElementById('provider_region').value,
    cost_per_gb: parseFloat(document.getElementById('provider_cost').value),
    is_active: document.getElementById('provider_active').checked,
    credentials: {
      server: document.getElementById('cred_server').value,
      port: parseInt(document.getElementById('cred_port').value),
      username: document.getElementById('cred_username').value,
      password: document.getElementById('cred_password').value,
      api_key: document.getElementById('cred_api_key').value || null,
    }
  };
  
  try {
    if (providerId) {
      await adminFetch(`/admin/proxies/providers/${providerId}`, {
        method: 'PUT',
        body: JSON.stringify(data)
      });
      showAlert('Provedor atualizado!', 'success');
    } else {
      await adminFetch('/admin/proxies/providers', {
        method: 'POST',
        body: JSON.stringify(data)
      });
      showAlert('Provedor criado!', 'success');
    }
    
    closeProviderModal();
    loadProviders();
  } catch (error) {
    showAlert('Erro: ' + error.message, 'error');
  }
}

function editProvider(id) {
  openProviderModal(id);
}

async function deleteProvider(id) {
  if (!confirm('Tem certeza que deseja excluir este provedor?')) return;
  
  try {
    await adminFetch(`/admin/proxies/providers/${id}`, { method: 'DELETE' });
    showAlert('Provedor excluído!', 'success');
    loadProviders();
  } catch (error) {
    showAlert('Erro: ' + error.message, 'error');
  }
}

async function testProvider(id) {
  try {
    showAlert('Testando conexão...', 'info');
    const result = await adminFetch(`/admin/proxies/providers/${id}/test`, { method: 'POST' });
    
    if (result.success) {
      showAlert(`✅ Conexão OK! IP: ${result.ip}`, 'success');
    } else {
      showAlert(`❌ Falha: ${result.message}`, 'error');
    }
  } catch (error) {
    showAlert('Erro ao testar: ' + error.message, 'error');
  }
}

// ========== PROXIES ==========

async function loadProxies() {
  try {
    const response = await adminFetch('/admin/proxies/pool');
    proxies = response;
    
    const tbody = document.getElementById('proxies-table');
    if (proxies.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4">Nenhum proxy no pool</td></tr>';
      return;
    }
    
    tbody.innerHTML = proxies.map(p => `
      <tr>
        <td>${getProviderName(p.provider_id)}</td>
        <td><span class="badge badge-blue">${p.proxy_type}</span></td>
        <td>${p.region}</td>
        <td>
          <div class="flex items-center gap-2">
            <span>${p.health_score}</span>
            <div class="w-16 bg-gray-200 rounded-full h-2">
              <div class="bg-${p.health_score > 70 ? 'green' : p.health_score > 30 ? 'yellow' : 'red'}-500 h-2 rounded-full" style="width: ${p.health_score}%"></div>
            </div>
          </div>
        </td>
        <td>${(p.total_bytes_used / (1024**3)).toFixed(3)}</td>
        <td>
          <span class="badge ${p.is_active ? 'badge-green' : 'badge-gray'}">
            ${p.is_active ? 'Ativo' : 'Inativo'}
          </span>
        </td>
        <td>
          <button onclick="deleteProxy('${p.id}')" class="btn-sm btn-danger">Excluir</button>
        </td>
      </tr>
    `).join('');
  } catch (error) {
    showAlert('Erro ao carregar proxies: ' + error.message, 'error');
  }
}

function getProviderName(providerId) {
  const provider = providers.find(p => p.id === providerId);
  return provider ? provider.name : 'Desconhecido';
}

async function deleteProxy(id) {
  if (!confirm('Tem certeza que deseja remover este proxy?')) return;
  
  try {
    await adminFetch(`/admin/proxies/pool/${id}`, { method: 'DELETE' });
    showAlert('Proxy removido!', 'success');
    loadProxies();
  } catch (error) {
    showAlert('Erro: ' + error.message, 'error');
  }
}

// ========== STATS ==========

async function loadStats() {
  try {
    const stats = await adminFetch('/admin/proxies/stats/dashboard');
    
    document.getElementById('stats-today').textContent = `${stats.gb_today.toFixed(2)} GB`;
    document.getElementById('stats-month-gb').textContent = `${stats.gb_month.toFixed(2)}`;
    document.getElementById('stats-cost').textContent = `R$ ${stats.cost_month.toFixed(2)}`;
    document.getElementById('stats-proxies').textContent = `${stats.proxies_active}/${stats.proxies_active + stats.proxies_inactive}`;
    
    const topUsersTable = document.getElementById('top-users-table');
    if (stats.top_users.length === 0) {
      topUsersTable.innerHTML = '<tr><td colspan="3" class="text-center py-4">Sem dados</td></tr>';
    } else {
      topUsersTable.innerHTML = stats.top_users.map(u => `
        <tr>
          <td><code>${u.user_id.substring(0, 8)}...</code></td>
          <td>${u.gb.toFixed(3)} GB</td>
          <td>R$ ${u.cost.toFixed(2)}</td>
        </tr>
      `).join('');
    }
  } catch (error) {
    showAlert('Erro ao carregar estatísticas: ' + error.message, 'error');
  }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  loadProviders();
});

