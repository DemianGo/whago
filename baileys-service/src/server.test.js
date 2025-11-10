"use strict";

const request = require("supertest");
const { createServer } = require("./server");

describe("Baileys Service API", () => {
  let app;

  beforeEach(() => {
    ({ app } = createServer({ logFormat: "tiny" }));
  });

  test("GET /health", async () => {
    const response = await request(app).get("/health");
    expect(response.status).toBe(200);
    expect(response.body.status).toBe("ok");
  });

  test("cria sessão e envia mensagem", async () => {
    const createResponse = await request(app)
      .post("/api/v1/sessions/create")
      .send({ alias: "QA Session" });
    expect(createResponse.status).toBe(201);
    const { session_id: sessionId } = createResponse.body;
    expect(sessionId).toBeDefined();

    const statusResponse = await request(app).get(`/api/v1/sessions/${sessionId}`);
    expect(statusResponse.status).toBe(200);
    expect(statusResponse.body.status).toBe("connected");

    const messageResponse = await request(app)
      .post("/api/v1/messages/send")
      .send({ session_id: sessionId, to: "5511999999999", message: "Olá Playwright" });
    expect(messageResponse.status).toBe(200);
    expect(messageResponse.body.status).toBe("sent");

    const logResponse = await request(app).get(`/api/v1/messages?session_id=${sessionId}`);
    expect(logResponse.status).toBe(200);
    expect(logResponse.body.messages).toHaveLength(1);

    const deleteResponse = await request(app).delete(`/api/v1/sessions/${sessionId}`);
    expect(deleteResponse.status).toBe(204);
  });
});

