#!/bin/bash

# Script de teste completo do envio de campanhas
set -e

echo "🧪 TESTE COMPLETO DE ENVIO DE CAMPANHAS"
echo "========================================"
echo ""

BASE_URL="http://localhost:8000"
USER_EMAIL="teste@teste.com"
USER_PASSWORD="teste123"

# Login
echo "1. Fazendo login..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$USER_EMAIL\",\"password\":\"$USER_PASSWORD\"}")

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.tokens.access_token // .access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Erro ao fazer login"
    echo "$LOGIN_RESPONSE" | jq
    exit 1
fi

echo "✅ Login realizado com sucesso"
echo ""

# Verificar chip conectado
echo "2. Verificando chip conectado..."

# Usar chip conhecido do banco
CHIP_ID="ff20f892-c630-46fb-84a6-16c2e742e59e"
CHIP_STATUS=$(docker exec whago-postgres psql -U whago -d whago -t -c "SELECT status FROM chips WHERE id = '$CHIP_ID';")
CHIP_STATUS=$(echo "$CHIP_STATUS" | tr -d ' \n')

if [ -z "$CHIP_ID" ] || [ -z "$CHIP_STATUS" ]; then
    echo "❌ Nenhum chip encontrado"
    exit 1
fi

echo "✅ Chip encontrado: $CHIP_ID"
echo "   Status: $CHIP_STATUS"

if [ "$CHIP_STATUS" != "connected" ]; then
    echo "⚠️  AVISO: Chip não está conectado!"
    echo "   Mensagens não serão enviadas, mas a campanha será criada"
fi
echo ""

# Criar campanha
echo "3. Criando campanha de teste..."
CAMPAIGN_NAME="Teste_$(date +%s)"

CAMPAIGN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/campaigns/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$CAMPAIGN_NAME\",
    \"description\": \"Teste automático de envio\",
    \"type\": \"simple\",
    \"message_template\": \"Olá! Esta é uma mensagem de teste via WAHA Plus. Timestamp: $(date +%H:%M:%S)\",
    \"settings\": {
      \"chip_ids\": [\"$CHIP_ID\"],
      \"interval_seconds\": 5,
      \"randomize_interval\": false
    }
  }")

CAMPAIGN_ID=$(echo $CAMPAIGN_RESPONSE | jq -r '.id // empty')

if [ -z "$CAMPAIGN_ID" ]; then
    echo "❌ Erro ao criar campanha"
    echo "$CAMPAIGN_RESPONSE" | jq
    exit 1
fi

echo "✅ Campanha criada: $CAMPAIGN_ID"
echo "   Nome: $CAMPAIGN_NAME"
echo ""

# Upload de contatos
echo "4. Fazendo upload de contatos..."
cat > /tmp/test_contacts.csv << EOF
+5511999999999
+5511988888888
EOF

UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/campaigns/$CAMPAIGN_ID/contacts/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test_contacts.csv")

VALID_CONTACTS=$(echo $UPLOAD_RESPONSE | jq -r '.valid_contacts // 0')

if [ "$VALID_CONTACTS" -eq 0 ]; then
    echo "❌ Erro ao fazer upload de contatos"
    echo "$UPLOAD_RESPONSE" | jq
    exit 1
fi

echo "✅ Upload realizado: $VALID_CONTACTS contatos válidos"
echo ""

# Iniciar campanha
echo "5. Iniciando campanha..."
START_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/campaigns/$CAMPAIGN_ID/start" \
  -H "Authorization: Bearer $TOKEN")

START_STATUS=$(echo $START_RESPONSE | jq -r '.status // empty')

if [ "$START_STATUS" != "running" ]; then
    echo "❌ Erro ao iniciar campanha"
    echo "$START_RESPONSE" | jq
    exit 1
fi

echo "✅ Campanha iniciada com sucesso!"
echo "   Status: $START_STATUS"
echo ""

# Monitorar progresso
echo "6. Monitorando envio (30 segundos)..."
echo ""

for i in {1..6}; do
    sleep 5
    
    CAMPAIGN_STATUS=$(curl -s -X GET "$BASE_URL/api/v1/campaigns/$CAMPAIGN_ID" \
      -H "Authorization: Bearer $TOKEN")
    
    STATUS=$(echo $CAMPAIGN_STATUS | jq -r '.status')
    SENT=$(echo $CAMPAIGN_STATUS | jq -r '.sent_count')
    FAILED=$(echo $CAMPAIGN_STATUS | jq -r '.failed_count')
    TOTAL=$(echo $CAMPAIGN_STATUS | jq -r '.total_contacts')
    
    echo "[$(date +%H:%M:%S)] Status: $STATUS | Enviadas: $SENT/$TOTAL | Falhas: $FAILED"
    
    if [ "$STATUS" == "completed" ]; then
        echo ""
        echo "✅ Campanha concluída!"
        break
    fi
done

echo ""
echo "========================================"
echo "📊 RESULTADO FINAL"
echo "========================================"

# Resultado final
FINAL_STATUS=$(curl -s -X GET "$BASE_URL/api/v1/campaigns/$CAMPAIGN_ID" \
  -H "Authorization: Bearer $TOKEN")

echo "Campanha: $CAMPAIGN_NAME"
echo "ID: $CAMPAIGN_ID"
echo "Status: $(echo $FINAL_STATUS | jq -r '.status')"
echo "Enviadas: $(echo $FINAL_STATUS | jq -r '.sent_count')/$(echo $FINAL_STATUS | jq -r '.total_contacts')"
echo "Falhas: $(echo $FINAL_STATUS | jq -r '.failed_count')"
echo ""

# Verificar mensagens
echo "📨 Detalhes das mensagens:"
docker exec whago-postgres psql -U whago -d whago -c "
SELECT 
  cm.status,
  LEFT(cm.failure_reason, 50) as erro,
  cm.sent_at
FROM campaign_messages cm
WHERE cm.campaign_id = '$CAMPAIGN_ID'
ORDER BY cm.created_at;
" 2>/dev/null || echo "Erro ao consultar mensagens"

echo ""
echo "🎉 Teste concluído!"

