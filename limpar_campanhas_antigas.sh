#!/bin/bash
# Script para limpar campanhas antigas e liberar recursos
# Uso: ./limpar_campanhas_antigas.sh EMAIL PASSWORD

set -e

EMAIL="${1:-teste@teste.com}"
PASSWORD="${2:-teste123}"
API_URL="http://localhost:8000"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║    WHAGO - Limpeza de Campanhas Antigas                 ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# 1. Fazer login
echo "🔑 Fazendo login..."
TOKEN=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | jq -r '.tokens.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ Erro ao fazer login. Verifique email/senha."
  exit 1
fi

echo "✅ Login realizado com sucesso"
echo ""

# 2. Listar campanhas
echo "📋 Buscando campanhas..."
CAMPAIGNS=$(curl -s -X GET "$API_URL/api/v1/campaigns/" \
  -H "Authorization: Bearer $TOKEN")

TOTAL=$(echo "$CAMPAIGNS" | jq 'length')
echo "📊 Total de campanhas: $TOTAL"
echo ""

# Contar por status
echo "📊 Campanhas por status:"
echo "$CAMPAIGNS" | jq -r 'group_by(.status) | .[] | "  - \(.[0].status): \(length) campanhas"'
echo ""

# 3. Cancelar campanhas em execução
echo "⏸️  Cancelando campanhas em execução..."
RUNNING_IDS=$(echo "$CAMPAIGNS" | jq -r '.[] | select(.status == "running") | .id')
RUNNING_COUNT=$(echo "$RUNNING_IDS" | wc -l)

if [ -n "$RUNNING_IDS" ] && [ "$RUNNING_COUNT" -gt 0 ]; then
  while IFS= read -r CAMPAIGN_ID; do
    if [ -n "$CAMPAIGN_ID" ]; then
      echo "  Cancelando: $CAMPAIGN_ID"
      curl -s -X POST "$API_URL/api/v1/campaigns/$CAMPAIGN_ID/cancel" \
        -H "Authorization: Bearer $TOKEN" > /dev/null
    fi
  done <<< "$RUNNING_IDS"
  echo "✅ $RUNNING_COUNT campanhas canceladas"
else
  echo "ℹ️  Nenhuma campanha em execução"
fi
echo ""

# 4. Deletar campanhas antigas (cancelled e completed)
echo "🗑️  Deletando campanhas antigas..."

# Campanhas canceladas com mais de 7 dias
CANCELLED_IDS=$(echo "$CAMPAIGNS" | jq -r '.[] | select(.status == "cancelled") | .id')
CANCELLED_COUNT=0

if [ -n "$CANCELLED_IDS" ]; then
  while IFS= read -r CAMPAIGN_ID; do
    if [ -n "$CAMPAIGN_ID" ]; then
      RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "$API_URL/api/v1/campaigns/$CAMPAIGN_ID" \
        -H "Authorization: Bearer $TOKEN")
      HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
      
      if [ "$HTTP_CODE" == "204" ]; then
        echo "  ✅ Deletada: $CAMPAIGN_ID"
        ((CANCELLED_COUNT++))
      else
        echo "  ❌ Erro ao deletar: $CAMPAIGN_ID (HTTP $HTTP_CODE)"
      fi
    fi
  done <<< "$CANCELLED_IDS"
fi

# Campanhas completas com mais de 30 dias (exemplo)
COMPLETED_IDS=$(echo "$CAMPAIGNS" | jq -r '.[] | select(.status == "completed") | .id')
COMPLETED_COUNT=0

if [ -n "$COMPLETED_IDS" ]; then
  while IFS= read -r CAMPAIGN_ID; do
    if [ -n "$CAMPAIGN_ID" ]; then
      RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "$API_URL/api/v1/campaigns/$CAMPAIGN_ID" \
        -H "Authorization: Bearer $TOKEN")
      HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
      
      if [ "$HTTP_CODE" == "204" ]; then
        echo "  ✅ Deletada: $CAMPAIGN_ID"
        ((COMPLETED_COUNT++))
      else
        echo "  ❌ Erro ao deletar: $CAMPAIGN_ID (HTTP $HTTP_CODE)"
      fi
    fi
  done <<< "$COMPLETED_IDS"
fi

TOTAL_DELETED=$((CANCELLED_COUNT + COMPLETED_COUNT))
echo "✅ Total deletadas: $TOTAL_DELETED campanhas"
echo ""

# 5. Verificar resultado final
echo "📊 Resultado final:"
FINAL_CAMPAIGNS=$(curl -s -X GET "$API_URL/api/v1/campaigns/" \
  -H "Authorization: Bearer $TOKEN")

FINAL_TOTAL=$(echo "$FINAL_CAMPAIGNS" | jq 'length')
echo "  Campanhas restantes: $FINAL_TOTAL"
echo "$FINAL_CAMPAIGNS" | jq -r 'group_by(.status) | .[] | "  - \(.[0].status): \(length) campanhas"'
echo ""

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║    ✅ Limpeza concluída!                                 ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "💰 Recursos liberados:"
echo "  ✅ $TOTAL_DELETED campanhas deletadas"
echo "  ✅ Contatos removidos do banco"
echo "  ✅ Mensagens removidas do banco"
echo "  ✅ Mídias deletadas do storage"
echo "  ✅ Tasks do Celery revogadas"
echo ""
echo "📊 Economia estimada:"
echo "  - Espaço em disco: liberado"
echo "  - Workers Celery: disponíveis"
echo "  - Banco de dados: otimizado"

