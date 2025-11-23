#!/bin/bash

# TESTE RÁPIDO COM PROXY MOBILE
# Configure suas credenciais abaixo e execute

set -e

echo "🚀 TESTE COM FINGERPRINTS + PROXY MOBILE"
echo "========================================"
echo ""

# ============================================
# CONFIGURE SUAS CREDENCIAIS AQUI:
# ============================================

# Opção 1: Smartproxy Mobile
PROXY_USER="user-session_test1"
PROXY_PASS="SUA_SENHA_AQUI"
PROXY_HOST="gate.smartproxy.com"
PROXY_PORT="7000"

# Opção 2: Bright Data
# PROXY_USER="brd-customer-USERNAME-zone-mobile-session-test1"
# PROXY_PASS="SUA_SENHA"
# PROXY_HOST="brd.superproxy.io"
# PROXY_PORT="22225"

# Opção 3: IPRoyal
# PROXY_USER="seu_usuario"
# PROXY_PASS="sua_senha_country-br"
# PROXY_HOST="geo.iproyal.com"
# PROXY_PORT="12321"

# Opção 4: Proxy FREE para teste (não recomendado para produção)
# PROXY_USER=""
# PROXY_PASS=""
# PROXY_HOST="proxy-server.com"
# PROXY_PORT="8080"

# ============================================

PROXY_URL="http://${PROXY_USER}:${PROXY_PASS}@${PROXY_HOST}:${PROXY_PORT}"

echo "🌐 Proxy configurado: ${PROXY_USER}@${PROXY_HOST}:${PROXY_PORT}"
echo ""

# Verificar se proxy funciona
echo "🔍 Testando conectividade do proxy..."
if curl -x "$PROXY_URL" -s --connect-timeout 10 https://api.ipify.org > /dev/null 2>&1; then
  IP=$(curl -x "$PROXY_URL" -s https://api.ipify.org)
  echo "✅ Proxy funcionando! IP: $IP"
else
  echo "❌ Proxy não conectou. Verifique credenciais."
  echo ""
  echo "💡 Para configurar:"
  echo "   nano $0"
  echo ""
  exit 1
fi

echo ""
echo "🎭 Criando sessão com FINGERPRINT + PROXY..."
echo ""

# Criar sessão
response=$(curl -s -X POST "http://localhost:3030/api/sessions/create" \
  -H "Content-Type: application/json" \
  -d "{
    \"alias\": \"test-proxy-samsung\",
    \"tenant_id\": \"tenant-prod-001\",
    \"chip_id\": \"chip-prod-001\",
    \"proxy_url\": \"${PROXY_URL}\",
    \"preferred_manufacturer\": \"Samsung\"
  }")

echo "$response" | jq '.' 2>/dev/null || echo "$response"

SESSION_ID=$(echo "$response" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$SESSION_ID" ]; then
  echo ""
  echo "❌ Erro ao criar sessão"
  exit 1
fi

echo ""
echo "✅ Session ID: $SESSION_ID"
echo ""
echo "⏳ Aguardando 15 segundos para conexão..."
sleep 15

echo ""
echo "📋 LOGS DA SESSÃO:"
echo "=================="
docker logs whago-baileys 2>&1 | grep -E "$SESSION_ID" | tail -15

echo ""
echo "🔍 VERIFICANDO QR CODE..."
echo "========================="

for i in {1..10}; do
  qr_response=$(curl -s "http://localhost:3030/api/sessions/${SESSION_ID}/qr")
  qr_code=$(echo "$qr_response" | grep -o '"qr_code":"[^"]*"' | cut -d'"' -f4)
  status=$(echo "$qr_response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
  
  echo "Tentativa $i/10 - Status: $status"
  
  if [ "$qr_code" != "null" ] && [ -n "$qr_code" ] && [ "$qr_code" != "" ]; then
    echo ""
    echo "🎉🎉🎉 SUCESSO! QR CODE GERADO! 🎉🎉🎉"
    echo ""
    echo "✅ Session ID: $SESSION_ID"
    echo "✅ Device: Samsung (fingerprint)"
    echo "✅ Proxy: $PROXY_HOST"
    echo "✅ IP: $IP"
    echo ""
    echo "📱 Acesse para ver QR:"
    echo "   http://localhost:3030/api/sessions/${SESSION_ID}/qr"
    echo ""
    exit 0
  fi
  
  if [ "$i" -lt 10 ]; then
    sleep 3
  fi
done

echo ""
echo "⚠️ QR code não gerado ainda."
echo ""
echo "📋 Ver logs completos:"
echo "   docker logs whago-baileys -f"
echo ""






