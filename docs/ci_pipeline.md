# CI & Observabilidade de Testes

Este documento consolida a estratégia da fase 5 do plano de testes (`prd_testes.md`), cobrindo automação, cobertura e documentação.

## Objetivos

- Rodar a suíte backend (`pytest`) com relatório de cobertura.
- Executar testes do serviço Baileys (`npm --prefix baileys-service test`).
- Rodar a suíte E2E (Playwright) contra o backend real (com Celery e Baileys ativos).
- Documentar comandos locais e preparar pipeline CI (GitHub Actions).

## Execução Local (com Docker Compose)

1. Subir os serviços necessários:

   ```bash
   docker-compose up -d backend redis postgres celery baileys
   ```

2. Aplicar migrations e rodar a suíte completa com cobertura:

   ```bash
   ./scripts/run_ci.sh
   ```

   O script executa:

   - `docker-compose exec backend alembic upgrade head`
   - `docker-compose exec backend pytest --cov=app --cov-report=xml:backend/coverage.xml`
   - `npm --prefix baileys-service test`
   - `npm install` + `npx playwright install`
   - `npm run test:e2e`

3. Cobertura:

   - Arquivo `backend/coverage.xml`
   - Pode ser consumido por ferramentas como Codecov/Sonar.

## Pipeline GitHub Actions (`.github/workflows/tests.yml`)

- Dispara em `push`/`pull_request`.
- Jobs:
  - **backend**: instala dependências Python, sobe Postgres/Redis como serviços, aplica migrations e roda `pytest --cov`.
  - **frontend**: usa Node 18, instala dependências, executa `npx playwright install --with-deps`, roda `npm run test:e2e`.
- Artefatos gerados:
  - `backend/coverage.xml`
  - Relatórios Playwright (`frontend-tests/report/`)

## Checklist Fase 5 (PRD Testes)

- [x] Pipeline CI (via GitHub Actions) rodando pytest + coverage.
- [x] Job separado para testes E2E (Playwright).
- [x] Documentação de execução local/CI (README + este documento).


