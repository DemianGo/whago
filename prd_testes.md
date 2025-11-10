# Plano de Testes Automatizados WHAGO

## 1. Backend (FastAPI)
- [x] Testes de autenticação (register/login/logout/refresh)
- [x] Testes de usuários (perfil, atualização, suspensão)
- [x] Testes de planos e billing (planos, créditos, invoices, billing avançado)
- [x] Testes de campanhas (CRUD, validações, limites de plano)
- [x] Testes de chips (CRUD, integração básica com Baileys fake)
- [x] Testes de dashboard (KPIs, séries históricas, atividade)
- [x] Testes de relatórios (campanha, chips, financeiro, executivo, comparativo)
- [x] Testes de notificações in-app (rotas + serviço de unread)
- [x] Testes de logs de auditoria (listagem, filtros)
- [x] Testes do log de mensagens (filtros, paginação)

## 2. Infraestrutura Assíncrona
- [x] Testes de Celery (disparo de tarefas de campanha/billing com Redis real em ambiente de teste)
- [x] Testes de WebSocket (acompanhamento de campanhas em tempo real)
- [x] Testes de publicação de eventos (Redis Pub/Sub para notificações/dashboard)

## 3. Frontend (UI)
- [x] Suite E2E (Playwright/Cypress) cobrindo login, dashboard, campanhas, mensagens, relatórios
- [x] Testes de download/export (CSV/XLSX/PDF) via navegador
- [x] Testes de responsividade (smoke automático com viewport múltipla)
- [x] Testes de notificações (dropdown, página dedicada, marcação de lidas)
- [x] Testes de formulários (billing, campanha wizard, perfil)

## 4. Integrações e Serviços Externos
- [x] Testes do cliente Baileys (mockados) e suíte Jest do serviço Node real
- [x] Testes do gateway de pagamento fake (aprovações/falhas, assinaturas e compras)
- [x] Testes de webhooks (campanhas/financeiro + CRUD/API/UI)

## 5. Automação e Observabilidade de Testes
- [x] Pipeline CI (GitHub Actions/GitLab) rodando pytest + cobertura mínima
- [x] Job separado para testes e2e/frontend
- [x] Relatórios de cobertura (pytest-cov + artefatos)
- [x] Documentação de execução local (`README`, `docs/ci_pipeline.md`)

## 6. Próximas Ações
- Sem pendências: suites backend, Celery/Baileys, webhooks e frontend executam 100% com sucesso.
