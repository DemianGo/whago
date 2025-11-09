@echo off
REM Script para criar toda a estrutura de pastas do projeto WHAGO no Windows
REM Execute: create_structure.bat

echo 🚀 Criando estrutura de pastas do projeto WHAGO...

REM Criar diretório raiz
mkdir whago
cd whago

REM Backend
echo 📁 Criando estrutura do Backend...
mkdir backend\app\models
mkdir backend\app\routes
mkdir backend\app\services
mkdir backend\app\middleware
mkdir backend\app\schemas
mkdir backend\app\utils
mkdir backend\tasks
mkdir backend\logs
mkdir backend\uploads
mkdir backend\alembic\versions

REM Baileys Service
echo 📁 Criando estrutura do Baileys Service...
mkdir baileys-service\src\controllers
mkdir baileys-service\src\services
mkdir baileys-service\src\utils
mkdir baileys-service\sessions
mkdir baileys-service\logs

REM Frontend
echo 📁 Criando estrutura do Frontend...
mkdir frontend\static\css
mkdir frontend\static\js
mkdir frontend\static\images
mkdir frontend\templates

REM Criar arquivos __init__.py vazios (Python)
echo 📄 Criando arquivos __init__.py...
type nul > backend\app\__init__.py
type nul > backend\app\models\__init__.py
type nul > backend\app\routes\__init__.py
type nul > backend\app\services\__init__.py
type nul > backend\app\middleware\__init__.py
type nul > backend\app\schemas\__init__.py
type nul > backend\app\utils\__init__.py
type nul > backend\tasks\__init__.py

REM Criar arquivos de configuração vazios
echo 📄 Criando arquivos de configuração...
type nul > backend\alembic.ini
type nul > baileys-service\.eslintrc.json
type nul > baileys-service\.prettierrc

echo ✅ Estrutura criada com sucesso!
echo.
echo 📂 Para ver a estrutura:
dir /s /b
echo.
echo 🎯 Próximos passos:
echo 1. Mova os arquivos baixados para suas respectivas pastas
echo 2. Configure os arquivos .env
echo 3. Execute: docker-compose up -d
echo.
echo 📖 Leia SETUP_INSTRUCTIONS.md para mais detalhes!

pause
