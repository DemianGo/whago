"use strict";

/**
 * Servidor Express com integração completa do Sistema Anti-Block
 * 
 * ETAPAS INTEGRADAS:
 * 1. Humanização de Timing e Typing (8 perfis, anti-burst)
 * 2. Fingerprint Avançado (60+ dispositivos, headers dinâmicos)
 * 3. Comportamento Orgânico (ações automáticas, 6 padrões)
 * 4. Monitoramento Adaptativo (pattern detector, auto-ajuste)
 */

const http = require("http");
const fs = require("fs");
const path = require("path");

const cors = require("cors");
const express = require("express");
const helmet = require("helmet");
const morgan = require("morgan");
const { Server } = require("socket.io");
const { v4: uuidv4 } = require("uuid");
const NodeCache = require("node-cache");
const QRCode = require("qrcode");
const makeWASocket = require("@whiskeysockets/baileys").default;
const { useMultiFileAuthState, DisconnectReason, makeCacheableSignalKeyStore, Browsers } = require("@whiskeysockets/baileys");
const pino = require("pino");

// Importar módulo de proxy (isolado e opcional)
const proxyManager = require("./proxy-manager");

// ========== IMPORTAR SISTEMA ANTI-BLOCK ==========
const {
  // Etapa 1: Humanização
  messageQueueManager,
  TIMING_PROFILES,
  
  // Etapa 2: Fingerprint
  generateAdvancedFingerprint,
  toBaileysConfig,
  generateDynamicHeaders,
  getDeviceStats,
  
  // Etapa 3: Comportamento Orgânico
  organicBehaviorManager,
  sessionLifecycleManager,
  ActivitySimulator,
  ACTIVITY_PATTERNS,
  
  // Etapa 4: Monitoramento
  globalPatternDetector,
  adaptiveConfigManager
} = require("./humanization");

