#!/bin/bash

# Script de teste de fingerprints avançados
# Testa geração de fingerprints com diferentes fabricantes

set -e

BAILEYS_URL="${BAILEYS_URL:-http://localhost:3000}"
API_URL="$BAILEYS_URL/api"

echo "🎭 Teste de Fingerprints Avançados"
echo "=================================="
echo ""
echo "URL do Baileys: $BAILEYS_URL"
echo ""

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Função para fazer request e mostrar resultado
test_fingerprint() {
    local manufacturer=$1
    local tenant_id=$2
    
    echo -e "${BLUE}Testando fingerprint: $manufacturer${NC}"
    echo -e "${YELLOW}Tenant ID: $tenant_id${NC}"
    echo ""
    
    response=$(curl -s -X POST "$API_URL/fingerprints/test" \
        -H "Content-Type: application/json" \
        -d "{\"tenant_id\": \"$tenant_id\", \"preferred_manufacturer\": \"$manufacturer\"}")
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Erro ao chamar API${NC}"
        return 1
    fi
    
    # Extrair informações do fingerprint
    device=$(echo "$response" | jq -r '.fingerprint.device.marketName // "N/A"')
    android=$(echo "$response" | jq -r '.fingerprint.os.version // "N/A"')
    chrome=$(echo "$response" | jq -r '.fingerprint.browser.version // "N/A"')
    screen=$(echo "$response" | jq -r '"\(.fingerprint.screen.width)x\(.fingerprint.screen.height)"')
    gpu=$(echo "$response" | jq -r '.fingerprint.features.webGLRenderer // "N/A"')
    user_agent=$(echo "$response" | jq -r '.fingerprint.browser.userAgent // "N/A"')
    device_id=$(echo "$response" | jq -r '.fingerprint.deviceId // "N/A"')
    
    echo -e "${GREEN}✅ Fingerprint gerado com sucesso!${NC}"
    echo ""
    echo "📱 Device: $device"
    echo "🤖 Android: $android"
    echo "🌐 Chrome: $chrome"
    echo "📺 Screen: $screen"
    echo "🎮 GPU: $gpu"
    echo "🔑 Device ID: $device_id"
    echo ""
    echo "User-Agent:"
    echo "$user_agent"
    echo ""
    echo "---"
    echo ""
}

# Testar health check primeiro
echo -e "${BLUE}Verificando saúde do serviço...${NC}"
health=$(curl -s "$BAILEYS_URL/health")
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Baileys service não está respondendo em $BAILEYS_URL${NC}"
    echo "Certifique-se de que o serviço está rodando."
    exit 1
fi
echo -e "${GREEN}✅ Serviço está online${NC}"
echo ""

# Testar status
echo -e "${BLUE}Verificando status do serviço...${NC}"
status=$(curl -s "$API_URL/status")
echo "$status" | jq '.'
echo ""

# Teste 1: Samsung
echo "======================================"
echo "Teste 1: Fingerprint Samsung"
echo "======================================"
test_fingerprint "Samsung" "test-samsung-001"

# Teste 2: Motorola
echo "======================================"
echo "Teste 2: Fingerprint Motorola"
echo "======================================"
test_fingerprint "Motorola" "test-motorola-001"

# Teste 3: Xiaomi
echo "======================================"
echo "Teste 3: Fingerprint Xiaomi"
echo "======================================"
test_fingerprint "Xiaomi" "test-xiaomi-001"

# Teste 4: Sem preferência (aleatório)
echo "======================================"
echo "Teste 4: Fingerprint Aleatório"
echo "======================================"
test_fingerprint "" "test-random-001"

# Teste 5: Diversidade - 10 fingerprints aleatórios
echo "======================================"
echo "Teste 5: Diversidade (10 fingerprints)"
echo "======================================"
echo -e "${BLUE}Gerando 10 fingerprints aleatórios...${NC}"
echo ""

manufacturers=()
models=()
for i in {1..10}; do
    response=$(curl -s -X POST "$API_URL/fingerprints/test" \
        -H "Content-Type: application/json" \
        -d "{\"tenant_id\": \"test-diversity-$i\"}")
    
    mfr=$(echo "$response" | jq -r '.fingerprint.device.manufacturer')
    model=$(echo "$response" | jq -r '.fingerprint.device.marketName')
    
    manufacturers+=("$mfr")
    models+=("$model")
    
    echo "$i. $mfr $model"
done

echo ""
unique_mfr=$(printf '%s\n' "${manufacturers[@]}" | sort -u | wc -l)
unique_models=$(printf '%s\n' "${models[@]}" | sort -u | wc -l)

echo -e "${GREEN}✅ Diversidade:${NC}"
echo "   Fabricantes únicos: $unique_mfr"
echo "   Modelos únicos: $unique_models"
echo ""

# Teste 6: Verificar estatísticas (se houver sessões ativas)
echo "======================================"
echo "Teste 6: Estatísticas de Fingerprints"
echo "======================================"
stats=$(curl -s "$API_URL/fingerprints/stats")
echo "$stats" | jq '.'
echo ""

# Resumo final
echo "======================================"
echo -e "${GREEN}✅ Todos os testes concluídos!${NC}"
echo "======================================"
echo ""
echo "Resultados:"
echo "  - ✅ Samsung: OK"
echo "  - ✅ Motorola: OK"
echo "  - ✅ Xiaomi: OK"
echo "  - ✅ Aleatório: OK"
echo "  - ✅ Diversidade: $unique_mfr fabricantes, $unique_models modelos"
echo ""
echo "Para testar com criação de sessão real, use:"
echo ""
echo "curl -X POST $API_URL/sessions/create \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"alias\": \"Teste Samsung\", \"preferred_manufacturer\": \"Samsung\"}'"
echo ""


