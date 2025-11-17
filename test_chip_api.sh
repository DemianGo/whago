#!/bin/bash
# Script para testar API de chips com WAHA integrado

API_URL="http://localhost:8000"
TOKEN=""

echo "================================================================================"
echo "🧪 TESTE: API de Chips com WAHA Integrado"
echo "================================================================================"
echo ""

# 1. Login para obter token
echo "1️⃣ Fazendo login..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@whago.com",
    "password": "Admin@123"
  }')

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // empty')

if [ -z "$TOKEN" ]; then
    echo "❌ Erro ao fazer login. Tentando criar admin..."
    # Tentar criar admin se não existir
    curl -s -X POST "$API_URL/api/v1/auth/register" \
      -H "Content-Type: application/json" \
      -d '{
        "email": "admin@whago.com",
        "password": "Admin@123",
        "full_name": "Admin WHAGO"
      }' > /dev/null
    
    # Tentar login novamente
    LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
      -H "Content-Type: application/json" \
      -d '{
        "email": "admin@whago.com",
        "password": "Admin@123"
      }')
    
    TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // empty')
fi

if [ -z "$TOKEN" ]; then
    echo "❌ Falha ao obter token de acesso"
    exit 1
fi

echo "✅ Login realizado com sucesso"
echo ""

# 2. Listar chips existentes
echo "2️⃣ Listando chips existentes..."
CHIPS=$(curl -s "$API_URL/api/v1/chips" \
  -H "Authorization: Bearer $TOKEN")

CHIP_COUNT=$(echo "$CHIPS" | jq '. | length')
echo "📊 Chips encontrados: $CHIP_COUNT"
echo ""

# 3. Criar novo chip
echo "3️⃣ Criando novo chip com WAHA..."
TIMESTAMP=$(date +%s)
CHIP_ALIAS="chip_test_$TIMESTAMP"

CREATE_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/chips" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"alias\": \"$CHIP_ALIAS\"
  }")

CHIP_ID=$(echo "$CREATE_RESPONSE" | jq -r '.id // empty')

if [ -z "$CHIP_ID" ]; then
    echo "❌ Erro ao criar chip:"
    echo "$CREATE_RESPONSE" | jq .
    exit 1
fi

echo "✅ Chip criado com sucesso!"
echo "   ID: $CHIP_ID"
echo "   Alias: $CHIP_ALIAS"
echo "   Status: $(echo "$CREATE_RESPONSE" | jq -r '.status')"
echo ""

# 4. Aguardar sessão WAHA inicializar
echo "4️⃣ Aguardando sessão WAHA inicializar (15 segundos)..."
sleep 15
echo ""

# 5. Obter QR Code
echo "5️⃣ Obtendo QR Code..."
QR_RESPONSE=$(curl -s "$API_URL/api/v1/chips/$CHIP_ID/qr" \
  -H "Authorization: Bearer $TOKEN")

QR_CODE=$(echo "$QR_RESPONSE" | jq -r '.qr // empty')

if [ -z "$QR_CODE" ] || [ "$QR_CODE" == "null" ]; then
    echo "⚠️  QR Code não retornado pela API (pode estar nos logs do WAHA)"
    echo ""
    echo "🔍 Verificando logs do WAHA..."
    docker logs waha 2>&1 | grep -A 35 '▄▄▄▄▄' | tail -40
else
    echo "✅ QR Code obtido com sucesso!"
    echo "   Primeiros 100 caracteres: ${QR_CODE:0:100}..."
fi

echo ""

# 6. Verificar detalhes do chip
echo "6️⃣ Verificando detalhes do chip..."
CHIP_DETAILS=$(curl -s "$API_URL/api/v1/chips/$CHIP_ID" \
  -H "Authorization: Bearer $TOKEN")

echo "📱 Detalhes do chip:"
echo "$CHIP_DETAILS" | jq '{id, alias, status, session_id, extra_data}'
echo ""

# 7. Resumo
echo "================================================================================"
echo "📊 RESUMO DO TESTE"
echo "================================================================================"
echo ""
echo "✅ Login realizado"
echo "✅ Chip criado: $CHIP_ALIAS"
echo "✅ ID: $CHIP_ID"

if [ -n "$QR_CODE" ] && [ "$QR_CODE" != "null" ]; then
    echo "✅ QR Code obtido via API"
else
    echo "⚠️  QR Code disponível nos logs do Docker (WAHA)"
fi

echo ""
echo "🔍 Para ver o QR Code completo:"
echo "   docker logs waha 2>&1 | grep -A 35 '▄▄▄▄▄' | tail -40"
echo ""
echo "🗑️  Para deletar o chip de teste:"
echo "   curl -X DELETE \"$API_URL/api/v1/chips/$CHIP_ID\" -H \"Authorization: Bearer $TOKEN\""
echo ""
echo "================================================================================"

