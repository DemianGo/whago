# 🔧 PATCHES PARA INTEGRAÇÃO NO SERVER.JS

## APLICAR ESTAS MODIFICAÇÕES NO ARQUIVO EXISTENTE `/src/server.js`

---

### PATCH 1: Adicionar imports no topo (após linha 27)

```javascript
// ========== IMPORTAR SISTEMA ANTI-BLOCK ==========
const {
  // Etapa 1: Humanização
  messageQueueManager,
  
  // Etapa 2: Fingerprint
  generateAdvancedFingerprint,
  toBaileysConfig,
  generateDynamicHeaders,
  
  // Etapa 3: Comportamento Orgânico
  organicBehaviorManager,
  sessionLifecycleManager,
  ActivitySimulator,
  
  // Etapa 4: Monitoramento
  globalPatternDetector,
  adaptiveConfigManager
} = require("./humanization");
```

---

### PATCH 2: Adicionar maps após `sockets` (após linha 55)

```javascript
// ========== MAPS PARA SISTEMA ANTI-BLOCK ==========
const sessionFingerprints = new Map(); // session_id -> AdvancedFingerprint
const messageQueues = new Map();       // session_id -> MessageQueue
```

---

### PATCH 3: Modificar endpoint `/sessions/create` (linha 196)

Substituir todo o endpoint por:

```javascript
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
  
  // Verificar rate limiting
  const rateLimitCheck = checkConnectionAllowed(sessionId);
  if (!rateLimitCheck.allowed) {
    return res.status(429).json({
      error: rateLimitCheck.reason,
      wait_minutes: rateLimitCheck.waitMinutes
    });
  }
  
  // ✅ ADAPTIVE CONFIG
  const adaptiveConfig = adaptiveConfigManager.getConfig(tenantId);
  const currentConfig = adaptiveConfig.getCurrentConfig();
  
  const sessionPath = path.join(sessionsDir, sessionId);
  
  try {
    const { state, saveCreds } = await useMultiFileAuthState(sessionPath);
    
    // ✅ GERAR FINGERPRINT AVANÇADO
    const fingerprint = generateAdvancedFingerprint(
      tenantId,
      sessionId,
      preferred_manufacturer
    );
    
    sessionFingerprints.set(sessionId, fingerprint);
    
    console.log(`[Session ${sessionId}] 🎭 ${fingerprint.device.manufacturer} ${fingerprint.device.marketName}`);
    
    const baileysFingerprint = toBaileysConfig(fingerprint);
    const customHeaders = generateDynamicHeaders(fingerprint, {
      includeOptional: true,
      randomizeOrder: true,
      varyValues: true
    });
    
    // ✅ LIFECYCLE PARA KEEPALIVE VARIÁVEL
    const tempLifecycle = sessionLifecycleManager.register(
      null,
      tenantId,
      sessionId
    );
    const variableKeepAlive = tempLifecycle.generateKeepAlive();
    sessionLifecycleManager.unregister(tenantId, sessionId);
    
    const authState = {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys, pino({ level: 'silent' })),
    };
    
    const socketConfig = {
      auth: authState,
      logger: pino({ level: 'silent' }),
      printQRInTerminal: false,
      
      // ✅ FINGERPRINT
      browser: baileysFingerprint.browser,
      manufacturer: baileysFingerprint.manufacturer,
      
      // ✅ KEEPALIVE VARIÁVEL
      keepAliveIntervalMs: variableKeepAlive,
      
      // ✅ RETRY COM VARIAÇÃO
      retryRequestDelayMs: 2000 + Math.floor(Math.random() * 1000),
      
      connectTimeoutMs: 120000,
      defaultQueryTimeoutMs: 120000,
      qrTimeout: 90000,
      
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
    
    // ✅ PROXY COM HEADERS
    let proxyAgent = null;
    if (proxy_url) {
      const { HttpsProxyAgent } = require('https-proxy-agent');
      proxyAgent = new HttpsProxyAgent(proxy_url, { headers: customHeaders });
      socketConfig.agent = proxyAgent;
      console.log(`[Session ${sessionId}] 🔒 Proxy + headers aplicados`);
    }
    
    const sock = makeWASocket(socketConfig);
    sockets.set(sessionId, sock);
    
    // ===== CONNECTION UPDATE =====
    sock.ev.on("connection.update", async (update) => {
      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        try {
          const qrDataUrl = await QRCode.toDataURL(qr);
          const sessionData = sessions.get(sessionId) || {};
          sessionData.qr_code = qrDataUrl;
          sessionData.qr_expires_at = new Date(Date.now() + 60_000).toISOString();
          sessions.set(sessionId, sessionData);
          io.to(sessionId).emit("qr_updated", { session_id: sessionId, qr_code: qrDataUrl });
        } catch (error) {
          console.error(`[Session ${sessionId}] Error generating QR:`, error);
        }
      }

      if (connection === "open") {
        console.log(`[Session ${sessionId}] ✅ Connected`);
        
        // ✅ REGISTRAR SUCESSO
        adaptiveConfig.recordAttempt(true);
        globalPatternDetector.recordEvent({
          timestamp: new Date(),
          type: 'creation',
          tenantId,
          chipId: sessionId,
          metadata: { fingerprint: fingerprint.device.marketName }
        });
        
        // ✅ CRIAR MESSAGE QUEUE
        const timingProfileName = timing_profile || currentConfig.timingProfile || 'normal';
        const queue = messageQueueManager.getQueue(sock, tenantId, sessionId, timingProfileName);
        messageQueues.set(sessionId, queue);
        
        // ✅ CRIAR LIFECYCLE
        const lifecycle = sessionLifecycleManager.register(sock, tenantId, sessionId);
        lifecycle.start();
        lifecycle.onConnectionSuccess();
        
        // ✅ CRIAR ORGANIC BEHAVIOR
        const behavior = organicBehaviorManager.register(sock, tenantId, sessionId);
        behavior.start();
        
        // ✅ ACTIVITY SIMULATOR
        const activityPatternName = activity_pattern || currentConfig.activityPattern || 'balanced';
        const activitySimulator = new ActivitySimulator(tenantId, sessionId, activityPatternName);
        console.log(`[Session ${sessionId}] 🤖 Pattern: ${activityPatternName}`);
        
        connectionAttempts.delete(sessionId);
        io.to(sessionId).emit("connection_ready", { session_id: sessionId });
      }

      if (connection === "close") {
        const errorCode = lastDisconnect?.error?.output?.statusCode;
        
        // ✅ REGISTRAR FALHA
        const lifecycle = sessionLifecycleManager.get(tenantId, sessionId);
        const uptime = lifecycle?.getHealth().uptime || 0;
        adaptiveConfig.recordAttempt(false, errorCode, uptime);
        
        if (lifecycle) {
          lifecycle.onConnectionError(errorCode);
        }
        
        sockets.delete(sessionId);
        
        if (errorCode === 405 || errorCode === 429 || errorCode === 515) {
          recordConnectionFailure(sessionId);
        }
      }
    });

    sock.ev.on("creds.update", saveCreds);

    sessions.set(sessionId, { 
      qr_code: null, 
      qr_expires_at: null,
      tenant_id: tenantId 
    });

    return res.status(201).json({ 
      session_id: sessionId,
      anti_block: {
        timing_profile: timing_profile || currentConfig.timingProfile,
        keepalive_ms: variableKeepAlive
      }
    });

  } catch (error) {
    console.error(`[Session ${sessionId}] Error:`, error);
    adaptiveConfig.recordAttempt(false, 500);
    return res.status(500).json({ error: "Erro ao criar sessão." });
  }
});
```

