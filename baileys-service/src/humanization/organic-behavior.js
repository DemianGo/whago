"use strict";
/**
 * Organic Behavior - Simula comportamento orgânico pós-conexão
 *
 * Inclui:
 * - Leitura de mensagens não lidas
 * - Visualização de status
 * - Atualização de presença (online/offline)
 * - Ações aleatórias para parecer humano
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.organicBehaviorManager = exports.OrganicBehaviorManager = exports.OrganicBehavior = exports.DEFAULT_ORGANIC_CONFIG = void 0;
const human_timing_1 = require("./human-timing");
exports.DEFAULT_ORGANIC_CONFIG = {
    enabled: true,
    readUnreadOnConnect: true,
    maxMessagesToRead: 3,
    viewStatuses: true,
    maxStatusesToView: 2,
    updatePresence: true,
    actionIntervalMin: 300000, // 5 minutos
    actionIntervalMax: 900000, // 15 minutos
    probabilities: {
        readMessage: 0.4, // 40% de chance
        viewStatus: 0.3, // 30%
        updateProfile: 0.05, // 5%
        checkGroups: 0.25 // 25%
    }
};
/**
 * Simulador de comportamento orgânico
 */
class OrganicBehavior {
    constructor(socket, tenantId, chipId, config = {}) {
        this.isActive = false;
        this.actionInterval = null;
        // Estatísticas
        this.stats = {
            messagesRead: 0,
            statusesViewed: 0,
            actionsPerformed: 0,
            lastAction: null
        };
        this.socket = socket;
        this.tenantId = tenantId;
        this.chipId = chipId;
        this.config = { ...exports.DEFAULT_ORGANIC_CONFIG, ...config };
        this.timing = new human_timing_1.HumanTiming(tenantId, chipId);
        console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} - Inicializado ` +
            `(enabled: ${this.config.enabled})`);
    }
    /**
     * Inicia comportamento orgânico
     */
    start() {
        if (!this.config.enabled) {
            console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} - ` +
                `Comportamento orgânico desabilitado`);
            return;
        }
        if (this.isActive) {
            console.warn(`[OrganicBehavior] ${this.chipId.substring(0, 8)} - Já está ativo`);
            return;
        }
        this.isActive = true;
        console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ✅ Iniciado`);
        // Executar ações iniciais (após delay)
        this.scheduleInitialActions();
        // Agendar ações periódicas
        this.schedulePeriodicActions();
    }
    /**
     * Para comportamento orgânico
     */
    stop() {
        if (!this.isActive)
            return;
        this.isActive = false;
        if (this.actionInterval) {
            clearInterval(this.actionInterval);
            this.actionInterval = null;
        }
        console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ⏹️  Parado`);
    }
    /**
     * Agenda ações iniciais (após conectar)
     */
    async scheduleInitialActions() {
        // Aguardar 30s-2min após conectar antes de começar
        const initialDelay = 30000 + Math.floor(Math.random() * 90000); // 30s-2min
        console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
            `⏰ Aguardando ${(initialDelay / 60000).toFixed(1)}min antes das ações iniciais...`);
        setTimeout(async () => {
            if (!this.isActive)
                return;
            try {
                // Ler mensagens não lidas
                if (this.config.readUnreadOnConnect) {
                    await this.readUnreadMessages();
                }
                // Ver status
                if (this.config.viewStatuses) {
                    await this.viewRandomStatuses();
                }
            }
            catch (error) {
                console.error(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
                    `Erro nas ações iniciais:`, error);
            }
        }, initialDelay);
    }
    /**
     * Agenda ações periódicas
     */
    schedulePeriodicActions() {
        // Intervalo aleatório entre ações
        const interval = this.randomDelay(this.config.actionIntervalMin, this.config.actionIntervalMax);
        console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
            `🔄 Próxima ação em ${(interval / 60000).toFixed(1)}min`);
        this.actionInterval = setTimeout(async () => {
            if (!this.isActive)
                return;
            await this.performRandomAction();
            // Reagendar
            if (this.isActive) {
                this.schedulePeriodicActions();
            }
        }, interval);
    }
    /**
     * Executa ação aleatória baseada em probabilidades
     */
    async performRandomAction() {
        const random = Math.random();
        const probs = this.config.probabilities;
        try {
            if (random < probs.readMessage) {
                await this.readUnreadMessages();
            }
            else if (random < probs.readMessage + probs.viewStatus) {
                await this.viewRandomStatuses();
            }
            else if (random < probs.readMessage + probs.viewStatus + probs.updateProfile) {
                await this.updatePresenceRandomly();
            }
            else if (random < probs.readMessage + probs.viewStatus + probs.updateProfile + probs.checkGroups) {
                await this.checkGroups();
            }
            else {
                // Nenhuma ação (20-40% de chance de não fazer nada)
                console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
                    `💤 Nenhuma ação (comportamento idle)`);
            }
            this.stats.actionsPerformed++;
            this.stats.lastAction = new Date();
        }
        catch (error) {
            console.error(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
                `Erro ao executar ação:`, error);
        }
    }
    /**
     * Lê mensagens não lidas
     */
    async readUnreadMessages() {
        try {
            console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} 📖 Lendo mensagens não lidas...`);
            // Buscar chats (limitado - Baileys pode não suportar diretamente)
            // Esta é uma simulação - adapt baseado na API do Baileys
            // Simular leitura de 1-3 mensagens
            const messagesToRead = Math.floor(Math.random() * this.config.maxMessagesToRead) + 1;
            for (let i = 0; i < messagesToRead; i++) {
                // Delay de leitura
                await this.timing.waitForRead();
                // Aqui você precisaria buscar mensagens reais do Baileys
                // Por ora, apenas simular a ação
                console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
                    `✅ Mensagem ${i + 1}/${messagesToRead} lida`);
                this.stats.messagesRead++;
                // Delay entre mensagens
                if (i < messagesToRead - 1) {
                    await this.timing.waitBetweenActions();
                }
            }
        }
        catch (error) {
            console.warn(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
                `⚠️ Erro ao ler mensagens:`, error);
        }
    }
    /**
     * Visualiza status de contatos
     */
    async viewRandomStatuses() {
        try {
            console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} 📸 Visualizando status...`);
            const statusesToView = Math.floor(Math.random() * this.config.maxStatusesToView) + 1;
            for (let i = 0; i < statusesToView; i++) {
                // Tempo de visualização (3-8s por status)
                const viewTime = 3000 + Math.floor(Math.random() * 5000);
                console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
                    `👁️  Vendo status ${i + 1}/${statusesToView} por ${(viewTime / 1000).toFixed(1)}s...`);
                await this.timing.sleep(viewTime);
                this.stats.statusesViewed++;
                // Delay entre status
                if (i < statusesToView - 1) {
                    await this.timing.waitBetweenActions();
                }
            }
        }
        catch (error) {
            console.warn(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
                `⚠️ Erro ao ver status:`, error);
        }
    }
    /**
     * Atualiza presença (online/offline) aleatoriamente
     */
    async updatePresenceRandomly() {
        if (!this.config.updatePresence)
            return;
        try {
            // 50% online, 50% offline
            const goOnline = Math.random() < 0.5;
            if (goOnline) {
                console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} 🟢 Ficando online...`);
                await this.socket.sendPresenceUpdate('available');
                // Ficar online por 1-5 minutos
                const onlineTime = 60000 + Math.floor(Math.random() * 240000);
                console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
                    `⏱️  Online por ${(onlineTime / 60000).toFixed(1)}min`);
                await this.timing.sleep(onlineTime);
                // Voltar para unavailable
                await this.socket.sendPresenceUpdate('unavailable');
                console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ⚫ Ficando offline`);
            }
            else {
                console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
                    `⚫ Mantendo offline (comportamento discreto)`);
            }
        }
        catch (error) {
            console.warn(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
                `⚠️ Erro ao atualizar presença:`, error);
        }
    }
    /**
     * Simula verificação de grupos
     */
    async checkGroups() {
        try {
            console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} 👥 Verificando grupos...`);
            // Simular verificação de 1-3 grupos
            const groupsToCheck = Math.floor(Math.random() * 3) + 1;
            for (let i = 0; i < groupsToCheck; i++) {
                // Tempo de visualização do grupo
                const viewTime = 2000 + Math.floor(Math.random() * 5000);
                console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
                    `👁️  Vendo grupo ${i + 1}/${groupsToCheck} por ${(viewTime / 1000).toFixed(1)}s...`);
                await this.timing.sleep(viewTime);
                // Delay entre grupos
                if (i < groupsToCheck - 1) {
                    await this.timing.waitBetweenActions();
                }
            }
        }
        catch (error) {
            console.warn(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
                `⚠️ Erro ao verificar grupos:`, error);
        }
    }
    /**
     * Gera delay aleatório
     */
    randomDelay(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }
    /**
     * Retorna estatísticas
     */
    getStats() {
        return {
            ...this.stats,
            isActive: this.isActive
        };
    }
    /**
     * Atualiza configuração
     */
    updateConfig(config) {
        this.config = { ...this.config, ...config };
        console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
            `🔄 Configuração atualizada`);
    }
    /**
     * Força execução de uma ação específica
     */
    async forceAction(action) {
        console.log(`[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
            `🔧 Forçando ação: ${action}`);
        switch (action) {
            case 'read':
                await this.readUnreadMessages();
                break;
            case 'status':
                await this.viewRandomStatuses();
                break;
            case 'presence':
                await this.updatePresenceRandomly();
                break;
            case 'groups':
                await this.checkGroups();
                break;
        }
    }
}
exports.OrganicBehavior = OrganicBehavior;
/**
 * Gerenciador de comportamentos orgânicos (multi-tenant)
 */
