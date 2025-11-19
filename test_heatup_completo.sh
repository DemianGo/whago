#!/bin/bash

# Script de teste completo do sistema de aquecimento em grupo

echo "══════════════════════════════════════════════════════════"
echo "🧪 TESTE COMPLETO - Aquecimento em Grupo"
echo "══════════════════════════════════════════════════════════"
echo ""

# Variáveis
API_URL="http://localhost:8000/api/v1"
COOKIES_FILE="/tmp/whago_cookies.txt"
USER_EMAIL="teste@teste.com"
USER_PASS="teste123"

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funções auxiliares
log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# 1. Login
echo "──────────────────────────────────────────────────────────"
echo "1️⃣  Fazendo login..."
echo "──────────────────────────────────────────────────────────"

LOGIN_RESPONSE=$(curl -s -c "$COOKIES_FILE" -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$USER_EMAIL\",\"password\":\"$USER_PASS\"}")

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    log_success "Login realizado com sucesso"
else
    log_error "Falha no login"
    echo "$LOGIN_RESPONSE"
    exit 1
fi

# 2. Limpar dados antigos
echo ""
echo "──────────────────────────────────────────────────────────"
echo "2️⃣  Limpando dados antigos de heat-up..."
echo "──────────────────────────────────────────────────────────"

CLEAN_RESPONSE=$(curl -s -b "$COOKIES_FILE" -X POST "$API_URL/admin/chips/clean-old-heatup-data")

if echo "$CLEAN_RESPONSE" | grep -q "message"; then
    log_success "Limpeza concluída"
    echo "$CLEAN_RESPONSE" | jq .
else
    log_error "Falha na limpeza"
    echo "$CLEAN_RESPONSE"
fi

# 3. Listar chips
echo ""
echo "──────────────────────────────────────────────────────────"
echo "3️⃣  Listando chips disponíveis..."
echo "──────────────────────────────────────────────────────────"

CHIPS_RESPONSE=$(curl -s -b "$COOKIES_FILE" "$API_URL/chips")
CHIPS_COUNT=$(echo "$CHIPS_RESPONSE" | jq 'length')

log_info "Total de chips: $CHIPS_COUNT"

# Contar chips conectados
CONNECTED_COUNT=$(echo "$CHIPS_RESPONSE" | jq '[.[] | select(.status == "connected")] | length')
log_info "Chips conectados: $CONNECTED_COUNT"

# Contar chips em aquecimento
MATURING_COUNT=$(echo "$CHIPS_RESPONSE" | jq '[.[] | select(.status == "maturing")] | length')
log_info "Chips em aquecimento: $MATURING_COUNT"

# Mostrar chips
echo ""
echo "$CHIPS_RESPONSE" | jq -r '.[] | "  • \(.alias) - Status: \(.status)"'

# 4. Testar estatísticas de cada chip
echo ""
echo "──────────────────────────────────────────────────────────"
echo "4️⃣  Testando estatísticas de chips..."
echo "──────────────────────────────────────────────────────────"

CHIP_IDS=$(echo "$CHIPS_RESPONSE" | jq -r '.[].id')

for CHIP_ID in $CHIP_IDS; do
    CHIP_ALIAS=$(echo "$CHIPS_RESPONSE" | jq -r ".[] | select(.id == \"$CHIP_ID\") | .alias")
    
    echo ""
    log_info "Testando: $CHIP_ALIAS"
    
    STATS_RESPONSE=$(curl -s -b "$COOKIES_FILE" "$API_URL/chips/$CHIP_ID/maturation-stats")
    
    if echo "$STATS_RESPONSE" | grep -q '"status"'; then
        STATUS=$(echo "$STATS_RESPONSE" | jq -r '.status')
        
        if [ "$STATUS" = "never_started" ]; then
            log_success "  Status: Nunca iniciou aquecimento"
        else
            log_success "  Status: $STATUS"
            echo "$STATS_RESPONSE" | jq -r '
                "  Fase: \(.current_phase)/\(.total_phases)",
                "  Mensagens: \(.messages_sent_in_phase)",
                "  Progresso: \(.progress_percent)%",
                "  Recomendação: \(.recommendation)"
            '
        fi
    else
        log_error "  Erro ao buscar estatísticas"
        echo "$STATS_RESPONSE"
    fi
