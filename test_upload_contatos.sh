#!/bin/bash
set -e

BASE_URL="http://localhost:8000"
API_URL="${BASE_URL}/api/v1"

echo "🧪 TESTE: Upload de Contatos em Campanhas"
echo "=========================================="
echo ""

# Registrar usuário
RANDOM_EMAIL="test-upload-$(date +%s)@example.com"
echo "1️⃣ Registrando usuário..."
TOKEN=$(curl -s -X POST "${API_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Test\",
    \"email\": \"$RANDOM_EMAIL\",
    \"phone\": \"+5511999999999\",
    \"password\": \"Test@123\"
  }" | jq -r '.tokens.access_token // .access_token')

echo "✅ Registrado!"
echo ""

# Criar campanha DRAFT
echo "2️⃣ Criando campanha DRAFT..."
CAMPAIGN_ID=$(curl -s -X POST "${API_URL}/campaigns/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Teste Upload",
    "description": "Teste",
    "message_template": "Mensagem teste",
    "settings": {
      "chip_ids": [],
      "interval_seconds": 10,
      "randomize_interval": false
    }
  }' | jq -r '.id')

echo "✅ Campanha criada: $CAMPAIGN_ID"
echo ""

# Criar CSV temporário
CSV_FILE="/tmp/test_contacts_${RANDOM_EMAIL}.csv"
echo "+5511964416417,+5511963076830" > "$CSV_FILE"

# Upload de contatos
echo "3️⃣ Fazendo upload de contatos..."
UPLOAD_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  "${API_URL}/campaigns/${CAMPAIGN_ID}/contacts/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@${CSV_FILE}")

HTTP_CODE=$(echo "$UPLOAD_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$UPLOAD_RESPONSE" | head -n -1)

if [ "$HTTP_CODE" != "200" ]; then
  echo "❌ Erro no upload (HTTP $HTTP_CODE)"
  echo "$RESPONSE_BODY" | jq '.' || echo "$RESPONSE_BODY"
  rm -f "$CSV_FILE"
  exit 1
fi

VALID_CONTACTS=$(echo "$RESPONSE_BODY" | jq -r '.valid_contacts')

if [ "$VALID_CONTACTS" != "2" ]; then
  echo "❌ Esperado 2 contatos, recebido: $VALID_CONTACTS"
  rm -f "$CSV_FILE"
  exit 1
fi

echo "✅ Upload realizado: $VALID_CONTACTS contatos válidos"
echo ""

# Criar novo CSV com mais contatos
echo "4️⃣ Criando novo CSV para substituir..."
echo "+5511111111111,+5511222222222,+5511333333333" > "$CSV_FILE"

# Upload novamente (substituir)
echo "5️⃣ Fazendo upload de novos contatos (substituir)..."
UPLOAD2_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  "${API_URL}/campaigns/${CAMPAIGN_ID}/contacts/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@${CSV_FILE}")

HTTP_CODE2=$(echo "$UPLOAD2_RESPONSE" | tail -n1)
RESPONSE_BODY2=$(echo "$UPLOAD2_RESPONSE" | head -n -1)

if [ "$HTTP_CODE2" != "200" ]; then
  echo "❌ Erro ao substituir contatos (HTTP $HTTP_CODE2)"
  echo "$RESPONSE_BODY2" | jq '.' || echo "$RESPONSE_BODY2"
  rm -f "$CSV_FILE"
  exit 1
fi

VALID_CONTACTS2=$(echo "$RESPONSE_BODY2" | jq -r '.valid_contacts')

if [ "$VALID_CONTACTS2" != "3" ]; then
  echo "❌ Esperado 3 contatos, recebido: $VALID_CONTACTS2"
  rm -f "$CSV_FILE"
  exit 1
fi

echo "✅ Contatos substituídos: $VALID_CONTACTS2 contatos válidos"
echo ""

# Limpar
echo "6️⃣ Limpando..."
curl -s -X DELETE "${API_URL}/campaigns/${CAMPAIGN_ID}" \
  -H "Authorization: Bearer $TOKEN" > /dev/null
rm -f "$CSV_FILE"

echo "✅ Limpeza concluída!"
echo ""

echo "=========================================="
echo "✅ TODOS OS TESTES PASSARAM!"
echo "=========================================="
echo ""
echo "📋 Resumo:"
echo "  ✅ Criar campanha DRAFT"
echo "  ✅ Upload inicial de contatos (2)"
echo "  ✅ Upload novamente (substituir por 3)"
echo "  ✅ Backend permite upload em edição"
echo ""
echo "🎯 TESTE NO NAVEGADOR:"
echo "   1. Edite uma campanha com contatos"
echo "   2. No Passo 3, selecione um novo CSV"
echo "   3. Clique 'Continuar'"
echo "   4. ✅ Deve fazer upload e ir para Passo 4"

