/**
 * Pattern Detector - Detecta padrões nos nossos próprios comportamentos
 * 
 * Analisa se estamos criando padrões detectáveis em:
 * - Timings repetitivos
 * - Fingerprints similares
 * - Horários de criação
 * - Intervalos entre ações
 */

export interface PatternAnalysis {
  diversityScore: number;        // 0-100 (quanto maior, melhor)
  detectedPatterns: string[];
  warnings: string[];
  recommendations: string[];
  metrics: {
    timingVariance: number;
    fingerprintDiversity: number;
    hourlyDistribution: number[];
    actionIntervalStdDev: number;
  };
}

export interface SessionEvent {
  timestamp: Date;
  type: 'creation' | 'action' | 'reconnect' | 'error';
  tenantId: string;
  chipId: string;
  metadata?: Record<string, any>;
}

/**
 * Detector de padrões
 */
export class PatternDetector {
  private events: SessionEvent[] = [];
  private readonly MAX_EVENTS = 1000; // Manter últimos 1000 eventos

  /**
   * Registra um evento
   */
  public recordEvent(event: SessionEvent): void {
    this.events.push(event);

    // Limitar tamanho do histórico
    if (this.events.length > this.MAX_EVENTS) {
      this.events.shift();
    }
  }

  /**
   * Analisa padrões nos eventos
   */
  public analyze(): PatternAnalysis {
    const analysis: PatternAnalysis = {
      diversityScore: 100,
      detectedPatterns: [],
      warnings: [],
      recommendations: [],
      metrics: {
        timingVariance: 0,
        fingerprintDiversity: 0,
        hourlyDistribution: Array(24).fill(0),
        actionIntervalStdDev: 0
      }
    };

    if (this.events.length < 10) {
      analysis.warnings.push('Poucos eventos para análise significativa (mínimo: 10)');
      return analysis;
    }

    // Analisar diferentes aspectos
    this.analyzeTimingPatterns(analysis);
    this.analyzeHourlyDistribution(analysis);
    this.analyzeActionIntervals(analysis);
    this.analyzeTenantDistribution(analysis);

    // Calcular diversity score final
    analysis.diversityScore = this.calculateDiversityScore(analysis);

    // Gerar recomendações
    this.generateRecommendations(analysis);

    return analysis;
  }

  /**
   * Analisa padrões de timing
   */
  private analyzeTimingPatterns(analysis: PatternAnalysis): void {
    const creationEvents = this.events.filter(e => e.type === 'creation');
    if (creationEvents.length < 5) return;

    // Calcular intervalos entre criações
    const intervals: number[] = [];
    for (let i = 1; i < creationEvents.length; i++) {
      const interval = creationEvents[i].timestamp.getTime() - creationEvents[i - 1].timestamp.getTime();
      intervals.push(interval);
    }

    // Calcular variância
    const mean = intervals.reduce((a, b) => a + b, 0) / intervals.length;
    const variance = intervals.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / intervals.length;
    const stdDev = Math.sqrt(variance);
    const coefficientOfVariation = stdDev / mean;

    analysis.metrics.timingVariance = coefficientOfVariation;

    // Detectar padrão se variação for muito baixa
    if (coefficientOfVariation < 0.3) {
      analysis.detectedPatterns.push(
        `Timing de criação muito regular (CV: ${(coefficientOfVariation * 100).toFixed(1)}%)`
      );
      analysis.warnings.push(
        'Intervalos entre criações muito uniformes - WhatsApp pode detectar'
      );
    }

    // Detectar criações muito rápidas
    const fastCreations = intervals.filter(i => i < 60000).length; // < 1min
    if (fastCreations / intervals.length > 0.3) {
      analysis.detectedPatterns.push(
        `${fastCreations} criações muito rápidas (< 1min)`
      );
      analysis.warnings.push(
        'Muitas sessões criadas rapidamente - aumentar delays'
      );
    }
  }

  /**
   * Analisa distribuição por hora do dia
   */
  private analyzeHourlyDistribution(analysis: PatternAnalysis): void {
    // Contar eventos por hora
    for (const event of this.events) {
      const hour = event.timestamp.getHours();
      analysis.metrics.hourlyDistribution[hour]++;
    }

    // Normalizar
    const total = this.events.length;
    analysis.metrics.hourlyDistribution = analysis.metrics.hourlyDistribution.map(
      count => (count / total) * 100
    );

    // Detectar concentração em horários específicos
    const maxHourlyPercent = Math.max(...analysis.metrics.hourlyDistribution);
    if (maxHourlyPercent > 30) {
      const peakHour = analysis.metrics.hourlyDistribution.indexOf(maxHourlyPercent);
      analysis.detectedPatterns.push(
        `${maxHourlyPercent.toFixed(1)}% dos eventos concentrados às ${peakHour}h`
      );
      analysis.warnings.push(
        'Distribuição horária muito concentrada - variar horários de criação'
      );
    }

    // Detectar ausência completa em horários (não-humano)
    const zeroHours = analysis.metrics.hourlyDistribution.filter(p => p === 0).length;
    if (zeroHours > 8) {
      analysis.detectedPatterns.push(
        `${zeroHours} horas sem nenhuma atividade`
      );
      analysis.warnings.push(
        'Ausência total em muitas horas - não parece humano'
      );
    }
  }

