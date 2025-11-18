# Botões de Campanhas Melhorados

## 🎯 **MUDANÇAS SOLICITADAS**

1. ❌ **Botão "Editar" sumia quando pausava a campanha**
2. ❌ **Ao editar, não tinha opção de "Salvar" sem iniciar**
3. ❌ **Botões não eram contextuais para cada status**

---

## ✅ **CORREÇÕES APLICADAS**

### **1. Botões Contextuais por Status**

#### **DRAFT (Rascunho)**
```
✏️ Editar  |  Iniciar  |  🗑️ Deletar
```

#### **SCHEDULED (Agendada)**
```
✏️ Editar  |  Cancelar  |  🗑️ Deletar
```

#### **RUNNING (Em andamento)**
```
✏️ Editar  |  Pausar  |  Cancelar
```

#### **PAUSED (Pausada)** ← **CORRIGIDO!**
```
✏️ Editar  |  Retomar  |  Cancelar
```

#### **COMPLETED / CANCELLED**
```
🗑️ Deletar
```

---

### **2. Dois Botões no Final do Wizard**

**ANTES:**
```html
<button>Voltar</button>
<button>Iniciar envio</button>
```

**AGORA:**
```html
<button>Voltar</button>
<button>💾 Salvar</button>
<button>🚀 Iniciar envio</button>
```

#### **Comportamento:**

**💾 Salvar:**
- Fecha o wizard
- Mantém a campanha como DRAFT (se estava em DRAFT)
- Mantém a campanha como PAUSED (se estava em PAUSED)
- Não inicia o envio
- Mostra: "Campanha salva com sucesso!"

**🚀 Iniciar envio:**
- Faz POST `/campaigns/{id}/start`
- Muda status para RUNNING
- Fecha o wizard
- Mostra: "Campanha iniciada com status..."

---

### **3. Edição Permitida em Mais Status**

**ANTES:** Só permitia editar DRAFT e SCHEDULED

**AGORA:** Permite editar:
- ✅ DRAFT
- ✅ SCHEDULED
- ✅ RUNNING
- ✅ PAUSED

**NÃO permite editar:**
- ❌ COMPLETED
- ❌ CANCELLED

```javascript
// Validação atualizada
if (campaign.status === "completed" || campaign.status === "cancelled") {
  setCampaignFeedback("Não é possível editar campanhas completas ou canceladas.", "warning");
  return;
}
```

---

## 📋 **CÓDIGO MODIFICADO**

### **1. Botões Contextuais (`buildCampaignActionButtons`)**

```javascript
function buildCampaignActionButtons(campaign) {
  const status = (campaign.status || "").toLowerCase();
  const buttons = [];
  
  // DRAFT: Editar, Iniciar, Deletar
  if (status === "draft") {
    buttons.push(`<button data-campaign-action="edit" ... >✏️ Editar</button>`);
    buttons.push(`<button data-campaign-action="start" ... >Iniciar</button>`);
    buttons.push(`<button data-campaign-action="delete" ... >🗑️</button>`);
  }
  
  // SCHEDULED: Editar, Cancelar, Deletar
  if (status === "scheduled") {
    buttons.push(`<button data-campaign-action="edit" ... >✏️ Editar</button>`);
    buttons.push(`<button data-campaign-action="cancel" ... >Cancelar</button>`);
    buttons.push(`<button data-campaign-action="delete" ... >🗑️</button>`);
  }
  
  // RUNNING: Editar, Pausar, Cancelar
  if (status === "running") {
    buttons.push(`<button data-campaign-action="edit" ... >✏️ Editar</button>`);
    buttons.push(`<button data-campaign-action="pause" ... >Pausar</button>`);
    buttons.push(`<button data-campaign-action="cancel" ... >Cancelar</button>`);
  }
  
  // PAUSED: Editar, Retomar, Cancelar ← CORRIGIDO!
  if (status === "paused") {
    buttons.push(`<button data-campaign-action="edit" ... >✏️ Editar</button>`);
    buttons.push(`<button data-campaign-action="resume" ... >Retomar</button>`);
    buttons.push(`<button data-campaign-action="cancel" ... >Cancelar</button>`);
  }
  
  // CANCELLED e COMPLETED: Apenas Deletar
  if (status === "cancelled" || status === "completed") {
    buttons.push(`<button data-campaign-action="delete" ... >🗑️ Deletar</button>`);
  }
  
  return buttons.join(" ");
}
```