---

### PATCH 4: Modificar endpoint `/messages/send` (encontrar e substituir)

```javascript
router.post("/messages/send", async (req, res) => {
  const { session_id, to, text, tenant_id } = req.body;

  if (!session_id || !to || !text) {
    return res.status(400).json({ error: "Dados inválidos." });
  }

  const sock = sockets.get(session_id);
  if (!sock) {
    return res.status(404).json({ error: "Sessão não encontrada." });
  }

  try {
    // ✅ USAR FILA DE MENSAGENS (ANTI-BURST + HUMANIZAÇÃO)
    const queue = messageQueues.get(session_id);
    
    if (queue) {
      console.log(`[Session ${session_id}] 📤 Enfileirando mensagem`);
      
      const result = await queue.enqueue(
        to,
        text,
        {
          showTyping: true,
          simulatePauses: true,
          pauseProbability: 0.3,
          reviewBeforeSend: true,
          stayOnlineAfter: false
        },
        'normal'
      );

      // ✅ REGISTRAR AÇÃO
      globalPatternDetector.recordEvent({
        timestamp: new Date(),
        type: 'action',
        tenantId: tenant_id || 'default',
        chipId: session_id,
        metadata: { action: 'send_message' }
      });

      return res.status(200).json({
        success: true,
        message: "Mensagem enviada com humanização",
        result
      });
      
    } else {
      // Fallback: enviar direto
      const result = await sock.sendMessage(to, { text });
      return res.status(200).json({ success: true, result });
    }

  } catch (error) {
    console.error(`[Session ${session_id}] Erro ao enviar:`, error);
    return res.status(500).json({ error: error.message });
  }
});
```

