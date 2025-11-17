"use strict";
/**
 * Session Lifecycle - Gerencia ciclo de vida da sessão com comportamento humano
 *
 * Inclui:
 * - KeepAlive variável
 * - Reconnect com delays humanizados
 * - Estratégias de retry exponencial + jitter
 * - Monitoramento de saúde da conexão
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.sessionLifecycleManager = exports.SessionLifecycleManager = exports.SessionLifecycle = exports.DEFAULT_LIFECYCLE_CONFIG = void 0;
exports.DEFAULT_LIFECYCLE_CONFIG = {
    keepAliveMin: 90000, // 90s
    keepAliveMax: 150000, // 150s (2.5min)
    enableAutoReconnect: true,
    reconnectDelayMin: 30000, // 30s
    reconnectDelayMax: 120000, // 2min
    maxReconnectAttempts: 5,
    retryStrategy: 'exponential',
    baseRetryDelay: 2000, // 2s
    maxRetryDelay: 60000, // 1min
    jitterPercent: 0.3, // 30%
    healthCheckInterval: 300000, // 5min
    maxConsecutiveErrors: 3
};
/**
 * Gerenciador de ciclo de vida da sessão
 */
class SessionLifecycle {
    constructor(socket, tenantId, chipId, config = {}) {
        // Estado
        this.connectionState = 'close';
        this.isActive = false;
        this.reconnectAttempts = 0;
        this.reconnectTimeout = null;
        // Saúde
        this.health = {
            isHealthy: true,
            consecutiveErrors: 0,
            lastError: null,
            lastSuccess: null,
            uptime: 0,
            reconnectCount: 0
        };
        this.connectedAt = null;
        this.healthCheckInterval = null;
        this.socket = socket;
        this.tenantId = tenantId;
        this.chipId = chipId;
        this.config = { ...exports.DEFAULT_LIFECYCLE_CONFIG, ...config };
        console.log(`[SessionLifecycle] ${this.chipId.substring(0, 8)} - Inicializado`);
    }
    /**
     * Inicia monitoramento do ciclo de vida
     */
    start() {
        if (this.isActive) {
            console.warn(`[SessionLifecycle] ${this.chipId.substring(0, 8)} - Já está ativo`);
            return;
        }
        this.isActive = true;
        this.connectedAt = new Date();
        console.log(`[SessionLifecycle] ${this.chipId.substring(0, 8)} ✅ Iniciado`);
        // Iniciar health check
        this.startHealthCheck();
    }
    /**
     * Para monitoramento
     */
    stop() {
        if (!this.isActive)
            return;
        this.isActive = false;
        // Cancelar reconnect pendente
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }
        // Parar health check
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = null;
        }
        console.log(`[SessionLifecycle] ${this.chipId.substring(0, 8)} ⏹️  Parado`);
    }
    /**
     * Gera keepAlive aleatório
     */
    generateKeepAlive() {
        const min = this.config.keepAliveMin;
        const max = this.config.keepAliveMax;
        const keepAlive = Math.floor(Math.random() * (max - min + 1)) + min;
        console.log(`[SessionLifecycle] ${this.chipId.substring(0, 8)} ` +
            `💓 KeepAlive: ${(keepAlive / 1000).toFixed(1)}s`);
        return keepAlive;
    }
    /**
     * Calcula delay de retry com estratégia configurada
     */
    calculateRetryDelay(attempt) {
        let delay;
        switch (this.config.retryStrategy) {
            case 'linear':
                delay = this.config.baseRetryDelay * attempt;
                break;
            case 'exponential':
                delay = this.config.baseRetryDelay * Math.pow(2, attempt - 1);
                break;
            case 'fibonacci':
                delay = this.config.baseRetryDelay * this.fibonacci(attempt);
                break;
            default:
                delay = this.config.baseRetryDelay;
        }
        // Aplicar limite máximo
        delay = Math.min(delay, this.config.maxRetryDelay);
        // Aplicar jitter
        const jitter = delay * this.config.jitterPercent * (Math.random() * 2 - 1);
        delay = Math.max(0, Math.round(delay + jitter));
        return delay;
    }
    /**
     * Calcula número de Fibonacci
     */
    fibonacci(n) {
        if (n <= 1)
            return 1;
        if (n === 2)
            return 2;
        let prev = 1, curr = 2;
        for (let i = 3; i <= n; i++) {
            const next = prev + curr;
            prev = curr;
            curr = next;
        }
        return curr;
    }
    /**
     * Registra conexão bem-sucedida
     */
    onConnectionSuccess() {
        this.health.consecutiveErrors = 0;
        this.health.lastSuccess = new Date();
        this.health.isHealthy = true;
        this.reconnectAttempts = 0;
        this.connectedAt = new Date();
        console.log(`[SessionLifecycle] ${this.chipId.substring(0, 8)} ` +
            `✅ Conexão bem-sucedida`);
    }
    /**
     * Registra erro de conexão
     */
    onConnectionError(errorCode) {
        this.health.consecutiveErrors++;
        this.health.lastError = new Date();
        if (this.health.consecutiveErrors >= this.config.maxConsecutiveErrors) {
            this.health.isHealthy = false;
            console.error(`[SessionLifecycle] ${this.chipId.substring(0, 8)} ` +
                `🚨 Conexão não-saudável (${this.health.consecutiveErrors} erros consecutivos)`);
        }
        console.error(`[SessionLifecycle] ${this.chipId.substring(0, 8)} ` +
            `❌ Erro de conexão (código: ${errorCode || 'unknown'})`);
    }
    /**
     * Agenda reconnect com delay humanizado
     */
    scheduleReconnect(reconnectFn, errorCode) {
        if (!this.config.enableAutoReconnect) {
            console.log(`[SessionLifecycle] ${this.chipId.substring(0, 8)} ` +
                `⚠️ Auto-reconnect desabilitado`);
            return;
        }
        if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
            console.error(`[SessionLifecycle] ${this.chipId.substring(0, 8)} ` +
                `🛑 Limite de tentativas atingido (${this.reconnectAttempts}/${this.config.maxReconnectAttempts})`);
            this.health.isHealthy = false;
            return;
        }
        this.reconnectAttempts++;
        // Calcular delay
        let delay;
        // Se erro 405 ou 429, usar delay longo
        if (errorCode === 405 || errorCode === 429) {
            delay = 300000 + Math.floor(Math.random() * 300000); // 5-10min
            console.warn(`[SessionLifecycle] ${this.chipId.substring(0, 8)} ` +
                `⚠️ Erro ${errorCode} - Aguardando ${(delay / 60000).toFixed(1)}min antes de reconectar`);
        }
        else {
            // Delay normal com retry strategy
            delay = this.calculateRetryDelay(this.reconnectAttempts);
            // Adicionar delay aleatório extra (humanização)
            const extraDelay = Math.floor(Math.random() * (this.config.reconnectDelayMax - this.config.reconnectDelayMin)) + this.config.reconnectDelayMin;
            delay += extraDelay;
        }
        console.log(`[SessionLifecycle] ${this.chipId.substring(0, 8)} ` +
            `🔄 Tentativa ${this.reconnectAttempts}/${this.config.maxReconnectAttempts} ` +
            `em ${(delay / 1000).toFixed(1)}s...`);
        this.reconnectTimeout = setTimeout(async () => {
            if (!this.isActive)
                return;
            try {
                console.log(`[SessionLifecycle] ${this.chipId.substring(0, 8)} ` +
                    `🔌 Reconnectando...`);
                await reconnectFn();
                this.health.reconnectCount++;
            }
            catch (error) {
                console.error(`[SessionLifecycle] ${this.chipId.substring(0, 8)} ` +
                    `❌ Erro ao reconectar:`, error);
                // Tentar novamente
                this.onConnectionError();
                this.scheduleReconnect(reconnectFn);
            }
        }, delay);
    }
    /**
     * Cancela reconnect agendado
     */
    cancelReconnect() {
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
            console.log(`[SessionLifecycle] ${this.chipId.substring(0, 8)} ` +
                `⏹️  Reconnect cancelado`);
        }
    }
    /**
     * Inicia health check periódico
     */
    startHealthCheck() {
        this.healthCheckInterval = setInterval(() => {
            if (!this.isActive)
                return;
            // Calcular uptime
            if (this.connectedAt) {
                this.health.uptime = Date.now() - this.connectedAt.getTime();
            }
            // Log de saúde
            const uptimeMin = (this.health.uptime / 60000).toFixed(1);
            console.log(`[SessionLifecycle] ${this.chipId.substring(0, 8)} ` +
                `💊 Health Check | Uptime: ${uptimeMin}min | ` +
                `Erros: ${this.health.consecutiveErrors} | ` +
                `Reconnects: ${this.health.reconnectCount} | ` +
                `Status: ${this.health.isHealthy ? '✅ Saudável' : '⚠️ Não-saudável'}`);
        }, this.config.healthCheckInterval);
    }
    /**
     * Retorna saúde da conexão
     */
    getHealth() {
        // Atualizar uptime
        if (this.connectedAt) {
            this.health.uptime = Date.now() - this.connectedAt.getTime();
        }
        return { ...this.health };
    }
    /**
     * Reseta saúde (após recovery)
     */
    resetHealth() {
        this.health = {
            isHealthy: true,
            consecutiveErrors: 0,
            lastError: null,
            lastSuccess: new Date(),
            uptime: 0,
            reconnectCount: 0
        };
        this.reconnectAttempts = 0;
        this.connectedAt = new Date();
        console.log(`[SessionLifecycle] ${this.chipId.substring(0, 8)} ` +
            `🔄 Saúde resetada`);
    }
    /**
     * Atualiza configuração
     */
    updateConfig(config) {
        this.config = { ...this.config, ...config };
        console.log(`[SessionLifecycle] ${this.chipId.substring(0, 8)} ` +
            `🔄 Configuração atualizada`);
    }
    /**
     * Retorna estatísticas
     */
    getStats() {
        return {
            isActive: this.isActive,
            reconnectAttempts: this.reconnectAttempts,
            health: this.getHealth(),
            config: this.config
        };
    }
}
exports.SessionLifecycle = SessionLifecycle;
/**
 * Gerenciador de lifecycles (multi-tenant)
 */
