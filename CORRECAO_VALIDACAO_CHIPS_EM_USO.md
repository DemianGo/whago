# Correção: Validação de Chips em Uso

## 🐛 **PROBLEMAS REPORTADOS**

### **1. Conseguiu usar o mesmo chip em duas campanhas:**
> "acabei de escolher o mesmo chip com sucesso em duas campanhas diferentes, corrija."

**Causa:** A validação de "um chip por campanha" só estava no `start_campaign`, não no `update_campaign`.

---

### **2. Erros apareciam fora do popup:**
> "Mostre erros dentro do popup, não na página de trás caso o popup esteja ativo."

**Causa:** O feedback não fazia scroll para o topo do wizard e o parsing de erros estava incorreto.

---

## 🔍 **ANÁLISE DO PROBLEMA 1**

### **Fluxo Problemático:**

```
Usuário cria Campanha A:
  Passo 1: Informações básicas
  Passo 2: Seleciona chip1 ← PUT /campaigns/{id} com settings
    ❌ Backend NÃO validava chips em uso
  Passo 3: Contatos
  Passo 4: Iniciar ← Aqui sim validava, mas tarde demais
    ❌ Se iniciasse, validaria e bloquearia
    ✅ Mas se pausasse/editasse, não validava

Usuário cria Campanha B:
  Passo 2: Seleciona chip1 (mesmo chip)
    ❌ Backend NÃO validava
    ✅ Permitia salvar
    
Resultado: Duas campanhas com o mesmo chip!
```

### **Problema:**
A validação só estava em `start_campaign()`, mas os chips são escolhidos em `update_campaign()` no passo 2.

---

## ✅ **SOLUÇÃO 1: Validar no Update**

### **Backend - Adicionar validação no `update_campaign`:**

```python
# backend/app/services/campaign_service.py - update_campaign()

if data.settings is not None:
    settings = self._normalize_settings(db_user, data.settings, campaign.type)
    await self._validate_chip_limits(db_user, settings.chip_ids)
    
    # ✅ NOVA VALIDAÇÃO: Chips não podem estar em uso
    chip_ids = settings.chip_ids or []
    if chip_ids:
        # Buscar todas as campanhas RUNNING do usuário (excluindo a atual)
        result_running = await self.session.execute(
            select(Campaign).where(
                Campaign.user_id == user.id,
                Campaign.status == CampaignStatus.RUNNING,
                Campaign.id != campaign.id
            )
        )
        running_campaigns = result_running.scalars().all()
        
        # Extrair todos os chip_ids em uso
        chips_in_use = set()
        for running_campaign in running_campaigns:
            running_settings = running_campaign.settings or {}
            running_chip_ids = running_settings.get("chip_ids") or []
            chips_in_use.update(running_chip_ids)
        
        # Verificar conflitos
        chip_ids_set = set(chip_ids)
        conflicting_chips = chip_ids_set & chips_in_use
        
        if conflicting_chips:
            # Buscar aliases dos chips conflitantes
            result_chip_aliases = await self.session.execute(
                select(Chip.alias).where(Chip.id.in_(conflicting_chips))
            )
            chip_aliases = [row[0] for row in result_chip_aliases.all()]
            chips_str = ", ".join(chip_aliases)
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Os seguintes chips já estão sendo usados por outra campanha em andamento: {chips_str}. Um chip não pode ser usado por múltiplas campanhas simultaneamente.",
            )
    
    campaign.settings = settings.model_dump(mode="json")
```

---

## 🎬 **NOVO FLUXO (CORRETO)**

```
Usuário cria Campanha A:
  Passo 2: Seleciona chip1
    ✅ PUT /campaigns/{id} com settings
    ✅ Backend valida chips em uso
    ✅ chip1 não está em uso
    ✅ Salva settings
  Passo 4: Iniciar
    ✅ Campanha A → RUNNING com chip1

Usuário cria Campanha B:
  Passo 2: Seleciona chip1 (mesmo chip)
    ✅ PUT /campaigns/{id} com settings
    ✅ Backend valida chips em uso
    ❌ chip1 JÁ está em uso por Campanha A
    ❌ Retorna 400 com mensagem clara
    💬 "Os seguintes chips já estão sendo usados por outra campanha em andamento: chip1"
    
Usuário vê erro no popup
```