---

### PATCH 5: Modificar endpoint DELETE `/sessions/:session_id`

Adicionar limpeza dos recursos anti-block:

```javascript
router.delete("/sessions/:session_id", (req, res) => {
  const { session_id } = req.params;
  const { tenant_id } = req.query;

  const sock = sockets.get(session_id);
  
  if (sock) {
    try {
      sock.end();
    } catch (error) {
      console.error(`[Session ${session_id}] Error ending socket:`, error);
    }
  }

  sockets.delete(session_id);
  sessions.del(session_id);

  // ✅ LIMPAR RECURSOS ANTI-BLOCK
  if (messageQueues.has(session_id)) {
    const queue = messageQueues.get(session_id);
    queue.clear('Sessão deletada');
    messageQueues.delete(session_id);
  }
  
  if (sessionFingerprints.has(session_id)) {
    sessionFingerprints.delete(session_id);
  }
  
  const tenantId = tenant_id || 'default';
  organicBehaviorManager.unregister(tenantId, session_id);
  sessionLifecycleManager.unregister(tenantId, session_id);

  console.log(`[Session ${session_id}] 🗑️  Sessão e recursos removidos`);

  return res.json({ 
    success: true, 
    message: "Sessão deletada com sucesso." 
  });
});
```

---

### PATCH 6: Adicionar novos endpoints de monitoramento (no final do router, antes de app.use)

```javascript
// ========== ENDPOINTS DE MONITORAMENTO ANTI-BLOCK ==========

router.get("/monitoring/pattern-analysis", (_req, res) => {
  const analysis = globalPatternDetector.analyze();
  return res.json(analysis);
});

router.get("/monitoring/pattern-report", (_req, res) => {
  const report = globalPatternDetector.generateReport();
  return res.type('text/plain').send(report);
});

router.get("/monitoring/adaptive/:tenant_id", (req, res) => {
  const { tenant_id } = req.params;
  const adaptiveConfig = adaptiveConfigManager.getConfig(tenant_id);
  
  return res.json({
    metrics: adaptiveConfig.getMetrics(),
    config: adaptiveConfig.getCurrentConfig(),
    adjustmentHistory: adaptiveConfig.getAdjustmentHistory()
  });
});

router.get("/monitoring/adaptive/:tenant_id/report", (req, res) => {
  const { tenant_id } = req.params;
  const adaptiveConfig = adaptiveConfigManager.getConfig(tenant_id);
  const report = adaptiveConfig.generateReport();
  
  return res.type('text/plain').send(report);
});

router.get("/monitoring/dashboard", (_req, res) => {
  const patternAnalysis = globalPatternDetector.analyze();
  const patternStats = globalPatternDetector.getStats();
  const adaptiveStats = adaptiveConfigManager.getGlobalStats();
  
  return res.json({
    diversityScore: patternAnalysis.diversityScore,
    patterns: patternAnalysis.detectedPatterns,
    warnings: patternAnalysis.warnings,
    recommendations: patternAnalysis.recommendations,
    metrics: patternAnalysis.metrics,
    globalStats: {
      pattern: patternStats,
      adaptive: adaptiveStats,
      activeSessions: sockets.size,
      messageQueues: messageQueues.size
    }
  });
});

router.get("/sessions/:session_id/queue/stats", (req, res) => {
  const { session_id } = req.params;
  const queue = messageQueues.get(session_id);

  if (!queue) {
    return res.status(404).json({ error: "Fila não encontrada." });
  }

  const stats = queue.getStats();
  const pending = queue.getPendingMessages();

  return res.json({ stats, pending });
});
```

---

## ✅ RESUMO DAS MODIFICAÇÕES

1. ✅ Imports do sistema anti-block
2. ✅ Maps para fingerprints e queues
3. ✅ Criação de sessão com fingerprint + lifecycle + behavior
4. ✅ Envio de mensagens com fila anti-burst
5. ✅ Limpeza correta ao deletar sessão
6. ✅ Endpoints de monitoramento

---

## 🚀 APÓS APLICAR OS PATCHES

1. Reiniciar o Baileys service:
```bash
cd /home/liberai/whago
docker-compose restart baileys
```

2. Testar criação de sessão:
```bash
curl -X POST http://localhost:3000/api/v1/sessions/create \
  -H "Content-Type: application/json" \
  -d '{"alias": "Teste Anti-Block", "tenant_id": "tenant-123"}'
```

3. Verificar monitoramento:
```bash
curl http://localhost:3000/api/v1/monitoring/dashboard
```

---

**IMPORTANTE:** Estas modificações são incrementais e não quebram funcionalidades existentes!

