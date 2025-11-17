/**
 * Message Queue - Sistema anti-burst para envio de mensagens
 * 
 * Garante que mensagens sejam enviadas com timing humano, mesmo quando
 * a API recebe múltiplas requisições simultâneas
 * 
 * Multi-tenant: cada chip tem sua própria fila isolada
 */

import type { WASocket } from '@whiskeysockets/baileys';
import { TypingSimulator, TypingSimulationOptions } from './typing-simulator';

export interface QueuedMessage {
  id: string;
  jid: string;
  text: string;
  options?: TypingSimulationOptions;
  priority: 'low' | 'normal' | 'high';
  enqueuedAt: Date;
  resolve: (result: any) => void;
  reject: (error: any) => void;
}

export interface QueueStats {
  pending: number;
  processing: boolean;
  totalProcessed: number;
  totalFailed: number;
  averageProcessingTime: number;
  oldestMessageAge: number | null;
}

/**
 * Fila de mensagens com processamento humano
 */
export class MessageQueue {
  private queue: QueuedMessage[] = [];
  private processing: boolean = false;
  private simulator: TypingSimulator;
  private chipId: string;
  private tenantId: string;
  
  // Estatísticas
  private stats = {
    totalProcessed: 0,
    totalFailed: 0,
    processingTimes: [] as number[]
  };

  // Limites de segurança
  private readonly MAX_QUEUE_SIZE = 100;
  private readonly MAX_PROCESSING_TIME = 300000; // 5 minutos por mensagem

  constructor(
    socket: WASocket,
    tenantId: string,
    chipId: string,
    timingProfile?: string
  ) {
    this.chipId = chipId;
    this.tenantId = tenantId;
    this.simulator = new TypingSimulator(socket, tenantId, chipId, timingProfile);

    console.log(
      `[MessageQueue] Fila criada para Tenant ${tenantId} | Chip ${chipId.substring(0, 8)}`
    );
  }

  /**
   * Adiciona mensagem à fila
   */
  public async enqueue(
    jid: string,
    text: string,
    options?: TypingSimulationOptions,
    priority: 'low' | 'normal' | 'high' = 'normal'
  ): Promise<any> {
    // Verificar limite da fila
    if (this.queue.length >= this.MAX_QUEUE_SIZE) {
      const error = new Error(
        `Fila cheia (${this.MAX_QUEUE_SIZE} mensagens). Aguarde processamento.`
      );
      console.error(
        `[MessageQueue] ${this.chipId.substring(0, 8)} ❌ Fila cheia!`
      );
      throw error;
    }

    // Criar promise que será resolvida quando mensagem for enviada
    return new Promise((resolve, reject) => {
      const messageId = `msg_${Date.now()}_${Math.random().toString(36).substring(7)}`;
      
      const queuedMessage: QueuedMessage = {
        id: messageId,
        jid,
        text,
        options,
        priority,
        enqueuedAt: new Date(),
        resolve,
        reject
      };

      // Adicionar à fila (ordenar por prioridade)
      this.queue.push(queuedMessage);
      this.sortQueue();

      console.log(
        `[MessageQueue] ${this.chipId.substring(0, 8)} ➕ Mensagem enfileirada ` +
        `[${priority.toUpperCase()}] | ID: ${messageId} | Posição: ${this.queue.length}`
      );

      // Iniciar processamento se não estiver processando
      if (!this.processing) {
        this.processQueue();
      }
    });
  }

  /**
   * Ordena fila por prioridade
   */
  private sortQueue(): void {
    const priorityOrder = { high: 1, normal: 2, low: 3 };
    
    this.queue.sort((a, b) => {
      // Primeiro por prioridade
      const priorityDiff = priorityOrder[a.priority] - priorityOrder[b.priority];
      if (priorityDiff !== 0) return priorityDiff;
      
      // Depois por ordem de chegada
      return a.enqueuedAt.getTime() - b.enqueuedAt.getTime();
    });
  }

