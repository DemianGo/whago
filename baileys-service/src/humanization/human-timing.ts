/**
 * Human Timing - Gera delays realistas para simular comportamento humano
 * 
 * Sistema multi-tenant com alta variação para evitar padrões detectáveis
 */

export interface TimingProfile {
  name: string;
  
  // Tempo de leitura de mensagem (ms)
  readMessage: { min: number; max: number };
  
  // Tempo de digitação por caractere (ms)
  typingPerChar: { min: number; max: number };
  
  // Pausa antes de começar a digitar (ms)
  thinkingTime: { min: number; max: number };
  
  // Pausa após terminar de digitar (revisar) (ms)
  reviewTime: { min: number; max: number };
  
  // Delay entre mensagens consecutivas (ms)
  betweenMessages: { min: number; max: number };
  
  // Delay entre ações (abrir chat, ver status, etc) (ms)
  betweenActions: { min: number; max: number };
  
  // Tempo de presença "online" após enviar msg (ms)
  onlinePresence: { min: number; max: number };
  
  // Variação adicional (jitter %) - adiciona aleatoriedade extra
  jitter: number;
}

/**
 * Perfis de timing - muitas opções para alta variação
 */
export const TIMING_PROFILES: Record<string, TimingProfile> = {
  // Usuário muito lento (idoso, não acostumado)
  very_slow: {
    name: 'Muito Lento',
    readMessage: { min: 3000, max: 8000 },
    typingPerChar: { min: 300, max: 500 },
    thinkingTime: { min: 2000, max: 5000 },
    reviewTime: { min: 2000, max: 5000 },
    betweenMessages: { min: 15000, max: 30000 },
    betweenActions: { min: 8000, max: 15000 },
    onlinePresence: { min: 120000, max: 300000 },
    jitter: 0.3
  },

  // Usuário lento (típico, não apressado)
  slow: {
    name: 'Lento',
    readMessage: { min: 2000, max: 5000 },
    typingPerChar: { min: 200, max: 350 },
    thinkingTime: { min: 1500, max: 4000 },
    reviewTime: { min: 1000, max: 3000 },
    betweenMessages: { min: 10000, max: 20000 },
    betweenActions: { min: 5000, max: 12000 },
    onlinePresence: { min: 90000, max: 240000 },
    jitter: 0.25
  },

  // Usuário médio (padrão realista)
  normal: {
    name: 'Normal',
    readMessage: { min: 1500, max: 4000 },
    typingPerChar: { min: 120, max: 250 },
    thinkingTime: { min: 1000, max: 3000 },
    reviewTime: { min: 800, max: 2000 },
    betweenMessages: { min: 7000, max: 15000 },
    betweenActions: { min: 3000, max: 8000 },
    onlinePresence: { min: 60000, max: 180000 },
    jitter: 0.2
  },

  // Usuário rápido (jovem, habituado)
  fast: {
    name: 'Rápido',
    readMessage: { min: 1000, max: 2500 },
    typingPerChar: { min: 80, max: 180 },
    thinkingTime: { min: 500, max: 2000 },
    reviewTime: { min: 500, max: 1500 },
    betweenMessages: { min: 5000, max: 10000 },
    betweenActions: { min: 2000, max: 5000 },
    onlinePresence: { min: 45000, max: 120000 },
    jitter: 0.15
  },

  // Usuário muito rápido (power user)
  very_fast: {
    name: 'Muito Rápido',
    readMessage: { min: 800, max: 2000 },
    typingPerChar: { min: 50, max: 120 },
    thinkingTime: { min: 300, max: 1500 },
    reviewTime: { min: 300, max: 1000 },
    betweenMessages: { min: 3000, max: 8000 },
    betweenActions: { min: 1500, max: 4000 },
    onlinePresence: { min: 30000, max: 90000 },
    jitter: 0.1
  },

  // Usuário corporativo (formal, pausado)
  corporate: {
    name: 'Corporativo',
    readMessage: { min: 2000, max: 5000 },
    typingPerChar: { min: 150, max: 280 },
    thinkingTime: { min: 2000, max: 4500 },
    reviewTime: { min: 1500, max: 3500 },
    betweenMessages: { min: 12000, max: 25000 },
    betweenActions: { min: 6000, max: 12000 },
    onlinePresence: { min: 90000, max: 240000 },
    jitter: 0.2
  },

  // Usuário casual (variável, sem pressa)
  casual: {
    name: 'Casual',
    readMessage: { min: 1800, max: 6000 },
    typingPerChar: { min: 100, max: 300 },
    thinkingTime: { min: 1000, max: 5000 },
    reviewTime: { min: 800, max: 3000 },
    betweenMessages: { min: 8000, max: 20000 },
    betweenActions: { min: 4000, max: 10000 },
    onlinePresence: { min: 60000, max: 300000 },
    jitter: 0.35
  },

  // Usuário distraído (muitas pausas)
  distracted: {
    name: 'Distraído',
    readMessage: { min: 2500, max: 10000 },
    typingPerChar: { min: 150, max: 400 },
    thinkingTime: { min: 2000, max: 8000 },
    reviewTime: { min: 1500, max: 5000 },
    betweenMessages: { min: 15000, max: 45000 },
    betweenActions: { min: 8000, max: 20000 },
    onlinePresence: { min: 120000, max: 600000 },
    jitter: 0.4
  }
};

