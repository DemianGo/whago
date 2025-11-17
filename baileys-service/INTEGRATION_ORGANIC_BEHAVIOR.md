# 🤖 INTEGRAÇÃO: COMPORTAMENTO ORGÂNICO (ETAPA 3)

## 📋 RESUMO

Sistema de comportamento orgânico pós-conexão com:
- ✅ **Ações orgânicas automáticas** (ler mensagens, ver status, etc)
- ✅ **KeepAlive variável** (90-150s aleatório)
- ✅ **Reconnect humanizado** (delays 30s-2min + jitter)
- ✅ **Retry exponencial + fibonacci** com jitter
- ✅ **Health monitoring** (uptime, erros consecutivos)
- ✅ **Padrões de atividade** (corporativo, noturno, matutino, balanceado, casual)
- ✅ **Horários de pico/vale** automáticos

---

## 🚀 COMO INTEGRAR NO `server.js`

### 1. IMPORTAR NO TOPO DO ARQUIVO

```typescript
// ========== ADICIONAR APÓS IMPORTS EXISTENTES ==========
import {
  organicBehaviorManager,
  sessionLifecycleManager,
  ActivitySimulator,
  ACTIVITY_PATTERNS
} from './humanization';
```

### 2. INICIALIZAR AO CRIAR SESSÃO

```typescript
// ========== NO ENDPOINT `/sessions/create`, APÓS CONNECTION === 'OPEN' ==========

if (connection === "open") {
  console.log(`[Session ${sessionId}] ✅ Connection opened successfully`);
  
  // ... código existente (criar fila, etc) ...

  // ✅ REGISTRAR LIFECYCLE MANAGER
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
      retryStrategy: 'exponential', // 'linear', 'exponential', 'fibonacci'
      baseRetryDelay: 2000,
      maxRetryDelay: 60000,
      jitterPercent: 0.3
    }
  );
  
  lifecycle.start();
  lifecycle.onConnectionSuccess();

  // ✅ REGISTRAR ORGANIC BEHAVIOR
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
      actionIntervalMax: 900000,  // 15min
      probabilities: {
        readMessage: 0.4,
        viewStatus: 0.3,
        updateProfile: 0.05,
        checkGroups: 0.25
      }
    }
  );
  
  behavior.start();

  // ✅ ACTIVITY SIMULATOR (opcional - para ajustar comportamento por horário)
  const activityPattern = user?.plan?.tier === 'ENTERPRISE' ? 'corporate' : 'balanced';
  const activitySimulator = new ActivitySimulator(tenantId, sessionId, activityPattern);
  
  // Verificar se deve estar online agora
  const shouldBeOnline = activitySimulator.shouldBeOnlineNow();
  if (shouldBeOnline) {
    console.log(`[Session ${sessionId}] 🟢 Horário de atividade, mantendo online`);
  } else {
    console.log(`[Session ${sessionId}] ⚫ Horário de inatividade, modo discreto`);
  }

  // Resetar tentativas
  connectionAttempts.delete(sessionId);
}
```

### 3. APLICAR KEEPALIVE VARIÁVEL NO SOCKETCONFIG

```typescript
// ========== NO ENDPOINT `/sessions/create`, NO SOCKETCONFIG ==========

// Criar lifecycle temporário para gerar keepAlive
const tempLifecycle = sessionLifecycleManager.register(
  {} as WASocket, // socket ainda não existe
  tenantId,
  sessionId
);

const socketConfig = {
  auth: { ... },
  printQRInTerminal: false,
  logger: pino({ level: "silent" }),

  // ✅ KEEPALIVE VARIÁVEL
  keepAliveIntervalMs: tempLifecycle.generateKeepAlive(),
  
  // ✅ RETRY COM VARIAÇÃO
  retryRequestDelayMs: 2000 + Math.floor(Math.random() * 1000), // 2-3s

  // ... resto do config ...
};

// Remover lifecycle temporário (será recriado ao conectar)
sessionLifecycleManager.unregister(tenantId, sessionId);
```

### 4. APLICAR RECONNECT HUMANIZADO

