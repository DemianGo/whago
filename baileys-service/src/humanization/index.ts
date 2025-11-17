/**
 * Humanization Module - Exportações centralizadas
 */

// ========== ETAPA 1: Timing e Typing ==========
export { HumanTiming, TIMING_PROFILES } from './human-timing';
export type { TimingProfile } from './human-timing';

export { TypingSimulator } from './typing-simulator';
export type { TypingSimulationOptions, SimulationResult } from './typing-simulator';

export { MessageQueue, MessageQueueManager, messageQueueManager } from './message-queue';
export type { QueuedMessage, QueueStats } from './message-queue';

// ========== ETAPA 2: Fingerprint Avançado ==========
export { 
  DEVICE_PROFILES, 
  selectRandomDevice, 
  selectDeviceByManufacturer, 
  getDeviceStats 
} from './device-profiles';
export type { DeviceProfile } from './device-profiles';

export {
  generateAdvancedFingerprint,
  toBaileysConfig,
  generateCustomHeaders,
  saveFingerprintToJSON,
  loadFingerprintFromJSON
} from './advanced-fingerprint';
export type { AdvancedFingerprint } from './advanced-fingerprint';

export {
  generateDynamicHeaders,
  generateWebSocketHeaders,
  generateAPIHeaders,
  varyHeadersPerRequest,
  compareHeaders,
  logHeaders
} from './dynamic-headers';
export type { DynamicHeadersOptions } from './dynamic-headers';

// ========== ETAPA 3: Comportamento Orgânico ==========
export {
  OrganicBehavior,
  OrganicBehaviorManager,
  organicBehaviorManager,
  DEFAULT_ORGANIC_CONFIG
} from './organic-behavior';
export type { OrganicBehaviorConfig } from './organic-behavior';

export {
  SessionLifecycle,
  SessionLifecycleManager,
  sessionLifecycleManager,
  DEFAULT_LIFECYCLE_CONFIG
} from './session-lifecycle';
export type { SessionLifecycleConfig, ConnectionHealth } from './session-lifecycle';

export {
  ActivitySimulator,
  ACTIVITY_PATTERNS
} from './activity-simulator';
export type { ActivityPattern } from './activity-simulator';

// ========== ETAPA 4: Monitoramento e Ajuste Adaptativo ==========
export {
  PatternDetector,
  globalPatternDetector
} from './pattern-detector';
export type { PatternAnalysis, SessionEvent } from './pattern-detector';

export {
  AdaptiveConfig,
  AdaptiveConfigManager,
  adaptiveConfigManager
} from './adaptive-config';
export type { AdaptiveMetrics, ConfigAdjustment, AdaptiveStrategy } from './adaptive-config';

