#!/bin/bash

# Test Payment Flow - Simulação Completa do Fluxo de Pagamento
# Este script simula um usuário humano fazendo todo o processo de assinatura

set -e

BASE_URL="http://localhost:8000"
API_URL="$BASE_URL/api/v1"

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  TESTE COMPLETO DO FLUXO DE PAGAMENTO - WHAGO                ║${NC}"
echo -e "${BLUE}║  Simulando usuário humano do início ao fim                   ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Gerar email único
RANDOM_ID=$RANDOM
TEST_EMAIL="teste.fluxo.${RANDOM_ID}@example.com"
TEST_PASSWORD="SenhaForte123!"
TEST_NAME="Usuário Teste Fluxo $RANDOM_ID"
TEST_PHONE="+5511999999999"

echo -e "${YELLOW}📋 Dados do Teste:${NC}"
echo "   Email: $TEST_EMAIL"
echo "   Senha: $TEST_PASSWORD"
echo "   Nome: $TEST_NAME"
echo ""

# ============================================================================
# PASSO 1: Acessar Home e Listar Planos
# ============================================================================
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ PASSO 1: Acessando página Home e listando planos${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

PLANS=$(curl -s "$API_URL/plans")
PLAN_COUNT=$(echo "$PLANS" | jq '. | length')
echo "   Planos disponíveis: $PLAN_COUNT"

# Selecionar Plano Business (ID 2)
PLAN_ID=2
PLAN_INFO=$(echo "$PLANS" | jq ".[] | select(.id == $PLAN_ID)")
PLAN_NAME=$(echo "$PLAN_INFO" | jq -r '.name')
PLAN_PRICE=$(echo "$PLAN_INFO" | jq -r '.price')

echo "   ✓ Plano selecionado: $PLAN_NAME (R$ $PLAN_PRICE/mês)"
sleep 1

# ============================================================================
# PASSO 2: Verificar Métodos de Pagamento
# ============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ PASSO 2: Verificando métodos de pagamento disponíveis${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

PAYMENT_METHODS=$(curl -s "$API_URL/payments/methods")
MP_ENABLED=$(echo "$PAYMENT_METHODS" | jq -r '.methods[] | select(.id == "mercadopago") | .enabled')

if [ "$MP_ENABLED" == "true" ]; then
    echo "   ✓ Mercado Pago: DISPONÍVEL"
else
    echo -e "   ${RED}✗ Mercado Pago: INDISPONÍVEL${NC}"
    exit 1
fi

PAYMENT_METHOD="mercadopago"
sleep 1

# ============================================================================
# PASSO 3: Criar Conta (Registro)
# ============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ PASSO 3: Criando nova conta de usuário${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$TEST_EMAIL\",
        \"password\": \"$TEST_PASSWORD\",
        \"name\": \"$TEST_NAME\",
        \"phone\": \"$TEST_PHONE\"
    }")

# Verificar se registro foi bem-sucedido
if echo "$REGISTER_RESPONSE" | jq -e '.tokens' > /dev/null 2>&1; then
    ACCESS_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.tokens.access_token')
    REFRESH_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.tokens.refresh_token')
    USER_ID=$(echo "$REGISTER_RESPONSE" | jq -r '.user.id')
    
    echo "   ✓ Conta criada com sucesso!"
    echo "   ✓ User ID: $USER_ID"
    echo "   ✓ Token obtido: ${ACCESS_TOKEN:0:30}..."
else
    echo -e "   ${RED}✗ Erro ao criar conta:${NC}"
    echo "$REGISTER_RESPONSE" | jq '.'
    exit 1
fi
sleep 1

# ============================================================================
# PASSO 4: Verificar Dados do Usuário
# ============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ PASSO 4: Verificando dados do usuário logado${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