---

## ✅ **SOLUÇÃO 2: Feedback no Popup**

### **Problema do Feedback:**

1. **Mensagem aparecia fora do popup** (na página de trás)
2. **Não fazia scroll** para o topo do wizard
3. **Parsing incorreto** de mensagens de erro JSON

### **Frontend Corrigido:**

```javascript
// frontend/static/js/app.js - setCampaignFeedback()

function setCampaignFeedback(message, type = "info") {
  const feedback = document.getElementById("campaign-feedback");
  if (!feedback) return;
  
  // ✅ Fazer scroll para o topo do wizard para mostrar a mensagem
  const wizard = document.getElementById("campaign-wizard");
  if (wizard && !wizard.classList.contains("hidden")) {
    wizard.scrollTop = 0;  // ← NOVO
  }
  
  feedback.textContent = message ?? "";
  // ... resto do código ...
}
```

```javascript
// frontend/static/js/app.js - handleCampaignChipsSubmit()

if (!response?.ok) {
  let message = "Não foi possível salvar as configurações de chips.";
  
  // ✅ Parsing robusto de erro JSON
  try {
    const errorData = await response.json();
    message = errorData.detail || errorData.message || message;
  } catch {
    const text = await response.text();
    if (text) {
      try {
        const parsed = JSON.parse(text);
        message = parsed.detail || parsed.message || text;
      } catch {
        message = text;
      }
    }
  }
  
  setCampaignFeedback(message, "error");  // ← Mostra no popup
  return;
}
```

---

## 📊 **PONTOS DE VALIDAÇÃO**

### **Agora a validação acontece em 2 momentos:**

1. **`update_campaign` (Passo 2 do Wizard):**
   - Quando usuário seleciona chips
   - Valida se chips já estão em uso
   - Bloqueia ANTES de salvar

2. **`start_campaign` (Iniciar Campanha):**
   - Quando usuário clica "Iniciar"
   - Valida novamente (defesa em profundidade)
   - Garante que mesmo se algo falhar, não inicia

---

## 🎨 **EXPERIÊNCIA DO USUÁRIO**

### **Antes (❌ Ruim):**
```
Usuário cria 2 campanhas com mesmo chip
  ✅ Ambas salvam sem erro
  ✅ Usuário pensa que está tudo ok
  ❌ Ao iniciar segunda, recebe erro genérico
  ❌ Mensagem aparece fora do popup
  ❌ Usuário não sabe o que fazer
```

### **Agora (✅ Bom):**
```
Usuário cria Campanha A com chip1
  ✅ Inicia Campanha A → RUNNING

Usuário cria Campanha B
  ✅ Tenta selecionar chip1 no passo 2
  ❌ Wizard mostra DENTRO DO POPUP:
      "Os seguintes chips já estão sendo usados 
       por outra campanha em andamento: chip1. 
       Um chip não pode ser usado por múltiplas 
       campanhas simultaneamente."
  ✅ Scroll automático para o topo
  ✅ Usuário vê o erro claramente
  ✅ Seleciona chip2 e continua
```

---

## 📝 **ARQUIVOS MODIFICADOS**

### **Backend:**
1. ✅ `/home/liberai/whago/backend/app/services/campaign_service.py`
   - Linha 198-241: `update_campaign()`
   - Adiciona validação de chips em uso quando `settings` são atualizados
   - Mesma lógica de `start_campaign`

### **Frontend:**
2. ✅ `/home/liberai/whago/frontend/static/js/app.js`
   - Linha 67-90: `setCampaignFeedback()`
     - Adiciona scroll para topo do wizard
   - Linha 2481-2492: `handleCampaignChipsSubmit()`
     - Melhora parsing de erros JSON
     - Extrai `detail` corretamente

---

## ✅ **GARANTIAS AGORA**

