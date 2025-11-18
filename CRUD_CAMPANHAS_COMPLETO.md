# CRUD Completo de Campanhas - WHAGO

## ✅ Implementação Completa

O CRUD de campanhas foi completamente implementado com gerenciamento adequado de recursos para evitar custos desnecessários.

---

## 📋 Operações Implementadas

### 1. **CREATE (Criar Campanha)**
```http
POST /api/v1/campaigns/
```
**O que cria:**
- ✅ Registro da campanha
- ✅ Configurações (settings)
- ✅ Mensagem template

**Recursos NÃO criados (reutilizados):**
- Chips (já existem)
- Proxies (já atribuídos aos chips)
- Sessões WAHA (já existem nos chips)

---

### 2. **READ (Listar/Buscar Campanhas)**
```http
GET /api/v1/campaigns/              # Listar todas
GET /api/v1/campaigns/{id}          # Buscar uma
GET /api/v1/campaigns/{id}/messages # Mensagens
GET /api/v1/campaigns/{id}/media    # Mídias
```

---

### 3. **UPDATE (Atualizar Campanha)**
```http
PUT /api/v1/campaigns/{id}
```
**Pode atualizar:**
- Nome
- Descrição
- Templates de mensagem
- Configurações (settings)

**Restrição:** Apenas campanhas em `DRAFT` ou `SCHEDULED`

---

### 4. **DELETE (Deletar Campanha)** ✨ **MELHORADO**

```http
DELETE /api/v1/campaigns/{id}
```

#### **Processo de Deleção (6 etapas):**

1. **Validação de Status**
   - ✅ Permitido: `DRAFT`, `CANCELLED`, `COMPLETED`
   - ❌ Bloqueado: `RUNNING`, `PAUSED`, `SCHEDULED`
   - Mensagem: "Cancele a campanha antes de excluir"

2. **Revogação de Task Celery**
   ```python
   celery_app.control.revoke(campaign_id, terminate=True, signal='SIGKILL')
   ```
   - Para envios em andamento
   - Libera workers do Celery

3. **Deleção de Mídias**
   - Deleta arquivos físicos do storage
   - Remove registros do banco
   - Log: `N mídias deletadas`

4. **Deleção de Mensagens**
   - DELETE em lote (performance)
   - Log: `N mensagens deletadas`

5. **Deleção de Contatos**
   - DELETE em lote (performance)
   - Log: `N contatos deletados`

6. **Deleção da Campanha**
   - Registra auditoria
   - Remove campanha
   - COMMIT transação

#### **Logs de Sucesso:**
```
INFO - Iniciando deleção da campanha {id} (nome: {name})
INFO - Task Celery revogada para campanha {id}
INFO - 0 mídias deletadas da campanha {id}
INFO - 2 mensagens deletadas da campanha {id}
INFO - 2 contatos deletados da campanha {id}
INFO - Campanha {id} deletada com sucesso
```

---

### 5. **CANCEL (Cancelar Campanha)** ✨ **MELHORADO**

```http
POST /api/v1/campaigns/{id}/cancel
```

#### **Processo de Cancelamento:**

1. **Revogação de Task Celery**
   ```python
   celery_app.control.revoke(campaign_id, terminate=True, signal='SIGKILL')
   ```

2. **Marcação de Mensagens como Falhas**
   - Status: `PENDING`, `SENDING`, `FAILED` → `FAILED`
   - Motivo: "Campanha cancelada pelo usuário"

3. **Atualização da Campanha**
   - Status: `CANCELLED`
   - `completed_at`: timestamp atual
   - Atualiza `failed_count`

4. **Notificações**
   - Registra auditoria
   - Publica status no Redis
   - Dispara webhook

**Recursos NÃO liberados:**
- ❌ Chips (continuam conectados)
- ❌ Proxies (continuam atribuídos)
- ❌ Sessões WAHA (continuam ativas)

---

### 6. **PAUSE (Pausar Campanha)** ✨ **MELHORADO**

```http
POST /api/v1/campaigns/{id}/pause
```

#### **Processo de Pausa:**

1. **Revogação de Task Celery**
   ```python
   celery_app.control.revoke(campaign_id, terminate=True, signal='SIGKILL')
   ```

2. **Atualização de Status**
   - Status: `PAUSED`
   - Mensagens pendentes permanecem pendentes

3. **Notificações**
   - Registra auditoria
   - Publica status no Redis
   - Dispara webhook

---

### 7. **START (Iniciar Campanha)**

```http
POST /api/v1/campaigns/{id}/start
```

#### **Processo de Início:**

