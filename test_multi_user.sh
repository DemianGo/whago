#!/bin/bash

BASE_URL="http://localhost:8000/api/v1"

echo "🧪 TESTE MULTI-USUÁRIO: 2 USUÁRIOS SIMULTÂNEOS"
echo "=============================================="
echo ""

# ========== USUÁRIO 1 ==========
echo "👤 USUÁRIO 1: Criando conta..."

USER1_EMAIL="user1_$(date +%s)@whago.com"
USER1_PASSWORD="Test@123456"

REGISTER1=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$USER1_EMAIL\",
    \"password\": \"$USER1_PASSWORD\",
    \"name\": \"Usuario 1 Teste\",
    \"phone\": \"+5511999990001\",
    \"plan_slug\": \"free\"
  }")

TOKEN1=$(echo "$REGISTER1" | jq -r '.tokens.access_token')
USER1_ID=$(echo "$REGISTER1" | jq -r '.user.id')

if [ "$TOKEN1" == "null" ] || [ -z "$TOKEN1" ]; then
  echo "❌ Erro ao criar usuário 1"
  echo "$REGISTER1"
  exit 1
fi

echo "✅ Usuário 1 criado: $USER1_EMAIL"
echo "   ID: $USER1_ID"
echo ""

# ========== USUÁRIO 2 ==========
echo "👤 USUÁRIO 2: Criando conta..."

USER2_EMAIL="user2_$(date +%s)@whago.com"
USER2_PASSWORD="Test@123456"

REGISTER2=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$USER2_EMAIL\",
    \"password\": \"$USER2_PASSWORD\",
    \"name\": \"Usuario 2 Teste\",
    \"phone\": \"+5511999990002\",
    \"plan_slug\": \"free\"
  }")

TOKEN2=$(echo "$REGISTER2" | jq -r '.tokens.access_token')
USER2_ID=$(echo "$REGISTER2" | jq -r '.user.id')

if [ "$TOKEN2" == "null" ] || [ -z "$TOKEN2" ]; then
  echo "❌ Erro ao criar usuário 2"
  echo "$REGISTER2"
  exit 1
fi

echo "✅ Usuário 2 criado: $USER2_EMAIL"
echo "   ID: $USER2_ID"
echo ""

# ========== CRIAR CHIPS (2 PARA CADA USUÁRIO) ==========
echo "📱 Criando chips para ambos os usuários..."
echo ""

# User 1 - Chip 1
echo "📱 User 1 - Chip 1..."
CHIP1_U1=$(curl -s -X POST "$BASE_URL/chips" \
  -H "Authorization: Bearer $TOKEN1" \
  -H "Content-Type: application/json" \
  -d '{"alias": "user1_chip1"}')

CHIP1_U1_ID=$(echo "$CHIP1_U1" | jq -r '.id')
echo "✅ User 1 - Chip 1 criado: $CHIP1_U1_ID"

# User 1 - Chip 2
echo "📱 User 1 - Chip 2..."
CHIP2_U1=$(curl -s -X POST "$BASE_URL/chips" \
  -H "Authorization: Bearer $TOKEN1" \
  -H "Content-Type: application/json" \
  -d '{"alias": "user1_chip2"}')

CHIP2_U1_ID=$(echo "$CHIP2_U1" | jq -r '.id')
echo "✅ User 1 - Chip 2 criado: $CHIP2_U1_ID"

# User 2 - Chip 1
echo "📱 User 2 - Chip 1..."
CHIP1_U2=$(curl -s -X POST "$BASE_URL/chips" \
  -H "Authorization: Bearer $TOKEN2" \
  -H "Content-Type: application/json" \
  -d '{"alias": "user2_chip1"}')

CHIP1_U2_ID=$(echo "$CHIP1_U2" | jq -r '.id')
echo "✅ User 2 - Chip 1 criado: $CHIP1_U2_ID"

# User 2 - Chip 2
echo "📱 User 2 - Chip 2..."
CHIP2_U2=$(curl -s -X POST "$BASE_URL/chips" \
  -H "Authorization: Bearer $TOKEN2" \
  -H "Content-Type: application/json" \
  -d '{"alias": "user2_chip2"}')

CHIP2_U2_ID=$(echo "$CHIP2_U2" | jq -r '.id')
echo "✅ User 2 - Chip 2 criado: $CHIP2_U2_ID"

