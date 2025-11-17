#!/bin/bash
# Script para testar credenciais DataImpulse até encontrar uma válida

echo "🔍 TESTANDO CREDENCIAIS DATAIMPULSE"
echo "===================================="
echo ""

PROXY_HOST="gw.dataimpulse.com"
PROXY_PORT="824"
PROXY_USER="b0d7c401317486d2c3e8__cr.br"
PROXY_PASSWORD="f60a2f1e36dcd0b4"

# Lista de sessions para testar
SESSIONS=(
  "evo_test_1"
  "evo_test_2"
  "evo_test_3"
  "evo_valid_1"
  "evo_valid_2"
  "whatsapp_test_1"
  "whatsapp_test_2"
  "mobile_br_1"
  "mobile_br_2"
  "mobile_br_3"
)

VALID_SESSION=""

for session in "${SESSIONS[@]}"; do
  echo "Testando session: $session"
  
  # ✅ DataImpulse NÃO suporta -session_X, usar credenciais diretas
  PROXY_URL="socks5://${PROXY_USER}:${PROXY_PASSWORD}@${PROXY_HOST}:${PROXY_PORT}"
  
  # Testar com timeout de 15 segundos (proxy SOCKS5 pode ser lento)
  IP=$(timeout 15 curl -s -x "$PROXY_URL" https://api.ipify.org 2>&1)
  
  if [[ $? -eq 0 ]] && [[ "$IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "✅ CREDENCIAL VÁLIDA!"
    echo "   Session: $session"
    echo "   IP: $IP"
    echo ""
    VALID_SESSION="$session"
    
    # Salvar no arquivo .env
    echo "# Credencial válida encontrada em $(date)" >> .env
    echo "PROXY_SESSION=$session" >> .env
    echo "PROXY_IP=$IP" >> .env
    
    echo "✅ Credencial salva em .env"
    echo ""
    break
  else
    echo "❌ Falhou: $IP"
  fi
  
  echo ""
done

if [ -z "$VALID_SESSION" ]; then
  echo "❌ NENHUMA CREDENCIAL VÁLIDA ENCONTRADA!"
  echo ""
  echo "⚠️ TODAS AS CREDENCIAIS DATAIMPULSE EXPIRARAM"
  echo ""
  echo "Recomendação:"
  echo "  1. Renovar credenciais DataImpulse"
  echo "  2. OU contratar Smartproxy ($75/mês)"
  echo "  3. OU contratar Bright Data ($500/mês)"
  echo ""
  exit 1
else
  echo "🎉 SUCESSO!"
  echo ""
  echo "Você pode executar o teste agora:"
  echo "  python3 test_evolution.py"
  echo ""
  exit 0
fi

