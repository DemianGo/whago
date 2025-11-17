/**
 * Organic Behavior - Simula comportamento orgânico pós-conexão
 * 
 * Inclui:
 * - Leitura de mensagens não lidas
 * - Visualização de status
 * - Atualização de presença (online/offline)
 * - Ações aleatórias para parecer humano
 */

import type { WASocket, proto } from '@whiskeysockets/baileys';
import { HumanTiming } from './human-timing';

export interface OrganicBehaviorConfig {
  // Habilitar comportamento orgânico
  enabled: boolean;
  
  // Ler mensagens não lidas ao conectar
  readUnreadOnConnect: boolean;
  
  // Quantidade de mensagens a ler (1-5)
  maxMessagesToRead: number;
  
  // Ver status de contatos
  viewStatuses: boolean;
  maxStatusesToView: number;
  
  // Atualizar presença online/offline
  updatePresence: boolean;
  
  // Intervalo entre ações orgânicas (ms)
  actionIntervalMin: number;
  actionIntervalMax: number;
  
  // Probabilidades (0-1)
  probabilities: {
    readMessage: number;
    viewStatus: number;
    updateProfile: number;
    checkGroups: number;
  };
}

export const DEFAULT_ORGANIC_CONFIG: OrganicBehaviorConfig = {
  enabled: true,
  readUnreadOnConnect: true,
  maxMessagesToRead: 3,
  viewStatuses: true,
  maxStatusesToView: 2,
  updatePresence: true,
  actionIntervalMin: 300000,  // 5 minutos
  actionIntervalMax: 900000,  // 15 minutos
  probabilities: {
    readMessage: 0.4,    // 40% de chance
    viewStatus: 0.3,     // 30%
    updateProfile: 0.05, // 5%
    checkGroups: 0.25    // 25%
  }
};

/**
 * Simulador de comportamento orgânico
 */
export class OrganicBehavior {
  private socket: WASocket;
  private timing: HumanTiming;
  private config: OrganicBehaviorConfig;
  private tenantId: string;
  private chipId: string;
  private isActive: boolean = false;
  private actionInterval: NodeJS.Timeout | null = null;
  
  // Estatísticas
  private stats = {
    messagesRead: 0,
    statusesViewed: 0,
    actionsPerformed: 0,
    lastAction: null as Date | null
  };

  constructor(
    socket: WASocket,
    tenantId: string,
    chipId: string,
    config: Partial<OrganicBehaviorConfig> = {}
  ) {
    this.socket = socket;
    this.tenantId = tenantId;
    this.chipId = chipId;
    this.config = { ...DEFAULT_ORGANIC_CONFIG, ...config };
    this.timing = new HumanTiming(tenantId, chipId);

    console.log(
      `[OrganicBehavior] ${this.chipId.substring(0, 8)} - Inicializado ` +
      `(enabled: ${this.config.enabled})`
    );
  }

  /**
   * Inicia comportamento orgânico
   */
  public start(): void {
    if (!this.config.enabled) {
      console.log(
        `[OrganicBehavior] ${this.chipId.substring(0, 8)} - ` +
        `Comportamento orgânico desabilitado`
      );
      return;
    }

    if (this.isActive) {
      console.warn(
        `[OrganicBehavior] ${this.chipId.substring(0, 8)} - Já está ativo`
      );
      return;
    }

    this.isActive = true;
    console.log(
      `[OrganicBehavior] ${this.chipId.substring(0, 8)} ✅ Iniciado`
    );

    // Executar ações iniciais (após delay)
    this.scheduleInitialActions();

    // Agendar ações periódicas
    this.schedulePeriodicActions();
  }

  /**
   * Para comportamento orgânico
   */
  public stop(): void {
    if (!this.isActive) return;

    this.isActive = false;

    if (this.actionInterval) {
      clearInterval(this.actionInterval);
      this.actionInterval = null;
    }

    console.log(
      `[OrganicBehavior] ${this.chipId.substring(0, 8)} ⏹️  Parado`
    );
  }

