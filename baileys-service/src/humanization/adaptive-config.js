"use strict";
/**
 * Adaptive Config - Ajusta configurações automaticamente baseado em resultados
 *
 * Aprende com sucessos/falhas e adapta:
 * - Delays de criação
 * - Perfis de timing
 * - Padrões de atividade
 * - Estratégias de retry
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.adaptiveConfigManager = exports.AdaptiveConfigManager = exports.AdaptiveConfig = void 0;
const DEFAULT_STRATEGY = {
    thresholds: {
        minSuccessRate: 0.8,
        max405Count: 3,
        max429Count: 5,
        minUptime: 300000 // 5min
    },
    currentConfig: {
        creationDelayMin: 180000, // 3min
        creationDelayMax: 300000, // 5min
        timingProfile: 'normal',
        activityPattern: 'balanced',
        retryStrategy: 'exponential'
    },
    adjustmentHistory: []
};
/**
 * Configurador adaptativo
 */
class AdaptiveConfig {
    constructor(tenantId, strategy) {
        // Contadores de eventos
        this.eventCounts = {
            totalAttempts: 0,
            successfulConnections: 0,
            error405: 0,
            error429: 0,
            reconnects: 0
        };
        this.uptimes = [];
        this.tenantId = tenantId;
        this.strategy = {
            ...DEFAULT_STRATEGY,
            ...strategy,
            currentConfig: { ...DEFAULT_STRATEGY.currentConfig, ...strategy?.currentConfig },
            thresholds: { ...DEFAULT_STRATEGY.thresholds, ...strategy?.thresholds }
        };
        this.metrics = {
            successRate: 1.0,
            error405Count: 0,
            error429Count: 0,
            averageUptime: 0,
            reconnectRate: 0,
            lastAdjustment: null
        };
        console.log(`[AdaptiveConfig] Tenant ${tenantId} - Inicializado`);
    }
    /**
     * Registra tentativa de conexão
     */
    recordAttempt(success, errorCode, uptime) {
        this.eventCounts.totalAttempts++;
        if (success) {
            this.eventCounts.successfulConnections++;
            if (uptime) {
                this.uptimes.push(uptime);
                // Manter últimos 100 uptimes
                if (this.uptimes.length > 100) {
                    this.uptimes.shift();
                }
            }
        }
        else {
            if (errorCode === 405) {
                this.eventCounts.error405++;
            }
            else if (errorCode === 429) {
                this.eventCounts.error429++;
            }
        }
        // Atualizar métricas
        this.updateMetrics();
        // Verificar se precisa ajustar
        this.checkAndAdjust();
    }
    /**
     * Registra reconnect
     */
    recordReconnect() {
        this.eventCounts.reconnects++;
        this.updateMetrics();
    }
    /**
     * Atualiza métricas calculadas
     */
    updateMetrics() {
        const total = this.eventCounts.totalAttempts;
        if (total > 0) {
            this.metrics.successRate = this.eventCounts.successfulConnections / total;
            this.metrics.reconnectRate = this.eventCounts.reconnects / total;
        }
        this.metrics.error405Count = this.eventCounts.error405;
        this.metrics.error429Count = this.eventCounts.error429;
        if (this.uptimes.length > 0) {
            this.metrics.averageUptime = this.uptimes.reduce((a, b) => a + b, 0) / this.uptimes.length;
        }
    }
    /**
     * Verifica métricas e ajusta se necessário
     */
    checkAndAdjust() {
        // Não ajustar se não houver dados suficientes
        if (this.eventCounts.totalAttempts < 5)
            return;
        // Não ajustar com muita frequência (mínimo 1h entre ajustes)
        if (this.metrics.lastAdjustment) {
            const timeSinceLastAdjust = Date.now() - this.metrics.lastAdjustment.getTime();
            if (timeSinceLastAdjust < 3600000) { // 1 hora
                return;
            }
        }
        const problems = [];
        const adjustments = [];
        // ===== VERIFICAR PROBLEMAS =====
        // Problema 1: Taxa de sucesso baixa
        if (this.metrics.successRate < this.strategy.thresholds.minSuccessRate) {
            problems.push(`Taxa de sucesso baixa (${(this.metrics.successRate * 100).toFixed(1)}%)`);
            // Aumentar delays
            const newMin = Math.min(this.strategy.currentConfig.creationDelayMin * 1.5, 600000);
            const newMax = Math.min(this.strategy.currentConfig.creationDelayMax * 1.5, 900000);
            adjustments.push({
                parameter: 'creationDelayMin',
                oldValue: this.strategy.currentConfig.creationDelayMin,
                newValue: newMin
            });
            adjustments.push({
                parameter: 'creationDelayMax',
                oldValue: this.strategy.currentConfig.creationDelayMax,
                newValue: newMax
            });
            this.strategy.currentConfig.creationDelayMin = newMin;
            this.strategy.currentConfig.creationDelayMax = newMax;
        }
        // Problema 2: Muitos erros 405
        if (this.metrics.error405Count >= this.strategy.thresholds.max405Count) {
            problems.push(`Muitos erros 405 (${this.metrics.error405Count})`);
            // Trocar para perfil mais lento
            if (this.strategy.currentConfig.timingProfile !== 'slow') {
                adjustments.push({
                    parameter: 'timingProfile',
                    oldValue: this.strategy.currentConfig.timingProfile,
                    newValue: 'slow'
                });
                this.strategy.currentConfig.timingProfile = 'slow';
            }
            // Trocar para padrão mais discreto
            if (this.strategy.currentConfig.activityPattern !== 'casual') {
                adjustments.push({
                    parameter: 'activityPattern',
                    oldValue: this.strategy.currentConfig.activityPattern,
                    newValue: 'casual'
                });
                this.strategy.currentConfig.activityPattern = 'casual';
            }
            // Aumentar delays significativamente
            const newMin = Math.min(this.strategy.currentConfig.creationDelayMin * 2, 900000);
            const newMax = Math.min(this.strategy.currentConfig.creationDelayMax * 2, 1200000);
            adjustments.push({
                parameter: 'creationDelayMin',
                oldValue: this.strategy.currentConfig.creationDelayMin,
                newValue: newMin
            });
            adjustments.push({
                parameter: 'creationDelayMax',
                oldValue: this.strategy.currentConfig.creationDelayMax,
                newValue: newMax
            });
            this.strategy.currentConfig.creationDelayMin = newMin;
            this.strategy.currentConfig.creationDelayMax = newMax;
        }
        // Problema 3: Muitos erros 429 (rate limit)
        if (this.metrics.error429Count >= this.strategy.thresholds.max429Count) {
            problems.push(`Muitos erros 429 (${this.metrics.error429Count})`);
            // Trocar para retry fibonacci (mais lento)
            if (this.strategy.currentConfig.retryStrategy !== 'fibonacci') {
                adjustments.push({
                    parameter: 'retryStrategy',
                    oldValue: this.strategy.currentConfig.retryStrategy,
                    newValue: 'fibonacci'
                });
                this.strategy.currentConfig.retryStrategy = 'fibonacci';
            }
        }
        // Problema 4: Uptime muito baixo
        if (this.metrics.averageUptime > 0 && this.metrics.averageUptime < this.strategy.thresholds.minUptime) {
            problems.push(`Uptime médio muito baixo (${(this.metrics.averageUptime / 60000).toFixed(1)}min)`);
            // Aumentar estabilidade (delays maiores)
            const newMin = Math.min(this.strategy.currentConfig.creationDelayMin * 1.3, 600000);
            const newMax = Math.min(this.strategy.currentConfig.creationDelayMax * 1.3, 900000);
            adjustments.push({
                parameter: 'creationDelayMin',
                oldValue: this.strategy.currentConfig.creationDelayMin,
                newValue: newMin
            });
            adjustments.push({
                parameter: 'creationDelayMax',
                oldValue: this.strategy.currentConfig.creationDelayMax,
                newValue: newMax
            });
            this.strategy.currentConfig.creationDelayMin = newMin;
            this.strategy.currentConfig.creationDelayMax = newMax;
        }
        // ===== APLICAR AJUSTES =====
        if (adjustments.length > 0) {
            const adjustment = {
                timestamp: new Date(),
                reason: problems.join('; '),
                changes: adjustments,
                expectedImpact: this.estimateImpact(adjustments)
            };
            this.strategy.adjustmentHistory.push(adjustment);
            this.metrics.lastAdjustment = new Date();
            console.log(`[AdaptiveConfig] Tenant ${this.tenantId} - 🔧 AJUSTE AUTOMÁTICO\n` +
                `  Motivo: ${adjustment.reason}\n` +
                `  Mudanças: ${adjustments.map(a => `${a.parameter}: ${a.oldValue} → ${a.newValue}`).join(', ')}\n` +
                `  Impacto esperado: ${adjustment.expectedImpact}`);
            // Resetar contadores de erros após ajuste
            this.eventCounts.error405 = 0;
            this.eventCounts.error429 = 0;
        }
    }
    /**
     * Estima impacto do ajuste
     */
    estimateImpact(changes) {
        const impacts = [];
        for (const change of changes) {
            switch (change.parameter) {
                case 'creationDelayMin':
                case 'creationDelayMax':
                    const increase = ((change.newValue - change.oldValue) / change.oldValue) * 100;
                    impacts.push(`Delays ${increase > 0 ? '+' : ''}${increase.toFixed(0)}%`);
                    break;
                case 'timingProfile':
                    impacts.push(`Perfil mais ${change.newValue === 'slow' ? 'lento' : 'rápido'}`);
                    break;
                case 'activityPattern':
                    impacts.push(`Padrão mais ${change.newValue === 'casual' ? 'discreto' : 'ativo'}`);
                    break;
                case 'retryStrategy':
                    impacts.push(`Retry mais ${change.newValue === 'fibonacci' ? 'gradual' : 'rápido'}`);
                    break;
            }
        }
        return impacts.join(', ');
    }
    /**
     * Retorna configuração atual
     */
    getCurrentConfig() {
        return { ...this.strategy.currentConfig };
    }
    /**
     * Retorna métricas atuais
     */
    getMetrics() {
        return { ...this.metrics };
    }
    /**
     * Retorna histórico de ajustes
     */
    getAdjustmentHistory() {
        return [...this.strategy.adjustmentHistory];
    }
    /**
     * Força um ajuste manual
     */
    forceAdjustment(changes, reason) {
        const adjustmentChanges = [];
        for (const [key, newValue] of Object.entries(changes)) {
            const oldValue = this.strategy.currentConfig[key];
            if (oldValue !== newValue) {
                adjustmentChanges.push({
                    parameter: key,
                    oldValue,
                    newValue
                });
                this.strategy.currentConfig[key] = newValue;
            }
        }
        if (adjustmentChanges.length > 0) {
            const adjustment = {
                timestamp: new Date(),
                reason: `[MANUAL] ${reason}`,
                changes: adjustmentChanges,
                expectedImpact: 'Ajuste manual'
            };
            this.strategy.adjustmentHistory.push(adjustment);
            this.metrics.lastAdjustment = new Date();
            console.log(`[AdaptiveConfig] Tenant ${this.tenantId} - 🔧 AJUSTE MANUAL\n` +
                `  Motivo: ${adjustment.reason}\n` +
                `  Mudanças: ${adjustmentChanges.map(a => `${a.parameter}: ${a.oldValue} → ${a.newValue}`).join(', ')}`);
        }
    }
    /**
     * Reseta para configuração padrão
     */
    reset() {
        this.strategy.currentConfig = { ...DEFAULT_STRATEGY.currentConfig };
        this.eventCounts = {
            totalAttempts: 0,
            successfulConnections: 0,
            error405: 0,
            error429: 0,
            reconnects: 0
        };
        this.uptimes = [];
        this.updateMetrics();
        console.log(`[AdaptiveConfig] Tenant ${this.tenantId} - 🔄 Resetado para padrão`);
    }
    /**
     * Gera relatório
     */
    generateReport() {
        let report = '\n';
        report += '╔══════════════════════════════════════════════════════════╗\n';
        report += '║        ADAPTIVE CONFIG - RELATÓRIO DE ESTRATÉGIA         ║\n';
        report += '╚══════════════════════════════════════════════════════════╝\n\n';
        report += `🎯 Tenant: ${this.tenantId}\n\n`;
        // Métricas
        report += `📊 Métricas Atuais:\n`;
        report += `  Taxa de sucesso: ${(this.metrics.successRate * 100).toFixed(1)}%\n`;
        report += `  Erros 405: ${this.metrics.error405Count}\n`;
        report += `  Erros 429: ${this.metrics.error429Count}\n`;
        report += `  Uptime médio: ${(this.metrics.averageUptime / 60000).toFixed(1)}min\n`;
        report += `  Taxa de reconnect: ${(this.metrics.reconnectRate * 100).toFixed(1)}%\n`;
        report += `  Último ajuste: ${this.metrics.lastAdjustment?.toLocaleString('pt-BR') || 'Nunca'}\n\n`;
        // Configuração atual
        report += `⚙️  Configuração Atual:\n`;
        report += `  Delay de criação: ${(this.strategy.currentConfig.creationDelayMin / 1000).toFixed(0)}s - ${(this.strategy.currentConfig.creationDelayMax / 1000).toFixed(0)}s\n`;
        report += `  Perfil de timing: ${this.strategy.currentConfig.timingProfile}\n`;
        report += `  Padrão de atividade: ${this.strategy.currentConfig.activityPattern}\n`;
        report += `  Estratégia de retry: ${this.strategy.currentConfig.retryStrategy}\n\n`;
        // Histórico de ajustes (últimos 5)
        if (this.strategy.adjustmentHistory.length > 0) {
            report += `📜 Histórico de Ajustes (últimos 5):\n`;
            const recent = this.strategy.adjustmentHistory.slice(-5).reverse();
            for (const adj of recent) {
                report += `  [${adj.timestamp.toLocaleString('pt-BR')}]\n`;
                report += `    Motivo: ${adj.reason}\n`;
                for (const change of adj.changes) {
                    report += `    • ${change.parameter}: ${change.oldValue} → ${change.newValue}\n`;
                }
                report += `    Impacto: ${adj.expectedImpact}\n\n`;
            }
        }
        else {
            report += `📜 Histórico de Ajustes: Nenhum ajuste realizado ainda\n\n`;
        }
        // Status geral
        const status = this.metrics.successRate >= 0.9
            ? '✅ EXCELENTE'
            : this.metrics.successRate >= 0.8
                ? '✅ BOM'
                : this.metrics.successRate >= 0.6
                    ? '⚠️ ATENÇÃO'
                    : '🚨 CRÍTICO';
        report += `📈 Status Geral: ${status}\n`;
        report += '═══════════════════════════════════════════════════════════\n';
        return report;
    }
}
exports.AdaptiveConfig = AdaptiveConfig;
/**
 * Gerenciador de configs adaptativos (multi-tenant)
 */
