"use strict";
/**
 * Humanization Module - Exportações centralizadas
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.adaptiveConfigManager = exports.AdaptiveConfigManager = exports.AdaptiveConfig = exports.globalPatternDetector = exports.PatternDetector = exports.ACTIVITY_PATTERNS = exports.ActivitySimulator = exports.DEFAULT_LIFECYCLE_CONFIG = exports.sessionLifecycleManager = exports.SessionLifecycleManager = exports.SessionLifecycle = exports.DEFAULT_ORGANIC_CONFIG = exports.organicBehaviorManager = exports.OrganicBehaviorManager = exports.OrganicBehavior = exports.logHeaders = exports.compareHeaders = exports.varyHeadersPerRequest = exports.generateAPIHeaders = exports.generateWebSocketHeaders = exports.generateDynamicHeaders = exports.loadFingerprintFromJSON = exports.saveFingerprintToJSON = exports.generateCustomHeaders = exports.toBaileysConfig = exports.generateAdvancedFingerprint = exports.getDeviceStats = exports.selectDeviceByManufacturer = exports.selectRandomDevice = exports.DEVICE_PROFILES = exports.messageQueueManager = exports.MessageQueueManager = exports.MessageQueue = exports.TypingSimulator = exports.TIMING_PROFILES = exports.HumanTiming = void 0;
// ========== ETAPA 1: Timing e Typing ==========
var human_timing_1 = require("./human-timing");
Object.defineProperty(exports, "HumanTiming", { enumerable: true, get: function () { return human_timing_1.HumanTiming; } });
Object.defineProperty(exports, "TIMING_PROFILES", { enumerable: true, get: function () { return human_timing_1.TIMING_PROFILES; } });
var typing_simulator_1 = require("./typing-simulator");
Object.defineProperty(exports, "TypingSimulator", { enumerable: true, get: function () { return typing_simulator_1.TypingSimulator; } });
var message_queue_1 = require("./message-queue");
Object.defineProperty(exports, "MessageQueue", { enumerable: true, get: function () { return message_queue_1.MessageQueue; } });
Object.defineProperty(exports, "MessageQueueManager", { enumerable: true, get: function () { return message_queue_1.MessageQueueManager; } });
Object.defineProperty(exports, "messageQueueManager", { enumerable: true, get: function () { return message_queue_1.messageQueueManager; } });
// ========== ETAPA 2: Fingerprint Avançado ==========
var device_profiles_1 = require("./device-profiles");
Object.defineProperty(exports, "DEVICE_PROFILES", { enumerable: true, get: function () { return device_profiles_1.DEVICE_PROFILES; } });
Object.defineProperty(exports, "selectRandomDevice", { enumerable: true, get: function () { return device_profiles_1.selectRandomDevice; } });
Object.defineProperty(exports, "selectDeviceByManufacturer", { enumerable: true, get: function () { return device_profiles_1.selectDeviceByManufacturer; } });
Object.defineProperty(exports, "getDeviceStats", { enumerable: true, get: function () { return device_profiles_1.getDeviceStats; } });
var advanced_fingerprint_1 = require("./advanced-fingerprint");
Object.defineProperty(exports, "generateAdvancedFingerprint", { enumerable: true, get: function () { return advanced_fingerprint_1.generateAdvancedFingerprint; } });
Object.defineProperty(exports, "toBaileysConfig", { enumerable: true, get: function () { return advanced_fingerprint_1.toBaileysConfig; } });
Object.defineProperty(exports, "generateCustomHeaders", { enumerable: true, get: function () { return advanced_fingerprint_1.generateCustomHeaders; } });
Object.defineProperty(exports, "saveFingerprintToJSON", { enumerable: true, get: function () { return advanced_fingerprint_1.saveFingerprintToJSON; } });
Object.defineProperty(exports, "loadFingerprintFromJSON", { enumerable: true, get: function () { return advanced_fingerprint_1.loadFingerprintFromJSON; } });
var dynamic_headers_1 = require("./dynamic-headers");
Object.defineProperty(exports, "generateDynamicHeaders", { enumerable: true, get: function () { return dynamic_headers_1.generateDynamicHeaders; } });
Object.defineProperty(exports, "generateWebSocketHeaders", { enumerable: true, get: function () { return dynamic_headers_1.generateWebSocketHeaders; } });
Object.defineProperty(exports, "generateAPIHeaders", { enumerable: true, get: function () { return dynamic_headers_1.generateAPIHeaders; } });
Object.defineProperty(exports, "varyHeadersPerRequest", { enumerable: true, get: function () { return dynamic_headers_1.varyHeadersPerRequest; } });
Object.defineProperty(exports, "compareHeaders", { enumerable: true, get: function () { return dynamic_headers_1.compareHeaders; } });
Object.defineProperty(exports, "logHeaders", { enumerable: true, get: function () { return dynamic_headers_1.logHeaders; } });
// ========== ETAPA 3: Comportamento Orgânico ==========
var organic_behavior_1 = require("./organic-behavior");
Object.defineProperty(exports, "OrganicBehavior", { enumerable: true, get: function () { return organic_behavior_1.OrganicBehavior; } });
Object.defineProperty(exports, "OrganicBehaviorManager", { enumerable: true, get: function () { return organic_behavior_1.OrganicBehaviorManager; } });
Object.defineProperty(exports, "organicBehaviorManager", { enumerable: true, get: function () { return organic_behavior_1.organicBehaviorManager; } });
Object.defineProperty(exports, "DEFAULT_ORGANIC_CONFIG", { enumerable: true, get: function () { return organic_behavior_1.DEFAULT_ORGANIC_CONFIG; } });
var session_lifecycle_1 = require("./session-lifecycle");
Object.defineProperty(exports, "SessionLifecycle", { enumerable: true, get: function () { return session_lifecycle_1.SessionLifecycle; } });
Object.defineProperty(exports, "SessionLifecycleManager", { enumerable: true, get: function () { return session_lifecycle_1.SessionLifecycleManager; } });
Object.defineProperty(exports, "sessionLifecycleManager", { enumerable: true, get: function () { return session_lifecycle_1.sessionLifecycleManager; } });
Object.defineProperty(exports, "DEFAULT_LIFECYCLE_CONFIG", { enumerable: true, get: function () { return session_lifecycle_1.DEFAULT_LIFECYCLE_CONFIG; } });
var activity_simulator_1 = require("./activity-simulator");
Object.defineProperty(exports, "ActivitySimulator", { enumerable: true, get: function () { return activity_simulator_1.ActivitySimulator; } });
Object.defineProperty(exports, "ACTIVITY_PATTERNS", { enumerable: true, get: function () { return activity_simulator_1.ACTIVITY_PATTERNS; } });
// ========== ETAPA 4: Monitoramento e Ajuste Adaptativo ==========
var pattern_detector_1 = require("./pattern-detector");
Object.defineProperty(exports, "PatternDetector", { enumerable: true, get: function () { return pattern_detector_1.PatternDetector; } });
Object.defineProperty(exports, "globalPatternDetector", { enumerable: true, get: function () { return pattern_detector_1.globalPatternDetector; } });
var adaptive_config_1 = require("./adaptive-config");
Object.defineProperty(exports, "AdaptiveConfig", { enumerable: true, get: function () { return adaptive_config_1.AdaptiveConfig; } });
Object.defineProperty(exports, "AdaptiveConfigManager", { enumerable: true, get: function () { return adaptive_config_1.AdaptiveConfigManager; } });
Object.defineProperty(exports, "adaptiveConfigManager", { enumerable: true, get: function () { return adaptive_config_1.adaptiveConfigManager; } });
