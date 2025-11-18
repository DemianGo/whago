#!/bin/bash
set -e

BASE_URL="http://localhost:8000"
API_URL="${BASE_URL}/api/v1"

echo "🧪 TESTE RÁPIDO: Edição de Campanha no Backend"
echo "=============================================="
echo ""

# 1. Registrar
RANDOM_EMAIL="test-edit-$(date +%s)@example.com"
echo "1️⃣ Registrando..."
TOKEN=$(curl -s -X POST "${API_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Test\",
    \"email\": \"$RANDOM_EMAIL\",
    \"phone\": \"+5511999999999\",
    \"password\": \"Test@123\"
  }" | jq -r '.tokens.access_token // .access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "❌ Erro ao registrar"
  exit 1
fi

echo "✅ Registrado!"
echo ""

# 2. Criar campanha
echo "2️⃣ Criando campanha..."
CAMPAIGN_ID=$(curl -s -X POST "${API_URL}/campaigns/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Teste Original",
    "description": "Desc",
    "message_template": "Msg original",
    "settings": {
      "chip_ids": [],
      "interval_seconds": 10,
      "randomize_interval": false
    }
  }' | jq -r '.id')

echo "✅ Campanha criada: $CAMPAIGN_ID"
echo ""

# 3. Editar campanha DRAFT
echo "3️⃣ Editando campanha (DRAFT)..."
EDIT_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${API_URL}/campaigns/${CAMPAIGN_ID}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Teste EDITADO",
    "description": "Desc editada",
    "message_template": "Msg editada",
    "settings": {
      "chip_ids": [],
      "interval_seconds": 20,
      "randomize_interval": true
    }
  }')

HTTP_CODE=$(echo "$EDIT_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$EDIT_RESPONSE" | head -n -1)

if [ "$HTTP_CODE" != "200" ]; then
  echo "❌ Erro ao editar (HTTP $HTTP_CODE)"
  echo "$RESPONSE_BODY" | jq '.'
  exit 1
fi

EDITED_NAME=$(echo "$RESPONSE_BODY" | jq -r '.name')

if [ "$EDITED_NAME" != "Teste EDITADO" ]; then
  echo "❌ Nome não foi atualizado"
  exit 1
fi

echo "✅ Campanha editada com sucesso!"
echo "   Nome: $EDITED_NAME"
echo ""

# 4. Limpar
echo "4️⃣ Limpando..."
curl -s -X DELETE "${API_URL}/campaigns/${CAMPAIGN_ID}" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

echo "✅ Limpeza concluída!"
echo ""

echo "=============================================="
echo "✅ TESTE PASSOU! Backend permite editar DRAFT"
echo "=============================================="
echo ""
echo "🎯 AGORA TESTE NO NAVEGADOR:"
echo "   1. Acesse: http://localhost:8000/campaigns"
echo "   2. Clique em '✏️ Editar' em qualquer campanha"
echo "   3. Modifique algo"
echo "   4. Clique em 'Continuar'"
echo "   5. ✅ Deve ir para o passo 2 (sem erro 400)"