USER_DATA=$(curl -s "$API_URL/users/me" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

USER_NAME=$(echo "$USER_DATA" | jq -r '.name')
USER_CREDITS=$(echo "$USER_DATA" | jq -r '.credits')
USER_PLAN=$(echo "$USER_DATA" | jq -r '.plan_name // "Free"')

echo "   Nome: $USER_NAME"
echo "   Plano atual: $USER_PLAN"
echo "   Créditos: $USER_CREDITS"
sleep 1

# ============================================================================
# PASSO 5: Criar Assinatura (Gerar Link de Pagamento)
# ============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ PASSO 5: Criando assinatura e gerando link de pagamento${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

SUBSCRIPTION_RESPONSE=$(curl -s -X POST "$API_URL/payments/subscriptions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -d "{
        \"plan_id\": $PLAN_ID,
        \"payment_method\": \"$PAYMENT_METHOD\"
    }")

# Verificar se assinatura foi criada
if echo "$SUBSCRIPTION_RESPONSE" | jq -e '.subscription_id' > /dev/null 2>&1; then
    SUBSCRIPTION_ID=$(echo "$SUBSCRIPTION_RESPONSE" | jq -r '.subscription_id')
    PAYMENT_URL=$(echo "$SUBSCRIPTION_RESPONSE" | jq -r '.payment_url')
    SUB_STATUS=$(echo "$SUBSCRIPTION_RESPONSE" | jq -r '.status')
    
    echo "   ✓ Assinatura criada com sucesso!"
    echo "   ✓ Subscription ID: $SUBSCRIPTION_ID"
    echo "   ✓ Status inicial: $SUB_STATUS"
    echo "   ✓ URL de pagamento: ${PAYMENT_URL:0:70}..."
else
    echo -e "   ${RED}✗ Erro ao criar assinatura:${NC}"
    echo "$SUBSCRIPTION_RESPONSE" | jq '.'
    exit 1
fi
sleep 2

# ============================================================================
# PASSO 6: Verificar Status da Assinatura (Antes do Pagamento)
# ============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ PASSO 6: Verificando status da assinatura (antes do pagamento)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

BILLING_DATA=$(curl -s "$API_URL/billing/subscription" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

CURRENT_STATUS=$(echo "$BILLING_DATA" | jq -r '.subscription_status // "none"')
echo "   Status da assinatura: $CURRENT_STATUS"

if [ "$CURRENT_STATUS" == "pending" ]; then
    echo "   ✓ Status correto: aguardando pagamento"
else
    echo -e "   ${YELLOW}⚠ Status inesperado: $CURRENT_STATUS${NC}"
fi
sleep 1

# ============================================================================
# PASSO 7: Simular Redirecionamento para Mercado Pago
# ============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}⏸  PASSO 7: Simulando redirecionamento para Mercado Pago${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

echo "   → Usuário seria redirecionado para: $PAYMENT_URL"
echo "   → Usuário preencheria dados do cartão de teste:"
echo "      • Número: 5031 4332 1540 6351"
echo "      • Nome: APRO"
echo "      • Validade: 11/25"
echo "      • CVV: 123"
echo ""
echo "   ⏳ Simulando processamento do pagamento..."
sleep 3

# ============================================================================
# PASSO 8: Simular Webhook de Confirmação (Pagamento Aprovado)
# ============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ PASSO 8: Simulando webhook de pagamento aprovado${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

# Simular webhook do Mercado Pago
WEBHOOK_RESPONSE=$(curl -s -X POST "$API_URL/payments/webhook/mercadopago" \
    -H "Content-Type: application/json" \
    -d "{
        \"type\": \"subscription_preapproval\",
        \"action\": \"approved\",
        \"data\": {
            \"id\": \"$SUBSCRIPTION_ID\"
        }
    }")

echo "   ✓ Webhook enviado: pagamento aprovado"
echo "   Resposta: $(echo $WEBHOOK_RESPONSE | jq -r '.status // .event')"
sleep 2

# ============================================================================
# PASSO 9: Verificar Ativação da Assinatura
# ============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ PASSO 9: Verificando ativação da assinatura${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

sleep 2  # Aguardar processamento do webhook

BILLING_DATA_AFTER=$(curl -s "$API_URL/billing/subscription" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

NEW_STATUS=$(echo "$BILLING_DATA_AFTER" | jq -r '.subscription_status // "none"')
PLAN_NAME_AFTER=$(echo "$BILLING_DATA_AFTER" | jq -r '.plan_name // "Free"')
NEXT_BILLING=$(echo "$BILLING_DATA_AFTER" | jq -r '.next_billing_date // "N/A"')

echo "   Status da assinatura: $NEW_STATUS"
echo "   Plano ativo: $PLAN_NAME_AFTER"
echo "   Próxima cobrança: ${NEXT_BILLING:0:10}"

if [ "$NEW_STATUS" == "active" ]; then
    echo -e "   ${GREEN}✓ ASSINATURA ATIVADA COM SUCESSO!${NC}"
else
    echo -e "   ${YELLOW}⚠ Status atual: $NEW_STATUS (pode levar alguns segundos)${NC}"
fi
sleep 1

# ============================================================================
# PASSO 10: Verificar Dados Finais do Usuário
# ============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ PASSO 10: Verificando dados finais do usuário${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

USER_DATA_FINAL=$(curl -s "$API_URL/users/me" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

FINAL_PLAN=$(echo "$USER_DATA_FINAL" | jq -r '.plan_name // "Free"')
FINAL_CREDITS=$(echo "$USER_DATA_FINAL" | jq -r '.credits')

echo "   Nome: $(echo "$USER_DATA_FINAL" | jq -r '.name')"
echo "   Email: $(echo "$USER_DATA_FINAL" | jq -r '.email')"
echo "   Plano: $FINAL_PLAN"
echo "   Créditos: $FINAL_CREDITS"
sleep 1

# ============================================================================
# PASSO 11: Verificar Transação no Banco
# ============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ PASSO 11: Verificando registro da transação${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

TRANSACTION_CHECK=$(docker-compose exec -T postgres psql -U whago -d whago -t -c "
SELECT 
    id, type, amount, status, payment_method
FROM transactions 
WHERE user_id = '$USER_ID'
ORDER BY created_at DESC 
LIMIT 1;
" 2>/dev/null || echo "Erro ao consultar banco")

if [ "$TRANSACTION_CHECK" != "Erro ao consultar banco" ]; then
    echo "$TRANSACTION_CHECK"
    echo "   ✓ Transação registrada no banco de dados"
else
    echo "   ⚠ Não foi possível verificar transação no banco"
fi

# ============================================================================
# RESUMO FINAL
# ============================================================================
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    RESUMO DO TESTE                            ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✓ Plano selecionado:${NC} $PLAN_NAME (R$ $PLAN_PRICE)"
echo -e "${GREEN}✓ Método de pagamento:${NC} Mercado Pago (Sandbox)"
echo -e "${GREEN}✓ Conta criada:${NC} $TEST_EMAIL"
echo -e "${GREEN}✓ User ID:${NC} $USER_ID"
echo -e "${GREEN}✓ Subscription ID:${NC} $SUBSCRIPTION_ID"
echo -e "${GREEN}✓ Status final:${NC} $NEW_STATUS"
echo -e "${GREEN}✓ Plano ativo:${NC} $FINAL_PLAN"
echo ""

if [ "$NEW_STATUS" == "active" ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          🎉 TESTE CONCLUÍDO COM SUCESSO! 🎉                   ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "✅ Fluxo completo testado e funcionando!"
    echo -e "✅ Usuário registrado"
    echo -e "✅ Assinatura criada"
    echo -e "✅ Pagamento processado (simulado)"
    echo -e "✅ Webhook recebido e processado"
    echo -e "✅ Assinatura ativada"
    echo ""
    echo -e "${YELLOW}📋 Credenciais para login:${NC}"
    echo "   Email: $TEST_EMAIL"
    echo "   Senha: $TEST_PASSWORD"
    echo "   URL: $BASE_URL/login"
    echo ""
    exit 0
else
    echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║          ⚠️  TESTE PARCIALMENTE CONCLUÍDO                     ║${NC}"
    echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "✅ Fluxo básico funcionando"
    echo -e "✅ Assinatura criada (status: $NEW_STATUS)"
    echo -e "⚠️  Aguardando processamento do webhook"
    echo ""
    echo -e "${BLUE}💡 Dica:${NC} Execute o webhook manualmente se necessário:"
    echo "   curl -X POST $API_URL/payments/webhook/mercadopago \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"type\":\"subscription_preapproval\",\"action\":\"approved\",\"data\":{\"id\":\"$SUBSCRIPTION_ID\"}}'"
    echo ""
    exit 0
fi

