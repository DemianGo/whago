#!/bin/bash

# Script de teste com rotação de proxies mobile
# Testa diferentes IPs até conseguir gerar QR code

set -e

BAILEYS_URL="http://localhost:3030"
API_URL="$BAILEYS_URL/api"

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 TESTE DE PROXIES MOBILE - ROTAÇÃO DE IP${NC}"
echo "=========================================="
echo ""

# Array de proxies mobile (sessões diferentes = IPs diferentes)
# Formato: http://user:pass@proxy-host:port
# Session ID diferente = IP diferente no Smartproxy/Mobile Proxy

declare -a PROXY_SESSIONS=(
  "session_mobile_1"
  "session_mobile_2"
  "session_mobile_3"
  "session_mobile_4"
  "session_mobile_5"
)

# Contador de tentativas
ATTEMPT=0
SUCCESS=false

# Função para gerar proxy URL com session ID
generate_proxy_url() {
  local session_id=$1
  
  # ⚠️ VOCÊ PRECISA CONFIGURAR SUAS CREDENCIAIS AQUI
  # Exemplo Smartproxy Mobile:
  # http://user-{session_id}:password@gate.smartproxy.com:7000
  
  # Exemplo genérico (ajustar para seu provider):
  local PROXY_USER="user-${session_id}"
  local PROXY_PASS="sua_senha_aqui"
  local PROXY_HOST="gate.smartproxy.com"
  local PROXY_PORT="7000"
  
  echo "http://${PROXY_USER}:${PROXY_PASS}@${PROXY_HOST}:${PROXY_PORT}"
}

# Função para criar sessão com proxy específico
create_session_with_proxy() {
  local session_name=$1
  local proxy_url=$2
  local tenant_id=$3
  local chip_id=$4
  
  echo -e "${BLUE}📱 Criando sessão: $session_name${NC}"
  echo -e "${YELLOW}🌐 Proxy: ${proxy_url}${NC}"
  echo ""
  
  # Fazer request
  response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/sessions/create" \
    -H "Content-Type: application/json" \
    -d "{
      \"alias\": \"${session_name}\",
      \"tenant_id\": \"${tenant_id}\",
      \"chip_id\": \"${chip_id}\",
      \"proxy_url\": \"${proxy_url}\",
      \"preferred_manufacturer\": \"Samsung\"
    }")
  
  # Separar body e status code
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')
  
  echo -e "Status HTTP: ${http_code}"
  
  if [ "$http_code" == "201" ] || [ "$http_code" == "200" ]; then
    session_id=$(echo "$body" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)
    echo -e "${GREEN}✅ Sessão criada: $session_id${NC}"
    echo "$session_id"
    return 0
  else
    echo -e "${RED}❌ Erro ao criar sessão${NC}"
    echo "$body"
    return 1
  fi
}