class OrganicBehaviorManager {
    constructor() {
        this.behaviors = new Map();
    }
    /**
     * Registra comportamento para uma sessão
     */
    register(socket, tenantId, chipId, config) {
        const key = `${tenantId}:${chipId}`;
        if (this.behaviors.has(key)) {
            console.warn(`[OrganicBehaviorManager] Comportamento já existe para ${key}, substituindo`);
            this.unregister(tenantId, chipId);
        }
        const behavior = new OrganicBehavior(socket, tenantId, chipId, config);
        this.behaviors.set(key, behavior);
        console.log(`[OrganicBehaviorManager] ➕ Comportamento registrado: ${key} | ` +
            `Total: ${this.behaviors.size}`);
        return behavior;
    }
    /**
     * Remove comportamento de uma sessão
     */
    unregister(tenantId, chipId) {
        const key = `${tenantId}:${chipId}`;
        const behavior = this.behaviors.get(key);
        if (behavior) {
            behavior.stop();
            this.behaviors.delete(key);
            console.log(`[OrganicBehaviorManager] ➖ Comportamento removido: ${key} | ` +
                `Total: ${this.behaviors.size}`);
            return true;
        }
        return false;
    }
    /**
     * Obtém comportamento de uma sessão
     */
    get(tenantId, chipId) {
        const key = `${tenantId}:${chipId}`;
        return this.behaviors.get(key);
    }
    /**
     * Lista todos os comportamentos
     */
    listAll() {
        const list = [];
        for (const [key, behavior] of this.behaviors.entries()) {
            const [tenantId, chipId] = key.split(':');
            list.push({
                key,
                tenantId,
                chipId,
                stats: behavior.getStats()
            });
        }
        return list;
    }
    /**
     * Para todos os comportamentos
     */
    stopAll() {
        console.log(`[OrganicBehaviorManager] ⏹️  Parando todos os ${this.behaviors.size} comportamentos...`);
        for (const behavior of this.behaviors.values()) {
            behavior.stop();
        }
    }
    /**
     * Estatísticas globais
     */
    getGlobalStats() {
        let active = 0;
        let totalMessagesRead = 0;
        let totalStatusesViewed = 0;
        let totalActions = 0;
        for (const behavior of this.behaviors.values()) {
            const stats = behavior.getStats();
            if (stats.isActive)
                active++;
            totalMessagesRead += stats.messagesRead;
            totalStatusesViewed += stats.statusesViewed;
            totalActions += stats.actionsPerformed;
        }
        return {
            total: this.behaviors.size,
            active,
            totalMessagesRead,
            totalStatusesViewed,
            totalActions
        };
    }
}
exports.OrganicBehaviorManager = OrganicBehaviorManager;
// Singleton global
exports.organicBehaviorManager = new OrganicBehaviorManager();
exports.default = OrganicBehavior;