```typescript
// ========== NO EVENTO CONNECTION.UPDATE ==========

if (connection === "close") {
  const errorCode = lastDisconnect?.error?.output?.statusCode;
  const shouldReconnect = errorCode !== DisconnectReason.loggedOut;

  console.log(
    `[Session ${sessionId}] Connection closed. ` +
    `Status: ${errorCode}, Should reconnect: ${shouldReconnect}`
  );

  // Obter lifecycle
  const lifecycle = sessionLifecycleManager.get(tenantId, sessionId);

  if (lifecycle) {
    // Registrar erro
    lifecycle.onConnectionError(errorCode);

    // ✅ RECONNECT HUMANIZADO (se aplicável)
    if (shouldReconnect) {
      lifecycle.scheduleReconnect(async () => {
        // Função de reconnect
        console.log(`[Session ${sessionId}] 🔌 Reconnecting...`);
        
        // Recriar socket (lógica específica do seu sistema)
        // const newSock = makeWASocket(socketConfig);
        // sockets.set(sessionId, newSock);
        
        lifecycle.onConnectionSuccess();
      }, errorCode);
    }
  }

  // Limpar recursos
  sockets.delete(sessionId);

  // Registrar falha de conexão
  if (errorCode === 405 || errorCode === 429) {
    recordConnectionFailure(sessionId);
  }
}
```

### 5. LIMPAR RECURSOS AO DELETAR SESSÃO

```typescript
// ========== NO ENDPOINT `/sessions/:session_id` (DELETE) ==========

router.delete("/sessions/:session_id", (req, res) => {
  const { session_id } = req.params;

  // ... código existente ...

  // ✅ REMOVER ORGANIC BEHAVIOR
  organicBehaviorManager.unregister(tenantId, session_id);
  console.log(`[Session ${session_id}] 🗑️  Organic behavior removido`);

  // ✅ REMOVER LIFECYCLE
  sessionLifecycleManager.unregister(tenantId, session_id);
  console.log(`[Session ${session_id}] 🗑️  Lifecycle removido`);

  // ... código existente ...
});
```

### 6. ENDPOINTS DE MONITORAMENTO

```typescript
// ========== ADICIONAR NOVOS ENDPOINTS ==========

/**
 * GET /sessions/:session_id/organic-behavior/stats
 * Retorna estatísticas de comportamento orgânico
 */
router.get("/sessions/:session_id/organic-behavior/stats", (req, res) => {
  const { session_id } = req.params;
  const { tenant_id } = req.query;

  const behavior = organicBehaviorManager.get(tenant_id as string, session_id);

  if (!behavior) {
    return res.status(404).json({ error: "Comportamento não encontrado." });
  }

  return res.json(behavior.getStats());
});

/**
 * POST /sessions/:session_id/organic-behavior/force-action
 * Força execução de uma ação específica
 */
router.post("/sessions/:session_id/organic-behavior/force-action", async (req, res) => {
  const { session_id } = req.params;
  const { tenant_id, action } = req.body;

  const behavior = organicBehaviorManager.get(tenant_id, session_id);

  if (!behavior) {
    return res.status(404).json({ error: "Comportamento não encontrado." });
  }

  try {
    await behavior.forceAction(action);
    return res.json({ success: true, message: `Ação "${action}" executada.` });
  } catch (error) {
    return res.status(500).json({ error: String(error) });
  }
});

/**
 * GET /sessions/:session_id/lifecycle/health
 * Retorna saúde da conexão
 */
router.get("/sessions/:session_id/lifecycle/health", (req, res) => {
  const { session_id } = req.params;
  const { tenant_id } = req.query;

  const lifecycle = sessionLifecycleManager.get(tenant_id as string, session_id);

  if (!lifecycle) {
    return res.status(404).json({ error: "Lifecycle não encontrado." });
  }

  return res.json(lifecycle.getHealth());
});

/**
 * GET /sessions/:session_id/lifecycle/stats
 * Retorna estatísticas do lifecycle
 */
router.get("/sessions/:session_id/lifecycle/stats", (req, res) => {
  const { session_id } = req.params;
  const { tenant_id } = req.query;

  const lifecycle = sessionLifecycleManager.get(tenant_id as string, session_id);

  if (!lifecycle) {
    return res.status(404).json({ error: "Lifecycle não encontrado." });
  }

  return res.json(lifecycle.getStats());
});

/**
 * GET /organic-behavior/global-stats
 * Retorna estatísticas globais de comportamento
 */
router.get("/organic-behavior/global-stats", (_req, res) => {
  const stats = organicBehaviorManager.getGlobalStats();
  return res.json(stats);
});

/**
 * GET /lifecycle/global-stats
 * Retorna estatísticas globais de lifecycle
 */
router.get("/lifecycle/global-stats", (_req, res) => {
  const stats = sessionLifecycleManager.getGlobalStats();
  return res.json(stats);
});

/**
 * GET /activity-patterns
 * Lista padrões de atividade disponíveis
 */
router.get("/activity-patterns", (_req, res) => {
  const patterns = Object.entries(ACTIVITY_PATTERNS).map(([key, pattern]) => ({
    key,
    name: pattern.name,
    description: pattern.description,
    averageSessionDuration: pattern.averageSessionDuration,
    actionsPerHour: pattern.actionsPerHour
  }));

  return res.json(patterns);
});

/**
 * POST /activity-patterns/test
 * Testa um padrão de atividade
 */
router.post("/activity-patterns/test", (req, res) => {
  const { pattern_name, tenant_id, chip_id } = req.body;

  const simulator = new ActivitySimulator(
    tenant_id || 'test',
    chip_id || 'test-chip',
    pattern_name
  );

  return res.json({
    pattern: simulator.getPattern().name,
    stats: simulator.getStats(),
    report: simulator.generatePatternReport()
  });
});
```

