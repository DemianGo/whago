#!/bin/bash
set -e

BASE_URL="http://localhost:8000"
API_URL="${BASE_URL}/api/v1"

echo "🧪 TESTE COMPLETO DE EDIÇÃO DE CAMPANHAS"
echo "========================================="
echo ""

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. REGISTRAR USUÁRIO
RANDOM_EMAIL="test-edit-full-$(date +%s)@example.com"
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
  echo "$REGISTER_RESPONSE" | jq '.'
  exit 1
fi

echo -e "${GREEN}✅ Usuário registrado e autenticado!${NC}"
echo ""

# 2. CRIAR CAMPANHA INICIAL
echo "2️⃣ Criando campanha inicial..."
CREATE_RESPONSE=$(curl -s -X POST "${API_URL}/campaigns/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Campanha Original",
    "description": "Descrição original da campanha",
    "message_template": "Olá {{nome}}, mensagem original!",
    "message_template_b": "Mensagem B original",
    "settings": {
      "chip_ids": [],
      "interval_seconds": 10,
      "randomize_interval": false
    }
  }')

CAMPAIGN_ID=$(echo "$CREATE_RESPONSE" | jq -r '.id')

if [ -z "$CAMPAIGN_ID" ] || [ "$CAMPAIGN_ID" = "null" ]; then
  echo -e "${RED}❌ Erro ao criar campanha${NC}"
  echo "$CREATE_RESPONSE" | jq '.'
  exit 1
fi

echo -e "${GREEN}✅ Campanha criada: $CAMPAIGN_ID${NC}"
echo ""

# 3. BUSCAR CAMPANHA (simular GET no frontend ao clicar em Editar)
echo "3️⃣ Simulando clique em 'Editar' (GET /campaigns/${CAMPAIGN_ID})..."
GET_RESPONSE=$(curl -s -X GET "${API_URL}/campaigns/${CAMPAIGN_ID}" \
  -H "Authorization: Bearer $TOKEN")

ORIGINAL_NAME=$(echo "$GET_RESPONSE" | jq -r '.name')
ORIGINAL_DESC=$(echo "$GET_RESPONSE" | jq -r '.description')
ORIGINAL_TEMPLATE=$(echo "$GET_RESPONSE" | jq -r '.message_template')

echo -e "${GREEN}✅ Dados carregados:${NC}"
echo "   Nome: $ORIGINAL_NAME"
echo "   Descrição: $ORIGINAL_DESC"
echo "   Template: $ORIGINAL_TEMPLATE"
echo ""

# 4. EDITAR PASSO 1 (Informações Básicas)
echo "4️⃣ Editando passo 1 (Informações Básicas)..."
EDIT_STEP1_RESPONSE=$(curl -s -X PUT "${API_URL}/campaigns/${CAMPAIGN_ID}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Campanha EDITADA",
    "description": "Descrição EDITADA",
    "message_template": "Olá {{nome}}, mensagem EDITADA!",
    "message_template_b": "Mensagem B EDITADA",
    "settings": {
      "chip_ids": [],
      "interval_seconds": 10,
      "randomize_interval": false
    }
  }')

EDITED_NAME=$(echo "$EDIT_STEP1_RESPONSE" | jq -r '.name')

if [ "$EDITED_NAME" != "Campanha EDITADA" ]; then
  echo -e "${RED}❌ Passo 1 não foi atualizado corretamente!${NC}"
  echo "Esperado: Campanha EDITADA"
  echo "Recebido: $EDITED_NAME"
  exit 1
fi

echo -e "${GREEN}✅ Passo 1 atualizado com sucesso!${NC}"
echo ""

# 5. EDITAR PASSO 2 (Chips e Configurações)
echo "5️⃣ Editando passo 2 (Configurações de Chips)..."
EDIT_STEP2_RESPONSE=$(curl -s -X PUT "${API_URL}/campaigns/${CAMPAIGN_ID}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "settings": {
      "chip_ids": [],
      "interval_seconds": 25,
      "randomize_interval": true
    }
  }')

INTERVAL=$(echo "$EDIT_STEP2_RESPONSE" | jq -r '.settings.interval_seconds')
RANDOMIZE=$(echo "$EDIT_STEP2_RESPONSE" | jq -r '.settings.randomize_interval')

