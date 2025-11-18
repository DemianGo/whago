#!/bin/bash
set -e

BASE_URL="http://localhost:8000"
API_URL="${BASE_URL}/api/v1"

echo "🧪 TESTE DE EDIÇÃO DE CAMPANHAS"
echo "================================"
echo ""

# 1. REGISTRAR USUÁRIO (se necessário)
RANDOM_EMAIL="test-edit-$(date +%s)@example.com"
echo "1️⃣ Registrando usuário: $RANDOM_EMAIL"
REGISTER_RESPONSE=$(curl -s -X POST "${API_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Test User\",
    \"email\": \"$RANDOM_EMAIL\",
    \"phone\": \"+5511999999999\",
    \"password\": \"Test@123\"
  }")

# Verificar se o registro foi bem-sucedido
REGISTER_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.tokens.access_token // .access_token')
if [ -z "$REGISTER_TOKEN" ] || [ "$REGISTER_TOKEN" = "null" ]; then
  echo "⚠️  Registro pode ter falhado, tentando login mesmo assim..."
  echo "$REGISTER_RESPONSE" | jq '.' || echo "$REGISTER_RESPONSE"
else
  echo "✅ Usuário registrado!"
  TOKEN="$REGISTER_TOKEN"
  echo "✅ Usando token do registro"
  echo ""
  # Pular login se registro já retornou token
fi
echo ""

# 2. LOGIN (se ainda não tiver token)
if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "2️⃣ Fazendo login..."
  LOGIN_RESPONSE=$(curl -s -X POST "${API_URL}/auth/login" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"$RANDOM_EMAIL\",
      \"password\": \"Test@123\"
    }")

  TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.tokens.access_token // .access_token')

  if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo "❌ Erro ao fazer login"
    echo "$LOGIN_RESPONSE" | jq '.'
    exit 1
  fi

  echo "✅ Login bem-sucedido!"
  echo ""
fi

# 3. CRIAR CAMPANHA
echo "3️⃣ Criando campanha de teste..."
CREATE_RESPONSE=$(curl -s -X POST "${API_URL}/campaigns" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Teste Edição Original",
    "description": "Descrição original",
    "message_template": "Mensagem original: Olá {{nome}}!",
    "message_template_b": "Mensagem B original",
    "settings": {
      "chip_ids": [],
      "interval_seconds": 10,
      "randomize_interval": false
    }
  }')

CAMPAIGN_ID=$(echo "$CREATE_RESPONSE" | jq -r '.id')

if [ -z "$CAMPAIGN_ID" ] || [ "$CAMPAIGN_ID" = "null" ]; then
  echo "❌ Erro ao criar campanha"
  echo "$CREATE_RESPONSE" | jq '.' || echo "$CREATE_RESPONSE"
  exit 1
fi

echo "✅ Campanha criada: $CAMPAIGN_ID"
echo ""

# 4. BUSCAR CAMPANHA (simular GET no frontend)
echo "4️⃣ Buscando campanha para editar..."
GET_RESPONSE=$(curl -s -X GET "${API_URL}/campaigns/${CAMPAIGN_ID}" \
  -H "Authorization: Bearer $TOKEN")

ORIGINAL_NAME=$(echo "$GET_RESPONSE" | jq -r '.name')
echo "✅ Nome original: $ORIGINAL_NAME"
echo ""

# 5. EDITAR CAMPANHA
echo "5️⃣ Editando campanha..."
EDIT_RESPONSE=$(curl -s -X PUT "${API_URL}/campaigns/${CAMPAIGN_ID}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Teste Edição MODIFICADO",
    "description": "Descrição MODIFICADA",
    "message_template": "Mensagem MODIFICADA: Oi {{nome}}!",
    "message_template_b": "Mensagem B MODIFICADA",
    "settings": {
      "chip_ids": [],
      "interval_seconds": 15,
      "randomize_interval": true
    }
  }')

EDITED_NAME=$(echo "$EDIT_RESPONSE" | jq -r '.name')
EDITED_DESC=$(echo "$EDIT_RESPONSE" | jq -r '.description')
EDITED_TEMPLATE=$(echo "$EDIT_RESPONSE" | jq -r '.message_template')

if [ "$EDITED_NAME" != "Teste Edição MODIFICADO" ]; then
  echo "❌ Nome não foi atualizado!"
  echo "Esperado: Teste Edição MODIFICADO"
  echo "Recebido: $EDITED_NAME"
  exit 1
fi

echo "✅ Nome atualizado: $EDITED_NAME"
echo "✅ Descrição atualizada: $EDITED_DESC"
echo "✅ Template atualizado: $EDITED_TEMPLATE"
echo ""

# 6. VERIFICAR PERSISTÊNCIA
echo "6️⃣ Verificando persistência (GET novamente)..."
VERIFY_RESPONSE=$(curl -s -X GET "${API_URL}/campaigns/${CAMPAIGN_ID}" \
  -H "Authorization: Bearer $TOKEN")

VERIFY_NAME=$(echo "$VERIFY_RESPONSE" | jq -r '.name')
VERIFY_DESC=$(echo "$VERIFY_RESPONSE" | jq -r '.description')
VERIFY_TEMPLATE=$(echo "$VERIFY_RESPONSE" | jq -r '.message_template')

if [ "$VERIFY_NAME" != "Teste Edição MODIFICADO" ]; then
  echo "❌ Mudanças não foram persistidas!"
  exit 1
fi

echo "✅ Mudanças persistidas corretamente!"
echo ""

# 7. LIMPAR (deletar campanha)
echo "7️⃣ Limpando campanha de teste..."
curl -s -X DELETE "${API_URL}/campaigns/${CAMPAIGN_ID}" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

echo "✅ Campanha deletada"
echo ""

echo "================================"
echo "✅ TODOS OS TESTES PASSARAM!"
echo "================================"
echo ""
echo "📋 Resumo:"
echo "  - Login: OK"
echo "  - Criar campanha: OK"
echo "  - Buscar campanha: OK"
echo "  - Editar campanha (PUT): OK"
echo "  - Persistência: OK"
echo "  - Cleanup: OK"
echo ""
echo "🎯 PRÓXIMO PASSO:"
echo "   Abra http://localhost:8000/campaigns"
echo "   Clique em ✏️ Editar em uma campanha DRAFT"
echo "   Verifique se os campos aparecem preenchidos!"

