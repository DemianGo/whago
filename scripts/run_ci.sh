#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Garantindo serviços necessários ativos"
docker-compose up -d backend redis postgres celery baileys

echo "==> Aplicando migrations"
docker-compose exec backend alembic upgrade head

echo "==> Instalando dependências backend (garantia)"
docker-compose exec backend pip install --disable-pip-version-check -r requirements.txt >/dev/null

echo "==> Executando pytest com cobertura"
docker-compose exec backend pytest --cov=app --cov-report=xml:coverage.xml -q
docker-compose exec backend ls coverage.xml >/dev/null
docker cp whago-backend:/app/coverage.xml "${ROOT_DIR}/backend/coverage.xml"

echo "==> Executando testes do serviço Baileys"
npm --prefix baileys-service install >/dev/null
npm --prefix baileys-service test >/dev/null

echo "==> Instalando dependências frontend"
cd "${ROOT_DIR}"
npm install >/dev/null
npx playwright install >/dev/null

echo "==> Executando Playwright (E2E)"
npm run test:e2e

echo "==> Suite completa finalizada com sucesso."