/**
 * Gerador de delays humanos
 */
export class HumanTiming {
  private profile: TimingProfile;
  private tenantId: string;
  private chipId: string;

  constructor(tenantId: string, chipId: string, profileName?: string) {
    this.tenantId = tenantId;
    this.chipId = chipId;

    // Selecionar perfil (se não especificado, escolhe aleatoriamente)
    if (profileName && TIMING_PROFILES[profileName]) {
      this.profile = TIMING_PROFILES[profileName];
    } else {
      this.profile = this.selectRandomProfile();
    }

    console.log(
      `[HumanTiming] Tenant ${tenantId} | Chip ${chipId.substring(0, 8)} ` +
      `→ Perfil: ${this.profile.name}`
    );
  }

  /**
   * Seleciona perfil aleatório com distribuição realista
   * (mais peso em normal/fast, menos em extremos)
   */
  private selectRandomProfile(): TimingProfile {
    const weights = {
      very_slow: 5,
      slow: 15,
      normal: 30,
      fast: 25,
      very_fast: 10,
      corporate: 8,
      casual: 5,
      distracted: 2
    };

    const totalWeight = Object.values(weights).reduce((a, b) => a + b, 0);
    let random = Math.random() * totalWeight;

    for (const [key, weight] of Object.entries(weights)) {
      random -= weight;
      if (random <= 0) {
        return TIMING_PROFILES[key];
      }
    }

    return TIMING_PROFILES.normal;
  }

  /**
   * Gera delay com jitter aplicado
   */
  private applyJitter(value: number, jitter: number): number {
    const variation = value * jitter * (Math.random() * 2 - 1);
    return Math.max(0, Math.round(value + variation));
  }

  /**
   * Gera delay aleatório dentro de range
   */
  private randomDelay(range: { min: number; max: number }): number {
    const base = Math.floor(Math.random() * (range.max - range.min + 1)) + range.min;
    return this.applyJitter(base, this.profile.jitter);
  }

  /**
   * Tempo para ler uma mensagem
   */
  public getReadMessageDelay(): number {
    const delay = this.randomDelay(this.profile.readMessage);
    console.log(`[HumanTiming] ${this.chipId.substring(0, 8)} - Ler mensagem: ${delay}ms`);
    return delay;
  }

  /**
   * Tempo de "pensamento" antes de começar a digitar
   */
  public getThinkingDelay(): number {
    const delay = this.randomDelay(this.profile.thinkingTime);
    console.log(`[HumanTiming] ${this.chipId.substring(0, 8)} - Pensando: ${delay}ms`);
    return delay;
  }