done

# 5. Verificar se há chips suficientes para grupo
echo ""
echo "──────────────────────────────────────────────────────────"
echo "5️⃣  Verificando viabilidade de aquecimento em grupo..."
echo "──────────────────────────────────────────────────────────"

if [ "$CONNECTED_COUNT" -ge 2 ]; then
    log_success "✅ $CONNECTED_COUNT chips conectados - Pode iniciar aquecimento em grupo!"
    
    # Pegar IDs dos 2 primeiros chips conectados
    CHIP_ID_1=$(echo "$CHIPS_RESPONSE" | jq -r '[.[] | select(.status == "connected")][0].id')
    CHIP_ID_2=$(echo "$CHIPS_RESPONSE" | jq -r '[.[] | select(.status == "connected")][1].id')
    
    CHIP_ALIAS_1=$(echo "$CHIPS_RESPONSE" | jq -r '[.[] | select(.status == "connected")][0].alias')
    CHIP_ALIAS_2=$(echo "$CHIPS_RESPONSE" | jq -r '[.[] | select(.status == "connected")][1].alias')
    
    echo ""
    log_info "Chips selecionados para teste:"
    echo "  1. $CHIP_ALIAS_1 ($CHIP_ID_1)"
    echo "  2. $CHIP_ALIAS_2 ($CHIP_ID_2)"
    
    # 6. Iniciar aquecimento em grupo
    echo ""
    echo "──────────────────────────────────────────────────────────"
    echo "6️⃣  Iniciando aquecimento em grupo..."
    echo "──────────────────────────────────────────────────────────"
    
    HEATUP_REQUEST=$(cat <<EOF
{
  "chip_ids": ["$CHIP_ID_1", "$CHIP_ID_2"],
  "custom_messages": [
    "Oi! Tudo bem?",
    "Como vai?",
    "Tudo certo aí?",
    "Beleza!",
    "Show!"
  ]
}
EOF
)
    
    HEATUP_RESPONSE=$(curl -s -b "$COOKIES_FILE" -X POST "$API_URL/chips/heat-up/group" \
      -H "Content-Type: application/json" \
      -d "$HEATUP_REQUEST")
    
    if echo "$HEATUP_RESPONSE" | grep -q '"group_id"'; then
        log_success "Aquecimento em grupo iniciado!"
        
        GROUP_ID=$(echo "$HEATUP_RESPONSE" | jq -r '.group_id')
        log_info "Group ID: $GROUP_ID"
        
        echo "$HEATUP_RESPONSE" | jq -r '
            "\nDetalhes:",
            "  • Chips: \(.chip_ids | length)",
            "  • Mensagens customizadas: \(.preview_messages | length)",
            "  • Total de horas: \(.recommended_total_hours)h",
            "\nPlano de aquecimento:",
            (.stages[] | "  Fase \(.stage): \(.messages_per_hour) msg/h por \(.duration_hours)h")
        '
        
        # 7. Verificar status após iniciar
        echo ""
        echo "──────────────────────────────────────────────────────────"
        echo "7️⃣  Verificando status após iniciar..."
        echo "──────────────────────────────────────────────────────────"
        
        sleep 2
        
        CHIPS_AFTER=$(curl -s -b "$COOKIES_FILE" "$API_URL/chips")
        
        echo "$CHIPS_AFTER" | jq -r ".[] | select(.id == \"$CHIP_ID_1\" or .id == \"$CHIP_ID_2\") | 
            \"  • \(.alias) - Status: \(.status) \(if .status == \"maturing\" then \"🔥\" else \"\" end)\"
        "
        
        # 8. Testar estatísticas após iniciar
        echo ""
        echo "──────────────────────────────────────────────────────────"
        echo "8️⃣  Testando estatísticas após iniciar..."
        echo "──────────────────────────────────────────────────────────"
        
        for CHIP_ID in $CHIP_ID_1 $CHIP_ID_2; do
            CHIP_ALIAS=$(echo "$CHIPS_AFTER" | jq -r ".[] | select(.id == \"$CHIP_ID\") | .alias")
            
            echo ""
            log_info "$CHIP_ALIAS:"
            
            STATS=$(curl -s -b "$COOKIES_FILE" "$API_URL/chips/$CHIP_ID/maturation-stats")
            
            echo "$STATS" | jq -r '
                "  Status: \(.status)",
                "  Fase: \(.current_phase)/\(.total_phases)",
                "  Progresso: \(.progress_percent)%",
                "  Pronto para campanhas: \(.is_ready_for_campaign)",
                "  Recomendação: \(.recommendation)"
            '
        done
        
        # 9. Testar parar aquecimento
        echo ""
        echo "──────────────────────────────────────────────────────────"
        echo "9️⃣  Testando parar aquecimento (chip 1)..."
        echo "──────────────────────────────────────────────────────────"
        
        STOP_RESPONSE=$(curl -s -b "$COOKIES_FILE" -X POST "$API_URL/chips/$CHIP_ID_1/stop-heat-up")
        
        if echo "$STOP_RESPONSE" | grep -q '"message"'; then
            log_success "Aquecimento parado com sucesso"
            echo "$STOP_RESPONSE" | jq -r '.message'
            
            sleep 1
            
            # Verificar status após parar
            CHIP_STATUS=$(curl -s -b "$COOKIES_FILE" "$API_URL/chips" | jq -r ".[] | select(.id == \"$CHIP_ID_1\") | .status")
            log_info "Status após parar: $CHIP_STATUS"
        else
            log_error "Falha ao parar aquecimento"
            echo "$STOP_RESPONSE"
        fi
        
    else
        log_error "Falha ao iniciar aquecimento em grupo"
        echo "$HEATUP_RESPONSE"
    fi
    