---

### **2. Nova Função: Salvar sem Iniciar**

```javascript
async function handleCampaignSave() {
  if (!campaignState.campaignId) {
    setCampaignFeedback("Nenhuma campanha para salvar.", "warning");
    return;
  }
  
  // Fechar wizard e atualizar lista
  closeCampaignWizard();
  await loadCampaigns({ toast: "Campanha salva com sucesso!" });
}
```

**Event Listener:**
```javascript
document.getElementById("campaign-save-button")?.addEventListener("click", handleCampaignSave);
```

---

### **3. HTML Atualizado (Passo 4 do Wizard)**

```html
<section id="campaign-step-4" class="wizard__panel hidden">
  <div class="space-y-4" id="campaign-review"></div>
  <div class="wizard__actions">
    <button type="button" class="btn-secondary" data-step-back="3">Voltar</button>
    <div class="flex gap-2">
      <button type="button" class="btn-secondary" id="campaign-save-button">
        💾 Salvar
      </button>
      <button type="button" class="btn-primary" id="campaign-start-button">
        🚀 Iniciar envio
      </button>
    </div>
  </div>
</section>
```

---

## 🎬 **FLUXOS DE USO**

### **Cenário 1: Criar Nova Campanha e Salvar (sem iniciar)**

```
1. Clicar "Nova Campanha"
2. Preencher Passo 1 → Continuar
3. Preencher Passo 2 → Continuar
4. Preencher Passo 3 → Continuar
5. Passo 4 (Revisão) → Clicar "💾 Salvar"
   ✅ Wizard fecha
   ✅ Campanha permanece como DRAFT
   ✅ Mensagem: "Campanha salva com sucesso!"
```

### **Cenário 2: Criar e Iniciar Imediatamente**

```
1. Clicar "Nova Campanha"
2. Preencher todos os passos
3. Passo 4 (Revisão) → Clicar "🚀 Iniciar envio"
   ✅ POST /campaigns/{id}/start
   ✅ Status muda para RUNNING
   ✅ Wizard fecha
   ✅ Mensagem: "Campanha iniciada com status running"
```

### **Cenário 3: Pausar e Editar Campanha**

```
1. Campanha RUNNING
2. Clicar "Pausar"
   ✅ Status → PAUSED
   ✅ Botões: ✏️ Editar | Retomar | Cancelar
   
3. Clicar "✏️ Editar"
   ✅ Wizard abre com dados preenchidos
   
4. Modificar campos
5. Clicar "💾 Salvar"
   ✅ Mudanças salvas
   ✅ Status permanece PAUSED
   ✅ Wizard fecha
   
6. Clicar "Retomar"
   ✅ Status → RUNNING
   ✅ Continua enviando
```

### **Cenário 4: Editar Campanha RUNNING (sem pausar)**

```
1. Campanha RUNNING
2. Clicar "✏️ Editar" ← AGORA DISPONÍVEL!
   ✅ Wizard abre
   
3. Modificar mensagem, chips, etc
4. Clicar "💾 Salvar"
   ✅ Mudanças aplicadas
   ✅ Status permanece RUNNING
   ✅ Wizard fecha
```

---

## 📊 **MATRIZ DE BOTÕES POR STATUS**

| Status | Editar | Iniciar | Salvar | Pausar | Retomar | Cancelar | Deletar |
|--------|--------|---------|--------|--------|---------|----------|---------|
| **DRAFT** | ✅ | ✅ | ✅* | ❌ | ❌ | ❌ | ✅ |
| **SCHEDULED** | ✅ | ❌ | ✅* | ❌ | ❌ | ✅ | ✅ |
| **RUNNING** | ✅ | ❌ | ✅* | ✅ | ❌ | ✅ | ❌ |
| **PAUSED** | ✅ | ❌ | ✅* | ❌ | ✅ | ✅ | ❌ |
| **COMPLETED** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **CANCELLED** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