const createServer = (config = {}) => {
  const app = express();
  const httpServer = http.createServer(app);

  const io = new Server(httpServer, {
    cors: {
      origin: config.cors?.origins || ["http://localhost:3000", "http://localhost:8000"],
      methods: ["GET", "POST", "DELETE"],
      credentials: true,
    },
  });

  // Middlewares base
  app.use(helmet({ crossOriginResourcePolicy: false }));
  app.use(
    cors({
      origin: config.cors?.origins || "*",
      credentials: true,
    }),
  );
  app.use(express.json({ limit: "2mb" }));
  app.use(express.urlencoded({ extended: true }));
  app.use(morgan(config.logFormat || "dev"));

  const sessions = new NodeCache({ stdTTL: 60 * 60, checkperiod: 120 });
  const messageLog = new NodeCache({ stdTTL: 60 * 60, checkperiod: 300 });
  const sockets = new Map(); // Store Baileys socket instances
  
  // ========== MAPS PARA SISTEMA ANTI-BLOCK ==========
  const sessionFingerprints = new Map(); // session_id -> AdvancedFingerprint
  const messageQueues = new Map();       // session_id -> MessageQueue
  
  // Controle de tentativas de conexão (prevenir erro 515)
  const connectionAttempts = new Map(); // sessionId -> { count, lastAttempt, blockedUntil }
  const MAX_CONNECTION_ATTEMPTS = 3;
  const COOLDOWN_MINUTES = 10;
  const ATTEMPT_WINDOW_MS = 30 * 60 * 1000; // 30 minutos
  
  const sessionsDir = config.sessionsDir || path.resolve(__dirname, "../sessions");
  if (!fs.existsSync(sessionsDir)) {
    fs.mkdirSync(sessionsDir, { recursive: true });
  }

  /**
   * Verifica se uma sessão pode tentar conectar (rate limiting)
   */
  function checkConnectionAllowed(sessionId) {
    const now = Date.now();
    const attempt = connectionAttempts.get(sessionId);
    
    if (!attempt) {
      connectionAttempts.set(sessionId, {
        count: 1,
        lastAttempt: now,
        blockedUntil: null,
      });
      return { allowed: true };
    }
    
    // Verificar se está em cooldown
    if (attempt.blockedUntil && now < attempt.blockedUntil) {
      const waitMinutes = Math.ceil((attempt.blockedUntil - now) / 60000);
      return {
        allowed: false,
        reason: `Muitas tentativas de conexão. Aguarde ${waitMinutes} minutos.`,
        waitMinutes,
      };
    }
    
    // Resetar contador se passou a janela de tempo
    if (now - attempt.lastAttempt > ATTEMPT_WINDOW_MS) {
      connectionAttempts.set(sessionId, {
        count: 1,
        lastAttempt: now,
        blockedUntil: null,
      });
      return { allowed: true };
    }
    
    // Incrementar contador
    attempt.count++;
    attempt.lastAttempt = now;
    
    if (attempt.count > MAX_CONNECTION_ATTEMPTS) {
      attempt.blockedUntil = now + (COOLDOWN_MINUTES * 60 * 1000);
      connectionAttempts.set(sessionId, attempt);
      return {
        allowed: false,
        reason: `Limite de ${MAX_CONNECTION_ATTEMPTS} tentativas excedido. Aguarde ${COOLDOWN_MINUTES} minutos.`,
        waitMinutes: COOLDOWN_MINUTES,
      };
    }
    
    connectionAttempts.set(sessionId, attempt);
    return { allowed: true, attemptsLeft: MAX_CONNECTION_ATTEMPTS - attempt.count };
  }
  
  /**
   * Registra falha de conexão
   */
  function recordConnectionFailure(sessionId) {
    const attempt = connectionAttempts.get(sessionId);
    if (attempt) {
      attempt.count += 2;
      attempt.blockedUntil = Date.now() + (COOLDOWN_MINUTES * 60 * 1000);
      connectionAttempts.set(sessionId, attempt);
    }
  }

  // ========== HEALTH CHECK ==========
  app.get("/health", (_req, res) => {
    res.json({ status: "ok", uptime: process.uptime() });
  });

  const router = express.Router();

  router.get("/status", (_req, res) => {
    res.json({ 
      service: "baileys-antiblock", 
      version: "1.0.0", 
      timestamp: new Date().toISOString(),
      proxy: proxyManager.getInfo(),
      antiBlock: {
        diversityScore: globalPatternDetector.analyze().diversityScore,
        activeSessions: sockets.size,
        messageQueues: messageQueues.size
      }
    });
  });

  // ========== CRIAR SESSÃO COM ANTI-BLOCK ==========
  router.post("/sessions/create", async (req, res) => {
    const { 
      alias, 
      proxy_url, 
      tenant_id, 
      user_id,
      preferred_manufacturer, 
      timing_profile,
      activity_pattern 
    } = req.body || {};
    
    if (!alias || typeof alias !== "string") {
      return res.status(400).json({ error: "Alias inválido." });
    }
    
    const sessionId = uuidv4();
    const tenantId = tenant_id || 'default';
    const userId = user_id || tenantId;
    
    // Verificar rate limiting básico
    const rateLimitCheck = checkConnectionAllowed(sessionId);
    if (!rateLimitCheck.allowed) {
      console.log(`[Session ${sessionId}] Connection blocked: ${rateLimitCheck.reason}`);
      return res.status(429).json({
        error: rateLimitCheck.reason,
        wait_minutes: rateLimitCheck.waitMinutes,
        retry_after: rateLimitCheck.waitMinutes * 60,
      });
    }
    
    // ===== ETAPA 4: VERIFICAR COOLDOWN ADAPTATIVO =====
    const adaptiveConfig = adaptiveConfigManager.getConfig(tenantId);
    const currentConfig = adaptiveConfig.getCurrentConfig();
    
    const sessionPath = path.join(sessionsDir, sessionId);
    
    try {
      console.log(`[Session ${sessionId}] Creating session at path: ${sessionPath}`);
      const { state, saveCreds } = await useMultiFileAuthState(sessionPath);
      console.log(`[Session ${sessionId}] Auth state loaded, has creds: ${!!state.creds}`);
      
      // ===== ETAPA 2: GERAR FINGERPRINT AVANÇADO =====
      const fingerprint = generateAdvancedFingerprint(
        tenantId,
        sessionId,
        preferred_manufacturer
      );
      
      sessionFingerprints.set(sessionId, fingerprint);
      
      console.log(
        `[Session ${sessionId}] 🎭 Fingerprint gerado:`,
        `\n  Device: ${fingerprint.device.manufacturer} ${fingerprint.device.marketName}`,
        `\n  Android: ${fingerprint.os.version} (SDK ${fingerprint.os.sdkVersion})`,
        `\n  Chrome: ${fingerprint.browser.version}`,
        `\n  Screen: ${fingerprint.screen.width}x${fingerprint.screen.height} @${fingerprint.screen.pixelRatio}x`,
        `\n  GPU: ${fingerprint.features.webGLVendor} ${fingerprint.features.webGLRenderer}`
      );
      
      // Converter para config do Baileys
      const baileysFingerprint = toBaileysConfig(fingerprint);
      
      // Gerar headers dinâmicos
      const customHeaders = generateDynamicHeaders(fingerprint, {
        includeOptional: true,
        randomizeOrder: true,
        varyValues: true
      });
      
      // ===== ETAPA 3: CRIAR LIFECYCLE PARA KEEPALIVE VARIÁVEL =====
      const tempLifecycle = sessionLifecycleManager.register(
        null, // socket ainda não existe
        tenantId,
        sessionId,
        {
          keepAliveMin: 90000,
          keepAliveMax: 150000,
          retryStrategy: currentConfig.retryStrategy || 'exponential'
        }
      );
      
      const variableKeepAlive = tempLifecycle.generateKeepAlive();
      
      // Remover lifecycle temporário (será recriado ao conectar)
      sessionLifecycleManager.unregister(tenantId, sessionId);
      
      // CRÍTICO: Usar makeCacheableSignalKeyStore
      const authState = {
        creds: state.creds,
        keys: makeCacheableSignalKeyStore(state.keys, pino({ level: 'silent' })),
      };
      
      // ===== CONFIGURAÇÃO COM ANTI-BLOCK =====
      const socketConfig = {
        auth: authState,
        logger: pino({ level: 'silent' }),
        printQRInTerminal: false,
        
        // ✅ ETAPA 2: FINGERPRINT
        browser: baileysFingerprint.browser,
        manufacturer: baileysFingerprint.manufacturer,
        
        // ✅ ETAPA 3: KEEPALIVE VARIÁVEL
        keepAliveIntervalMs: variableKeepAlive,
        
        // ✅ ETAPA 1: RETRY COM VARIAÇÃO
        retryRequestDelayMs: 2000 + Math.floor(Math.random() * 1000), // 2-3s
        
        // Timeouts generosos
        connectTimeoutMs: 120000,
        defaultQueryTimeoutMs: 120000,
        qrTimeout: 90000,
        
        // Comportamento PASSIVO
        syncFullHistory: false,
        fireInitQueries: false,
        emitOwnEvents: false,
        generateHighQualityLinkPreview: false,
        markOnlineOnConnect: false,
        
        getMessage: async () => undefined,
        shouldSyncHistoryMessage: () => false,
        shouldIgnoreJid: () => false,
        patchMessageBeforeSending: (msg) => msg,
      };
      
      // ===== PROXY =====
      let proxyAgent = null;
      let usedProxyUrl = proxy_url;
      
      if (usedProxyUrl) {
        const proxyHost = usedProxyUrl.split('@')[1] || 'unknown';
        const proxyUser = usedProxyUrl.split('://')[1]?.split(':')[0] || 'unknown';
        console.log(`[Session ${sessionId}] 🌐 Proxy: ${proxyUser}@${proxyHost}`);
        
        // ✅ DETECTAR TIPO DE PROXY AUTOMATICAMENTE
        const isSocks = usedProxyUrl.startsWith('socks://') || usedProxyUrl.startsWith('socks5://') || usedProxyUrl.startsWith('socks4://');
        
        if (isSocks) {
          // Usar SOCKS Proxy Agent (DataImpulse, etc)
          const { SocksProxyAgent } = require('socks-proxy-agent');
          proxyAgent = new SocksProxyAgent(usedProxyUrl, {
            family: 4  // ✅ Forçar IPv4
          });
          console.log(`[Session ${sessionId}] ✅ SocksProxyAgent (IPv4) criado (suporta WebSocket)`);
        } else {
          // Usar HTTPS Proxy Agent (Smartproxy, Bright Data, etc)
          const { HttpsProxyAgent } = require('https-proxy-agent');
          proxyAgent = new HttpsProxyAgent(usedProxyUrl, {
            headers: customHeaders,
            family: 4  // ✅ Forçar IPv4 (proxies mobile geralmente não suportam IPv6)
          });
          console.log(`[Session ${sessionId}] ✅ HttpsProxyAgent (IPv4) com headers customizados criado`);
        }
      } else if (proxyManager.getAgent()) {
        console.log(`[Session ${sessionId}] 🌐 Usando proxy global`);
        proxyAgent = proxyManager.getAgent();
      }
      
      // ⚠️ CRÍTICO: Proxy é ALTAMENTE recomendado para evitar detecção
      if (!proxyAgent) {
        console.log(`[Session ${sessionId}] ⚠️⚠️⚠️ SEM PROXY - Alto risco de ban!`);
        console.log(`[Session ${sessionId}] Recomendação: Use proxy mobile brasileiro`);
      }
      
      if (proxyAgent) {
        socketConfig.agent = proxyAgent;
        socketConfig.fetchAgent = proxyAgent;
        console.log(`[Session ${sessionId}] 🔒 Proxy agent + fetchAgent com headers customizados aplicados`);
      } else {
        // Sem proxy, tentar injetar headers via options do Baileys
        socketConfig.options = {
          headers: customHeaders
        };
        console.log(`[Session ${sessionId}] ⚠️ Headers customizados aplicados ao socketConfig.options`);
      }
      
      // Criar socket
      const sock = makeWASocket(socketConfig);
      
      // Armazenar
      sockets.set(sessionId, sock);
      
      // ===== HANDLE CONNECTION UPDATES =====
      sock.ev.on("connection.update", async (update) => {
        const { connection, lastDisconnect, qr } = update;

        console.log(`[Session ${sessionId}] Connection update:`, {
          connection,
          lastDisconnect: lastDisconnect ? {
            error: lastDisconnect.error?.message,
            statusCode: lastDisconnect.error?.output?.statusCode
          } : null,
          hasQR: !!qr
        });

        // QR Code
        if (qr && qr.length > 0) {
          try {
            console.log(`[Session ${sessionId}] Generating QR code...`);
            const qrDataUrl = await QRCode.toDataURL(qr);
            const sessionData = sessions.get(sessionId) || {};
            sessionData.qr_code = qrDataUrl;
            sessionData.qr_expires_at = new Date(Date.now() + 60_000).toISOString();
            sessions.set(sessionId, sessionData);

            // Emitir via Socket.IO
            io.to(sessionId).emit("qr_updated", { 
              session_id: sessionId, 
              qr_code: qrDataUrl,
              expires_at: sessionData.qr_expires_at
            });

            console.log(`[Session ${sessionId}] QR code generated and emitted`);
          } catch (error) {
            console.error(`[Session ${sessionId}] Error generating QR:`, error);
          }
        }

        // CONEXÃO ESTABELECIDA
        if (connection === "open") {
          console.log(`[Session ${sessionId}] ✅ Connection opened successfully`);
          
          // ===== ETAPA 4: REGISTRAR SUCESSO =====
          adaptiveConfig.recordAttempt(true);
          
          // ===== ETAPA 4: REGISTRAR NO PATTERN DETECTOR =====
          globalPatternDetector.recordEvent({
            timestamp: new Date(),
            type: 'creation',
            tenantId,
            chipId: sessionId,
            metadata: {
              fingerprint: fingerprint.device.marketName,
              profile: timing_profile || 'normal'
            }
          });
          
          // ===== ETAPA 1: CRIAR MESSAGE QUEUE =====
          const timingProfileName = timing_profile || currentConfig.timingProfile || 'normal';
          const queue = messageQueueManager.getQueue(
            sock,
            tenantId,
            sessionId,
            timingProfileName
          );
          messageQueues.set(sessionId, queue);
          console.log(`[Session ${sessionId}] 📬 MessageQueue criada (perfil: ${timingProfileName})`);
          
          // ===== ETAPA 3: CRIAR LIFECYCLE =====
          const lifecycle = sessionLifecycleManager.register(
            sock,
            tenantId,
            sessionId,
            {
              keepAliveMin: 90000,
              keepAliveMax: 150000,
              enableAutoReconnect: true,
              reconnectDelayMin: 30000,
              reconnectDelayMax: 120000,
              maxReconnectAttempts: 5,
              retryStrategy: currentConfig.retryStrategy || 'exponential'
            }
          );
          
          lifecycle.start();
          lifecycle.onConnectionSuccess();
          
          // ===== ETAPA 3: CRIAR ORGANIC BEHAVIOR =====
          const behavior = organicBehaviorManager.register(
            sock,
            tenantId,
            sessionId,
            {
              enabled: true,
              readUnreadOnConnect: true,
              maxMessagesToRead: 3,
              viewStatuses: true,
              maxStatusesToView: 2,
              updatePresence: true,
              actionIntervalMin: 300000,  // 5min
              actionIntervalMax: 900000   // 15min
            }
          );
          
          behavior.start();
          
          // ===== ETAPA 3: ACTIVITY SIMULATOR =====
          const activityPatternName = activity_pattern || currentConfig.activityPattern || 'balanced';
          const activitySimulator = new ActivitySimulator(tenantId, sessionId, activityPatternName);
          
          console.log(
            `[Session ${sessionId}] 🤖 Activity Pattern: ${activityPatternName} | ` +
            `Prob. online agora: ${(activitySimulator.getCurrentProbability() * 100).toFixed(0)}%`
          );
          
          // Resetar tentativas
          connectionAttempts.delete(sessionId);
          
          // Emitir evento de conexão
          io.to(sessionId).emit("connection_ready", {
            session_id: sessionId,
            status: "authenticated",
            timestamp: new Date().toISOString()
          });
        }

        // CONEXÃO FECHADA
        if (connection === "close") {
          const errorCode = lastDisconnect?.error?.output?.statusCode;
          const shouldReconnect = errorCode !== DisconnectReason.loggedOut;

          console.log(
            `[Session ${sessionId}] Connection closed. ` +
            `Status: ${errorCode}, Should reconnect: ${shouldReconnect}`
          );

          // ===== ETAPA 4: REGISTRAR FALHA =====
          const lifecycle = sessionLifecycleManager.get(tenantId, sessionId);
          const uptime = lifecycle?.getHealth().uptime || 0;
          adaptiveConfig.recordAttempt(false, errorCode, uptime);

          // Registrar no lifecycle
          if (lifecycle) {
            lifecycle.onConnectionError(errorCode);
            
            // ===== ETAPA 3: RECONNECT HUMANIZADO =====
            if (shouldReconnect) {
              lifecycle.scheduleReconnect(async () => {
                try {
                  console.log(`[Session ${sessionId}] 🔌 Reconnecting...`);
                  
                  // Reutilizar fingerprint existente
                  const existingFingerprint = sessionFingerprints.get(sessionId);
                  if (!existingFingerprint) {
                    console.error(`[Session ${sessionId}] ❌ Fingerprint não encontrado para reconnect`);
                    return;
                  }
                  
                  // Recarregar auth state
                  const sessionPath = path.join(sessionsDir, sessionId);
                  const { state, saveCreds } = await useMultiFileAuthState(sessionPath);
                  
                  // Obter configurações existentes
                  const existingQueue = messageQueues.get(sessionId);
                  const existingBehavior = organicBehaviorManager.get(tenantId, sessionId);
                  
                  // Converter fingerprint para config Baileys
                  const baileysFingerprint = toBaileysConfig(existingFingerprint);
                  const customHeaders = generateDynamicHeaders(existingFingerprint, {
                    acceptLanguage: 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
                  });
                  
                  // Configurar proxy se existir
                  const proxyAgent = proxyManager.getAgent();
                  const socketConfig = {
                    auth: state,
                    printQRInTerminal: false,
                    logger: pino({ level: 'silent' }),
                    browser: baileysFingerprint.browser,
                    manufacturer: baileysFingerprint.manufacturer,
                    markOnlineOnConnect: false,
                    connectTimeoutMs: 60000,
                    defaultQueryTimeoutMs: 60000,
                    keepAliveIntervalMs: adaptiveConfigManager.getConfig(tenantId).getCurrentConfig().keepAliveInterval,
                    retryRequestDelayMs: 5000,
                    maxMsgRetryCount: 3,
                    generateHighQualityLinkPreview: false,
                    syncFullHistory: false,
                    shouldSyncHistoryMessage: () => false,
                    getMessage: async () => undefined
                  };
                  
                  if (proxyAgent) {
                    socketConfig.agent = proxyAgent;
                    socketConfig.fetchAgent = proxyAgent;
                  }
                  
                  // Criar novo socket com mesma configuração
                  const sock = makeWASocket(socketConfig);
                  sockets.set(sessionId, sock);
                  
                  // Re-registrar eventos
                  sock.ev.on("creds.update", saveCreds);
                  
                  sock.ev.on("connection.update", (update) => {
                    const { connection, lastDisconnect } = update;
                    
                    if (connection === "open") {
                      console.log(`[Session ${sessionId}] ✅ Reconnected successfully`);
                      lifecycle.onConnectionSuccess();
                      adaptiveConfig.recordAttempt(true, 200);
                      
                      io.to(sessionId).emit("connection_success", {
                        session_id: sessionId,
                        timestamp: new Date().toISOString()
                      });
                    } else if (connection === "close") {
                      const statusCode = lastDisconnect?.error?.output?.statusCode;
                      console.log(`[Session ${sessionId}] ❌ Reconnect failed with code: ${statusCode}`);
                      sockets.delete(sessionId);
                    }
                  });
                  
                  console.log(`[Session ${sessionId}] 🔌 Reconnect initiated with same fingerprint`);
                  
                } catch (error) {
                  console.error(`[Session ${sessionId}] ❌ Reconnect error:`, error);
                  lifecycle.onConnectionError(500);
                }
              }, errorCode);
            }
          }

          // Limpar recursos
          sockets.delete(sessionId);
          
          // Registrar falha de conexão
          if (errorCode === 405 || errorCode === 429 || errorCode === 515) {
            recordConnectionFailure(sessionId);
          }
          
          // Emitir evento
          io.to(sessionId).emit("connection_closed", {
            session_id: sessionId,
            error_code: errorCode,
            timestamp: new Date().toISOString()
          });
        }
      });

      sock.ev.on("creds.update", saveCreds);

      sessions.set(sessionId, { 
        qr_code: null, 
        qr_expires_at: null,
        created_at: new Date().toISOString(),
        tenant_id: tenantId,
        user_id: userId
      });

      return res.status(201).json({ 
        session_id: sessionId,
        tenant_id: tenantId,
        fingerprint: {
          device: fingerprint.device.marketName,
          android: fingerprint.os.version,
          chrome: fingerprint.browser.version
        },
        anti_block: {
          timing_profile: timing_profile || currentConfig.timingProfile,
          activity_pattern: activity_pattern || currentConfig.activityPattern,
          keepalive_ms: variableKeepAlive
        }
      });

    } catch (error) {
      console.error(`[Session ${sessionId}] Error creating session:`, error);
      
      // ===== ETAPA 4: REGISTRAR ERRO =====
      adaptiveConfig.recordAttempt(false, 500);
      
      return res.status(500).json({ error: "Erro ao criar sessão." });
    }
  });

  // ========== ENDPOINTS DE FINGERPRINT ==========
  
  /**
   * GET /sessions/:session_id/fingerprint
   * Retorna fingerprint de uma sessão específica
   */
  router.get("/sessions/:session_id/fingerprint", (req, res) => {
    const { session_id } = req.params;
    const fingerprint = sessionFingerprints.get(session_id);
    
    if (!fingerprint) {
      return res.status(404).json({ 
        error: "Fingerprint não encontrado para esta sessão." 
      });
    }
    
    return res.json({
      session_id,
      fingerprint: {
        device: {
          manufacturer: fingerprint.device.manufacturer,
          model: fingerprint.device.model,
          marketName: fingerprint.device.marketName,
          deviceId: fingerprint.deviceId
        },
        os: {
          name: fingerprint.os.name,
          version: fingerprint.os.version,
          sdkVersion: fingerprint.os.sdkVersion
        },
        browser: {
          name: fingerprint.browser.name,
          version: fingerprint.browser.version,
          userAgent: fingerprint.browser.userAgent
        },
        screen: {
          width: fingerprint.screen.width,
          height: fingerprint.screen.height,
          pixelRatio: fingerprint.screen.pixelRatio
        },
        features: {
          webGLVendor: fingerprint.features.webGLVendor,
          webGLRenderer: fingerprint.features.webGLRenderer
        },
        locale: {
          language: fingerprint.locale.language,
          timezone: fingerprint.locale.timezone
        }
      }
    });
  });
  
  /**
   * GET /fingerprints/stats
   * Retorna estatísticas de fingerprints ativos
   */
  router.get("/fingerprints/stats", (_req, res) => {
    const fingerprints = Array.from(sessionFingerprints.values());
    
    // Contar por fabricante
    const byManufacturer = {};
    fingerprints.forEach(fp => {
      const mfr = fp.device.manufacturer;
      byManufacturer[mfr] = (byManufacturer[mfr] || 0) + 1;
    });
    
    // Contar por versão Android
    const byAndroid = {};
    fingerprints.forEach(fp => {
      const ver = fp.os.version;
      byAndroid[ver] = (byAndroid[ver] || 0) + 1;
    });
    
    // Contar por GPU
    const byGPU = {};
    fingerprints.forEach(fp => {
      const gpu = fp.features.webGLRenderer;
      byGPU[gpu] = (byGPU[gpu] || 0) + 1;
    });
    
    return res.json({
      total: fingerprints.length,
      diversity: {
        manufacturers: Object.keys(byManufacturer).length,
        androidVersions: Object.keys(byAndroid).length,
        gpus: Object.keys(byGPU).length
      },
      byManufacturer,
      byAndroid,
      topGPUs: Object.entries(byGPU)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([gpu, count]) => ({ gpu, count })),
      deviceStats: getDeviceStats()
    });
  });
  
  /**
   * POST /fingerprints/test
   * Gera fingerprint de teste sem criar sessão
   */
  router.post("/fingerprints/test", (req, res) => {
    const { tenant_id, preferred_manufacturer } = req.body || {};
    
    const testFingerprint = generateAdvancedFingerprint(
      tenant_id || 'test',
      'test-' + Date.now(),
      preferred_manufacturer
    );
    
    return res.json({
      fingerprint: testFingerprint,
      baileysConfig: toBaileysConfig(testFingerprint),
      headers: generateDynamicHeaders(testFingerprint, {
        acceptLanguage: 'pt-BR,pt;q=0.9'
      })
    });
  });
  
  // ========== CONTINUA NO PRÓXIMO BLOCO ==========
  // (endpoints de mensagens, delete, monitoramento, etc)
  
  app.use('/api', router);

  return { app, httpServer, io, router };
};

module.exports = { createServer };