# Função para verificar QR code
check_qr_code() {
  local session_id=$1
  local max_attempts=15
  local attempt=0
  
  echo -e "${BLUE}🔍 Aguardando QR code...${NC}"
  
  while [ $attempt -lt $max_attempts ]; do
    sleep 3
    
    # Verificar QR
    qr_response=$(curl -s "$API_URL/sessions/${session_id}/qr")
    qr_code=$(echo "$qr_response" | grep -o '"qr_code":"[^"]*"' | cut -d'"' -f4)
    status=$(echo "$qr_response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    
    echo -e "  Tentativa $((attempt+1))/$max_attempts - Status: $status"
    
    if [ "$qr_code" != "null" ] && [ -n "$qr_code" ]; then
      echo -e "${GREEN}✅✅✅ QR CODE GERADO COM SUCESSO! ✅✅✅${NC}"
      echo -e "${GREEN}Session ID: $session_id${NC}"
      echo ""
      return 0
    fi
    
    if [ "$status" == "connected" ]; then
      echo -e "${GREEN}✅ Já conectado (sem QR necessário)${NC}"
      return 0
    fi
    
    if [ "$status" == "error" ] || [ "$status" == "failed" ]; then
      echo -e "${RED}❌ Sessão falhou${NC}"
      return 1
    fi
    
    attempt=$((attempt+1))
  done
  
  echo -e "${RED}❌ Timeout aguardando QR code${NC}"
  return 1
}

# Função para verificar logs
check_logs() {
  local session_id=$1
  echo -e "${BLUE}📋 Logs da sessão:${NC}"
  docker logs whago-baileys 2>&1 | grep "$session_id" | tail -20
  echo ""
}

# ========== LOOP DE TESTES ==========

echo -e "${YELLOW}🔄 Iniciando testes com rotação de IP...${NC}"
echo ""

for session_id in "${PROXY_SESSIONS[@]}"; do
  ATTEMPT=$((ATTEMPT+1))
  
  echo ""
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BLUE}   TENTATIVA #${ATTEMPT} - IP: ${session_id}${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  
  # Gerar proxy URL
  proxy_url=$(generate_proxy_url "$session_id")
  
  # Criar sessão
  created_session=$(create_session_with_proxy \
    "test_proxy_${ATTEMPT}" \
    "$proxy_url" \
    "tenant_test_001" \
    "chip_test_${ATTEMPT}")
  
  if [ $? -eq 0 ]; then
    echo ""
    echo -e "${YELLOW}⏳ Aguardando 8 segundos para estabilizar...${NC}"
    sleep 8
    
    # Verificar logs
    check_logs "$created_session"
    
    # Verificar QR code
    if check_qr_code "$created_session"; then
      echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
      echo -e "${GREEN}   🎉 SUCESSO! QR CODE GERADO! 🎉${NC}"
      echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
      echo ""
      echo -e "${GREEN}✅ Proxy funcionando: ${session_id}${NC}"
      echo -e "${GREEN}✅ Session ID: ${created_session}${NC}"
      echo ""
      
      SUCCESS=true
      WORKING_PROXY="$proxy_url"
      WORKING_SESSION="$session_id"
      break
    else
      echo -e "${RED}❌ Falha com proxy ${session_id}${NC}"
      echo -e "${YELLOW}🔄 Rotando para próximo IP...${NC}"
    fi
  else
    echo -e "${RED}❌ Erro ao criar sessão com proxy ${session_id}${NC}"
  fi
  
  # Aguardar antes de próxima tentativa
  if [ $ATTEMPT -lt ${#PROXY_SESSIONS[@]} ]; then
    echo ""
    echo -e "${YELLOW}⏳ Aguardando 15 segundos antes da próxima tentativa...${NC}"
    sleep 15
  fi
done

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   RESULTADO FINAL${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ "$SUCCESS" = true ]; then
  echo -e "${GREEN}✅ TESTE CONCLUÍDO COM SUCESSO!${NC}"
  echo -e "${GREEN}✅ Proxy funcionando: ${WORKING_SESSION}${NC}"
  echo ""
  echo -e "${BLUE}🚀 INICIANDO TESTE COM 3 CHIPS SIMULTÂNEOS...${NC}"
  echo ""
  
  # ========== TESTE COM 3 CHIPS ==========
  
  declare -a CHIP_SESSIONS=()
  
  for i in {1..3}; do
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}   CHIP #${i}/3${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Usar session ID diferente para cada chip (IP diferente)
    chip_session_id="chip_${i}_session_$(date +%s)"
    chip_proxy_url=$(generate_proxy_url "$chip_session_id")
    
    chip_session=$(create_session_with_proxy \
      "chip_simultaneous_${i}" \
      "$chip_proxy_url" \
      "tenant_prod_001" \
      "chip_prod_${i}")
    
    if [ $? -eq 0 ]; then
      CHIP_SESSIONS+=("$chip_session")
      echo -e "${GREEN}✅ Chip #${i} criado: $chip_session${NC}"
    else
      echo -e "${RED}❌ Falha ao criar chip #${i}${NC}"
    fi
    
    # Pequeno delay entre criações
    if [ $i -lt 3 ]; then
      sleep 5
    fi
  done
  
  echo ""
  echo -e "${BLUE}⏳ Aguardando 10 segundos para todos estabilizarem...${NC}"
  sleep 10
  
  echo ""
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BLUE}   VERIFICANDO QR CODES DOS 3 CHIPS${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  
  for i in "${!CHIP_SESSIONS[@]}"; do
    chip_num=$((i+1))
    session_id="${CHIP_SESSIONS[$i]}"
    
    echo ""
    echo -e "${BLUE}🔍 Chip #${chip_num}: ${session_id}${NC}"
    
    if check_qr_code "$session_id"; then
      echo -e "${GREEN}✅ Chip #${chip_num} - QR CODE OK!${NC}"
    else
      echo -e "${YELLOW}⚠️ Chip #${chip_num} - Sem QR code ainda${NC}"
    fi
  done
  
  echo ""
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${GREEN}   🎉 TESTE DE 3 CHIPS CONCLUÍDO! 🎉${NC}"
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  
else
  echo -e "${RED}❌ NENHUM PROXY FUNCIONOU${NC}"
  echo -e "${YELLOW}💡 Sugestões:${NC}"
  echo "  1. Verifique suas credenciais de proxy"
  echo "  2. Teste o proxy manualmente com curl"
  echo "  3. Aguarde 30-60 minutos (cooldown do WhatsApp)"
  echo "  4. Use proxies mobile de outro provedor"
  echo ""
fi

echo ""
echo -e "${BLUE}📋 Ver logs completos:${NC}"
echo "  docker logs whago-baileys -f"
echo ""


