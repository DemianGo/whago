/**
 * Activity Simulator - Simula padrões de atividade humana
 * 
 * Inclui:
 * - Horários de pico/vale de atividade
 * - Padrões diários (manhã, tarde, noite)
 * - Fins de semana vs dias úteis
 * - Ajuste automático de comportamento por horário
 */

export interface ActivityPattern {
  name: string;
  description: string;
  
  // Probabilidade de estar online por hora do dia (0-23)
  hourlyProbability: number[];
  
  // Multiplicador de atividade por dia da semana (0=domingo)
  weeklyMultiplier: number[];
  
  // Duração média de sessão online (ms)
  averageSessionDuration: number;
  
  // Frequência de ações por hora quando online
  actionsPerHour: {
    min: number;
    max: number;
  };
}

/**
 * Padrões de atividade pré-definidos
 */
export const ACTIVITY_PATTERNS: Record<string, ActivityPattern> = {
  // Usuário corporativo (horário comercial)
  corporate: {
    name: 'Corporativo',
    description: 'Ativo durante horário comercial (9h-18h)',
    hourlyProbability: [
      0.05, 0.05, 0.05, 0.05, 0.05, 0.10, // 00h-05h (baixa)
      0.20, 0.40, 0.70, 0.85, 0.90, 0.95, // 06h-11h (crescente)
      0.90, 0.95, 0.95, 0.90, 0.85, 0.80, // 12h-17h (pico)
      0.60, 0.40, 0.25, 0.15, 0.10, 0.05  // 18h-23h (decrescente)
    ],
    weeklyMultiplier: [
      0.3, // Domingo (baixa)
      1.0, 1.0, 1.0, 1.0, 1.0, // Seg-Sex (normal)
      0.4  // Sábado (baixa)
    ],
    averageSessionDuration: 240000, // 4min
    actionsPerHour: { min: 5, max: 15 }
  },

  // Usuário noturno (ativo à noite)
  night_owl: {
    name: 'Noturno',
    description: 'Ativo principalmente à noite (20h-02h)',
    hourlyProbability: [
      0.60, 0.50, 0.30, 0.10, 0.05, 0.05, // 00h-05h (decrescente)
      0.05, 0.10, 0.20, 0.30, 0.40, 0.50, // 06h-11h (crescente)
      0.55, 0.60, 0.65, 0.70, 0.75, 0.80, // 12h-17h (médio-alto)
      0.85, 0.90, 0.95, 0.95, 0.80, 0.70  // 18h-23h (pico)
    ],
    weeklyMultiplier: [
      0.9, // Domingo
      0.7, 0.7, 0.7, 0.7, // Seg-Qui
      1.0, // Sexta (pico)
      1.0  // Sábado (pico)
    ],
    averageSessionDuration: 360000, // 6min
    actionsPerHour: { min: 8, max: 20 }
  },

  // Usuário matutino (ativo pela manhã)
  early_bird: {
    name: 'Matutino',
    description: 'Ativo principalmente pela manhã (06h-12h)',
    hourlyProbability: [
      0.05, 0.05, 0.05, 0.05, 0.10, 0.20, // 00h-05h (baixa, crescente no fim)
      0.60, 0.80, 0.95, 0.95, 0.90, 0.85, // 06h-11h (pico)
      0.75, 0.70, 0.60, 0.50, 0.40, 0.30, // 12h-17h (decrescente)
      0.25, 0.20, 0.15, 0.10, 0.05, 0.05  // 18h-23h (baixa)
    ],
    weeklyMultiplier: [
      0.8, // Domingo
      1.0, 1.0, 1.0, 1.0, 1.0, // Seg-Sex (normal)
      0.9  // Sábado
    ],
    averageSessionDuration: 180000, // 3min
    actionsPerHour: { min: 10, max: 25 }
  },

  // Usuário balanceado (ativo o dia todo)
  balanced: {
    name: 'Balanceado',
    description: 'Ativo uniformemente durante o dia',
    hourlyProbability: [
      0.10, 0.05, 0.05, 0.05, 0.05, 0.10, // 00h-05h (baixa)
      0.30, 0.50, 0.70, 0.80, 0.85, 0.85, // 06h-11h (crescente)
      0.85, 0.85, 0.85, 0.80, 0.75, 0.70, // 12h-17h (estável)
      0.65, 0.60, 0.50, 0.35, 0.20, 0.15  // 18h-23h (decrescente)
    ],
    weeklyMultiplier: [
      0.7, // Domingo
      1.0, 1.0, 1.0, 1.0, 1.0, // Seg-Sex (normal)
      0.8  // Sábado
    ],
    averageSessionDuration: 300000, // 5min
    actionsPerHour: { min: 6, max: 18 }
  },

  // Usuário casual (baixa frequência)
  casual: {
    name: 'Casual',
    description: 'Ativo esporadicamente, sem padrão fixo',
    hourlyProbability: [
      0.15, 0.10, 0.08, 0.05, 0.05, 0.08, // 00h-05h
      0.20, 0.35, 0.50, 0.60, 0.65, 0.65, // 06h-11h
      0.65, 0.70, 0.70, 0.65, 0.60, 0.55, // 12h-17h
      0.50, 0.45, 0.40, 0.30, 0.25, 0.20  // 18h-23h
    ],
    weeklyMultiplier: [
      1.0, // Domingo
      0.8, 0.8, 0.8, 0.8, 0.8, // Seg-Sex (mais baixo)
      1.0  // Sábado
    ],
    averageSessionDuration: 120000, // 2min
    actionsPerHour: { min: 2, max: 8 }
  },

  // Usuário 24/7 (sempre ativo - bot-like, usar com cuidado!)
  always_on: {
    name: 'Sempre Ativo',
    description: 'Ativo 24/7 (usar apenas para testes)',
    hourlyProbability: Array(24).fill(0.95), // 95% sempre
    weeklyMultiplier: Array(7).fill(1.0),
    averageSessionDuration: 600000, // 10min
    actionsPerHour: { min: 15, max: 30 }
  }
};

