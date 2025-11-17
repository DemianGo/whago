#!/bin/bash
# Script para criar instância e monitorar QR Code

set -e

API_URL="http://localhost:8080"
API_KEY="evolution-test-key-2025"
INSTANCE_NAME="whatsapp_test_$(date +%s)"

echo "🚀 Criando instância: $INSTANCE_NAME"
echo ""

# Criar instância com proxy
RESPONSE=$(curl -s -X POST "$API_URL/instance/create" \
  -H "apikey: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"instanceName\": \"$INSTANCE_NAME\",
    \"token\": \"test-token-$(date +%s)\",
    \"qrcode\": true,
    \"integration\": \"WHATSAPP-BAILEYS\",
    \"reject_call\": false,
    \"msg_call\": \"\",
    \"groups_ignore\": true,
    \"always_online\": false,
    \"read_messages\": false,
    \"read_status\": false,
    \"sync_full_history\": false,
    \"proxy\": {
      \"enabled\": true,
      \"host\": \"gw.dataimpulse.com\",
      \"port\": \"824\",
      \"protocol\": \"socks5\",
      \"username\": \"b0d7c401317486d2c3e8__cr.br\",
      \"password\": \"f60a2f1e36dcd0b4\"
    }
  }")

echo "📦 Resposta da criação:"
echo "$RESPONSE" | jq .
echo ""

# Extrair hash da instância
INSTANCE_HASH=$(echo "$RESPONSE" | jq -r '.instance.instanceId // .hash.instanceId // empty')

if [ -z "$INSTANCE_HASH" ]; then
  echo "❌ Falha ao criar instância!"
  echo "$RESPONSE"
  exit 1
fi

echo "✅ Instância criada: $INSTANCE_HASH"
echo ""

# Aguardar e buscar QR Code (tentar por 60 segundos)
echo "🔍 Buscando QR Code..."
for i in {1..20}; do
  echo "Tentativa $i/20..."
  
  QR_RESPONSE=$(curl -s "$API_URL/instance/connect/$INSTANCE_NAME" \
    -H "apikey: $API_KEY")
  
  echo "Resposta: $(echo "$QR_RESPONSE" | jq -c .)"
  
  # Verificar se tem QR code
  QR_CODE=$(echo "$QR_RESPONSE" | jq -r '.qrcode.code // .code // .base64 // empty')
  
  if [ ! -z "$QR_CODE" ] && [ "$QR_CODE" != "null" ]; then
    echo ""
    echo "🎉 QR CODE OBTIDO!"
    echo ""
    echo "$QR_CODE"
    echo ""
    echo "✅ SUCESSO!"
    exit 0
  fi
  
  sleep 3
done

echo ""
echo "⚠️ QR Code não gerado após 60 segundos"
echo ""

# Buscar status da instância
echo "📊 Status da instância:"
curl -s "$API_URL/instance/fetchInstances?instanceName=$INSTANCE_NAME" \
  -H "apikey: $API_KEY" | jq .

echo ""
echo "🧹 Limpando instância..."
curl -s -X DELETE "$API_URL/instance/delete/$INSTANCE_NAME" \
  -H "apikey: $API_KEY" | jq .

exit 1

