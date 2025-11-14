/**
 * WHAGO Admin Panel JavaScript
 */

const API_BASE = "/api/v1";

// ============================================================================
// AUTH & SESSION
// ============================================================================
function getAdminToken() {
    return localStorage.getItem('admin_token') || localStorage.getItem('access_token');
}

function setAdminToken(token) {
    localStorage.setItem('admin_token', token);
}

function clearAdminToken() {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
}

async function adminFetch(url, options = {}) {
    const token = getAdminToken();
    
    const headers = {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers
    };
    
    try {
        const response = await fetch(`${API_BASE}${url}`, {
            ...options,
            headers
        });
        
        if (response.status === 401) {
            clearAdminToken();
            window.location.href = '/admin/login';
            return null;
        }
        
        return response;
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}

function adminLogout() {
    clearAdminToken();
    window.location.href = '/admin/login';
}

// ============================================================================
// ALERTS
// ============================================================================
function showAlert(message, type = 'info') {
    const container = document.getElementById('alertContainer');
    if (!container) return;
    
    const alertClass = type === 'error' ? 'alert-error' : type === 'success' ? 'alert-success' : 'alert-info';
    
    const alert = document.createElement('div');
    alert.className = `alert ${alertClass} active`;
    alert.textContent = message;
    
    container.innerHTML = '';
    container.appendChild(alert);
    
    setTimeout(() => {
        alert.classList.remove('active');
        setTimeout(() => alert.remove(), 300);
    }, 5000);
}

// ============================================================================
// PAGE INIT
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
    const page = document.body.getAttribute('data-page');
    
    // Handle admin login page
    if (page === 'admin-login') {
        const form = document.getElementById('adminLoginForm');
        if (form) {
            form.addEventListener('submit', handleAdminLogin);
        }
        return;
    }
    
    // Check auth for other admin pages
    if (page && page.startsWith('admin-')) {
        checkAdminAuth();
        loadAdminInfo();
    }
    
    // Set active nav link
    setActiveNavLink();
});