  /**
   * Analisa intervalos entre ações
   */
  private analyzeActionIntervals(analysis: PatternAnalysis): void {
    const actionEvents = this.events.filter(e => e.type === 'action');
    if (actionEvents.length < 10) return;

    // Calcular intervalos
    const intervals: number[] = [];
    for (let i = 1; i < actionEvents.length; i++) {
      const interval = actionEvents[i].timestamp.getTime() - actionEvents[i - 1].timestamp.getTime();
      intervals.push(interval);
    }

    // Calcular desvio padrão
    const mean = intervals.reduce((a, b) => a + b, 0) / intervals.length;
    const variance = intervals.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / intervals.length;
    const stdDev = Math.sqrt(variance);

    analysis.metrics.actionIntervalStdDev = stdDev;

    // Detectar intervalos muito regulares
    const coefficientOfVariation = stdDev / mean;
    if (coefficientOfVariation < 0.4) {
      analysis.detectedPatterns.push(
        `Intervalos entre ações muito regulares (CV: ${(coefficientOfVariation * 100).toFixed(1)}%)`
      );
      analysis.warnings.push(
        'Ações muito uniformes - adicionar mais variação'
      );
    }
  }

  /**
   * Analisa distribuição por tenant
   */
  private analyzeTenantDistribution(analysis: PatternAnalysis): void {
    const tenantCounts = new Map<string, number>();

    for (const event of this.events) {
      const count = tenantCounts.get(event.tenantId) || 0;
      tenantCounts.set(event.tenantId, count + 1);
    }

    // Calcular diversidade de tenants
    const uniqueTenants = tenantCounts.size;
    const totalEvents = this.events.length;
    const avgEventsPerTenant = totalEvents / uniqueTenants;

    analysis.metrics.fingerprintDiversity = uniqueTenants;

    // Detectar concentração em poucos tenants
    const sortedCounts = Array.from(tenantCounts.values()).sort((a, b) => b - a);
    const top3Percent = (sortedCounts.slice(0, 3).reduce((a, b) => a + b, 0) / totalEvents) * 100;

    if (top3Percent > 70 && uniqueTenants > 3) {
      analysis.detectedPatterns.push(
        `${top3Percent.toFixed(1)}% dos eventos concentrados em 3 tenants`
      );
      analysis.warnings.push(
        'Atividade muito concentrada em poucos tenants'
      );
    }
  }

  /**
   * Calcula score de diversidade geral (0-100)
   */
  private calculateDiversityScore(analysis: PatternAnalysis): number {
    let score = 100;

    // Penalizar por cada padrão detectado
    score -= analysis.detectedPatterns.length * 10;

    // Penalizar timing muito regular
    if (analysis.metrics.timingVariance < 0.3) {
      score -= 20;
    } else if (analysis.metrics.timingVariance < 0.5) {
      score -= 10;
    }

    // Penalizar distribuição horária concentrada
    const maxHourly = Math.max(...analysis.metrics.hourlyDistribution);
    if (maxHourly > 30) {
      score -= 15;
    } else if (maxHourly > 20) {
      score -= 5;
    }

    // Penalizar ações muito regulares
    const actionEvents = this.events.filter(e => e.type === 'action').length;
    if (actionEvents >= 10) {
      const mean = analysis.metrics.actionIntervalStdDev;
      // Calcular CV aproximado (não temos mean armazenado, usar heurística)
      const estimatedCV = mean / 300000; // Assumir média ~5min
      if (estimatedCV < 0.4) {
        score -= 15;
      }
    }

    // Garantir score entre 0-100
    return Math.max(0, Math.min(100, score));
  }

  /**
   * Gera recomendações baseadas na análise
   */
  private generateRecommendations(analysis: PatternAnalysis): void {
    // Timing
    if (analysis.metrics.timingVariance < 0.5) {
      analysis.recommendations.push(
        '🎲 Aumentar variação nos delays de criação (usar jitter > 30%)'
      );
    }

    // Distribuição horária
    const maxHourly = Math.max(...analysis.metrics.hourlyDistribution);
    if (maxHourly > 20) {
      analysis.recommendations.push(
        '⏰ Distribuir criações ao longo do dia (usar ActivitySimulator)'
      );
    }

    const zeroHours = analysis.metrics.hourlyDistribution.filter(p => p === 0).length;
    if (zeroHours > 6) {
      analysis.recommendations.push(
        '🌙 Criar algumas sessões em horários variados (incluir madrugada)'
      );
    }

    // Ações
    if (analysis.metrics.actionIntervalStdDev > 0 && analysis.metrics.actionIntervalStdDev < 120000) {
      analysis.recommendations.push(
        '📝 Aumentar variação nos intervalos entre ações (usar perfis de timing diferentes)'
      );
    }

    // Score geral
    if (analysis.diversityScore < 50) {
      analysis.recommendations.push(
        '⚠️ CRÍTICO: Diversidade muito baixa - revisar toda a estratégia de humanização'
      );
    } else if (analysis.diversityScore < 70) {
      analysis.recommendations.push(
        '⚡ Diversidade moderada - aplicar algumas melhorias sugeridas'
      );
    } else if (analysis.diversityScore >= 90) {
      analysis.recommendations.push(
        '✅ Excelente diversidade - manter estratégia atual'
      );
    }
  }

