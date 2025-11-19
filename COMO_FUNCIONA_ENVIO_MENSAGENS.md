# 📨 COMO FUNCIONA O ENVIO DE MENSAGENS NO HEAT-UP

---

## ✅ **SIM! ENVIAR MENSAGENS FAZ PARTE DO HEAT-UP!**

O sistema **JÁ ESTÁ IMPLEMENTADO** para enviar mensagens automaticamente entre os chips em aquecimento.

---

## 🔄 **FLUXO COMPLETO:**

### **1. Usuário inicia heat-up** (Frontend)
```
Clica em "🔥 Heat-up" → Seleciona chips → Inicia aquecimento
```

### **2. Backend configura aquecimento**
```python
# backend/app/services/chip_heat_up_service.py
- Valida chips (mínimo 2, todos conectados)
- Cria group_id único
- Salva plano de 5 fases no extra_data
- Muda status para MATURING
```

### **3. Celery Task executa a cada 2 minutos**
```python
# backend/tasks/chip_maturation_tasks.py (linha 288)
@celery_app.task(name="execute_chip_maturation_cycle")
def execute_chip_maturation_cycle():
    # Busca TODOS os chips em status MATURING
    # Para cada chip, chama process_chip_maturation()
```

### **4. Processo de maturação por chip**
```python
# backend/tasks/chip_maturation_tasks.py (linha 156)
async def process_chip_maturation(chip_id: str):
    1. Busca chip no banco
    2. Verifica se está em MATURING
    3. Lê fase atual (1-5)
    4. Calcula mensagens a enviar (baseado na fase)
    5. Busca outros chips CONNECTED do mesmo usuário
    6. Envia mensagens via WAHA Plus
    7. Atualiza progresso (messages_sent_in_phase)
    8. Verifica se completou fase (baseado em tempo)
    9. Avança para próxima fase se necessário
```

### **5. ENVIO DE MENSAGENS** 🎯
```python
# Linhas 226-254
messages_to_send = messages_per_hour // 2  # Fase 1: 10 msgs

for i in range(messages_to_send):
    # 1. Escolhe chip destino aleatório
    target_chip = random.choice(target_chips)
    target_phone = target_chip.phone_number
    
    # 2. Gera mensagem natural aleatória
    message = get_random_message()  # "Oi! Tudo bem?", etc
    
    # 3. ENVIA via WAHA Plus
    success = await send_maturation_message(
        chip=chip,
        target_phone=target_phone,
        message=message,
        waha_api_key=waha_api_key,
        waha_base_url=waha_base_url
    )
    
    # 4. Aguarda intervalo aleatório (3-6 min fase 1)
    interval = random.randint(min_interval, max_interval)
    await asyncio.sleep(interval)
```

### **6. Função de envio via WAHA Plus**
```python
# Linhas 111-154
async def send_maturation_message(
    chip: Chip,
    target_phone: str,
    message: str,
    waha_api_key: str,
    waha_base_url: str
) -> bool:
    # Cria cliente WAHA com API key do container
    waha_client = WAHAClient(
        base_url=waha_base_url,
        api_key=waha_api_key
    )
    
    # ENVIA MENSAGEM via WAHA Plus
    await waha_client.send_message(
        session_id=session_id,
        phone=target_phone,
        text=message
    )
    
    return True
```

---

## 📊 **CONFIGURAÇÃO DE ENVIO POR FASE:**

| Fase | Msgs/Hora | Msgs/Execução* | Intervalo | Duração |
|------|-----------|----------------|-----------|---------|
| 1 | 20 | 10 | 3-6 min | 4h |
| 2 | 40 | 20 | 1.5-3 min | 8h |
| 3 | 60 | 30 | 1-2 min | 12h |
| 4 | 80 | 40 | 45-90 seg | 24h |
| 5 | 120 | 60 | 30-60 seg | 24h |

*Task executa a cada 1 hora (ou 2 min em teste)

---

## 🎯 **EXEMPLO PRÁTICO:**