echo ""
echo "⏳ Aguardando inicialização dos containers (15 segundos)..."
sleep 15

echo ""
echo "🐳 VERIFICANDO CONTAINERS WAHA PLUS..."
echo "========================================"
docker ps | grep waha_plus | awk '{print $NF, $7}'

echo ""
echo "📊 Detalhes dos containers:"
echo "User 1: waha_plus_user_$USER1_ID"
docker ps | grep "waha_plus_user_$USER1_ID" && echo "  ✅ Container User 1 rodando" || echo "  ❌ Container User 1 NÃO encontrado"

echo ""
echo "User 2: waha_plus_user_$USER2_ID"
docker ps | grep "waha_plus_user_$USER2_ID" && echo "  ✅ Container User 2 rodando" || echo "  ❌ Container User 2 NÃO encontrado"

echo ""
echo "📸 OBTENDO QR CODES..."
echo "======================"

echo ""
echo "User 1 - Chip 1:"
QR1_U1=$(curl -s -X GET "$BASE_URL/chips/$CHIP1_U1_ID/qr" -H "Authorization: Bearer $TOKEN1")
echo "$QR1_U1" | jq -r 'if .qr != null then "✅ QR Code gerado" else "❌ QR Code não disponível: " + (.message // "sem mensagem") end'

echo ""
echo "User 1 - Chip 2:"
QR2_U1=$(curl -s -X GET "$BASE_URL/chips/$CHIP2_U1_ID/qr" -H "Authorization: Bearer $TOKEN1")
echo "$QR2_U1" | jq -r 'if .qr != null then "✅ QR Code gerado" else "❌ QR Code não disponível: " + (.message // "sem mensagem") end'

echo ""
echo "User 2 - Chip 1:"
QR1_U2=$(curl -s -X GET "$BASE_URL/chips/$CHIP1_U2_ID/qr" -H "Authorization: Bearer $TOKEN2")
echo "$QR1_U2" | jq -r 'if .qr != null then "✅ QR Code gerado" else "❌ QR Code não disponível: " + (.message // "sem mensagem") end'

echo ""
echo "User 2 - Chip 2:"
QR2_U2=$(curl -s -X GET "$BASE_URL/chips/$CHIP2_U2_ID/qr" -H "Authorization: Bearer $TOKEN2")
echo "$QR2_U2" | jq -r 'if .qr != null then "✅ QR Code gerado" else "❌ QR Code não disponível: " + (.message // "sem mensagem") end'

echo ""
echo "🔍 VERIFICANDO PROXY ALLOCATION..."
echo "===================================="

docker exec -i whago-postgres psql -U whago -d whago -c "
SELECT 
  c.id,
  c.alias,
  u.email,
  c.extra_data->>'waha_plus_container' as container,
  c.extra_data->>'waha_session' as session,
  c.extra_data->>'proxy_enabled' as proxy_enabled,
  c.status
FROM chips c
JOIN users u ON c.user_id = u.id
WHERE u.email IN ('$USER1_EMAIL', '$USER2_EMAIL')
ORDER BY u.email, c.created_at;
"

echo ""
echo "🔍 VERIFICANDO PROXY ASSIGNMENTS..."
echo "===================================="

docker exec -i whago-postgres psql -U whago -d whago -c "
SELECT 
  cpa.chip_id,
  c.alias,
  u.email,
  p.proxy_url,
  cpa.session_identifier,
  cpa.created_at
FROM chip_proxy_assignments cpa
JOIN chips c ON cpa.chip_id = c.id
JOIN users u ON c.user_id = u.id
JOIN proxies p ON cpa.proxy_id = p.id
WHERE u.email IN ('$USER1_EMAIL', '$USER2_EMAIL')
ORDER BY u.email, cpa.created_at;
"

echo ""
echo "📝 RESUMO FINAL"
echo "==============="
echo "User 1: $USER1_EMAIL"
echo "  - ID: $USER1_ID"
echo "  - Chips criados: 2"
echo ""
echo "User 2: $USER2_EMAIL"
echo "  - ID: $USER2_ID"
echo "  - Chips criados: 2"
echo ""
echo "Total de chips criados: 4"
echo ""
echo "✅ Teste multi-usuário concluído!"
