# 🧪 WAHA PLUS - GUIA DE TESTES

**Status:** ✅ Código implementado e pronto para testes  
**Data:** 17 de Novembro de 2025

---

## 📋 PRÉ-REQUISITOS

Antes de iniciar os testes, certifique-se de que:

- ✅ Docker e Docker Compose instalados
- ✅ Backend WHAGO rodando (`docker ps | grep whago-backend`)
- ✅ PostgreSQL rodando (`docker ps | grep postgres`)
- ✅ Redis rodando (opcional, mas recomendado)
- ✅ Credenciais WAHA Plus configuradas

---

## 🚀 PASSO 1: INSTALAR DEPENDÊNCIAS

### 1.1. Instalar bibliotecas Python

```bash
# Entrar no container backend
docker exec -it whago-backend bash

# Instalar dependências
pip install --break-system-packages docker redis

# Sair do container
exit
```

### 1.2. Reiniciar backend

```bash
docker compose restart backend
```

### 1.3. Verificar logs (não deve haver erros de import)

```bash
docker logs whago-backend -f
```

**✅ Esperado:** Nenhum erro de `ModuleNotFoundError: No module named 'docker'`

---

## 🧪 PASSO 2: TESTES VIA API

### 2.1. Fazer Login

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@whago.com", "password": "Test@123456"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"
```

**✅ Esperado:** Token JWT válido

### 2.2. Criar Primeiro Chip

```bash
CHIP1=$(curl -s -X POST http://localhost:8000/api/v1/chips \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"alias": "teste_waha_plus_1"}')

echo $CHIP1 | jq .

# Salvar ID do chip
CHIP1_ID=$(echo $CHIP1 | jq -r '.id')
echo "Chip ID: $CHIP1_ID"
```

**✅ Esperado:**
```json
{
  "id": "abc-123-...",
  "alias": "teste_waha_plus_1",
  "status": "WAITING_QR",
  "extra_data": {
    "waha_plus_container": "waha_plus_user_<uuid>",
    "waha_plus_port": 3100,
    "waha_session": "chip_abc-123",
    "proxy_enabled": true
  }
}
```

### 2.3. Verificar Container WAHA Plus Criado

```bash
docker ps | grep waha_plus
```

**✅ Esperado:**
```
waha_plus_user_<uuid>  devlikeapro/waha-plus:latest  Up  0.0.0.0:3100->3000/tcp
```

### 2.4. Obter QR Code

```bash
QR_RESPONSE=$(curl -s -X GET "http://localhost:8000/api/v1/chips/$CHIP1_ID/qr" \
  -H "Authorization: Bearer $TOKEN")

echo $QR_RESPONSE | jq .
```

**✅ Esperado:**
```json
{
  "qr": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...",
  "expires_at": null
}
```

### 2.5. Salvar QR Code como Imagem (Opcional)

```bash
# Extrair base64 e salvar como PNG
echo $QR_RESPONSE | jq -r '.qr' | sed 's/data:image\/png;base64,//' | base64 -d > /tmp/qr_waha_plus_test.png

# Verificar
file /tmp/qr_waha_plus_test.png
```

**✅ Esperado:** `/tmp/qr_waha_plus_test.png: PNG image data`

---

## 🧪 PASSO 3: TESTE DE MÚLTIPLOS CHIPS

### 3.1. Criar 10 Chips (Mesmo Usuário)

```bash
for i in {2..10}; do
  echo "Criando chip $i..."
  curl -s -X POST http://localhost:8000/api/v1/chips \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"alias\": \"teste_waha_plus_$i\"}" | jq '.id, .alias'
  sleep 2
done
```

**✅ Esperado:** 10 chips criados, todos no **mesmo container** WAHA Plus

### 3.2. Verificar Quantidade de Containers

```bash
docker ps | grep waha_plus | wc -l
```

**✅ Esperado:** `1` (apenas 1 container para o usuário)

### 3.3. Listar Sessões no Container WAHA Plus

```bash
# Obter nome do container
CONTAINER_NAME=$(docker ps --filter "label=whago.service=waha-plus" --format "{{.Names}}" | head -1)

# Obter API Key
API_KEY=$(docker exec $CONTAINER_NAME printenv WAHA_API_KEY)

# Listar sessões
curl -s http://localhost:3100/api/sessions \
  -H "X-Api-Key: $API_KEY" | jq '.[] | {name, status}'
```

**✅ Esperado:** Lista de 10 sessões (`chip_<id1>`, `chip_<id2>`, ..., `chip_<id10>`)

---

## 🧪 PASSO 4: TESTE DE MÚLTIPLOS USUÁRIOS

### 4.1. Criar Usuários de Teste (via Seed ou API)

```bash
# Supondo que você tenha um script de seed
docker exec -it whago-backend python -m backend.scripts.seed_users
```

### 4.2. Login com Usuário 2

```bash
TOKEN2=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test2@whago.com", "password": "Test@123456"}' \
  | jq -r '.access_token')
```

### 4.3. Criar Chip para Usuário 2

```bash
curl -s -X POST http://localhost:8000/api/v1/chips \
  -H "Authorization: Bearer $TOKEN2" \
  -H "Content-Type: application/json" \
  -d '{"alias": "chip_user2_1"}' | jq .
```

**✅ Esperado:** Novo container `waha_plus_user_<uuid2>` na porta `3101`

### 4.4. Verificar 2 Containers

```bash
docker ps | grep waha_plus
```

**✅ Esperado:**
```
waha_plus_user_<uuid1>  ...  0.0.0.0:3100->3000/tcp
waha_plus_user_<uuid2>  ...  0.0.0.0:3101->3000/tcp
```

---

## 🧪 PASSO 5: MONITORAMENTO E LOGS

### 5.1. Logs do Backend

```bash
docker logs whago-backend -f
```

**🔍 Procurar por:**
- `Verificando/criando container WAHA Plus para user...`
- `Container WAHA Plus criado: waha_plus_user_xxx`
- `Sessão WAHA Plus criada e iniciada: chip_xxx`

### 5.2. Logs do Container WAHA Plus

```bash
# Container do usuário 1
docker logs waha_plus_user_<uuid1> -f
```

**🔍 Procurar por:**
- `WAHA is starting...`
- `WAHA Tier: PLUS`
- `Session chip_xxx started`
- `Status: SCAN_QR_CODE`

### 5.3. Estatísticas dos Containers

```bash
docker stats $(docker ps --filter "label=whago.service=waha-plus" --format "{{.Names}}")
```

**✅ Esperado:** CPU ~5-10%, Memória ~200-300 MB por container

---

## 🧪 PASSO 6: TESTES FUNCIONAIS (COM WHATSAPP REAL)

### 6.1. Escanear QR Code

1. Abrir WhatsApp no celular
2. Ir em **Dispositivos Conectados** → **Conectar Dispositivo**
3. Escanear o QR code obtido no Passo 2.4

**✅ Esperado:** Chip muda de status para `CONNECTED`

### 6.2. Verificar Status do Chip

```bash
curl -s -X GET "http://localhost:8000/api/v1/chips/$CHIP1_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.status'
```

**✅ Esperado:** `"CONNECTED"`

### 6.3. Enviar Mensagem de Teste (via API)

```bash
curl -X POST "http://localhost:8000/api/v1/chips/$CHIP1_ID/messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "5511999999999",
    "message": "Teste WAHA Plus integrado!"
  }'