  /**
   * Tempo de digitação baseado no comprimento do texto
   * Inclui variações realistas (pausas, aceleração, erros)
   */
  public getTypingDelay(textLength: number): number {
    // Tempo base por caractere
    const perChar = this.randomDelay(this.profile.typingPerChar);
    let totalTime = textLength * perChar;

    // Adicionar pausas aleatórias (simulando pensar em palavras)
    const words = textLength / 5; // média 5 chars por palavra
    const pausesCount = Math.floor(words * 0.3); // 30% das palavras tem pausa
    for (let i = 0; i < pausesCount; i++) {
      totalTime += this.randomDelay({ min: 300, max: 1500 });
    }

    // Simular "burst" de digitação rápida (25% de chance)
    if (Math.random() < 0.25) {
      totalTime *= 0.7; // digitou 30% mais rápido
    }

    // Simular hesitação (15% de chance)
    if (Math.random() < 0.15) {
      totalTime += this.randomDelay({ min: 2000, max: 5000 });
    }

    const finalDelay = Math.round(totalTime);
    console.log(
      `[HumanTiming] ${this.chipId.substring(0, 8)} - Digitando "${textLength} chars": ${finalDelay}ms ` +
      `(${(finalDelay / 1000).toFixed(1)}s)`
    );
    return finalDelay;
  }

  /**
   * Tempo de revisão após digitar (antes de enviar)
   */
  public getReviewDelay(): number {
    const delay = this.randomDelay(this.profile.reviewTime);
    console.log(`[HumanTiming] ${this.chipId.substring(0, 8)} - Revisando: ${delay}ms`);
    return delay;
  }

  /**
   * Delay entre mensagens consecutivas
   */
  public getBetweenMessagesDelay(): number {
    const delay = this.randomDelay(this.profile.betweenMessages);
    console.log(`[HumanTiming] ${this.chipId.substring(0, 8)} - Entre mensagens: ${delay}ms`);
    return delay;
  }

  /**
   * Delay entre ações genéricas (abrir chat, ver status, etc)
   */
  public getBetweenActionsDelay(): number {
    const delay = this.randomDelay(this.profile.betweenActions);
    console.log(`[HumanTiming] ${this.chipId.substring(0, 8)} - Entre ações: ${delay}ms`);
    return delay;
  }

  /**
   * Tempo de presença online após atividade
   */
  public getOnlinePresenceDelay(): number {
    const delay = this.randomDelay(this.profile.onlinePresence);
    console.log(
      `[HumanTiming] ${this.chipId.substring(0, 8)} - Online por: ${delay}ms ` +
      `(${(delay / 60000).toFixed(1)}min)`
    );
    return delay;
  }

  /**
   * Retorna perfil atual
   */
  public getProfile(): TimingProfile {
    return this.profile;
  }

  /**
   * Troca perfil dinamicamente
   */
  public changeProfile(profileName: string): void {
    if (TIMING_PROFILES[profileName]) {
      this.profile = TIMING_PROFILES[profileName];
      console.log(
        `[HumanTiming] ${this.chipId.substring(0, 8)} - ` +
        `Perfil alterado para: ${this.profile.name}`
      );
    } else {
      console.warn(
        `[HumanTiming] Perfil "${profileName}" não existe. ` +
        `Mantendo: ${this.profile.name}`
      );
    }
  }

  /**
   * Helper: sleep assíncrono
   */
  public async sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Executa delay de leitura
   */
  public async waitForRead(): Promise<void> {
    await this.sleep(this.getReadMessageDelay());
  }

  /**
   * Executa delay de pensamento
   */
  public async waitForThinking(): Promise<void> {
    await this.sleep(this.getThinkingDelay());
  }

  /**
   * Executa delay de digitação
   */
  public async waitForTyping(textLength: number): Promise<void> {
    await this.sleep(this.getTypingDelay(textLength));
  }

  /**
   * Executa delay de revisão
   */
  public async waitForReview(): Promise<void> {
    await this.sleep(this.getReviewDelay());
  }

  /**
   * Executa delay entre mensagens
   */
  public async waitBetweenMessages(): Promise<void> {
    await this.sleep(this.getBetweenMessagesDelay());
  }

  /**
   * Executa delay entre ações
   */
  public async waitBetweenActions(): Promise<void> {
    await this.sleep(this.getBetweenActionsDelay());
  }
}

export default HumanTiming;