/**
 * Simulador de atividade
 */
export class ActivitySimulator {
  private pattern: ActivityPattern;
  private tenantId: string;
  private chipId: string;

  constructor(
    tenantId: string,
    chipId: string,
    patternName: string = 'balanced'
  ) {
    this.tenantId = tenantId;
    this.chipId = chipId;

    if (ACTIVITY_PATTERNS[patternName]) {
      this.pattern = ACTIVITY_PATTERNS[patternName];
    } else {
      console.warn(
        `[ActivitySimulator] Padrão "${patternName}" não encontrado, usando "balanced"`
      );
      this.pattern = ACTIVITY_PATTERNS.balanced;
    }

    console.log(
      `[ActivitySimulator] ${this.chipId.substring(0, 8)} - ` +
      `Padrão: ${this.pattern.name}`
    );
  }

  /**
   * Verifica se deve estar online agora
   */
  public shouldBeOnlineNow(): boolean {
    const now = new Date();
    const hour = now.getHours();
    const dayOfWeek = now.getDay();

    // Probabilidade base por hora
    const hourlyProb = this.pattern.hourlyProbability[hour];

    // Multiplicador por dia da semana
    const weeklyMult = this.pattern.weeklyMultiplier[dayOfWeek];

    // Probabilidade final
    const finalProb = hourlyProb * weeklyMult;

    // Decisão aleatória
    const shouldBeOnline = Math.random() < finalProb;

    console.log(
      `[ActivitySimulator] ${this.chipId.substring(0, 8)} - ` +
      `${now.toLocaleTimeString('pt-BR')} | ` +
      `Prob: ${(finalProb * 100).toFixed(0)}% | ` +
      `Resultado: ${shouldBeOnline ? '🟢 Online' : '⚫ Offline'}`
    );

    return shouldBeOnline;
  }

  /**
   * Retorna duração de sessão online recomendada
   */
  public getSessionDuration(): number {
    // Variação de ±30% em torno da média
    const variation = 0.3;
    const base = this.pattern.averageSessionDuration;
    const variance = base * variation * (Math.random() * 2 - 1);
    const duration = Math.max(60000, Math.round(base + variance)); // mínimo 1min

    console.log(
      `[ActivitySimulator] ${this.chipId.substring(0, 8)} - ` +
      `Duração de sessão: ${(duration / 60000).toFixed(1)}min`
    );

    return duration;
  }

  /**
   * Retorna quantidade de ações recomendadas para próxima hora
   */
  public getActionsForNextHour(): number {
    const min = this.pattern.actionsPerHour.min;
    const max = this.pattern.actionsPerHour.max;
    const actions = Math.floor(Math.random() * (max - min + 1)) + min;

    console.log(
      `[ActivitySimulator] ${this.chipId.substring(0, 8)} - ` +
      `Ações na próxima hora: ${actions}`
    );

    return actions;
  }