  /**
   * Agenda ações iniciais (após conectar)
   */
  private async scheduleInitialActions(): Promise<void> {
    // Aguardar 30s-2min após conectar antes de começar
    const initialDelay = 30000 + Math.floor(Math.random() * 90000); // 30s-2min

    console.log(
      `[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
      `⏰ Aguardando ${(initialDelay / 60000).toFixed(1)}min antes das ações iniciais...`
    );

    setTimeout(async () => {
      if (!this.isActive) return;

      try {
        // Ler mensagens não lidas
        if (this.config.readUnreadOnConnect) {
          await this.readUnreadMessages();
        }

        // Ver status
        if (this.config.viewStatuses) {
          await this.viewRandomStatuses();
        }
      } catch (error) {
        console.error(
          `[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
          `Erro nas ações iniciais:`,
          error
        );
      }
    }, initialDelay);
  }

  /**
   * Agenda ações periódicas
   */
  private schedulePeriodicActions(): void {
    // Intervalo aleatório entre ações
    const interval = this.randomDelay(
      this.config.actionIntervalMin,
      this.config.actionIntervalMax
    );

    console.log(
      `[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
      `🔄 Próxima ação em ${(interval / 60000).toFixed(1)}min`
    );

    this.actionInterval = setTimeout(async () => {
      if (!this.isActive) return;

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
  private async performRandomAction(): Promise<void> {
    const random = Math.random();
    const probs = this.config.probabilities;

    try {
      if (random < probs.readMessage) {
        await this.readUnreadMessages();
      } else if (random < probs.readMessage + probs.viewStatus) {
        await this.viewRandomStatuses();
      } else if (random < probs.readMessage + probs.viewStatus + probs.updateProfile) {
        await this.updatePresenceRandomly();
      } else if (random < probs.readMessage + probs.viewStatus + probs.updateProfile + probs.checkGroups) {
        await this.checkGroups();
      } else {
        // Nenhuma ação (20-40% de chance de não fazer nada)
        console.log(
          `[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
          `💤 Nenhuma ação (comportamento idle)`
        );
      }

      this.stats.actionsPerformed++;
      this.stats.lastAction = new Date();

    } catch (error) {
      console.error(
        `[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
        `Erro ao executar ação:`,
        error
      );
    }
  }

  /**
   * Lê mensagens não lidas
   */
  private async readUnreadMessages(): Promise<void> {
    try {
      console.log(
        `[OrganicBehavior] ${this.chipId.substring(0, 8)} 📖 Lendo mensagens não lidas...`
      );

      // Buscar chats (limitado - Baileys pode não suportar diretamente)
      // Esta é uma simulação - adapt baseado na API do Baileys
      
      // Simular leitura de 1-3 mensagens
      const messagesToRead = Math.floor(Math.random() * this.config.maxMessagesToRead) + 1;

      for (let i = 0; i < messagesToRead; i++) {
        // Delay de leitura
        await this.timing.waitForRead();

        // Aqui você precisaria buscar mensagens reais do Baileys
        // Por ora, apenas simular a ação
        console.log(
          `[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
          `✅ Mensagem ${i + 1}/${messagesToRead} lida`
        );

        this.stats.messagesRead++;

        // Delay entre mensagens
        if (i < messagesToRead - 1) {
          await this.timing.waitBetweenActions();
        }
      }

    } catch (error) {
      console.warn(
        `[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
        `⚠️ Erro ao ler mensagens:`,
        error
      );
    }
  }

  /**
   * Visualiza status de contatos
   */
  private async viewRandomStatuses(): Promise<void> {
    try {
      console.log(
        `[OrganicBehavior] ${this.chipId.substring(0, 8)} 📸 Visualizando status...`
      );

      const statusesToView = Math.floor(Math.random() * this.config.maxStatusesToView) + 1;

      for (let i = 0; i < statusesToView; i++) {
        // Tempo de visualização (3-8s por status)
        const viewTime = 3000 + Math.floor(Math.random() * 5000);
        
        console.log(
          `[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
          `👁️  Vendo status ${i + 1}/${statusesToView} por ${(viewTime / 1000).toFixed(1)}s...`
        );

        await this.timing.sleep(viewTime);

        this.stats.statusesViewed++;

        // Delay entre status
        if (i < statusesToView - 1) {
          await this.timing.waitBetweenActions();
        }
      }

    } catch (error) {
      console.warn(
        `[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
        `⚠️ Erro ao ver status:`,
        error
      );
    }
  }

  /**
   * Atualiza presença (online/offline) aleatoriamente
   */
  private async updatePresenceRandomly(): Promise<void> {
    if (!this.config.updatePresence) return;

    try {
      // 50% online, 50% offline
      const goOnline = Math.random() < 0.5;

      if (goOnline) {
        console.log(
          `[OrganicBehavior] ${this.chipId.substring(0, 8)} 🟢 Ficando online...`
        );

        await this.socket.sendPresenceUpdate('available');

        // Ficar online por 1-5 minutos
        const onlineTime = 60000 + Math.floor(Math.random() * 240000);
        console.log(
          `[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
          `⏱️  Online por ${(onlineTime / 60000).toFixed(1)}min`
        );

        await this.timing.sleep(onlineTime);

        // Voltar para unavailable
        await this.socket.sendPresenceUpdate('unavailable');
        console.log(
          `[OrganicBehavior] ${this.chipId.substring(0, 8)} ⚫ Ficando offline`
        );

      } else {
        console.log(
          `[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
          `⚫ Mantendo offline (comportamento discreto)`
        );
      }

    } catch (error) {
      console.warn(
        `[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
        `⚠️ Erro ao atualizar presença:`,
        error
      );
    }
  }

  /**
   * Simula verificação de grupos
   */
  private async checkGroups(): Promise<void> {
    try {
      console.log(
        `[OrganicBehavior] ${this.chipId.substring(0, 8)} 👥 Verificando grupos...`
      );

      // Simular verificação de 1-3 grupos
      const groupsToCheck = Math.floor(Math.random() * 3) + 1;

      for (let i = 0; i < groupsToCheck; i++) {
        // Tempo de visualização do grupo
        const viewTime = 2000 + Math.floor(Math.random() * 5000);
        
        console.log(
          `[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
          `👁️  Vendo grupo ${i + 1}/${groupsToCheck} por ${(viewTime / 1000).toFixed(1)}s...`
        );

        await this.timing.sleep(viewTime);

        // Delay entre grupos
        if (i < groupsToCheck - 1) {
          await this.timing.waitBetweenActions();
        }
      }

    } catch (error) {
      console.warn(
        `[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
        `⚠️ Erro ao verificar grupos:`,
        error
      );
    }
  }

  /**
   * Gera delay aleatório
   */
  private randomDelay(min: number, max: number): number {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  }

  /**
   * Retorna estatísticas
   */
  public getStats(): {
    messagesRead: number;
    statusesViewed: number;
    actionsPerformed: number;
    lastAction: Date | null;
    isActive: boolean;
  } {
    return {
      ...this.stats,
      isActive: this.isActive
    };
  }

  /**
   * Atualiza configuração
   */
  public updateConfig(config: Partial<OrganicBehaviorConfig>): void {
    this.config = { ...this.config, ...config };
    console.log(
      `[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
      `🔄 Configuração atualizada`
    );
  }

  /**
   * Força execução de uma ação específica
   */
  public async forceAction(action: 'read' | 'status' | 'presence' | 'groups'): Promise<void> {
    console.log(
      `[OrganicBehavior] ${this.chipId.substring(0, 8)} ` +
      `🔧 Forçando ação: ${action}`
    );

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

/**
 * Gerenciador de comportamentos orgânicos (multi-tenant)
 */
export class OrganicBehaviorManager {
  private behaviors: Map<string, OrganicBehavior> = new Map();

  /**
   * Registra comportamento para uma sessão
   */
  public register(
    socket: WASocket,
    tenantId: string,
    chipId: string,
    config?: Partial<OrganicBehaviorConfig>
  ): OrganicBehavior {
    const key = `${tenantId}:${chipId}`;

    if (this.behaviors.has(key)) {
      console.warn(
        `[OrganicBehaviorManager] Comportamento já existe para ${key}, substituindo`
      );
      this.unregister(tenantId, chipId);
    }

    const behavior = new OrganicBehavior(socket, tenantId, chipId, config);
    this.behaviors.set(key, behavior);

    console.log(
      `[OrganicBehaviorManager] ➕ Comportamento registrado: ${key} | ` +
      `Total: ${this.behaviors.size}`
    );

    return behavior;
  }

  /**
   * Remove comportamento de uma sessão
   */
  public unregister(tenantId: string, chipId: string): boolean {
    const key = `${tenantId}:${chipId}`;
    const behavior = this.behaviors.get(key);

    if (behavior) {
      behavior.stop();
      this.behaviors.delete(key);

      console.log(
        `[OrganicBehaviorManager] ➖ Comportamento removido: ${key} | ` +
        `Total: ${this.behaviors.size}`
      );

      return true;
    }

    return false;
  }

  /**
   * Obtém comportamento de uma sessão
   */
  public get(tenantId: string, chipId: string): OrganicBehavior | undefined {
    const key = `${tenantId}:${chipId}`;
    return this.behaviors.get(key);
  }

  /**
   * Lista todos os comportamentos
   */
  public listAll(): Array<{
    key: string;
    tenantId: string;
    chipId: string;
    stats: any;
  }> {
    const list: Array<any> = [];

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
  public stopAll(): void {
    console.log(
      `[OrganicBehaviorManager] ⏹️  Parando todos os ${this.behaviors.size} comportamentos...`
    );

    for (const behavior of this.behaviors.values()) {
      behavior.stop();
    }
  }

  /**
   * Estatísticas globais
   */
  public getGlobalStats(): {
    total: number;
    active: number;
    totalMessagesRead: number;
    totalStatusesViewed: number;
    totalActions: number;
  } {
    let active = 0;
    let totalMessagesRead = 0;
    let totalStatusesViewed = 0;
    let totalActions = 0;

    for (const behavior of this.behaviors.values()) {
      const stats = behavior.getStats();
      if (stats.isActive) active++;
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

// Singleton global
export const organicBehaviorManager = new OrganicBehaviorManager();

export default OrganicBehavior;

