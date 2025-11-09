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

  // Endpoint de health-check para orquestradores/monitoramento
  app.get("/health", (_req, res) => {
    res.json({ status: "ok", uptime: process.uptime() });
  });

  // Placeholder para rotas futuras da API REST do serviço Baileys
  const router = express.Router();

  router.get("/status", (_req, res) => {
    res.json({ service: "baileys", version: "0.1.0", timestamp: new Date().toISOString() });
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


