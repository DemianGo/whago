#!/bin/bash

set -e

echo "🧪 TESTE: Validação de Chip Único por Campanha"
echo "=============================================="
echo ""

BASE_URL="http://localhost:8000"

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "1️⃣  Obtendo usuário de teste..."
# Buscar primeiro usuário de teste do banco
USER_EMAIL=$(docker-compose exec -T backend python3 -c "
import asyncio
from sqlalchemy import select
from app.database import get_db
from app.models.user import User

async def get_user():
    async for db in get_db():
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if user:
            print(user.email)
        break

asyncio.run(get_user())
" 2>/dev/null | tail -1)

echo "Usuário: $USER_EMAIL"

echo "2️⃣  Fazendo login..."
# Tentar logar - senha padrão dos testes
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$USER_EMAIL\",
    \"password\": \"Test123!\"
  }")

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Falha no login! Tentando senha alternativa...${NC}"
    
    # Tentar senha alternativa
    LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
      -H "Content-Type: application/json" \
      -d "{
        \"email\": \"$USER_EMAIL\",
        \"password\": \"testpass123\"
      }")
    
    TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
    
    if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
        echo -e "${RED}❌ Falha no login!${NC}"
        echo "Response: $LOGIN_RESPONSE"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Login OK${NC}"
echo ""

echo "2️⃣  Buscando chips do usuário..."
CHIPS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/chips/" \
  -H "Authorization: Bearer $TOKEN")

CHIP_ID=$(echo $CHIPS_RESPONSE | jq -r '.items[0].id')
CHIP_ALIAS=$(echo $CHIPS_RESPONSE | jq -r '.items[0].alias')

if [ "$CHIP_ID" == "null" ] || [ -z "$CHIP_ID" ]; then
    echo -e "${RED}❌ Nenhum chip encontrado!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Chip encontrado: $CHIP_ALIAS ($CHIP_ID)${NC}"
echo ""

echo "3️⃣  Criando primeira campanha (Teste Validação A)..."
# Criar campanha básica
CREATE1_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/campaigns/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Teste Validação A",
    "description": "Primeira campanha de teste",
    "message_template": "Olá teste A"
  }')

CAMPAIGN1_ID=$(echo $CREATE1_RESPONSE | jq -r '.id')

if [ "$CAMPAIGN1_ID" == "null" ] || [ -z "$CAMPAIGN1_ID" ]; then
    echo -e "${RED}❌ Falha ao criar campanha 1!${NC}"
    echo "Response: $CREATE1_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Campanha 1 criada: $CAMPAIGN1_ID${NC}"

# Atualizar com chip
echo "   Adicionando chip à campanha 1..."
UPDATE1_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X PUT "$BASE_URL/api/v1/campaigns/$CAMPAIGN1_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"settings\": {
      \"chip_ids\": [\"$CHIP_ID\"]
    }
  }")

HTTP_STATUS1=$(echo "$UPDATE1_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
BODY1=$(echo "$UPDATE1_RESPONSE" | sed '$d')

if [ "$HTTP_STATUS1" != "200" ]; then
    echo -e "${RED}❌ Falha ao atualizar campanha 1!${NC}"
    echo "Status: $HTTP_STATUS1"
    echo "Body: $BODY1"
    exit 1
fi

echo -e "${GREEN}✅ Chip adicionado à campanha 1${NC}"
echo ""

echo "4️⃣  Tentando criar segunda campanha com MESMO chip (deve FALHAR)..."
# Criar segunda campanha básica
CREATE2_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/campaigns/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Teste Validação B",
    "description": "Segunda campanha de teste",
    "message_template": "Olá teste B"
  }')

CAMPAIGN2_ID=$(echo $CREATE2_RESPONSE | jq -r '.id')

if [ "$CAMPAIGN2_ID" == "null" ] || [ -z "$CAMPAIGN2_ID" ]; then
    echo -e "${RED}❌ Falha ao criar campanha 2!${NC}"
    echo "Response: $CREATE2_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Campanha 2 criada: $CAMPAIGN2_ID${NC}"

# Tentar atualizar com MESMO chip - DEVE FALHAR
echo "   Tentando adicionar MESMO chip à campanha 2..."
UPDATE2_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X PUT "$BASE_URL/api/v1/campaigns/$CAMPAIGN2_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"settings\": {
      \"chip_ids\": [\"$CHIP_ID\"]
    }
  }")

HTTP_STATUS2=$(echo "$UPDATE2_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
BODY2=$(echo "$UPDATE2_RESPONSE" | sed '$d')

echo ""
echo "=============================================="
echo "📊 RESULTADO DO TESTE"
echo "=============================================="
echo ""

if [ "$HTTP_STATUS2" == "400" ]; then
    ERROR_DETAIL=$(echo "$BODY2" | jq -r '.detail')
    echo -e "${GREEN}✅ TESTE PASSOU!${NC}"
    echo ""
    echo "   Status HTTP: $HTTP_STATUS2 (esperado: 400)"
    echo "   Erro: $ERROR_DETAIL"
    echo ""
    echo -e "${GREEN}🎯 A validação está funcionando corretamente!${NC}"
    echo -e "${GREEN}   O sistema bloqueou o uso do mesmo chip em duas campanhas.${NC}"
    
    # Limpar campanhas de teste
    echo ""
    echo "🧹 Limpando campanhas de teste..."
    curl -s -X DELETE "$BASE_URL/api/v1/campaigns/$CAMPAIGN1_ID" \
      -H "Authorization: Bearer $TOKEN" > /dev/null
    curl -s -X DELETE "$BASE_URL/api/v1/campaigns/$CAMPAIGN2_ID" \
      -H "Authorization: Bearer $TOKEN" > /dev/null
    echo -e "${GREEN}✅ Campanhas de teste removidas${NC}"
    
    exit 0
else
    echo -e "${RED}❌ TESTE FALHOU!${NC}"
    echo ""
    echo "   Status HTTP: $HTTP_STATUS2 (esperado: 400)"
    echo "   Body: $BODY2"
    echo ""
    echo -e "${RED}⚠️  A validação NÃO está funcionando!${NC}"
    echo -e "${RED}   O sistema permitiu usar o mesmo chip em duas campanhas.${NC}"
    
    # Mostrar logs
    echo ""
    echo "📋 Logs da validação (últimas 20 linhas):"
    docker-compose logs backend --tail=20 | grep -E "(campaign_validation|Comparando)" || echo "Nenhum log encontrado"
    
    # Limpar campanhas de teste
    echo ""
    echo "🧹 Limpando campanhas de teste..."
    curl -s -X DELETE "$BASE_URL/api/v1/campaigns/$CAMPAIGN1_ID" \
      -H "Authorization: Bearer $TOKEN" > /dev/null
    curl -s -X DELETE "$BASE_URL/api/v1/campaigns/$CAMPAIGN2_ID" \
      -H "Authorization: Bearer $TOKEN" > /dev/null
    echo -e "${GREEN}✅ Campanhas de teste removidas${NC}"
    
    exit 1
fi