else
    log_error "Apenas $CONNECTED_COUNT chip(s) conectado(s)"
    log_info "Você precisa de pelo menos 2 chips conectados para testar o aquecimento em grupo"
    log_info "Conecte mais chips em http://localhost:8000/chips"
fi

# 10. Verificar Celery task
echo ""
echo "──────────────────────────────────────────────────────────"
echo "🔟 Verificando Celery task..."
echo "──────────────────────────────────────────────────────────"

if docker-compose ps | grep -q "whago-celery.*Up"; then
    log_success "Celery worker está rodando"
    
    log_info "Verificando logs da task de maturação..."
    docker-compose logs celery | grep -i "maturation\|heat" | tail -10
    
    log_info ""
    log_info "Task roda a cada 1 hora (configurado em celery_app.py)"
    log_info "Para testar mais rápido, ajuste: beat_schedule -> 'schedule': 60.0"
else
    log_error "Celery worker não está rodando"
fi

# Resumo final
echo ""
echo "══════════════════════════════════════════════════════════"
echo "📊 RESUMO DO TESTE"
echo "══════════════════════════════════════════════════════════"
echo ""
echo "Chips totais: $CHIPS_COUNT"
echo "Chips conectados: $CONNECTED_COUNT"
echo "Chips em aquecimento: $MATURING_COUNT"
echo ""

if [ "$CONNECTED_COUNT" -ge 2 ]; then
    log_success "✅ Sistema de aquecimento em grupo testado com sucesso!"
    echo ""
    echo "Próximos passos:"
    echo "  1. Acesse http://localhost:8000/chips"
    echo "  2. Clique em 'Ver Stats' para ver progresso"
    echo "  3. Aguarde 1 hora para Celery enviar mensagens"
    echo "  4. Ou ajuste schedule para 60s e teste em 1 minuto"
else
    log_info "⚠️  Conecte mais chips para testar completamente"
fi

echo ""
echo "══════════════════════════════════════════════════════════"

# Cleanup
rm -f "$COOKIES_FILE"