### **1. Validação em Múltiplos Pontos:**
- ✅ No passo 2 (seleção de chips) - `update_campaign`
- ✅ Ao iniciar (start) - `start_campaign`
- ✅ Ao retomar (resume) - `start_campaign`

### **2. Feedback Sempre Visível:**
- ✅ Mensagem aparece DENTRO do popup
- ✅ Scroll automático para o topo
- ✅ Parsing correto de erros JSON

### **3. Mensagens Claras:**
- ✅ Informa quais chips estão em conflito
- ✅ Explica que não pode usar múltiplas campanhas
- ✅ Usuário sabe exatamente o que fazer

---

## 🧪 **COMO TESTAR**

### **Teste 1: Tentar usar mesmo chip em duas campanhas**
```
1. Inicie Campanha A com chip1
   ✅ Campanha A → RUNNING

2. Crie Campanha B
3. Vá para passo 2
4. Veja que chip1 aparece "(Em uso por outra campanha)"
   ✅ Checkbox desabilitado

5. Se conseguir burlar e tentar salvar mesmo assim:
   ❌ Erro 400
   💬 "Os seguintes chips já estão sendo usados..."
   ✅ Mensagem aparece NO POPUP
   ✅ Scroll para o topo automaticamente
```

### **Teste 2: Editar campanha e trocar para chip em uso**
```
1. Campanha A (RUNNING) com chip1
2. Campanha B (PAUSED) com chip2

3. Edite Campanha B
4. Passo 2: Troque chip2 por chip1
5. Clique "Continuar"
   ❌ Erro 400
   💬 "Os seguintes chips já estão sendo usados: chip1"
   ✅ Mensagem NO POPUP
```

### **Teste 3: Mensagem de erro visível**
```
1. Force qualquer erro no passo 2
2. Verifique:
   ✅ Mensagem aparece no topo do popup
   ✅ Scroll automático para o topo
   ✅ Mensagem clara e legível
   ✅ Página de trás não mostra nada
```

---

## 💡 **POR QUE ESTAVA QUEBRANDO?**

### **Minha Falha:**
Implementei a validação apenas em `start_campaign`, assumindo que era suficiente.

**Mas esqueci que:**
- Usuário seleciona chips no **passo 2** (update)
- Não necessariamente inicia a campanha imediatamente
- Pode criar, pausar, editar, etc.

**Resultado:** 
- Validação só no `start` é tarde demais
- Usuário já salvou settings com chips conflitantes

### **Lição:**
**Validar no momento da seleção (update), não apenas na execução (start).**

---

## ✅ **STATUS FINAL**

### **Correções Aplicadas:**
- [x] Backend valida chips em uso no `update_campaign`
- [x] Backend valida chips em uso no `start_campaign` (já tinha)
- [x] Frontend faz scroll para topo do wizard
- [x] Frontend parseia erros JSON corretamente
- [x] Mensagens aparecem DENTRO do popup
- [x] Backend reiniciado
- [x] Documentação criada

### **Garantias:**
- ✅ **Impossível** usar mesmo chip em múltiplas campanhas RUNNING
- ✅ **Validação dupla** (update + start)
- ✅ **Feedback sempre visível** dentro do popup
- ✅ **Mensagens claras** com nomes dos chips

---

## 🎯 **TESTE AGORA**

**Por favor, teste:**

1. **Inicie Campanha A com chip1**
2. **Crie Campanha B**
3. **Tente selecionar chip1 no passo 2**
   - ✅ Deve aparecer "(Em uso por outra campanha)"
   - ✅ Checkbox desabilitado

4. **Se tentar salvar chip1 (burlar):**
   - ❌ Erro 400
   - ✅ Mensagem NO POPUP (não na página de trás)
   - ✅ Mensagem: "Os seguintes chips já estão sendo usados..."

5. **Selecione chip2 e continue:**
   - ✅ Deve funcionar normalmente

---

**Desculpe novamente pelo bug! Agora está validando corretamente e mostrando erros dentro do popup!** 🙏

**Confirme se está funcionando?**