  /**
   * Processa fila de forma assíncrona
   */
  private async processQueue(): Promise<void> {
    if (this.processing) {
      console.warn(
        `[MessageQueue] ${this.chipId.substring(0, 8)} ⚠️ Já está processando`
      );
      return;
    }

    this.processing = true;
    console.log(
      `[MessageQueue] ${this.chipId.substring(0, 8)} 🚀 Iniciando processamento ` +
      `(${this.queue.length} na fila)`
    );

    while (this.queue.length > 0) {
      const message = this.queue.shift()!;
      const startTime = Date.now();

      try {
        console.log(
          `[MessageQueue] ${this.chipId.substring(0, 8)} 📤 Processando ` +
          `${message.id} → ${message.jid} | "${message.text.substring(0, 30)}..."`
        );

        // Timeout de segurança
        const timeoutPromise = new Promise((_, reject) => {
          setTimeout(
            () => reject(new Error('Timeout ao enviar mensagem')),
            this.MAX_PROCESSING_TIME
          );
        });

        // Enviar com simulação humana
        const resultPromise = this.simulator.sendMessageHumanLike(
          message.jid,
          message.text,
          message.options
        );

        const result = await Promise.race([resultPromise, timeoutPromise]);

        // Registrar tempo de processamento
        const processingTime = Date.now() - startTime;
        this.stats.processingTimes.push(processingTime);
        
        // Manter apenas últimos 100 tempos (para média)
        if (this.stats.processingTimes.length > 100) {
          this.stats.processingTimes.shift();
        }

        this.stats.totalProcessed++;

        console.log(
          `[MessageQueue] ${this.chipId.substring(0, 8)} ✅ ${message.id} enviado ` +
          `em ${(processingTime / 1000).toFixed(1)}s`
        );

        // Resolver promise
        message.resolve(result);

      } catch (error) {
        this.stats.totalFailed++;

        console.error(
          `[MessageQueue] ${this.chipId.substring(0, 8)} ❌ Erro ao processar ${message.id}:`,
          error
        );

        // Rejeitar promise
        message.reject(error);
      }

      // Log de progresso
      if (this.queue.length > 0) {
        console.log(
          `[MessageQueue] ${this.chipId.substring(0, 8)} 📊 Progresso: ` +
          `${this.stats.totalProcessed} enviadas | ${this.queue.length} restantes`
        );
      }
    }

    this.processing = false;
    console.log(
      `[MessageQueue] ${this.chipId.substring(0, 8)} ✅ Fila vazia | ` +
      `Total processado: ${this.stats.totalProcessed}`
    );
  }

  /**
   * Retorna estatísticas da fila
   */
  public getStats(): QueueStats {
    const avgTime = this.stats.processingTimes.length > 0
      ? this.stats.processingTimes.reduce((a, b) => a + b, 0) / this.stats.processingTimes.length
      : 0;

    const oldestMessage = this.queue.length > 0
      ? Date.now() - this.queue[0].enqueuedAt.getTime()
      : null;

    return {
      pending: this.queue.length,
      processing: this.processing,
      totalProcessed: this.stats.totalProcessed,
      totalFailed: this.stats.totalFailed,
      averageProcessingTime: Math.round(avgTime),
      oldestMessageAge: oldestMessage
    };
  }

  /**
   * Limpa fila (rejeitando todas as mensagens)
   */
  public clear(reason: string = 'Fila limpa manualmente'): void {
    console.log(
      `[MessageQueue] ${this.chipId.substring(0, 8)} 🧹 Limpando ${this.queue.length} mensagens ` +
      `(motivo: ${reason})`
    );

    while (this.queue.length > 0) {
      const message = this.queue.shift()!;
      message.reject(new Error(reason));
    }

    this.processing = false;
  }

  /**
   * Pausa processamento da fila
   */
  public pause(): void {
    if (this.processing) {
      console.log(
        `[MessageQueue] ${this.chipId.substring(0, 8)} ⏸️  Fila pausada ` +
        `(${this.queue.length} mensagens aguardando)`
      );
      this.processing = false;
    }
  }

  /**
   * Retoma processamento da fila
   */
  public resume(): void {
    if (!this.processing && this.queue.length > 0) {
      console.log(
        `[MessageQueue] ${this.chipId.substring(0, 8)} ▶️  Retomando processamento ` +
        `(${this.queue.length} mensagens)`
      );
      this.processQueue();
    }
  }

  /**
   * Remove mensagem específica da fila
   */
  public remove(messageId: string): boolean {
    const index = this.queue.findIndex(m => m.id === messageId);
    
    if (index !== -1) {
      const message = this.queue.splice(index, 1)[0];
      message.reject(new Error('Mensagem removida da fila'));
      
      console.log(
        `[MessageQueue] ${this.chipId.substring(0, 8)} ➖ Mensagem ${messageId} removida`
      );
      return true;
    }

    return false;
  }