async function checkAdminAuth() {
    const token = getAdminToken();
    if (!token) {
        window.location.href = '/admin/login';
        return;
    }
    
    // Verify token is valid
    try {
        const response = await adminFetch('/admin/dashboard/stats');
        if (!response || !response.ok) {
            throw new Error('Invalid token');
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        clearAdminToken();
        window.location.href = '/admin/login';
    }
}

function setActiveNavLink() {
    const page = document.body.getAttribute('data-page');
    if (!page) return;
    
    document.querySelectorAll('.admin-nav-link').forEach(link => {
        if (link.getAttribute('data-page') === page) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

async function loadAdminInfo() {
    try {
        // Buscar informações do usuário atual
        const response = await adminFetch('/users/me');
        if (!response || !response.ok) {
            return;
        }
        
        const user = await response.json();
        
        // Atualizar UI
        const adminNameEl = document.getElementById('adminName');
        const adminRoleEl = document.getElementById('adminRole');
        
        if (adminNameEl) {
            adminNameEl.textContent = user.name || user.email;
        }
        
        if (adminRoleEl) {
            adminRoleEl.textContent = 'Administrador';
        }
    } catch (error) {
        console.error('Erro ao carregar info do admin:', error);
    }
}

// ============================================================================
// LOGIN
// ============================================================================
async function handleAdminLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    const btnText = document.getElementById('btnText');
    const btnLoading = document.getElementById('btnLoading');
    const submitBtn = e.target.querySelector('button[type="submit"]');
    
    btnText.style.display = 'none';
    btnLoading.classList.add('active');
    submitBtn.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Credenciais inválidas');
        }
        
        const data = await response.json();
        
        // Check if user is admin
        const checkResponse = await fetch(`${API_BASE}/admin/dashboard/stats`, {
            headers: { 'Authorization': `Bearer ${data.tokens.access_token}` }
        });
        
        if (!checkResponse.ok) {
            throw new Error('Acesso negado. Apenas administradores.');
        }
        
        setAdminToken(data.tokens.access_token);
        localStorage.setItem('refresh_token', data.tokens.refresh_token);
        
        window.location.href = '/admin/dashboard';
        
    } catch (error) {
        console.error('Login error:', error);
        showAlert(error.message || 'Erro ao fazer login', 'error');
        
        btnText.style.display = 'inline';
        btnLoading.classList.remove('active');
        submitBtn.disabled = false;
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('pt-BR');
}

function formatDateTime(dateString) {
    return new Date(dateString).toLocaleString('pt-BR');
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ============================================================================
// GATEWAYS CRUD
// ============================================================================
async function loadGateways() {
    const container = document.getElementById('gatewaysContainer');
    if (!container) return;
    
    container.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Carregando...</div>';
    
    try {
        const response = await adminFetch('/admin/gateways');
        
        if (!response || !response.ok) {
            throw new Error('Erro ao carregar gateways');
        }
        
        const gateways = await response.json();
        
        if (!gateways || gateways.length === 0) {
            container.innerHTML = '<div class="alert alert-info">Nenhum gateway configurado.</div>';
            return;
        }
        
        const gatewayInfo = {
            mercadopago: {
                name: 'Mercado Pago',
                icon: '💳',
                color: '#00a2ff',
                description: 'Gateway de pagamento da América Latina'
            },
            paypal: {
                name: 'PayPal',
                icon: '🅿️',
                color: '#003087',
                description: 'Gateway de pagamento internacional'
            },
            stripe: {
                name: 'Stripe',
                icon: '💰',
                color: '#635bff',
                description: 'Gateway de pagamento global'
            }
        };
        
        container.innerHTML = gateways.map(gw => {
            const info = gatewayInfo[gw.gateway] || { 
                name: gw.gateway, 
                icon: '🔌', 
                color: '#718096',
                description: 'Gateway de pagamento'
            };
            
            const mode = gw.is_active_mode_production ? 'Produção' : 'Sandbox';
            const modeIcon = gw.is_active_mode_production ? '💰' : '🧪';
            const modeColor = gw.is_active_mode_production ? '#dc2626' : '#f59e0b';
            
            return `
                <div class="gateway-card" style="border-left: 4px solid ${info.color};">
                    <div class="gateway-header">
                        <div>
                            <h4 style="margin: 0 0 0.5rem 0; color: ${info.color};">
                                ${info.icon} ${info.name}
                            </h4>
                            <p style="margin: 0; color: #718096; font-size: 0.9rem;">${info.description}</p>
                        </div>
                        <div style="text-align: right;">
                            <span class="badge ${gw.is_enabled ? 'badge-success' : 'badge-error'}">
                                ${gw.is_enabled ? '✅ Habilitado' : '❌ Desabilitado'}
                            </span>
                            <br>
                            <span class="badge" style="background: ${modeColor}; margin-top: 0.5rem;">
                                ${modeIcon} ${mode}
                            </span>
                        </div>
                    </div>
                    
                    <div class="gateway-details">
                        <div class="detail-item">
                            <strong>Configuração:</strong>
                            <span>${gw.sandbox_config ? '✅' : '❌'} Sandbox | ${gw.production_config ? '✅' : '❌'} Produção</span>
                        </div>
                        <div class="detail-item">
                            <strong>Última atualização:</strong>
                            <span>${formatDateTime(gw.updated_at)}</span>
                        </div>
                    </div>
                    
                    <div class="gateway-actions">
                        <button class="btn btn-primary btn-sm" onclick="openEditGatewayModal('${gw.id}')">
                            <i class="fas fa-edit"></i> Configurar
                        </button>
                    </div>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Error loading gateways:', error);
        container.innerHTML = '<div class="alert alert-error">Erro ao carregar gateways.</div>';
    }
}

async function openEditGatewayModal(gatewayId) {
    try {
        const response = await adminFetch(`/admin/gateways/${gatewayId}`);
        if (!response || !response.ok) throw new Error('Gateway não encontrado');
        
        const gateway = await response.json();
        
        const gatewayInfo = {
            mercadopago: { name: 'Mercado Pago', description: 'Configure suas credenciais do Mercado Pago' },
            paypal: { name: 'PayPal', description: 'Configure suas credenciais do PayPal' },
            stripe: { name: 'Stripe', description: 'Configure suas credenciais do Stripe' }
        };
        
        const info = gatewayInfo[gateway.gateway] || { name: gateway.gateway, description: 'Configuração do gateway' };
        
        document.getElementById('editGatewayId').value = gateway.id;
        document.getElementById('gatewayTitle').textContent = info.name;
        document.getElementById('gatewayDescription').textContent = info.description;
        document.getElementById('editGatewayEnabled').checked = gateway.is_enabled;
        document.getElementById('editGatewayMode').value = gateway.is_active_mode_production.toString();
        
        // Sandbox credentials
        const sandboxConfig = gateway.sandbox_config || {};
        document.getElementById('sandboxAccessToken').value = sandboxConfig.access_token || '';
        document.getElementById('sandboxPublicKey').value = sandboxConfig.public_key || '';
        document.getElementById('sandboxWebhookSecret').value = sandboxConfig.webhook_secret || '';
        
        // Production credentials
        const productionConfig = gateway.production_config || {};
        document.getElementById('productionAccessToken').value = productionConfig.access_token || '';
        document.getElementById('productionPublicKey').value = productionConfig.public_key || '';
        document.getElementById('productionWebhookSecret').value = productionConfig.webhook_secret || '';
        
        document.getElementById('editGatewayModal').classList.add('active');
        
    } catch (error) {
        console.error('Error loading gateway:', error);
        showAlert('Erro ao carregar gateway', 'error');
    }
}

function closeEditGatewayModal() {
    document.getElementById('editGatewayModal').classList.remove('active');
    document.getElementById('editGatewayForm').reset();
}

async function handleEditGatewaySubmit(e) {
    e.preventDefault();
    
    const gatewayId = document.getElementById('editGatewayId').value;
    
    const sandboxConfig = {
        access_token: document.getElementById('sandboxAccessToken').value.trim() || null,
        public_key: document.getElementById('sandboxPublicKey').value.trim() || null,
        webhook_secret: document.getElementById('sandboxWebhookSecret').value.trim() || null
    };
    
    const productionConfig = {
        access_token: document.getElementById('productionAccessToken').value.trim() || null,
        public_key: document.getElementById('productionPublicKey').value.trim() || null,
        webhook_secret: document.getElementById('productionWebhookSecret').value.trim() || null
    };
    
    const data = {
        is_enabled: document.getElementById('editGatewayEnabled').checked,
        is_active_mode_production: document.getElementById('editGatewayMode').value === 'true',
        sandbox_config: Object.values(sandboxConfig).some(v => v) ? sandboxConfig : null,
        production_config: Object.values(productionConfig).some(v => v) ? productionConfig : null
    };
    
    try {
        const response = await adminFetch(`/admin/gateways/${gatewayId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        
        if (!response || !response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao atualizar gateway');
        }
        
        showAlert('Gateway atualizado com sucesso!', 'success');
        closeEditGatewayModal();
        loadGateways();
        
    } catch (error) {
        console.error('Error updating gateway:', error);
        showAlert(error.message || 'Erro ao atualizar gateway', 'error');
    }
}

// Initialize gateway form handler
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('editGatewayForm');
    if (form) {
        form.addEventListener('submit', handleEditGatewaySubmit);
    }
});

// Export for use in templates
window.adminFetch = adminFetch;
window.adminLogout = adminLogout;
window.showAlert = showAlert;
window.formatCurrency = formatCurrency;
window.formatDate = formatDate;
window.formatDateTime = formatDateTime;
window.loadGateways = loadGateways;
window.openEditGatewayModal = openEditGatewayModal;
window.closeEditGatewayModal = closeEditGatewayModal;

