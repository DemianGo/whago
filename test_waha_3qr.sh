#!/bin/bash
# Script para testar geração de 3 QR Codes com WAHA + Proxy DataImpulse

API_KEY="0c5bd2c0cf1b46548db200a2735679e2"
WAHA_URL="http://localhost:3000"
SESSION="default"

# Proxy DataImpulse
PROXY_SERVER="socks5://gw.dataimpulse.com:824"
PROXY_USER="b0d7c401317486d2c3e8__cr.br"
PROXY_PASS="f60a2f1e36dcd0b4"

echo "================================================================================"
echo "🧪 TESTE: Geração de 3 QR Codes com WAHA + Proxy Mobile DataImpulse"
echo "================================================================================"
echo ""

# Função para configurar e iniciar sessão
start_session() {
    local test_num=$1
    
    echo "--------------------------------------------------------------------------------"
    echo "🔵 TESTE $test_num: Gerando QR Code #$test_num"
    echo "--------------------------------------------------------------------------------"
    
    # Parar sessão anterior se existir
    echo "⏸️  Parando sessão anterior..."
    curl -s -X POST "$WAHA_URL/api/sessions/$SESSION/stop" -H "X-Api-Key: $API_KEY" > /dev/null 2>&1
    sleep 3
    
    # Configurar proxy
    echo "🔧 Configurando proxy DataImpulse..."
    curl -s -X PUT "$WAHA_URL/api/sessions/$SESSION" \
      -H "X-Api-Key: $API_KEY" \
      -H "Content-Type: application/json" \
      -d "{
        \"name\": \"$SESSION\",
        \"config\": {
          \"proxy\": {
            \"server\": \"$PROXY_SERVER\",
            \"username\": \"$PROXY_USER\",
            \"password\": \"$PROXY_PASS\"
          }
        }
      }" | jq -r '.status // "Configurado"'
    
    # Iniciar sessão
    echo "▶️  Iniciando sessão..."
    curl -s -X POST "$WAHA_URL/api/sessions/$SESSION/start" \
      -H "X-Api-Key: $API_KEY" \
      -H "Content-Type: application/json" | jq -r '.status'
    
    # Aguardar inicialização
    echo "⏳ Aguardando inicialização (15 segundos)..."
    sleep 15
    
    # Verificar status
    STATUS=$(curl -s "$WAHA_URL/api/sessions/$SESSION" -H "X-Api-Key: $API_KEY" | jq -r '.status')
    
    echo "📊 Status da sessão: $STATUS"
    
    if [ "$STATUS" == "SCAN_QR_CODE" ]; then
        echo "✅ QR Code #$test_num GERADO COM SUCESSO!"
        return 0
    else
        echo "⚠️  Status inesperado: $STATUS"
        return 1
    fi
}

# Contador de sucessos
SUCCESS=0

# =================================================================
# TESTE 1
# =================================================================
if start_session 1; then
    SUCCESS=$((SUCCESS + 1))
fi
echo ""
sleep 2

# =================================================================
# TESTE 2
# =================================================================
if start_session 2; then
    SUCCESS=$((SUCCESS + 1))
fi
echo ""
sleep 2

# =================================================================
# TESTE 3
# =================================================================
if start_session 3; then
    SUCCESS=$((SUCCESS + 1))
fi
echo ""

# =================================================================
# RESUMO
# =================================================================
echo "================================================================================"
echo "📊 RESUMO DOS TESTES"
echo "================================================================================"
echo ""
echo "✅ QR Codes gerados com sucesso: $SUCCESS/3"
echo ""

if [ $SUCCESS -gt 0 ]; then
    echo "🔍 Para visualizar os QR Codes ASCII nos logs do Docker:"
    echo ""
    echo "   docker logs waha 2>&1 | grep -A 35 '▄▄▄▄▄'"
    echo ""
    echo "Ou para ver apenas os últimos:"
    echo ""
    echo "   docker logs waha 2>&1 | grep -A 35 '▄▄▄▄▄' | tail -40"
fi

echo ""
echo "================================================================================"

if [ $SUCCESS -eq 3 ]; then
    echo "🎉 TODOS OS TESTES PASSARAM!"
    exit 0
else
    echo "⚠️  Alguns testes falharam ($SUCCESS/3)"
    exit 1
fi