class AdaptiveConfigManager {
    constructor() {
        this.configs = new Map();
    }
    /**
     * Obtém ou cria config para tenant
     */
    getConfig(tenantId) {
        if (!this.configs.has(tenantId)) {
            const config = new AdaptiveConfig(tenantId);
            this.configs.set(tenantId, config);
            console.log(`[AdaptiveConfigManager] ➕ Config criado para tenant ${tenantId} | ` +
                `Total: ${this.configs.size}`);
        }
        return this.configs.get(tenantId);
    }
    /**
     * Remove config de tenant
     */
    removeConfig(tenantId) {
        const removed = this.configs.delete(tenantId);
        if (removed) {
            console.log(`[AdaptiveConfigManager] ➖ Config removido: ${tenantId} | ` +
                `Total: ${this.configs.size}`);
        }
        return removed;
    }
    /**
     * Lista todos os configs
     */
    listAll() {
        const list = [];
        for (const [tenantId, config] of this.configs.entries()) {
            list.push({
                tenantId,
                metrics: config.getMetrics(),
                config: config.getCurrentConfig()
            });
        }
        return list;
    }
    /**
     * Estatísticas globais
     */
    getGlobalStats() {
        let totalSuccessRate = 0;
        let total405 = 0;
        let total429 = 0;
        let totalAdjustments = 0;
        for (const config of this.configs.values()) {
            const metrics = config.getMetrics();
            totalSuccessRate += metrics.successRate;
            total405 += metrics.error405Count;
            total429 += metrics.error429Count;
            totalAdjustments += config.getAdjustmentHistory().length;
        }
        const count = this.configs.size;
        return {
            totalTenants: count,
            avgSuccessRate: count > 0 ? totalSuccessRate / count : 0,
            total405Errors: total405,
            total429Errors: total429,
            totalAdjustments
        };
    }
}
exports.AdaptiveConfigManager = AdaptiveConfigManager;
// Singleton global
exports.adaptiveConfigManager = new AdaptiveConfigManager();
exports.default = AdaptiveConfig;