```

**✅ Esperado:** Mensagem enviada com sucesso, recebida no WhatsApp de destino

---

## 🧪 PASSO 7: TESTE DE PERSISTÊNCIA

### 7.1. Reiniciar Container WAHA Plus

```bash
docker restart waha_plus_user_<uuid1>
```

### 7.2. Aguardar Reinicialização (30 segundos)

```bash
sleep 30
```

### 7.3. Verificar Status do Chip

```bash
curl -s -X GET "http://localhost:8000/api/v1/chips/$CHIP1_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.status'
```

**✅ Esperado:** `"CONNECTED"` (sessão persistiu via PostgreSQL)

---

## 🧪 PASSO 8: TESTE DE LIMPEZA

### 8.1. Deletar Chip

```bash
curl -X DELETE "http://localhost:8000/api/v1/chips/$CHIP1_ID" \
  -H "Authorization: Bearer $TOKEN"
```

**✅ Esperado:** Chip deletado, sessão removida do WAHA Plus

### 8.2. Verificar Container Continua (com outras sessões)

```bash
docker ps | grep waha_plus_user_<uuid1>
```

**✅ Esperado:** Container ainda rodando (tem 9 sessões restantes)

### 8.3. Deletar Todos os Chips do Usuário

```bash
# Obter lista de chips
CHIPS=$(curl -s -X GET "http://localhost:8000/api/v1/chips" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.[].id')

# Deletar cada chip
for chip_id in $CHIPS; do
  echo "Deletando chip $chip_id..."
  curl -X DELETE "http://localhost:8000/api/v1/chips/$chip_id" \
    -H "Authorization: Bearer $TOKEN"
  sleep 1
done
```

### 8.4. Container Deve Permanecer (até cleanup manual)

```bash
docker ps | grep waha_plus
```

**ℹ️ Nota:** Container permanece até cleanup manual ou implementação de auto-cleanup

---

## 🔧 TROUBLESHOOTING

### ❌ Erro: `ModuleNotFoundError: No module named 'docker'`

**Solução:**
```bash
docker exec -it whago-backend pip install --break-system-packages docker redis
docker compose restart backend
```

### ❌ Erro: `Port 3100 already in use`

**Solução:** WahaContainerManager aloca próxima porta disponível automaticamente.

Se todas estiverem ocupadas:
```bash
docker ps -a | grep waha_plus | awk '{print $1}' | xargs docker rm -f
```

### ❌ QR Code não aparece

**Diagnóstico:**
```bash
# 1. Verificar status da sessão
curl http://localhost:3100/api/sessions/chip_<id> \
  -H "X-Api-Key: <api_key>"

# 2. Verificar logs WAHA Plus
docker logs waha_plus_user_<uuid> -f

# 3. Verificar logs backend
docker logs whago-backend -f
```

**Status esperado:** `SCAN_QR_CODE`

### ❌ Container não inicia

**Logs:**
```bash
docker logs waha_plus_user_<uuid>
```

**Causas comuns:**
1. **SSL PostgreSQL:** Adicionar `sslmode=disable` na `POSTGRES_URL`
2. **Credenciais inválidas:** Verificar `WAHA_API_KEY`
3. **Imagem não encontrada:** `docker pull devlikeapro/waha-plus:latest`

---

## ✅ CHECKLIST DE SUCESSO

- [ ] Dependências instaladas no backend
- [ ] Backend reiniciado sem erros
- [ ] Chip criado via API
- [ ] Container WAHA Plus criado automaticamente
- [ ] QR Code obtido com sucesso (PNG base64)
- [ ] 10 chips criados no mesmo container
- [ ] Múltiplos usuários criando containers separados
- [ ] Logs sem erros
- [ ] QR Code escaneado e chip conectado (opcional)
- [ ] Mensagem enviada com sucesso (opcional)
- [ ] Persistência após reinicialização
- [ ] Chip deletado sem erros

---

## 📊 MÉTRICAS ESPERADAS

| Métrica | Valor Esperado |
|---------|----------------|
| Containers por usuário | 1 |
| Sessões por container | 0-10 (Enterprise) |
| Memória por container | ~200-300 MB |
| CPU por container | ~5-15% |
| Tempo de criação de container | ~10-20 segundos |
| Tempo de criação de sessão | ~3-5 segundos |
| Tempo de geração de QR | ~1-2 segundos |

---

## 🎯 PRÓXIMOS PASSOS

1. ✅ **Testes E2E:** Executar todos os passos acima
2. ⏳ **Frontend:** Testar criação de chips via interface web
3. ⏳ **Webhooks:** Implementar `/api/v1/webhooks/waha`
4. ⏳ **Monitoramento:** Configurar Grafana/Prometheus
5. ⏳ **Produção:** Deploy em ambiente de staging

---

**Dúvidas?** Consulte:
- `README_WAHA_PLUS_INTEGRATION.md` para documentação completa
- `CONCLUSAO_INTEGRACAO_WAHA_PLUS.md` para resumo executivo
- Logs: `docker logs whago-backend -f`

---

**Desenvolvido por:** Arquiteto de Software Sênior  
**Data:** 17 de Novembro de 2025  
**Versão:** 1.0.0