*✅ "Salvar" aparece apenas dentro do wizard (passo 4)

---

## 🧪 **TESTES NECESSÁRIOS**

### **Teste 1: Botão Editar em PAUSED**
```
1. Acesse /campaigns
2. Crie uma campanha e inicie
3. Pause a campanha
4. ✅ Verifique que botão "✏️ Editar" está visível
5. Clique em "✏️ Editar"
6. ✅ Wizard abre com dados preenchidos
```

### **Teste 2: Salvar sem Iniciar**
```
1. Acesse /campaigns
2. Clique em "Nova Campanha"
3. Preencha todos os passos
4. No passo 4, clique em "💾 Salvar"
5. ✅ Wizard fecha
6. ✅ Campanha permanece como DRAFT
7. ✅ Mensagem: "Campanha salva com sucesso!"
```

### **Teste 3: Editar Campanha RUNNING**
```
1. Campanha em RUNNING
2. Clique em "✏️ Editar"
3. ✅ Wizard abre
4. Modifique algo
5. Clique "💾 Salvar"
6. ✅ Mudanças salvas
7. ✅ Status permanece RUNNING
```

### **Teste 4: Todos os Botões Contextuais**
```
1. Crie campanhas em cada status:
   - DRAFT
   - SCHEDULED (agende uma)
   - RUNNING (inicie uma)
   - PAUSED (pause uma running)
   - COMPLETED (espere completar)
   - CANCELLED (cancele uma)

2. ✅ Verifique que os botões corretos aparecem para cada status conforme a matriz acima
```

---

## 📝 **ARQUIVOS MODIFICADOS**

1. ✅ `frontend/static/js/app.js`
   - `buildCampaignActionButtons()` - Adicionado "Editar" em todos os status
   - `loadCampaignForEdit()` - Permite editar RUNNING e PAUSED
   - `handleCampaignSave()` - Nova função para salvar sem iniciar
   - Event listener para `campaign-save-button`

2. ✅ `frontend/templates/campaigns.html`
   - Adicionado botão "💾 Salvar" no passo 4
   - Reorganizado layout dos botões finais

3. ✅ `BOTOES_CAMPANHAS_MELHORADOS.md`
   - Este documento

---

## ✅ **STATUS FINAL**

### **Correções Aplicadas:**
- [x] Botão "Editar" aparece em PAUSED
- [x] Botão "Editar" aparece em RUNNING
- [x] Botão "Editar" aparece em SCHEDULED
- [x] Botão "💾 Salvar" adicionado ao wizard
- [x] Botão "🚀 Iniciar envio" mantido no wizard
- [x] Edição permitida em mais status
- [x] Botões contextuais para cada status

### **Aguardando Testes:**
- [ ] Teste manual no navegador
- [ ] Validação do usuário

---

## 🎯 **PARA TESTAR AGORA:**

1. Acesse: **http://localhost:8000/campaigns**

2. **Teste 1 - Criar e Salvar sem Iniciar:**
   - Clique em "Nova Campanha"
   - Preencha os passos
   - No final, clique em "💾 Salvar"
   - ✅ Deve fechar wizard e campanha fica DRAFT

3. **Teste 2 - Pausar e Editar:**
   - Inicie uma campanha
   - Clique em "Pausar"
   - ✅ Botão "✏️ Editar" deve aparecer
   - Clique em "✏️ Editar"
   - ✅ Wizard abre com dados preenchidos

4. **Teste 3 - Editar RUNNING:**
   - Campanha em RUNNING
   - ✅ Botão "✏️ Editar" deve aparecer
   - Clique em "✏️ Editar"
   - ✅ Pode modificar e salvar

---

**Por favor, teste e confirme se está funcionando conforme esperado!** 🙏

