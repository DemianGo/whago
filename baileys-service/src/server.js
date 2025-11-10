"use strict";

/**
 * Configuração do servidor Express responsável pela comunicação com o Baileys.
 *
 * Nesta fase inicial garantimos endpoints básicos, middleware de segurança
 * e suporte a WebSockets (Socket.IO) para streaming de QR Codes em tempo real.
 */

const http = require("http");

const cors = require("cors");
const express = require("express");
const helmet = require("helmet");
const morgan = require("morgan");
const { Server } = require("socket.io");
const { v4: uuidv4 } = require("uuid");
const NodeCache = require("node-cache");

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

  // Endpoint de health-check para orquestradores/monitoramento
  app.get("/health", (_req, res) => {
    res.json({ status: "ok", uptime: process.uptime() });
  });

  // Placeholder para rotas futuras da API REST do serviço Baileys
  const router = express.Router();

  router.get("/status", (_req, res) => {
    res.json({ service: "baileys", version: "0.2.0", timestamp: new Date().toISOString() });
  });

  router.post("/sessions/create", (req, res) => {
    const { alias } = req.body || {};
    if (!alias || typeof alias !== "string") {
      return res.status(400).json({ error: "Alias inválido." });
    }
    const sessionId = uuidv4();
    sessions.set(sessionId, {
      alias,
      status: "connected",
      createdAt: new Date().toISOString(),
    });
    return res.status(201).json({ session_id: sessionId, alias });
  });

  router.delete("/sessions/:id", (req, res) => {
    const sessionId = req.params.id;
    if (!sessions.has(sessionId)) {
      return res.status(404).json({ error: "Sessão não encontrada." });
    }
    sessions.del(sessionId);
    return res.status(204).send();
  });

  router.post("/sessions/:id/disconnect", (req, res) => {
    const sessionId = req.params.id;
    const sessionData = sessions.get(sessionId);
    if (!sessionData) {
      return res.status(404).json({ error: "Sessão não encontrada." });
    }
    sessionData.status = "disconnected";
    sessionData.disconnectedAt = new Date().toISOString();
    sessions.set(sessionId, sessionData);
    return res.json({ status: "disconnected" });
  });

  router.get("/sessions/:id", (req, res) => {
    const sessionId = req.params.id;
    const sessionData = sessions.get(sessionId);
    if (!sessionData) {
      return res.status(404).json({ error: "Sessão não encontrada." });
    }
    return res.json({
      session_id: sessionId,
      alias: sessionData.alias,
      status: sessionData.status,
      created_at: sessionData.createdAt,
      disconnected_at: sessionData.disconnectedAt ?? null,
    });
  });

  router.get("/sessions/:id/qr", (req, res) => {
    const sessionId = req.params.id;
    if (!sessions.has(sessionId)) {
      return res.status(404).json({ error: "Sessão não encontrada." });
    }
    return res.json({
      session_id: sessionId,
      qr_code: `QR-${sessionId}`,
      expires_at: new Date(Date.now() + 60_000).toISOString(),
    });
  });

  router.post("/messages/send", (req, res) => {
    const { session_id: sessionIdRaw, sessionId, to, message } = req.body || {};
    const sessionIdentifier = sessionIdRaw || sessionId;
    if (!sessionIdentifier || !to || !message) {
      return res.status(400).json({ error: "Payload inválido." });
    }
    if (!sessions.has(sessionIdentifier)) {
      sessions.set(sessionIdentifier, {
        alias: `AutoSession-${sessionIdentifier.toString().slice(0, 8)}`,
        status: "connected",
        createdAt: new Date().toISOString(),
      });
    }
    const entry = {
      id: uuidv4(),
      session_id: sessionIdentifier,
      to,
      message,
      created_at: new Date().toISOString(),
    };
    const history = messageLog.get(sessionIdentifier) || [];
    history.push(entry);
    messageLog.set(sessionIdentifier, history);
    return res.status(200).json({ status: "sent", message_id: entry.id });
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