if [ "$INTERVAL" != "25" ] || [ "$RANDOMIZE" != "true" ]; then
  echo -e "${RED}❌ Configurações de chips não foram atualizadas!${NC}"
  echo "Esperado: interval=25, randomize=true"
  echo "Recebido: interval=$INTERVAL, randomize=$RANDOMIZE"
  exit 1
fi

echo -e "${GREEN}✅ Passo 2 atualizado com sucesso!${NC}"
echo ""

# 6. VERIFICAR PERSISTÊNCIA FINAL
echo "6️⃣ Verificando persistência final (GET novamente)..."
FINAL_RESPONSE=$(curl -s -X GET "${API_URL}/campaigns/${CAMPAIGN_ID}" \
  -H "Authorization: Bearer $TOKEN")

FINAL_NAME=$(echo "$FINAL_RESPONSE" | jq -r '.name')
FINAL_DESC=$(echo "$FINAL_RESPONSE" | jq -r '.description')
FINAL_TEMPLATE=$(echo "$FINAL_RESPONSE" | jq -r '.message_template')
FINAL_INTERVAL=$(echo "$FINAL_RESPONSE" | jq -r '.settings.interval_seconds')
FINAL_RANDOMIZE=$(echo "$FINAL_RESPONSE" | jq -r '.settings.randomize_interval')

echo -e "${GREEN}✅ Dados finais persistidos:${NC}"
echo "   Nome: $FINAL_NAME"
echo "   Descrição: $FINAL_DESC"
echo "   Template: $FINAL_TEMPLATE"
echo "   Intervalo: $FINAL_INTERVAL segundos"
echo "   Aleatorizar: $FINAL_RANDOMIZE"
echo ""

# Validações finais
ERRORS=0

if [ "$FINAL_NAME" != "Campanha EDITADA" ]; then
  echo -e "${RED}❌ Nome não persistiu corretamente${NC}"
  ERRORS=$((ERRORS + 1))
fi

if [ "$FINAL_DESC" != "Descrição EDITADA" ]; then
  echo -e "${RED}❌ Descrição não persistiu corretamente${NC}"
  ERRORS=$((ERRORS + 1))
fi

if [ "$FINAL_INTERVAL" != "25" ]; then
  echo -e "${RED}❌ Intervalo não persistiu corretamente${NC}"
  ERRORS=$((ERRORS + 1))
fi

if [ "$FINAL_RANDOMIZE" != "true" ]; then
  echo -e "${RED}❌ Randomização não persistiu corretamente${NC}"
  ERRORS=$((ERRORS + 1))
fi

if [ $ERRORS -gt 0 ]; then
  echo ""
  echo -e "${RED}❌ $ERRORS ERRO(S) ENCONTRADO(S)!${NC}"
  exit 1
fi

# 7. LIMPAR
echo "7️⃣ Limpando campanha de teste..."
curl -s -X DELETE "${API_URL}/campaigns/${CAMPAIGN_ID}" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

echo -e "${GREEN}✅ Campanha deletada${NC}"
echo ""

echo "========================================"
echo -e "${GREEN}✅ TODOS OS TESTES PASSARAM!${NC}"
echo "========================================"
echo ""
echo "📋 Resumo dos testes:"
echo "  ✅ Registro de usuário"
echo "  ✅ Criação de campanha"
echo "  ✅ Busca de campanha (GET)"
echo "  ✅ Edição do passo 1 (informações básicas)"
echo "  ✅ Edição do passo 2 (configurações de chips)"
echo "  ✅ Persistência de dados"
echo "  ✅ Cleanup"
echo ""
echo "🎯 TESTE NO NAVEGADOR:"
echo "   1. Acesse: http://localhost:8000/campaigns"
echo "   2. Clique em '✏️ Editar' em uma campanha DRAFT"
echo "   3. Verifique que os campos estão preenchidos"
echo "   4. Clique em 'Continuar' (deve ir para o passo 2)"
echo "   5. Verifique que os chips selecionados estão marcados"
echo "   6. Continue navegando pelos passos"
echo "   7. O wizard NÃO deve fechar até clicar em 'X' ou finalizar"

