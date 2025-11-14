"use strict";

/**
 * Configuração do servidor Express responsável pela comunicação com o Baileys.
 *
 * Nesta fase inicial garantimos endpoints básicos, middleware de segurança
 * e suporte a WebSockets (Socket.IO) para streaming de QR Codes em tempo real.
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
   * Retorna { allowed: boolean, reason?: string, waitMinutes?: number }
   */
  function checkConnectionAllowed(sessionId) {
    const now = Date.now();
    const attempt = connectionAttempts.get(sessionId);
    
    if (!attempt) {
      // Primeira tentativa
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
      // Bloquear por COOLDOWN_MINUTES
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
   * Registra falha de conexão (erro 515)
   */
  function recordConnectionFailure(sessionId) {
    const attempt = connectionAttempts.get(sessionId);
    if (attempt) {
      // Incrementar contador de forma mais agressiva em caso de erro 515
      attempt.count += 2;
      attempt.blockedUntil = Date.now() + (COOLDOWN_MINUTES * 60 * 1000);
      connectionAttempts.set(sessionId, attempt);
    }
  }

  // Endpoint de health-check para orquestradores/monitoramento
  app.get("/health", (_req, res) => {
    res.json({ status: "ok", uptime: process.uptime() });
  });

  // Placeholder para rotas futuras da API REST do serviço Baileys
  const router = express.Router();

  router.get("/status", (_req, res) => {
    res.json({ 
      service: "baileys", 
      version: "0.2.0", 
      timestamp: new Date().toISOString(),
      proxy: proxyManager.getInfo()
    });
  });
  
  // Endpoint de diagnóstico de proxy
  router.get("/proxy/status", (_req, res) => {
    const proxyInfo = proxyManager.getInfo();
    res.json({
      ...proxyInfo,
      message: proxyInfo.enabled 
        ? `Proxy ativo via ${proxyInfo.type}://${proxyInfo.host}:${proxyInfo.port}` 
        : "Proxy desabilitado - usando conexão direta"
    });
  });
  
  // Endpoint para testar conexão do proxy
  router.post("/proxy/test", async (_req, res) => {
    if (!proxyManager.isEnabled()) {
      return res.status(400).json({ 
        error: "Proxy desabilitado. Configure PROXY_ENABLED=true no .env" 
      });
    }
    
    try {
      const success = await proxyManager.testConnection();
      if (success) {
        return res.json({ 
          status: "ok", 
          message: "Proxy funcionando corretamente",
          proxy: proxyManager.getInfo()
        });
      } else {
        return res.status(500).json({ 
          status: "error", 
          message: "Falha ao testar proxy" 
        });
      }
    } catch (error) {
      return res.status(500).json({ 
        status: "error", 
        message: error.message 
      });
    }
  });

  router.post("/sessions/create", async (req, res) => {
    const { alias } = req.body || {};
    if (!alias || typeof alias !== "string") {
      return res.status(400).json({ error: "Alias inválido." });
    }
    
    const sessionId = uuidv4();
    
    // Verificar rate limiting
    const rateLimitCheck = checkConnectionAllowed(sessionId);
    if (!rateLimitCheck.allowed) {
      console.log(`[Session ${sessionId}] Connection blocked: ${rateLimitCheck.reason}`);
      return res.status(429).json({
        error: rateLimitCheck.reason,
        wait_minutes: rateLimitCheck.waitMinutes,
        retry_after: rateLimitCheck.waitMinutes * 60,
      });
    }
    
    if (rateLimitCheck.attemptsLeft !== undefined) {
      console.log(`[Session ${sessionId}] Connection allowed. Attempts left: ${rateLimitCheck.attemptsLeft}`);
    }
    
    const sessionPath = path.join(sessionsDir, sessionId);
    
    try {
      // Initialize Baileys session with auth state
      console.log(`[Session ${sessionId}] Creating session at path: ${sessionPath}`);
      const { state, saveCreds } = await useMultiFileAuthState(sessionPath);
      console.log(`[Session ${sessionId}] Auth state loaded, has creds: ${!!state.creds}`);
      
      // CRÍTICO: Usar makeCacheableSignalKeyStore para evitar erro 515
      const authState = {
        creds: state.creds,
        keys: makeCacheableSignalKeyStore(state.keys, pino({ level: 'silent' })),
      };
      
      // Configuração MÍNIMA para evitar erro 515 após login
      const socketConfig = {
        auth: authState,
        // Não especificar versão - deixar Baileys usar a versão padrão (mais atualizada)
        logger: pino({ level: 'silent' }),
        
        // Timeouts generosos
        connectTimeoutMs: 120000, // 2 minutos
        defaultQueryTimeoutMs: 120000,
        qrTimeout: 90000, // 90 segundos para escanear QR
        
        // Comportamento PASSIVO (não fazer nada após login)
        keepAliveIntervalMs: 120000, // 2 minutos (muito espaçado)
        retryRequestDelayMs: 2000, // 2 segundos entre retries
        
        // DESABILITAR todas as queries automáticas
        syncFullHistory: false,
        fireInitQueries: false,
        emitOwnEvents: false,
        generateHighQualityLinkPreview: false,
        
        // NÃO marcar presença
        markOnlineOnConnect: false,
        
        // Handler de mensagens (sempre retornar undefined)
        getMessage: async () => undefined,
        
        // Não especificar browser - usar padrão do Baileys (Chrome)
        
        // Configurações de socket
        socketConfig: {
          timeout: 120000,
        },
        
        // CRÍTICO: Não fazer fetch de dados após login
        shouldSyncHistoryMessage: () => false,
        shouldIgnoreJid: () => false,
        
        // Limitar operações pós-login
        patchMessageBeforeSending: (msg) => msg,
      };
      
      // ===== INTEGRAÇÃO COM PROXY (MODULAR) =====
      // Se proxy estiver habilitado, adicionar agent ao socketConfig
      const proxyAgent = proxyManager.getAgent();
      if (proxyAgent) {
        console.log(`[Session ${sessionId}] 🌐 Proxy habilitado:`, proxyManager.getInfo().url);
        socketConfig.agent = proxyAgent;
      } else {
        console.log(`[Session ${sessionId}] 🔓 Proxy desabilitado, conexão direta`);
      }
      // =========================================
      
      const sock = makeWASocket(socketConfig);
      
      // Store socket instance
      sockets.set(sessionId, sock);
      
      // Handle QR code generation
      sock.ev.on("connection.update", async (update) => {
        const { connection, lastDisconnect, qr } = update;
        
        console.log(`[Session ${sessionId}] Connection update FULL:`, JSON.stringify(update, null, 2));
        
        if (qr && qr.length > 0) {
          // Generate QR code as data URL
          try {
            console.log(`[Session ${sessionId}] Generating QR code...`);
            const qrDataUrl = await QRCode.toDataURL(qr);
            const sessionData = sessions.get(sessionId) || {};
            sessionData.qr_code = qrDataUrl;
            sessionData.qr_expires_at = new Date(Date.now() + 60_000).toISOString();
            sessions.set(sessionId, sessionData);
            
            console.log(`[Session ${sessionId}] QR code generated and stored`);
            
            // Emit via WebSocket
            io.emit(`qr:${sessionId}`, { qr: qrDataUrl, expires_at: sessionData.qr_expires_at });
          } catch (err) {
            console.error(`[Session ${sessionId}] Error generating QR code:`, err);
          }
        }
        
        if (connection === "open") {
          console.log(`[Session ${sessionId}] ✅ CONNECTION OPEN - WhatsApp conectado com sucesso!`);
          
          const sessionData = sessions.get(sessionId) || {};
          sessionData.status = "connected";
          sessionData.connectedAt = new Date().toISOString();
          sessionData.qr_code = null; // Clear QR after connection
          sessions.set(sessionId, sessionData);
          
          // Limpar tentativas de conexão (sucesso)
          connectionAttempts.delete(sessionId);
          
          io.emit(`status:${sessionId}`, { status: "connected" });
          
          console.log(`[Session ${sessionId}] Sessão totalmente estabelecida. Modo passivo ativado.`);
        }
        
        if (connection === "close") {
          const statusCode = lastDisconnect?.error?.output?.statusCode;
          const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
          const sessionData = sessions.get(sessionId) || {};
          
          console.log(`[Session ${sessionId}] Connection closed. Status: ${statusCode}, Should reconnect: ${shouldReconnect}`);
          
          if (statusCode === 515) {
            console.error(`[Session ${sessionId}] Error 515: WhatsApp bloqueou a conexão.`);
            
            // Registrar falha e bloquear novas tentativas
            recordConnectionFailure(sessionId);
            
            const attempt = connectionAttempts.get(sessionId);
            const waitMinutes = attempt?.blockedUntil 
              ? Math.ceil((attempt.blockedUntil - Date.now()) / 60000)
              : COOLDOWN_MINUTES;
            
            sessionData.status = "error";
            sessionData.error_code = 515;
            sessionData.error_message = `WhatsApp bloqueou a conexão (Error 515). Aguarde ${waitMinutes} minutos antes de tentar novamente.`;
            sessionData.blocked_until = attempt?.blockedUntil;
            sessions.set(sessionId, sessionData);
            sockets.delete(sessionId);
            
            console.log(`[Session ${sessionId}] Bloqueado por ${waitMinutes} minutos`);
            return;
          }
          
          if (!shouldReconnect) {
            sessionData.status = "disconnected";
            sessions.set(sessionId, sessionData);
            sockets.delete(sessionId);
          } else {
            sessionData.status = "reconnecting";
            sessions.set(sessionId, sessionData);
          }
        }
      });
      
      // Save credentials on update
      sock.ev.on("creds.update", () => {
        console.log(`[Session ${sessionId}] Credentials updated, saving...`);
        saveCreds();
      });
      
      sessions.set(sessionId, {
        alias,
        status: "waiting_qr",
        createdAt: new Date().toISOString(),
      });
      
      return res.status(201).json({ session_id: sessionId, alias });
    } catch (error) {
      console.error("Error creating Baileys session:", error);
      return res.status(500).json({ error: "Falha ao criar sessão Baileys." });
    }
  });

  router.delete("/sessions/:id", async (req, res) => {
    const sessionId = req.params.id;
    
    console.log(`[Session ${sessionId}] DELETE request received`);
    
    // 1. Desconectar socket se existir
    const sock = sockets.get(sessionId);
    if (sock) {
      try {
        console.log(`[Session ${sessionId}] Closing WebSocket connection...`);
        await sock.logout();
        sock.end(undefined);
      } catch (err) {
        console.error(`[Session ${sessionId}] Error closing socket:`, err.message);
      }
      sockets.delete(sessionId);
    }
    
    // 2. Remover do cache de sessões
    if (sessions.has(sessionId)) {
      sessions.del(sessionId);
      console.log(`[Session ${sessionId}] Removed from cache`);
    }
    
    // 3. Deletar arquivos de sessão do disco
    const sessionPath = path.join(sessionsDir, sessionId);
    if (fs.existsSync(sessionPath)) {
      try {
        console.log(`[Session ${sessionId}] Deleting session files from disk...`);
        fs.rmSync(sessionPath, { recursive: true, force: true });
        console.log(`[Session ${sessionId}] Session files deleted`);
      } catch (err) {
        console.error(`[Session ${sessionId}] Error deleting session files:`, err.message);
      }
    }
    
    console.log(`[Session ${sessionId}] DELETE completed successfully`);
    return res.status(204).send();
  });

  router.post("/sessions/:id/disconnect", async (req, res) => {
    const sessionId = req.params.id;
    
    console.log(`[Session ${sessionId}] DISCONNECT request received`);
    
    // Verificar se sessão existe
    const sessionData = sessions.get(sessionId);
    if (!sessionData) {
      console.log(`[Session ${sessionId}] Session not found in cache`);
      return res.status(404).json({ error: "Sessão não encontrada." });
    }
    
    // Desconectar socket se existir
    const sock = sockets.get(sessionId);
    if (sock) {
      try {
        console.log(`[Session ${sessionId}] Logging out from WhatsApp...`);
        await sock.logout();
        console.log(`[Session ${sessionId}] Closing socket...`);
        sock.end(undefined);
        console.log(`[Session ${sessionId}] Socket closed successfully`);
      } catch (err) {
        console.error(`[Session ${sessionId}] Error during disconnect:`, err.message);
        // Continuar mesmo com erro, para garantir limpeza
      }
      sockets.delete(sessionId);
    } else {
      console.log(`[Session ${sessionId}] No active socket found`);
    }
    
    // Atualizar status no cache
    sessionData.status = "disconnected";
    sessionData.disconnectedAt = new Date().toISOString();
    sessions.set(sessionId, sessionData);
    
    console.log(`[Session ${sessionId}] DISCONNECT completed successfully`);
    return res.json({ 
      status: "disconnected",
      disconnected_at: sessionData.disconnectedAt
    });
  });

  router.get("/sessions/:id", (req, res) => {
    const sessionId = req.params.id;
    const sessionData = sessions.get(sessionId);
    if (!sessionData) {
      return res.status(404).json({ error: "Sessão não encontrada." });
    }
    
    // Incluir informações de rate limit se houver
    const attempt = connectionAttempts.get(sessionId);
    const rateLimitInfo = {};
    if (attempt && attempt.blockedUntil && Date.now() < attempt.blockedUntil) {
      rateLimitInfo.blocked = true;
      rateLimitInfo.blocked_until = new Date(attempt.blockedUntil).toISOString();
      rateLimitInfo.wait_minutes = Math.ceil((attempt.blockedUntil - Date.now()) / 60000);
    }
    
    return res.json({
      session_id: sessionId,
      alias: sessionData.alias,
      status: sessionData.status,
      created_at: sessionData.createdAt,
      disconnected_at: sessionData.disconnectedAt ?? null,
      error_code: sessionData.error_code ?? null,
      error_message: sessionData.error_message ?? null,
      rate_limit: Object.keys(rateLimitInfo).length > 0 ? rateLimitInfo : null,
    });
  });

  router.get("/sessions/:id/qr", async (req, res) => {
    const sessionId = req.params.id;
    const sessionData = sessions.get(sessionId);
    
    if (!sessionData) {
      return res.status(404).json({ error: "Sessão não encontrada." });
    }
    
    // If session has QR code stored, return it
    if (sessionData.qr_code) {
      return res.json({
        session_id: sessionId,
        qr_code: sessionData.qr_code,
        expires_at: sessionData.qr_expires_at || new Date(Date.now() + 60_000).toISOString(),
      });
    }
    
    // If no QR code yet, return waiting status
    return res.json({
      session_id: sessionId,
      qr_code: null,
      status: "waiting",
      message: "QR Code ainda não foi gerado pelo Baileys",
    });
  });

  router.post("/messages/send", async (req, res) => {
    const { session_id: sessionIdRaw, sessionId, to, message } = req.body || {};
    const sessionIdentifier = sessionIdRaw || sessionId;
    
    if (!sessionIdentifier || !to || !message) {
      return res.status(400).json({ error: "Payload inválido." });
    }
    
    const sock = sockets.get(sessionIdentifier);
    if (!sock) {
      return res.status(404).json({ error: "Sessão não encontrada ou não conectada." });
    }
    
    try {
      // Format phone number for WhatsApp (add @s.whatsapp.net)
      const jid = to.includes("@") ? to : `${to}@s.whatsapp.net`;
      
      // Send message using Baileys
      const sentMsg = await sock.sendMessage(jid, { text: message });
      
      const entry = {
        id: sentMsg.key.id || uuidv4(),
        session_id: sessionIdentifier,
        to,
        message,
        created_at: new Date().toISOString(),
        status: "sent",
      };
      
      const history = messageLog.get(sessionIdentifier) || [];
      history.push(entry);
      messageLog.set(sessionIdentifier, history);
      
      return res.status(200).json({ status: "sent", message_id: entry.id });
    } catch (error) {
      console.error("Error sending message:", error);
      return res.status(500).json({ error: "Falha ao enviar mensagem.", details: error.message });
    }
  });

  router.get("/messages", (req, res) => {
    const sessionId = req.query.session_id;
    if (!sessionId) {
      return res.status(400).json({ error: "session_id é obrigatório." });
    }
    return res.json({
      session_id: sessionId,
      messages: messageLog.get(sessionId) || [],
    });
  });

  app.use("/api/v1", router);

  // Eventos básicos do Socket.IO (QR Code em fases posteriores)
  io.on("connection", (socket) => {
    if (config.logger) {
      config.logger.info(`Socket conectado: ${socket.id}`);
    }

    socket.on("disconnect", (reason) => {
      if (config.logger) {
        config.logger.info(`Socket desconectado: ${socket.id} (${reason})`);
      }
    });
  });

  return { app, httpServer, io };
};

module.exports = { createServer };


