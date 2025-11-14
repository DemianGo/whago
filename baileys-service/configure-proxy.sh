#!/bin/bash

# ========================================
# WHAGO - Script de Configuração de Proxy
# ========================================
# 
# Este script ajuda a configurar o proxy no Baileys service.
# Uso: ./configure-proxy.sh
#

set -e

echo "🌐 WHAGO - Configuração de Proxy"
echo "=================================="
echo ""

# Verificar se .env existe
if [ ! -f ".env" ]; then
    echo "⚠️  Arquivo .env não encontrado!"
    echo "📝 Criando .env a partir do exemplo..."
    
    if [ -f "proxy.env.example" ]; then
        cp proxy.env.example .env
        echo "✅ Arquivo .env criado!"
    else
        echo "❌ Arquivo proxy.env.example não encontrado!"
        exit 1
    fi
fi

echo "📋 Configuração atual:"
echo ""

# Ler configuração atual
PROXY_ENABLED=$(grep "^PROXY_ENABLED=" .env | cut -d'=' -f2 || echo "false")
PROXY_TYPE=$(grep "^PROXY_TYPE=" .env | cut -d'=' -f2 || echo "http")
PROXY_HOST=$(grep "^PROXY_HOST=" .env | cut -d'=' -f2 || echo "")
PROXY_PORT=$(grep "^PROXY_PORT=" .env | cut -d'=' -f2 || echo "")
PROXY_USERNAME=$(grep "^PROXY_USERNAME=" .env | cut -d'=' -f2 || echo "")
PROXY_COUNTRY=$(grep "^PROXY_COUNTRY=" .env | cut -d'=' -f2 || echo "")

echo "  Habilitado: $PROXY_ENABLED"
echo "  Tipo: $PROXY_TYPE"
echo "  Host: $PROXY_HOST"
echo "  Port: $PROXY_PORT"
echo "  Username: $PROXY_USERNAME"
echo "  Country: $PROXY_COUNTRY"
echo ""

# Menu
echo "O que deseja fazer?"
echo ""
echo "  1) Habilitar proxy (configurar credenciais)"
echo "  2) Desabilitar proxy (usar conexão direta)"
echo "  3) Testar proxy atual"
echo "  4) Ver status do proxy"
echo "  5) Sair"
echo ""

read -p "Escolha uma opção [1-5]: " option

case $option in
    1)
        echo ""
        echo "📝 Configurando proxy..."
        echo ""
        
        # Escolher provedor
        echo "Escolha o provedor:"
        echo "  1) Smartproxy (gate.smartproxy.com:7000)"
        echo "  2) IPRoyal (geo.iproyal.com:12321)"
        echo "  3) Bright Data (brd.superproxy.io:22225)"
        echo "  4) Oxylabs (pr.oxylabs.io:7777)"
        echo "  5) Outro (informar manualmente)"
        echo ""
        
        read -p "Provedor [1-5]: " provider
        
        case $provider in
            1)
                PROXY_HOST="gate.smartproxy.com"
                PROXY_PORT="7000"
                ;;
            2)
                PROXY_HOST="geo.iproyal.com"
                PROXY_PORT="12321"
                ;;
            3)
                PROXY_HOST="brd.superproxy.io"
                PROXY_PORT="22225"
                ;;
            4)
                PROXY_HOST="pr.oxylabs.io"
                PROXY_PORT="7777"
                ;;
            5)
                read -p "Host do proxy: " PROXY_HOST
                read -p "Porta do proxy: " PROXY_PORT
                ;;
            *)
                echo "❌ Opção inválida!"
                exit 1
                ;;
        esac
        
        # Credenciais
        read -p "Username: " PROXY_USERNAME
        read -sp "Password: " PROXY_PASSWORD
        echo ""
        
        # Tipo
        read -p "Tipo [http/socks5] (padrão: http): " PROXY_TYPE_INPUT
        PROXY_TYPE=${PROXY_TYPE_INPUT:-http}
        
        # País (opcional)
        read -p "País (código ISO, ex: BR, US) [opcional]: " PROXY_COUNTRY
        
        # Session ID (opcional)
        read -p "Session ID [opcional, padrão: whago_session_1]: " PROXY_SESSION_ID
        PROXY_SESSION_ID=${PROXY_SESSION_ID:-whago_session_1}
        
        # Atualizar .env
        sed -i "s/^PROXY_ENABLED=.*/PROXY_ENABLED=true/" .env
        sed -i "s/^PROXY_TYPE=.*/PROXY_TYPE=$PROXY_TYPE/" .env
        sed -i "s/^PROXY_HOST=.*/PROXY_HOST=$PROXY_HOST/" .env
        sed -i "s/^PROXY_PORT=.*/PROXY_PORT=$PROXY_PORT/" .env
        sed -i "s/^PROXY_USERNAME=.*/PROXY_USERNAME=$PROXY_USERNAME/" .env
        sed -i "s/^PROXY_PASSWORD=.*/PROXY_PASSWORD=$PROXY_PASSWORD/" .env
        sed -i "s/^PROXY_COUNTRY=.*/PROXY_COUNTRY=$PROXY_COUNTRY/" .env
        sed -i "s/^PROXY_SESSION_ID=.*/PROXY_SESSION_ID=$PROXY_SESSION_ID/" .env
        
        echo ""
        echo "✅ Proxy configurado com sucesso!"
        echo ""
        echo "🔄 Reinicie o serviço para aplicar:"
        echo "   docker-compose restart baileys"
        echo ""
        ;;
        
    2)
        echo ""
        echo "🔓 Desabilitando proxy..."
        sed -i "s/^PROXY_ENABLED=.*/PROXY_ENABLED=false/" .env
        echo "✅ Proxy desabilitado!"
        echo ""
        echo "🔄 Reinicie o serviço para aplicar:"
        echo "   docker-compose restart baileys"
        echo ""
        ;;
        
    3)
        echo ""
        echo "🧪 Testando proxy..."
        echo ""
        
        # Verificar se serviço está rodando
        if ! curl -s http://localhost:3000/health > /dev/null 2>&1; then
            echo "❌ Serviço Baileys não está rodando!"
            echo "   Inicie com: docker-compose up -d baileys"
            exit 1
        fi
        
        # Testar proxy
        response=$(curl -s -X POST http://localhost:3000/api/v1/proxy/test)
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
        echo ""
        ;;
        
    4)
        echo ""
        echo "📊 Status do proxy..."
        echo ""
        
        # Verificar se serviço está rodando
        if ! curl -s http://localhost:3000/health > /dev/null 2>&1; then
            echo "❌ Serviço Baileys não está rodando!"
            echo "   Inicie com: docker-compose up -d baileys"
            exit 1
        fi
        
        # Ver status
        response=$(curl -s http://localhost:3000/api/v1/proxy/status)
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
        echo ""
        ;;
        
    5)
        echo "👋 Até logo!"
        exit 0
        ;;
        
    *)
        echo "❌ Opção inválida!"
        exit 1
        ;;
esac

