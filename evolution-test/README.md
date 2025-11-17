# 🧪 TESTE EVOLUTION API - MÓDULO INDEPENDENTE

## ⚠️ IMPORTANTE

Este é um **módulo de teste isolado** para testar Evolution API como alternativa ao Baileys.

**NÃO mexe no código principal do projeto.**  
**Pode ser deletado depois sem afetar nada.**

---

## 🎯 OBJETIVO

Determinar se Evolution API resolve o erro 405 do WhatsApp que estamos enfrentando.

---

## 📋 PRÉ-REQUISITOS

- Docker e Docker Compose instalados
- Python 3.8+ instalado
- Credenciais DataImpulse (já configuradas automaticamente)
- Porta 8080 disponível

---

## 🚀 INSTALAÇÃO E EXECUÇÃO

### Passo 1: Entrar na pasta do teste

```bash
cd /home/liberai/whago/evolution-test
```

### Passo 2: Subir Evolution API

```bash
docker-compose up -d
```

**Aguarde 30-60 segundos** para os containers iniciarem.

### Passo 3: Verificar se está rodando

```bash
docker-compose ps
```

Você deve ver 3 containers rodando:
- evolution-test-api
- evolution-test-postgres  
- evolution-test-redis

### Passo 4: Verificar saúde da API

```bash
curl http://localhost:8080/
```

Deve retornar algo como `{"status":"ok"}` ou resposta HTML.

### Passo 5: Executar o teste

```bash
python3 test_evolution.py
```

### Passo 6: Acompanhar o resultado

O teste irá:

1. ✅ Validar proxy DataImpulse
2. ✅ Aplicar fingerprinting avançado
3. ✅ Criar instância Evolution
4. ✅ Gerar QR Code
5. ⏳ Aguardar 60 segundos para conexão
6. 📊 Gerar relatório completo

**Se encontrar credenciais inválidas do proxy**, o teste tentará automaticamente outras sessões.

---

## 📊 RELATÓRIO

Após o teste, será gerado `test_report.json` com:

```json
{
  "timestamp": "2025-11-17T03:30:00",
  "metrics": {
    "proxy_validated": true/false,
    "fingerprint_applied": true/false,
    "instance_created": true/false,
    "qr_generated": true/false,
    "error_405_occurred": true/false,
    "connection_successful": true/false
  },
  "conclusion": "SUCESSO / FALHA / INCONCLUSIVO"
}
```

---

## ✅ POSSÍVEIS RESULTADOS

### Resultado 1: ✅ SUCESSO

```
CONCLUSÃO: Evolution API resolveu o problema!
```

**Ação:** Planejar migração do Baileys para Evolution.

### Resultado 2: ❌ ERRO 405 PERSISTE

```
CONCLUSÃO: ERRO 405 PERSISTE COM EVOLUTION API
```

**Ação:** Problema é infraestrutura (proxy/IP), não biblioteca.  
Necessário contratar Smartproxy ou Bright Data.

### Resultado 3: ⏳ INCONCLUSIVO

```
CONCLUSÃO: QR Code gerado mas não foi escaneado
```

**Ação:** Repetir teste escaneando o QR Code dentro de 60s.

---

## 🔒 PROTEÇÕES APLICADAS

Este teste aplica **TODAS** as mesmas proteções que temos no sistema principal:

✅ **Mobile Proxy DataImpulse** obrigatório  
✅ **Fingerprinting** avançado (Samsung/Motorola/Xiaomi)  
✅ **Rate Limiting** (30s delay antes de conectar)  
✅ **Session ID** único com UUID para rotação de IP  
✅ **User-Agent** dinâmico e realista  
✅ **Timeout generoso** (60s+)  
✅ **Máximo 1 tentativa** por execução  
✅ **Log detalhado** de cada etapa

---

## 🧹 LIMPEZA

### Parar teste:

```bash
docker-compose down
```

### Remover completamente (incluindo volumes):

```bash
docker-compose down -v
```

### Deletar pasta:

```bash
cd /home/liberai/whago
rm -rf evolution-test
```

**Não afeta nada do projeto principal!**

---

## 🔍 TROUBLESHOOTING

### Problema: Porta 8080 já em uso

**Solução:** Editar `docker-compose.yml` e mudar para outra porta:

```yaml
ports:
  - "8081:8080"  # Usar 8081 ao invés de 8080
```

### Problema: Proxy não valida

**Solução:** O script tenta automaticamente outras sessões até encontrar credenciais válidas.

Se todas falharem, significa que **todas as credenciais DataImpulse expiraram**.

### Problema: Evolution API não responde

**Solução:** Verificar logs:

```bash
docker logs evolution-test-api
```

### Problema: QR Code não gera

**Solução:** Verificar se proxy está bloqueando:

```bash
curl -x "socks5://b0d7c401317486d2c3e8__cr.br:f60a2f1e36dcd0b4@gw.dataimpulse.com:824" \
     https://api.ipify.org
```

---

## 📚 DOCUMENTAÇÃO OFICIAL

- **Evolution API:** https://doc.evolution-api.com/
- **WhatsApp Baileys:** https://github.com/WhiskeySockets/Baileys
- **DataImpulse:** https://dataimpulse.com

---

## ⚡ EXECUÇÃO RÁPIDA (RESUMO)

```bash
# 1. Entrar na pasta
cd /home/liberai/whago/evolution-test

# 2. Subir containers
docker-compose up -d

# 3. Aguardar 60s

# 4. Executar teste
python3 test_evolution.py

# 5. Ver resultado
cat test_report.json

# 6. Limpar tudo
docker-compose down -v
```

---

**Última atualização:** 17/11/2025 03:30 UTC

