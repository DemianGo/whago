# Restrição: Não Editar Campanhas em Andamento

## 🎯 **SOLICITAÇÃO DO USUÁRIO**

> "Enquanto a campanha tá rodando, não pode editar, só ao pausar"

**Resposta:** Concordo 100%! Faz muito mais sentido! ✅

---

## 🐛 **PROBLEMA ANTERIOR**

**ANTES**, o sistema permitia editar campanhas **RUNNING** (em andamento):
- ✅ Botão "✏️ Editar" aparecia em campanhas RUNNING
- ✅ Backend permitia fazer PUT em campanhas RUNNING
- ⚠️ **Risco:** Editar configurações enquanto mensagens estão sendo enviadas

**Problemas potenciais:**
1. Mudar chips enquanto envia → inconsistência
2. Mudar intervalos → dessincronia com Celery
3. Mudar mensagens → contatos recebem mensagens diferentes
4. Confusão para o usuário sobre o que está sendo enviado

---

## ✅ **SOLUÇÃO IMPLEMENTADA**

### **Nova Regra: Pause Antes de Editar**

**Status que podem ser editados:**
- ✅ **DRAFT** - Rascunho, ainda não iniciou
- ✅ **SCHEDULED** - Agendada, ainda não iniciou
- ✅ **PAUSED** - Pausada, não está enviando

**Status que NÃO podem ser editados:**
- ❌ **RUNNING** - Em andamento, enviando mensagens
- ❌ **COMPLETED** - Completa, já finalizou
- ❌ **CANCELLED** - Cancelada, já encerrada

---

## 📝 **MUDANÇAS IMPLEMENTADAS**

### **1. Backend - Validação de Edição:**

```python
# backend/app/services/campaign_service.py - update_campaign()

# ✅ AGORA
if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.SCHEDULED, CampaignStatus.PAUSED}:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Pause a campanha antes de editá-la. Não é possível editar campanhas em andamento, completas ou canceladas.",
    )
```

### **2. Backend - Validação de Upload:**

```python
# backend/app/services/campaign_service.py - upload_contacts()

# ✅ AGORA
if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.SCHEDULED, CampaignStatus.PAUSED}:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Pause a campanha antes de importar novos contatos. Não é possível modificar campanhas em andamento, completas ou canceladas.",
    )
```

### **3. Frontend - Botões Removidos:**

```javascript
// frontend/static/js/app.js - buildCampaignActionButtons()

// ❌ ANTES
if (status === "running") {
  buttons.push("✏️ Editar");  // ← REMOVIDO
  buttons.push("Pausar");
  buttons.push("Cancelar");
}

// ✅ AGORA
if (status === "running") {
  buttons.push("Pausar");
  buttons.push("Cancelar");
  // Sem "Editar"
}
```

### **4. Frontend - Validação Adicional:**

```javascript
// frontend/static/js/app.js - loadCampaignForEdit()

if (campaign.status === "running") {
  setCampaignFeedback("Pause a campanha antes de editá-la.", "warning");
  return;
}
```

---

## 📊 **MATRIZ COMPLETA ATUALIZADA**

| Status | Pode Editar? | Botão "Editar" | Backend | Mensagem |
|--------|--------------|----------------|---------|----------|
| **DRAFT** | ✅ SIM | ✅ Visível | ✅ Permite | - |
| **SCHEDULED** | ✅ SIM | ✅ Visível | ✅ Permite | - |
| **RUNNING** | ❌ NÃO | ❌ **OCULTO** | ❌ Bloqueia | "Pause a campanha antes de editá-la" |
| **PAUSED** | ✅ SIM | ✅ Visível | ✅ Permite | - |
| **COMPLETED** | ❌ NÃO | ❌ Oculto | ❌ Bloqueia | "Não é possível editar campanhas completas..." |
| **CANCELLED** | ❌ NÃO | ❌ Oculto | ❌ Bloqueia | "Não é possível editar campanhas completas..." |

---

## 🎬 **FLUXO CORRETO**

### **Cenário 1: Editar Campanha RUNNING**

```
1. Campanha está RUNNING (enviando)
2. Usuário quer editar
3. Lista de campanhas:
   ✅ Botão "Pausar" visível
   ❌ Botão "Editar" OCULTO
4. Usuário clica "Pausar"
   ✅ Campanha → PAUSED
5. Agora lista mostra:
   ✅ Botão "Editar" visível
   ✅ Botão "Retomar" visível
6. Usuário clica "Editar"
   ✅ Wizard abre normalmente
7. Usuário faz mudanças e salva
8. Usuário clica "Retomar"
   ✅ Campanha volta para RUNNING com novas configurações
```

### **Cenário 2: Tentar Editar RUNNING (se conseguir chamar)**