1. **Validações**
   - Verifica status (deve ser `DRAFT` ou `SCHEDULED`)
   - Verifica se tem contatos
   - Verifica se tem chips configurados
   - Verifica créditos do usuário

2. **Preparação**
   - Cria mensagens para todos os contatos
   - Distribui mensagens entre chips (round-robin)
   - Atualiza status para `RUNNING`

3. **Dispatch**
   - Enfileira task no Celery
   - Task processa mensagens com intervalos configurados
   - Respeita rate limiting e camuflagem

---

## 🔒 Gerenciamento de Recursos

### **Recursos CRIADOS pela Campanha:**
1. ✅ Registros de contatos (`campaign_contacts`)
2. ✅ Mensagens (`campaign_messages`)
3. ✅ Mídias (arquivos + registros `campaign_media`)
4. ✅ Task do Celery (worker assíncrono)

### **Recursos DELETADOS ao excluir:**
1. ✅ Todos os contatos da campanha
2. ✅ Todas as mensagens da campanha
3. ✅ Todas as mídias (arquivos + registros)
4. ✅ Task do Celery (revogada)
5. ✅ Registro da campanha

### **Recursos NÃO DELETADOS (correto!):**
- ❌ Chips do usuário
- ❌ Proxies atribuídos aos chips
- ❌ Sessões WAHA dos chips
- ❌ Containers WAHA Plus do usuário

**Motivo:** Estes são recursos do USUÁRIO, não da campanha. Existem independentemente e são reutilizados entre campanhas.

---

## 💰 Economia de Custos

### **Antes da Melhoria:**
```
❌ Campanhas não eram deletadas
❌ Contatos acumulavam no banco
❌ Mensagens acumulavam no banco
❌ Mídias ocupavam storage
❌ Tasks do Celery poderiam continuar rodando
```

### **Depois da Melhoria:**
```
✅ Campanhas antigas podem ser deletadas
✅ Contatos liberados (reduz tamanho do DB)
✅ Mensagens liberadas (reduz tamanho do DB)
✅ Mídias deletadas (libera storage)
✅ Tasks do Celery revogadas (libera workers)
```

---

## 📊 Teste de Validação

### **Comandos Executados:**
```bash
# 1. Listar campanhas
GET /api/v1/campaigns/
# Resultado: 21 campanhas

# 2. Cancelar campanhas em execução
POST /api/v1/campaigns/{id}/cancel (x4)
# Resultado: 4 campanhas canceladas

# 3. Deletar campanhas
DELETE /api/v1/campaigns/{id} (x4)
# Resultado: 4 campanhas deletadas (HTTP 204)

# 4. Verificar campanhas restantes
GET /api/v1/campaigns/
# Resultado: 17 campanhas
```

### **Logs de Sucesso:**
```
INFO - Iniciando deleção da campanha 5e12e6b9... (nome: Teste_1763493712)
INFO - Task Celery revogada para campanha 5e12e6b9...
INFO - 0 mídias deletadas da campanha 5e12e6b9...
INFO - 2 mensagens deletadas da campanha 5e12e6b9...
INFO - 2 contatos deletados da campanha 5e12e6b9...
INFO - Campanha 5e12e6b9... deletada com sucesso
```

---

## 🎯 Fluxo Recomendado

### **Para Limpar Campanhas Antigas:**

1. **Cancelar campanhas em execução**
   ```http
   POST /api/v1/campaigns/{id}/cancel
   ```

2. **Deletar campanhas antigas**
   ```http
   DELETE /api/v1/campaigns/{id}
   ```

3. **Resultado:**
   - ✅ Banco de dados limpo
   - ✅ Storage liberado
   - ✅ Workers do Celery disponíveis
   - ✅ Sem custos mensais desnecessários

---

## 📝 Auditoria

Todas as operações são registradas:
```python
audit.record(
    action="campaign.delete",  # ou .cancel, .pause
    entity_type="campaign",
    entity_id=campaign_id,
    description=f"Campanha '{name}' deletada.",
    extra_data={
        "campaign_name": name,
        "status": status,
        "total_contacts": count,
    }
)
```

---

## ✅ Status Final

**CRUD de Campanhas: 100% IMPLEMENTADO**

- ✅ CREATE - Completo
- ✅ READ - Completo
- ✅ UPDATE - Completo
- ✅ DELETE - **Melhorado com liberação de recursos**
- ✅ CANCEL - **Melhorado com revogação de tasks**
- ✅ PAUSE - **Melhorado com revogação de tasks**
- ✅ START - Completo

**Gerenciamento de Custos: OTIMIZADO**

Todas as operações liberam adequadamente os recursos para evitar custos mensais desnecessários! 🚀

