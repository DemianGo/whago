# 📱 COMO CONFIGURAR PROXIES MOBILE

## 🎯 Por que usar Proxies Mobile?

O WhatsApp detecta:
- ✅ Mesmo IP fazendo múltiplas conexões
- ✅ IPs de datacenter (não residenciais)
- ✅ Headers inconsistentes com mobile real

**Proxies Mobile** = IPs de operadoras reais (Vivo, Claro, TIM, Oi)

---

## 🛒 Provedores Recomendados

### 1. Smartproxy Mobile (Recomendado)
- ✅ 40M+ IPs mobile reais
- ✅ Rotação automática de IP
- ✅ Suporte Brasil (Vivo, Claro, TIM)
- ✅ Session sticky (mesmo IP por sessão)
- 💰 A partir de $8/GB

**Link:** https://smartproxy.com/proxies/mobile-proxies

### 2. Bright Data (Luminati)
- ✅ Maior pool de IPs mobile
- ✅ Brasil bem coberto
- 💰 Mais caro, mas melhor qualidade

**Link:** https://brightdata.com/proxy-types/mobile-proxies

### 3. IPRoyal Mobile
- ✅ Mais barato
- ✅ Brasil disponível
- 💰 A partir de $5/GB

**Link:** https://iproyal.com/mobile-proxies/

---

## 🔧 CONFIGURAÇÃO

### Opção 1: Editar script de teste

Abra o arquivo `/home/liberai/whago/test_proxies_mobile.sh` e edite:

```bash
generate_proxy_url() {
  local session_id=$1
  
  # ==== CONFIGURAR AQUI ====
  
  # SMARTPROXY:
  local PROXY_USER="user-${session_id}"  # ← Seu usuário
  local PROXY_PASS="sua_senha_aqui"      # ← Sua senha
  local PROXY_HOST="gate.smartproxy.com"
  local PROXY_PORT="7000"
  
  # BRIGHT DATA:
  # local PROXY_USER="brd-customer-USERNAME-zone-mobile-session-${session_id}"
  # local PROXY_PASS="SUA_SENHA"
  # local PROXY_HOST="brd.superproxy.io"
  # local PROXY_PORT="22225"
  
  # IPROYAL:
  # local PROXY_USER="seu_usuario"
  # local PROXY_PASS="sua_senha"
  # local PROXY_HOST="geo.iproyal.com"
  # local PROXY_PORT="12321"
  
  echo "http://${PROXY_USER}:${PROXY_PASS}@${PROXY_HOST}:${PROXY_PORT}"
}
```

### Opção 2: Testar proxy manualmente

```bash
# Teste se o proxy funciona
curl -x http://user:pass@proxy-host:port https://api.ipify.org

# Deve retornar um IP brasileiro
```

---

## 🚀 EXECUTAR TESTES

### 1. Teste simples (1 chip)

```bash
cd /home/liberai/whago

# Testar com 1 proxy específico
curl -X POST http://localhost:3030/api/sessions/create \
  -H "Content-Type: application/json" \
  -d '{
    "alias": "test-mobile-001",
    "tenant_id": "tenant-001",
    "chip_id": "chip-001",
    "proxy_url": "http://user:pass@gate.smartproxy.com:7000",
    "preferred_manufacturer": "Samsung"
  }'
```

### 2. Teste com rotação automática

```bash
# Executar script de rotação
./test_proxies_mobile.sh
```

O script vai:
1. ✅ Testar 5 IPs diferentes
2. ✅ Parar no primeiro que funcionar
3. ✅ Se funcionar, criar 3 chips simultâneos
4. ✅ Mostrar logs em tempo real

---

## 📊 VERIFICAR RESULTADOS

### Ver logs em tempo real:
```bash
docker logs whago-baileys -f | grep -E "QR|fingerprint|Proxy|Connection"
```

### Verificar QR code:
```bash
# Substituir SESSION_ID pelo ID da sessão
curl -s http://localhost:3030/api/sessions/SESSION_ID/qr | jq '.'
```

### Ver sessões ativas:
```bash
curl -s http://localhost:3030/api/sessions | jq '.'
```

---

## 🎯 FORMATO DE PROXY POR PROVEDOR

### Smartproxy Mobile (Session Sticky)

```
# Mesmo IP por sessão
http://user-session_NOME:senha@gate.smartproxy.com:7000

# Exemplos:
http://user-session_chip1:senha@gate.smartproxy.com:7000
http://user-session_chip2:senha@gate.smartproxy.com:7000
http://user-session_chip3:senha@gate.smartproxy.com:7000
```