  /**
   * Retorna mensagens pendentes
   */
  public getPendingMessages(): Array<{
    id: string;
    jid: string;
    textPreview: string;
    priority: string;
    enqueuedAt: Date;
    ageMs: number;
  }> {
    const now = Date.now();
    
    return this.queue.map(msg => ({
      id: msg.id,
      jid: msg.jid,
      textPreview: msg.text.substring(0, 50) + (msg.text.length > 50 ? '...' : ''),
      priority: msg.priority,
      enqueuedAt: msg.enqueuedAt,
      ageMs: now - msg.enqueuedAt.getTime()
    }));
  }

  /**
   * Troca perfil de timing do simulator
   */
  public changeTimingProfile(profileName: string): void {
    this.simulator.changeTimingProfile(profileName);
    console.log(
      `[MessageQueue] ${this.chipId.substring(0, 8)} 🔄 Perfil alterado para: ${profileName}`
    );
  }

  /**
   * Retorna simulator (para acesso direto)
   */
  public getSimulator(): TypingSimulator {
    return this.simulator;
  }
}

/**
 * Gerenciador global de filas (multi-tenant)
 */
export class MessageQueueManager {
  private queues: Map<string, MessageQueue> = new Map();

  /**
   * Obtém ou cria fila para um chip
   */
  public getQueue(
    socket: WASocket,
    tenantId: string,
    chipId: string,
    timingProfile?: string
  ): MessageQueue {
    const queueKey = `${tenantId}:${chipId}`;

    if (!this.queues.has(queueKey)) {
      const queue = new MessageQueue(socket, tenantId, chipId, timingProfile);
      this.queues.set(queueKey, queue);
      
      console.log(
        `[MessageQueueManager] ➕ Fila criada: ${queueKey} | ` +
        `Total de filas: ${this.queues.size}`
      );
    }

    return this.queues.get(queueKey)!;
  }

  /**
   * Remove fila de um chip
   */
  public removeQueue(tenantId: string, chipId: string): boolean {
    const queueKey = `${tenantId}:${chipId}`;
    const queue = this.queues.get(queueKey);

    if (queue) {
      queue.clear('Chip removido');
      this.queues.delete(queueKey);
      
      console.log(
        `[MessageQueueManager] ➖ Fila removida: ${queueKey} | ` +
        `Total de filas: ${this.queues.size}`
      );
      return true;
    }

    return false;
  }

  /**
   * Retorna todas as filas de um tenant
   */
  public getTenantQueues(tenantId: string): MessageQueue[] {
    const tenantQueues: MessageQueue[] = [];

    for (const [key, queue] of this.queues.entries()) {
      if (key.startsWith(`${tenantId}:`)) {
        tenantQueues.push(queue);
      }
    }

    return tenantQueues;
  }

  /**
   * Retorna estatísticas globais
   */
  public getGlobalStats(): {
    totalQueues: number;
    totalPending: number;
    totalProcessed: number;
    totalFailed: number;
    activeQueues: number;
  } {
    let totalPending = 0;
    let totalProcessed = 0;
    let totalFailed = 0;
    let activeQueues = 0;

    for (const queue of this.queues.values()) {
      const stats = queue.getStats();
      totalPending += stats.pending;
      totalProcessed += stats.totalProcessed;
      totalFailed += stats.totalFailed;
      if (stats.processing) activeQueues++;
    }

    return {
      totalQueues: this.queues.size,
      totalPending,
      totalProcessed,
      totalFailed,
      activeQueues
    };
  }

  /**
   * Limpa todas as filas de um tenant
   */
  public clearTenantQueues(tenantId: string, reason?: string): number {
    const tenantQueues = this.getTenantQueues(tenantId);
    
    for (const queue of tenantQueues) {
      queue.clear(reason || `Tenant ${tenantId} limpo`);
    }

    console.log(
      `[MessageQueueManager] 🧹 ${tenantQueues.length} filas limpas para tenant ${tenantId}`
    );

    return tenantQueues.length;
  }

  /**
   * Lista todas as filas
   */
  public listQueues(): Array<{
    key: string;
    tenantId: string;
    chipId: string;
    stats: QueueStats;
  }> {
    const list: Array<any> = [];

    for (const [key, queue] of this.queues.entries()) {
      const [tenantId, chipId] = key.split(':');
      list.push({
        key,
        tenantId,
        chipId,
        stats: queue.getStats()
      });
    }

    return list;
  }
}

// Singleton global
export const messageQueueManager = new MessageQueueManager();

export default MessageQueue;