class SessionLifecycleManager {
    constructor() {
        this.lifecycles = new Map();
    }
    /**
     * Registra lifecycle para uma sessão
     */
    register(socket, tenantId, chipId, config) {
        const key = `${tenantId}:${chipId}`;
        if (this.lifecycles.has(key)) {
            console.warn(`[SessionLifecycleManager] Lifecycle já existe para ${key}, substituindo`);
            this.unregister(tenantId, chipId);
        }
        const lifecycle = new SessionLifecycle(socket, tenantId, chipId, config);
        this.lifecycles.set(key, lifecycle);
        console.log(`[SessionLifecycleManager] ➕ Lifecycle registrado: ${key} | ` +
            `Total: ${this.lifecycles.size}`);
        return lifecycle;
    }
    /**
     * Remove lifecycle de uma sessão
     */
    unregister(tenantId, chipId) {
        const key = `${tenantId}:${chipId}`;
        const lifecycle = this.lifecycles.get(key);
        if (lifecycle) {
            lifecycle.stop();
            this.lifecycles.delete(key);
            console.log(`[SessionLifecycleManager] ➖ Lifecycle removido: ${key} | ` +
                `Total: ${this.lifecycles.size}`);
            return true;
        }
        return false;
    }
    /**
     * Obtém lifecycle de uma sessão
     */
    get(tenantId, chipId) {
        const key = `${tenantId}:${chipId}`;
        return this.lifecycles.get(key);
    }
    /**
     * Lista todos os lifecycles
     */
    listAll() {
        const list = [];
        for (const [key, lifecycle] of this.lifecycles.entries()) {
            const [tenantId, chipId] = key.split(':');
            list.push({
                key,
                tenantId,
                chipId,
                stats: lifecycle.getStats()
            });
        }
        return list;
    }
    /**
     * Estatísticas globais
     */
    getGlobalStats() {
        let active = 0;
        let healthy = 0;
        let totalReconnects = 0;
        let totalUptime = 0;
        for (const lifecycle of this.lifecycles.values()) {
            const stats = lifecycle.getStats();
            if (stats.isActive)
                active++;
            if (stats.health.isHealthy)
                healthy++;
            totalReconnects += stats.health.reconnectCount;
            totalUptime += stats.health.uptime;
        }
        const avgUptime = this.lifecycles.size > 0
            ? totalUptime / this.lifecycles.size
            : 0;
        return {
            total: this.lifecycles.size,
            active,
            healthy,
            totalReconnects,
            avgUptime
        };
    }
}
exports.SessionLifecycleManager = SessionLifecycleManager;
// Singleton global
exports.sessionLifecycleManager = new SessionLifecycleManager();
exports.default = SessionLifecycle;