  /**
   * Retorna eventos recentes
   */
  public getRecentEvents(limit: number = 50): SessionEvent[] {
    return this.events.slice(-limit);
  }

  /**
   * Limpa eventos antigos
   */
  public clearOldEvents(olderThanMs: number = 86400000): number {
    const cutoff = Date.now() - olderThanMs;
    const initialLength = this.events.length;

    this.events = this.events.filter(e => e.timestamp.getTime() > cutoff);

    const removed = initialLength - this.events.length;
    console.log(
      `[PatternDetector] 🧹 Removidos ${removed} eventos antigos ` +
      `(${this.events.length} restantes)`
    );

    return removed;
  }

  /**
   * Retorna estatísticas gerais
   */
  public getStats(): {
    totalEvents: number;
    eventsByType: Record<string, number>;
    timeRange: { start: Date | null; end: Date | null };
    uniqueTenants: number;
  } {
    const eventsByType: Record<string, number> = {};
    const tenants = new Set<string>();

    for (const event of this.events) {
      eventsByType[event.type] = (eventsByType[event.type] || 0) + 1;
      tenants.add(event.tenantId);
    }

    return {
      totalEvents: this.events.length,
      eventsByType,
      timeRange: {
        start: this.events.length > 0 ? this.events[0].timestamp : null,
        end: this.events.length > 0 ? this.events[this.events.length - 1].timestamp : null
      },
      uniqueTenants: tenants.size
    };
  }

  /**
   * Gera relatório visual (ASCII)
   */
  public generateReport(): string {
    const analysis = this.analyze();
    const stats = this.getStats();

    let report = '\n';
    report += '╔══════════════════════════════════════════════════════════╗\n';
    report += '║         PATTERN DETECTOR - RELATÓRIO DE ANÁLISE          ║\n';
    report += '╚══════════════════════════════════════════════════════════╝\n\n';

    // Stats gerais
    report += `📊 Estatísticas Gerais:\n`;
    report += `  Total de eventos: ${stats.totalEvents}\n`;
    report += `  Tenants únicos: ${stats.uniqueTenants}\n`;
    report += `  Período: ${stats.timeRange.start?.toLocaleString('pt-BR')} → ${stats.timeRange.end?.toLocaleString('pt-BR')}\n`;
    report += `  Por tipo: ${Object.entries(stats.eventsByType).map(([k, v]) => `${k}=${v}`).join(', ')}\n\n`;

    // Diversity Score
    const scoreEmoji = analysis.diversityScore >= 80 ? '✅' : analysis.diversityScore >= 60 ? '⚠️' : '🚨';
    report += `${scoreEmoji} DIVERSITY SCORE: ${analysis.diversityScore.toFixed(1)}/100\n\n`;

    // Métricas
    report += `📈 Métricas:\n`;
    report += `  Variação de timing: ${(analysis.metrics.timingVariance * 100).toFixed(1)}% (ideal: >50%)\n`;
    report += `  Diversidade de fingerprints: ${analysis.metrics.fingerprintDiversity}\n`;
    report += `  Desvio padrão de ações: ${(analysis.metrics.actionIntervalStdDev / 1000).toFixed(1)}s\n\n`;

    // Distribuição horária (visual)
    report += `⏰ Distribuição Horária:\n`;
    const maxBar = 40;
    const maxPercent = Math.max(...analysis.metrics.hourlyDistribution);
    for (let hour = 0; hour < 24; hour++) {
      const percent = analysis.metrics.hourlyDistribution[hour];
      const barLength = Math.round((percent / Math.max(maxPercent, 10)) * maxBar);
      const bar = '█'.repeat(barLength) + '░'.repeat(maxBar - barLength);
      const hourStr = String(hour).padStart(2, '0');
      report += `  ${hourStr}h: ${bar} ${percent.toFixed(1)}%\n`;
    }
    report += '\n';

    // Padrões detectados
    if (analysis.detectedPatterns.length > 0) {
      report += `🔍 Padrões Detectados:\n`;
      for (const pattern of analysis.detectedPatterns) {
        report += `  • ${pattern}\n`;
      }
      report += '\n';
    }

    // Warnings
    if (analysis.warnings.length > 0) {
      report += `⚠️  Avisos:\n`;
      for (const warning of analysis.warnings) {
        report += `  ⚠️  ${warning}\n`;
      }
      report += '\n';
    }

    // Recomendações
    if (analysis.recommendations.length > 0) {
      report += `💡 Recomendações:\n`;
      for (const rec of analysis.recommendations) {
        report += `  ${rec}\n`;
      }
      report += '\n';
    }

    report += '═══════════════════════════════════════════════════════════\n';

    return report;
  }
}

// Singleton global
export const globalPatternDetector = new PatternDetector();

export default PatternDetector;