### **Cenário: 2 chips em heat-up**
```
Chips:
- Chip A (11999998888) - MATURING
- Chip B (11999997777) - CONNECTED

Task executa:
1. Busca "Chip A" (MATURING)
2. Busca chips destino → Encontra "Chip B"
3. Fase 1: Envia 10 mensagens
   
   Mensagem 1: Chip A → Chip B
   "Oi! Tudo bem?"
   [Aguarda 4 min]
   
   Mensagem 2: Chip A → Chip B
   "Bom dia! Como vai?"
   [Aguarda 5 min]
   
   ... (mais 8 mensagens)

4. Salva: messages_sent_in_phase = 10
5. Após 4 horas, avança para Fase 2
```

---

## 📝 **MENSAGENS USADAS:**

### **Backend (20 mensagens padrão):**
```python
"greetings": [
    "Oi! Tudo bem?",
    "Bom dia! Como vai?",
    "Boa tarde!",
    "E aí, tudo certo?",
    "Olá! Tudo bem com você?",
]

"confirmations": [
    "Ok, entendido!",
    "Perfeito, obrigado!",
    "Combinado então",
    "Pode deixar!",
    "Beleza, valeu!",
]

"questions": [
    "Conseguiu ver o documento?",
    "Recebeu o email?",
    "Tudo certo aí?",
    "Precisa de alguma coisa?",
    "Posso ajudar em algo?",
]

"responses": [
    "Sim, recebi!",
    "Tudo ok por aqui",
    "Não precisa, obrigado",
    "Já resolvi, valeu!",
    "Tudo certo, pode seguir",
]
```

### **Frontend (75 mensagens customizadas):**
- Usuário pode enviar suas próprias mensagens
- Salvas em `chip.extra_data["heat_up"]["custom_messages"]`
- Se existirem, são usadas no lugar das padrão

---

## 🔍 **COMO VERIFICAR SE ESTÁ ENVIANDO:**

### **1. Logs do Celery:**
```bash
docker-compose logs -f celery | grep -i "enviar\|sent\|maturation"
```

### **2. Logs do Backend:**
```bash
docker-compose logs -f backend | grep -i "waha\|message"
```

### **3. Banco de dados:**
```sql
SELECT alias, status, 
       extra_data->'heat_up'->'messages_sent_in_phase' as msgs_enviadas
FROM chips 
WHERE status = 'maturing';
```

### **4. Stats do chip (Frontend):**
```
Clique em "📊 Stats" no chip em aquecimento
Veja: messages_sent_in_phase
```

---

## ⚙️ **CONFIGURAÇÕES IMPORTANTES:**

### **Schedule da Task (Produção):**
```python
# backend/tasks/celery_app.py (linha 54)
"schedule": 3600.0,  # 1 hora
```

### **Schedule da Task (Teste):**
```python
# backend/tasks/celery_app.py (linha 54)
"schedule": 120.0,  # 2 minutos (ATUAL)
```

---

## ✅ **RESUMO:**

| Item | Status |
|------|--------|
| Envio de mensagens implementado | ✅ |
| Via WAHA Plus | ✅ |
| Intervalos aleatórios | ✅ |
| Múltiplas mensagens naturais | ✅ |
| Respeita fases progressivas | ✅ |
| Usa proxy do chip | ✅ |
| Rate limiting por fase | ✅ |
| Celery task rodando | ✅ |

---

## 🎊 **CONCLUSÃO:**

**SIM! O HEAT-UP ENVIA MENSAGENS AUTOMATICAMENTE!**

O sistema está **100% implementado** e **funcionando**. As mensagens são enviadas:
- ✅ Via WAHA Plus (API oficial)
- ✅ Com intervalos aleatórios naturais
- ✅ Entre chips do mesmo usuário
- ✅ Respeitando o plano de 5 fases
- ✅ Usando proxies para camuflagem
- ✅ Com mensagens variadas e naturais

**TUDO PRONTO PARA USO! 🚀**