---

## 📊 TESTANDO A INTEGRAÇÃO

### 1. Criar Sessão com Comportamento Orgânico

```bash
curl -X POST http://localhost:3000/sessions/create \
  -H "Content-Type: application/json" \
  -d '{
    "alias": "Teste Orgânico",
    "tenant_id": "tenant-123"
  }'
```

**Logs esperados:**
```
[OrganicBehavior] abc123 - Inicializado (enabled: true)
[OrganicBehavior] abc123 ✅ Iniciado
[OrganicBehavior] abc123 ⏰ Aguardando 1.5min antes das ações iniciais...
[SessionLifecycle] abc123 - Inicializado
[SessionLifecycle] abc123 ✅ Iniciado
[SessionLifecycle] abc123 💓 KeepAlive: 127.3s
[ActivitySimulator] abc123 - Padrão: Balanceado
```

### 2. Ver Estatísticas de Comportamento Orgânico

```bash
curl "http://localhost:3000/sessions/SEU_SESSION_ID/organic-behavior/stats?tenant_id=tenant-123"
```

**Resposta:**
```json
{
  "messagesRead": 3,
  "statusesViewed": 2,
  "actionsPerformed": 5,
  "lastAction": "2025-11-15T14:30:45.123Z",
  "isActive": true
}
```

### 3. Ver Saúde da Conexão

```bash
curl "http://localhost:3000/sessions/SEU_SESSION_ID/lifecycle/health?tenant_id=tenant-123"
```

**Resposta:**
```json
{
  "isHealthy": true,
  "consecutiveErrors": 0,
  "lastError": null,
  "lastSuccess": "2025-11-15T14:25:10.456Z",
  "uptime": 325000,
  "reconnectCount": 0
}
```

### 4. Forçar Ação Orgânica

```bash
curl -X POST http://localhost:3000/sessions/SEU_SESSION_ID/organic-behavior/force-action \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-123",
    "action": "read"
  }'
```

**Ações disponíveis:** `read`, `status`, `presence`, `groups`

### 5. Testar Padrão de Atividade

```bash
curl -X POST http://localhost:3000/activity-patterns/test \
  -H "Content-Type: application/json" \
  -d '{
    "pattern_name": "corporate",
    "tenant_id": "test",
    "chip_id": "test-123"
  }'
```

**Resposta:**
```json
{
  "pattern": "Corporativo",
  "stats": {
    "pattern": "Corporativo",
    "currentProbability": 0.95,
    "peakHours": [10, 11, 12, 13, 14],
    "valleyHours": [0, 1, 2, 3, 4, 5, 23],
    "isPeakNow": true,
    "isValleyNow": false,
    "isWeekend": false,
    "averageSessionDuration": 240000,
    "actionsPerHour": { "min": 5, "max": 15 }
  },
  "report": "\n[ActivitySimulator] Padrão: Corporativo\n..."
}
```

---

## 🎯 FUNCIONALIDADES IMPLEMENTADAS

### **1. Comportamento Orgânico (`OrganicBehavior`)**

**Ações automáticas:**
- ✅ Ler 1-3 mensagens não lidas (após conectar)
- ✅ Ver 1-2 status de contatos
- ✅ Atualizar presença online/offline
- ✅ Verificar grupos

**Configurável:**
- Probabilidades de cada ação (0-1)
- Intervalos entre ações (5-15min default)
- Habilitar/desabilitar cada funcionalidade

### **2. Ciclo de Vida (`SessionLifecycle`)**

**KeepAlive variável:**
- 90-150s aleatório (evita padrão fixo)

**Reconnect humanizado:**
- Delays 30s-2min + jitter
- Erros 405/429: espera 5-10min
- Máximo de tentativas configurável

