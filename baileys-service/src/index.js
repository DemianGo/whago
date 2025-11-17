"use strict";

/**
 * Ponto de entrada do serviço Baileys.
 *
 * Carrega variáveis de ambiente, inicializa o servidor HTTP + Socket.IO
 * e aplica boas práticas de desligamento gracioso.
 */

require("dotenv").config();

const path = require("path");

// ✅ USANDO SERVER-INTEGRATED COM FINGERPRINTS AVANÇADOS
const { createServer } = require("./server-integrated");

const PORT = Number(process.env.WHAGO_BAILEYS_PORT || process.env.PORT || 3030);
const HOST = process.env.WHAGO_BAILEYS_HOST || "0.0.0.0";

const LOG_LEVEL = (process.env.WHAGO_LOG_LEVEL || "info").toLowerCase();
const LOG_FORMAT = process.env.WHAGO_LOG_FORMAT || "dev";

const allowedOrigins = (process.env.WHAGO_CORS_ORIGINS || "")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

const logger = (() => {
  // Logger simples para evitar dependências neste estágio inicial.
  const levels = ["debug", "info", "warn", "error"];
  const shouldLog = (level) => levels.indexOf(level) >= levels.indexOf(LOG_LEVEL);
  const log = (level, message, payload) => {
    if (!shouldLog(level)) {
      return;
    }
    const timestamp = new Date().toISOString();
    const output = payload ? `${message} | ${JSON.stringify(payload)}` : message;
    // eslint-disable-next-line no-console
    console.log(`[${timestamp}] ${level.toUpperCase()} ${output}`);
  };
  return {
    debug: (message, payload) => log("debug", message, payload),
    info: (message, payload) => log("info", message, payload),
    warn: (message, payload) => log("warn", message, payload),
    error: (message, payload) => log("error", message, payload),
  };
})();

const { httpServer } = createServer({
  cors: { origins: allowedOrigins.length ? allowedOrigins : undefined },
  logger,
  logFormat: LOG_FORMAT,
  sessionsDir: process.env.WHAGO_BAILEYS_SESSIONS_DIR || path.resolve(__dirname, "../sessions"),
});

const shutdownSignals = ["SIGTERM", "SIGINT", "SIGQUIT"];

const start = async () => {
  httpServer.listen(PORT, HOST, () => {
    logger.info("Baileys service iniciado", { host: HOST, port: PORT });
  });

  shutdownSignals.forEach((signal) => {
    process.on(signal, () => {
      logger.warn(`Recebido sinal ${signal}. Encerrando servidor...`);
      httpServer.close((err) => {
        if (err) {
          logger.error("Erro ao encerrar servidor", { error: err.message });
          process.exit(1);
        }
        logger.info("Servidor encerrado com sucesso.");
        process.exit(0);
      });
    });
  });
};

start().catch((error) => {
  logger.error("Falha ao iniciar serviço Baileys", { error: error.message });
  process.exit(1);
});