  /**
   * Retorna intervalo médio entre ações (ms)
   */
  public getAverageActionInterval(): number {
    const actionsPerHour = (this.pattern.actionsPerHour.min + this.pattern.actionsPerHour.max) / 2;
    const interval = 3600000 / actionsPerHour; // ms

    return interval;
  }

  /**
   * Retorna probabilidade atual de estar online (0-1)
   */
  public getCurrentProbability(): number {
    const now = new Date();
    const hour = now.getHours();
    const dayOfWeek = now.getDay();

    const hourlyProb = this.pattern.hourlyProbability[hour];
    const weeklyMult = this.pattern.weeklyMultiplier[dayOfWeek];

    return hourlyProb * weeklyMult;
  }

  /**
   * Retorna horários de pico (probabilidade > 80%)
   */
  public getPeakHours(): number[] {
    return this.pattern.hourlyProbability
      .map((prob, hour) => ({ hour, prob }))
      .filter(({ prob }) => prob > 0.8)
      .map(({ hour }) => hour);
  }

  /**
   * Retorna horários de vale (probabilidade < 20%)
   */
  public getValleyHours(): number[] {
    return this.pattern.hourlyProbability
      .map((prob, hour) => ({ hour, prob }))
      .filter(({ prob }) => prob < 0.2)
      .map(({ hour }) => hour);
  }

  /**
   * Verifica se é horário de pico agora
   */
  public isPeakHourNow(): boolean {
    const hour = new Date().getHours();
    return this.pattern.hourlyProbability[hour] > 0.8;
  }

  /**
   * Verifica se é horário de vale agora
   */
  public isValleyHourNow(): boolean {
    const hour = new Date().getHours();
    return this.pattern.hourlyProbability[hour] < 0.2;
  }

  /**
   * Verifica se é fim de semana
   */
  public isWeekend(): boolean {
    const day = new Date().getDay();
    return day === 0 || day === 6;
  }

  /**
   * Retorna padrão atual
   */
  public getPattern(): ActivityPattern {
    return this.pattern;
  }

  /**
   * Troca padrão dinamicamente
   */
  public changePattern(patternName: string): void {
    if (ACTIVITY_PATTERNS[patternName]) {
      this.pattern = ACTIVITY_PATTERNS[patternName];
      console.log(
        `[ActivitySimulator] ${this.chipId.substring(0, 8)} - ` +
        `Padrão alterado para: ${this.pattern.name}`
      );
    } else {
      console.warn(
        `[ActivitySimulator] Padrão "${patternName}" não existe`
      );
    }
  }

  /**
   * Retorna estatísticas do padrão
   */
  public getStats(): {
    pattern: string;
    currentProbability: number;
    peakHours: number[];
    valleyHours: number[];
    isPeakNow: boolean;
    isValleyNow: boolean;
    isWeekend: boolean;
    averageSessionDuration: number;
    actionsPerHour: { min: number; max: number };
  } {
    return {
      pattern: this.pattern.name,
      currentProbability: this.getCurrentProbability(),
      peakHours: this.getPeakHours(),
      valleyHours: this.getValleyHours(),
      isPeakNow: this.isPeakHourNow(),
      isValleyNow: this.isValleyHourNow(),
      isWeekend: this.isWeekend(),
      averageSessionDuration: this.pattern.averageSessionDuration,
      actionsPerHour: this.pattern.actionsPerHour
    };
  }

  /**
   * Gera relatório visual do padrão (ASCII)
   */
  public generatePatternReport(): string {
    let report = `\n[ActivitySimulator] Padrão: ${this.pattern.name}\n`;
    report += `Descrição: ${this.pattern.description}\n\n`;
    report += `Probabilidade por hora:\n`;

    for (let hour = 0; hour < 24; hour++) {
      const prob = this.pattern.hourlyProbability[hour];
      const barLength = Math.round(prob * 50); // barra de 50 chars max
      const bar = '█'.repeat(barLength) + '░'.repeat(50 - barLength);
      const probPercent = (prob * 100).toFixed(0).padStart(3);
      const hourStr = String(hour).padStart(2, '0');

      report += `${hourStr}h: ${bar} ${probPercent}%\n`;
    }

    report += `\nPicos: ${this.getPeakHours().join(', ')}h\n`;
    report += `Vales: ${this.getValleyHours().join(', ')}h\n`;

    return report;
  }
}

export default ActivitySimulator;

