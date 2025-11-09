#!/bin/bash

# Script para criar toda a estrutura de pastas do projeto WHAGO
# Execute: chmod +x create_structure.sh && ./create_structure.sh

echo "🚀 Criando estrutura de pastas do projeto WHAGO..."

# Criar diretório raiz
mkdir -p whago
cd whago

# Backend
echo "📁 Criando estrutura do Backend..."
mkdir -p backend/app/models
mkdir -p backend/app/routes
mkdir -p backend/app/services
mkdir -p backend/app/middleware
mkdir -p backend/app/schemas
mkdir -p backend/app/utils
mkdir -p backend/tasks
mkdir -p backend/logs
mkdir -p backend/uploads
mkdir -p backend/alembic/versions

# Baileys Service
echo "📁 Criando estrutura do Baileys Service..."
mkdir -p baileys-service/src/controllers
mkdir -p baileys-service/src/services
mkdir -p baileys-service/src/utils
mkdir -p baileys-service/sessions
mkdir -p baileys-service/logs

# Frontend
echo "📁 Criando estrutura do Frontend..."
mkdir -p frontend/static/css
mkdir -p frontend/static/js
mkdir -p frontend/static/images
mkdir -p frontend/templates

# Criar arquivos __init__.py vazios (Python)
echo "📄 Criando arquivos __init__.py..."
touch backend/app/__init__.py
touch backend/app/models/__init__.py
touch backend/app/routes/__init__.py
touch backend/app/services/__init__.py
touch backend/app/middleware/__init__.py
touch backend/app/schemas/__init__.py
touch backend/app/utils/__init__.py
touch backend/tasks/__init__.py

# Criar arquivos de configuração vazios
echo "📄 Criando arquivos de configuração..."
touch backend/alembic.ini
touch baileys-service/.eslintrc.json
touch baileys-service/.prettierrc

echo "✅ Estrutura criada com sucesso!"
echo ""
echo "📂 Estrutura do projeto:"
tree -L 3 -I 'node_modules|venv|__pycache__|*.pyc' || ls -R

echo ""
echo "🎯 Próximos passos:"
echo "1. Mova os arquivos baixados para suas respectivas pastas"
echo "2. Configure os arquivos .env"
echo "3. Execute: docker-compose up -d"
echo ""
echo "📖 Leia SETUP_INSTRUCTIONS.md para mais detalhes!"
