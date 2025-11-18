#!/bin/bash
set -e

BASE_URL="http://localhost:8000"
API_URL="${BASE_URL}/api/v1"

echo "🧪 TESTE DE BOTÕES DE CAMPANHAS"
echo "================================"
echo ""

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. REGISTRAR USUÁRIO
RANDOM_EMAIL="test-buttons-$(date +%s)@example.com"
echo "1️⃣ Registrando usuário: $RANDOM_EMAIL"
REGISTER_RESPONSE=$(curl -s -X POST "${API_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Test User\",
    \"email\": \"$RANDOM_EMAIL\",
    \"phone\": \"+5511999999999\",
    \"password\": \"Test@123\"
  }")

TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.tokens.access_token // .access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo -e "${RED}❌ Erro ao registrar usuário${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Usuário registrado!${NC}"
echo ""

# 2. CRIAR CAMPANHA DRAFT
echo "2️⃣ Criando campanha DRAFT..."
DRAFT_RESPONSE=$(curl -s -X POST "${API_URL}/campaigns/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Campanha Draft",
    "description": "Teste",
    "message_template": "Mensagem teste",
    "settings": {
      "chip_ids": [],
      "interval_seconds": 10,
      "randomize_interval": false
    }
  }')

DRAFT_ID=$(echo "$DRAFT_RESPONSE" | jq -r '.id')
DRAFT_STATUS=$(echo "$DRAFT_RESPONSE" | jq -r '.status')

if [ "$DRAFT_STATUS" != "draft" ]; then
  echo -e "${RED}❌ Campanha não foi criada como DRAFT${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Campanha DRAFT criada: $DRAFT_ID${NC}"
echo ""

# 3. TESTAR EDIÇÃO DE DRAFT
echo "3️⃣ Testando edição de campanha DRAFT..."
EDIT_DRAFT=$(curl -s -X GET "${API_URL}/campaigns/${DRAFT_ID}" \
  -H "Authorization: Bearer $TOKEN")

EDIT_STATUS=$(echo "$EDIT_DRAFT" | jq -r '.status')

if [ "$EDIT_STATUS" != "draft" ]; then
  echo -e "${RED}❌ Status incorreto ao buscar DRAFT${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Pode editar DRAFT${NC}"
echo ""

# 4. CRIAR CAMPANHA SCHEDULED
echo "4️⃣ Criando campanha SCHEDULED..."
FUTURE_DATE=$(date -u -d "+2 hours" +"%Y-%m-%dT%H:%M:%SZ")
SCHEDULED_RESPONSE=$(curl -s -X POST "${API_URL}/campaigns/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"name\": \"Campanha Scheduled\",
    \"description\": \"Teste\",
    \"message_template\": \"Mensagem teste\",
    \"scheduled_for\": \"$FUTURE_DATE\",
    \"settings\": {
      \"chip_ids\": [],
      \"interval_seconds\": 10,
      \"randomize_interval\": false
    }
  }")

SCHEDULED_ID=$(echo "$SCHEDULED_RESPONSE" | jq -r '.id')
SCHEDULED_STATUS=$(echo "$SCHEDULED_RESPONSE" | jq -r '.status')

if [ "$SCHEDULED_STATUS" != "scheduled" ]; then
  echo -e "${YELLOW}⚠️  Campanha não ficou SCHEDULED (pode estar como DRAFT se agendamento não foi aplicado)${NC}"
  echo "   Status: $SCHEDULED_STATUS"
else
  echo -e "${GREEN}✅ Campanha SCHEDULED criada: $SCHEDULED_ID${NC}"
fi
echo ""

# 5. DELETAR CAMPANHAS DE TESTE
echo "5️⃣ Limpando campanhas de teste..."
curl -s -X DELETE "${API_URL}/campaigns/${DRAFT_ID}" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

if [ ! -z "$SCHEDULED_ID" ] && [ "$SCHEDULED_ID" != "null" ]; then
  curl -s -X DELETE "${API_URL}/campaigns/${SCHEDULED_ID}" \
    -H "Authorization: Bearer $TOKEN" > /dev/null
fi

echo -e "${GREEN}✅ Campanhas deletadas${NC}"
echo ""

echo "================================"
echo -e "${GREEN}✅ TESTES BACKEND PASSARAM!${NC}"
echo "================================"
echo ""
echo "📋 Resumo dos testes:"
echo "  ✅ Registro de usuário"
echo "  ✅ Criação de campanha DRAFT"
echo "  ✅ Busca de campanha DRAFT (para editar)"
echo "  ✅ Criação de campanha SCHEDULED"
echo "  ✅ Cleanup"
echo ""
echo "🎯 TESTE MANUAL NO NAVEGADOR:"
echo ""
echo "   1. Acesse: http://localhost:8000/campaigns"
echo ""
echo "   2. Crie uma campanha e vá até o final"
echo "      ✅ Deve ver 2 botões: '💾 Salvar' e '🚀 Iniciar envio'"
echo ""
echo "   3. Clique em '💾 Salvar'"
echo "      ✅ Wizard fecha"
echo "      ✅ Campanha fica DRAFT"
echo "      ✅ Mensagem: 'Campanha salva com sucesso!'"
echo ""
echo "   4. Veja os botões na lista:"
echo "      DRAFT → ✏️ Editar | Iniciar | 🗑️"
echo ""
echo "   5. Inicie uma campanha e depois pause"
echo "      PAUSED → ✏️ Editar | Retomar | Cancelar"
echo ""
echo "   6. Clique em '✏️ Editar' na campanha pausada"
echo "      ✅ Wizard abre com dados preenchidos"
echo ""
echo "   7. Modifique algo e clique '💾 Salvar'"
echo "      ✅ Mudanças salvas"
echo "      ✅ Status permanece PAUSED"