```
1. Campanha RUNNING
2. Se usuário tentar PUT /campaigns/{id}
   ❌ Backend retorna 400
   💬 "Pause a campanha antes de editá-la..."
3. Frontend mostra mensagem de erro
4. Usuário pausa a campanha
5. Tenta novamente
   ✅ Agora permite
```

---

## 🔒 **BOTÕES POR STATUS (ATUALIZADO)**

### **DRAFT:**
```
✏️ Editar  |  Iniciar  |  🗑️ Deletar
```

### **SCHEDULED:**
```
✏️ Editar  |  Cancelar  |  🗑️ Deletar
```

### **RUNNING:** ← **MUDOU!**
```
Pausar  |  Cancelar
```
*(Sem "Editar")*

### **PAUSED:**
```
✏️ Editar  |  Retomar  |  Cancelar
```

### **COMPLETED / CANCELLED:**
```
🗑️ Deletar
```

---

## 💡 **POR QUE ESSA RESTRIÇÃO FAZ SENTIDO?**

### **1. Consistência de Envio:**
- Garante que todas as mensagens sejam enviadas com as mesmas configurações
- Evita que alguns contatos recebam mensagem A e outros mensagem B

### **2. Integridade dos Dados:**
- Celery está executando com configurações específicas
- Mudar chips/intervalos durante execução causa dessincronia

### **3. Previsibilidade:**
- Usuário sabe exatamente o que está sendo enviado
- Não há surpresas ou inconsistências

### **4. Melhor UX:**
- Fluxo claro: Pausar → Editar → Retomar
- Menos confusão sobre o que pode ou não ser modificado

---

## 🧪 **COMO TESTAR**

### **Teste 1: Botão "Editar" oculto em RUNNING**
```
1. Inicie uma campanha
2. Vá para /campaigns
3. Veja a campanha RUNNING
4. ✅ Botões devem ser: "Pausar | Cancelar"
5. ❌ NÃO deve ter botão "Editar"
```

### **Teste 2: Editar após pausar**
```
1. Campanha RUNNING
2. Clique "Pausar"
3. ✅ Status → PAUSED
4. ✅ Botão "Editar" aparece
5. Clique "Editar"
6. ✅ Wizard abre normalmente
7. Faça mudanças e salve
8. Clique "Retomar"
9. ✅ Campanha retoma com novas configurações
```

### **Teste 3: Tentativa direta de editar RUNNING (API)**
```
1. Campanha RUNNING
2. Tente: PUT /api/v1/campaigns/{id}
3. ❌ Backend retorna 400
4. 💬 "Pause a campanha antes de editá-la..."
```

---

## 📝 **ARQUIVOS MODIFICADOS**

### **Backend:**
1. ✅ `/home/liberai/whago/backend/app/services/campaign_service.py`
   - `update_campaign()`: Linha 173-179
   - `upload_contacts()`: Linha 314-320
   - Ambos agora bloqueiam RUNNING

### **Frontend:**
2. ✅ `/home/liberai/whago/frontend/static/js/app.js`
   - `buildCampaignActionButtons()`: Linha 2630-2634 (RUNNING sem "Editar")
   - `loadCampaignForEdit()`: Linha 2662-2671 (validação adicional)

---

## ✅ **STATUS FINAL**

### **Implementação:**
- [x] Backend bloqueia edição de RUNNING
- [x] Backend bloqueia upload em RUNNING
- [x] Frontend oculta botão "Editar" de RUNNING
- [x] Frontend mostra mensagem clara se tentar editar
- [x] Permite editar PAUSED (após pausar)
- [x] Backend reiniciado
- [x] Documentação criada

### **Regra Final:**
**Para editar campanha RUNNING:**
1. Clique "Pausar"
2. Status → PAUSED
3. Clique "Editar"
4. Faça mudanças
5. Clique "Retomar"

---

## 🎯 **TESTE NO NAVEGADOR**

**Por favor, teste:**

1. **Inicie uma campanha**
2. **Veja a lista em /campaigns:**
   - ✅ Botões devem ser: "Pausar | Cancelar"
   - ❌ NÃO deve ter "Editar"

3. **Clique "Pausar"**
4. **Agora veja:**
   - ✅ Botão "Editar" aparece
   - ✅ Pode editar normalmente

---

## 💬 **RESPOSTA AO USUÁRIO**

> "Enquanto a campanha tá rodando, não pode editar, só ao pausar"

**Concordo 100%! ✅**

**Implementado:**
- ✅ Botão "Editar" removido de campanhas RUNNING
- ✅ Backend bloqueia edição de RUNNING
- ✅ Mensagem clara: "Pause a campanha antes de editá-la"
- ✅ Pode editar normalmente após pausar

**Está muito melhor assim! Evita inconsistências e confusão!** 🚀