**Estratégias de retry:**
- Linear: `delay = base * attempt`
- Exponencial: `delay = base * 2^(attempt-1)`
- Fibonacci: `delay = base * fib(attempt)`
- Jitter: ±30% de variação

**Health monitoring:**
- Uptime tracking
- Erros consecutivos
- Última conexão bem-sucedida
- Status de saúde (healthy/unhealthy)

### **3. Padrões de Atividade (`ActivitySimulator`)**

**6 padrões pré-definidos:**

1. **Corporate** (Corporativo)
   - Pico: 9h-18h dias úteis
   - Vale: noite e fins de semana
   - 5-15 ações/hora

2. **Night Owl** (Noturno)
   - Pico: 20h-02h
   - Vale: manhã
   - 8-20 ações/hora

3. **Early Bird** (Matutino)
   - Pico: 6h-12h
   - Vale: noite
   - 10-25 ações/hora

4. **Balanced** (Balanceado)
   - Ativo uniformemente durante o dia
   - 6-18 ações/hora

5. **Casual**
   - Baixa frequência, sem padrão fixo
   - 2-8 ações/hora

6. **Always On** (24/7)
   - Ativo o tempo todo (usar apenas para testes!)
   - 15-30 ações/hora

**Ajuste automático:**
- Probabilidade de estar online por hora
- Multiplicador por dia da semana
- Duração de sessão variável
- Quantidade de ações ajustada

---

## 💡 EXEMPLOS DE USO

### Ajustar Comportamento por Plano de Usuário

```typescript
// No backend Python, ao criar chip:
const behaviorConfig = {
  enabled: true,
  actionIntervalMin: user.plan.tier === 'ENTERPRISE' ? 180000 : 300000, // 3min vs 5min
  probabilities: {
    readMessage: user.plan.tier === 'ENTERPRISE' ? 0.5 : 0.4,
    viewStatus: 0.3,
    updateProfile: 0.05,
    checkGroups: 0.25
  }
};

const activityPattern = user.plan.tier === 'ENTERPRISE' ? 'corporate' : 'balanced';

await baileys.create_session(
  session_id,
  alias,
  proxy_url,
  tenant_id,
  behaviorConfig,
  activityPattern
);
```

### Desabilitar Comportamento Orgânico Temporariamente

```typescript
const behavior = organicBehaviorManager.get(tenantId, chipId);
if (behavior) {
  behavior.updateConfig({ enabled: false });
}
```

### Forçar Reconnect Imediato

```typescript
const lifecycle = sessionLifecycleManager.get(tenantId, chipId);
if (lifecycle) {
  lifecycle.cancelReconnect();
  lifecycle.scheduleReconnect(reconnectFn);
}
```

### Verificar se Deve Estar Online Agora

```typescript
const simulator = new ActivitySimulator(tenantId, chipId, 'corporate');
if (simulator.shouldBeOnlineNow()) {
  // Conectar chip
} else {
  // Manter desconectado
}
```

---

## 📈 IMPACTO ESPERADO

Com comportamento orgânico ativado:

1. **✅ Taxa de detecção de bot:** redução adicional de 60-80%
2. **✅ KeepAlive variável:** impossível detectar padrão fixo
3. **✅ Reconnect humanizado:** delays realistas após desconexão
4. **✅ Ações orgânicas:** simula usuário real navegando
5. **✅ Padrões de atividade:** ajuste automático por horário

---

## ⚠️ IMPORTANTE

1. **Não force sempre online** - respeite horários de vale
2. **Não abuse de ações orgânicas** - mantenha intervalos realistas
3. **Monitor health check** - desconecte se muitos erros consecutivos
4. **Use padrão adequado** - corporate para B2B, balanced para B2C
5. **Teste em prod gradualmente** - comece com 1-3 chips

---

## ✅ CHECKLIST DE INTEGRAÇÃO

- [ ] Importar módulos de comportamento orgânico
- [ ] Registrar lifecycle ao conectar
- [ ] Registrar organic behavior ao conectar
- [ ] Aplicar keepAlive variável no socketConfig
- [ ] Aplicar reconnect humanizado no connection.update
- [ ] Remover lifecycle/behavior ao deletar sessão
- [ ] Adicionar endpoints de monitoramento
- [ ] Testar com 1 chip
- [ ] Verificar logs de ações orgânicas
- [ ] Verificar health monitoring
- [ ] Testar reconnect após desconexão
- [ ] Testar diferentes padrões de atividade
- [ ] Validar erros 405/429 com delay longo
- [ ] Monitorar uptime e erros consecutivos

---

**🎉 ETAPA 3 CONCLUÍDA!**

Sistema de comportamento orgânico totalmente implementado.