Cada `session_NOME` diferente = IP diferente

### Bright Data

```
# Formato geral
http://brd-customer-USERNAME-zone-mobile-session-NAME:PASSWORD@brd.superproxy.io:22225

# Com país específico (Brasil)
http://brd-customer-USERNAME-zone-mobile-country-br-session-NAME:PASSWORD@brd.superproxy.io:22225
```

### IPRoyal

```
# Formato geral
http://usuario:senha@geo.iproyal.com:12321

# Com país específico
http://usuario:senha_country-br@geo.iproyal.com:12321
```

---

## 💡 DICAS IMPORTANTES

### 1. Session Sticky (Importante!)
- Use `session_NOME` diferente para cada chip
- Mesmo session_NOME = mesmo IP
- Troca de session_NOME = troca de IP

### 2. Rotação de IP
- Se um IP for bloqueado (erro 405), **troque o session_NOME**
- Nunca use o mesmo IP em múltiplos chips

### 3. Quantidade de Chips por IP
- **NUNCA** use mais de 1 chip por IP
- WhatsApp detecta e bloqueia
- Use IPs diferentes para cada chip

### 4. Cooldown entre tentativas
- Se falhar, aguarde 15-30 segundos antes de tentar com novo IP
- Se múltiplas falhas, aguarde 30-60 minutos

### 5. Monitoramento
- Sempre monitore os logs
- Procure por "QR code" ou "connected"
- Se ver erro 405 repetido com IPs diferentes, pode ser problema do Baileys

---

## 🔥 EXEMPLO COMPLETO (3 Chips Simultâneos)

```bash
# Chip 1 (IP brasileiro - São Paulo)
curl -X POST http://localhost:3030/api/sessions/create \
  -H "Content-Type: application/json" \
  -d '{
    "alias": "chip_vivo_001",
    "tenant_id": "tenant_prod",
    "chip_id": "chip_001",
    "proxy_url": "http://user-session_vivo001:senha@gate.smartproxy.com:7000",
    "preferred_manufacturer": "Samsung"
  }'

# Aguardar 5 segundos

# Chip 2 (IP brasileiro - Rio de Janeiro)
curl -X POST http://localhost:3030/api/sessions/create \
  -H "Content-Type: application/json" \
  -d '{
    "alias": "chip_claro_002",
    "tenant_id": "tenant_prod",
    "chip_id": "chip_002",
    "proxy_url": "http://user-session_claro002:senha@gate.smartproxy.com:7000",
    "preferred_manufacturer": "Motorola"
  }'

# Aguardar 5 segundos

# Chip 3 (IP brasileiro - Belo Horizonte)
curl -X POST http://localhost:3030/api/sessions/create \
  -H "Content-Type: application/json" \
  -d '{
    "alias": "chip_tim_003",
    "tenant_id": "tenant_prod",
    "chip_id": "chip_003",
    "proxy_url": "http://user-session_tim003:senha@gate.smartproxy.com:7000",
    "preferred_manufacturer": "Xiaomi"
  }'
```

Resultado esperado:
```
✅ 3 QR codes gerados
✅ 3 IPs diferentes
✅ 3 fingerprints diferentes (Samsung, Motorola, Xiaomi)
✅ Sem bloqueio do WhatsApp
```

---

## 🆘 TROUBLESHOOTING

### Problema: Erro 405 mesmo com proxy
**Solução:**
1. Aguardar 30-60 minutos (cooldown do WhatsApp)
2. Atualizar Baileys: `cd baileys-service && npm update @whiskeysockets/baileys`
3. Verificar se proxy está funcionando: `curl -x http://user:pass@proxy:port https://api.ipify.org`

### Problema: Proxy não conecta
**Solução:**
1. Verificar credenciais
2. Testar proxy fora do Docker
3. Verificar firewall

### Problema: QR code não aparece
**Solução:**
1. Ver logs: `docker logs whago-baileys -f`
2. Aguardar até 60 segundos
3. Verificar endpoint `/sessions/SESSION_ID/qr`

### Problema: Múltiplos chips não funcionam
**Solução:**
1. Verificar se está usando **IPs diferentes** para cada chip
2. Verificar se há delay entre criações (mínimo 5s)
3. Não criar mais de 3 chips por vez

---

## 📞 SUPORTE

Se precisar de ajuda:
1. Veja os logs: `docker logs whago-baileys -f`
2. Teste proxy: `curl -x http://proxy https://api.ipify.org`
3. Verifique fingerprints: `curl http://localhost:3030/api/fingerprints/stats`

---

**Última atualização:** 17/11/2025  
**Autor:** WHAGO Team



