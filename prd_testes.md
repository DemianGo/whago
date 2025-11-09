# Plano de Testes Automatizados WHAGO

## 1. Backend (FastAPI)
- [x] Testes de autenticação (register/login/logout/refresh)
- [x] Testes de usuários (perfil, atualização, suspensão)
- [x] Testes de planos e billing (planos, créditos, invoices, billing avançado)
- [x] Testes de campanhas (CRUD, validações, limites de plano)
- [x] Testes de chips (CRUD, integração básica com Baileys fake)
- [x] Testes de dashboard (KPIs, séries históricas, atividade)
- [x] Testes de relatórios (campanha, chips, financeiro, executivo, comparativo)
- [ ] Testes de notificações in-app (rotas + serviço de unread)
- [ ] Testes de logs de auditoria (listagem, filtros)
- [ ] Testes do log de mensagens (filtros, paginação)

## 2. Infraestrutura Assíncrona
- [ ] Testes de Celery (disparo de tarefas de campanha/billing com Redis real em ambiente de teste)
- [ ] Testes de WebSocket (acompanhamento de campanhas em tempo real)
- [ ] Testes de publicação de eventos (Redis Pub/Sub para notificações/dashboard)

## 3. Frontend (UI)
- [ ] Suite E2E (Playwright/Cypress) cobrindo login, dashboard, campanhas, mensagens, relatórios
- [ ] Testes de download/export (CSV/XLSX/PDF) via navegador
- [ ] Testes de responsividade (smoke automático com viewport múltipla)
- [ ] Testes de notificações (dropdown, página dedicada, marcação de lidas)
- [ ] Testes de formulários (billing, campanha wizard, perfil)

## 4. Integrações e Serviços Externos
- [ ] Testes (mockados) do cliente Baileys simulando respostas/erros
- [ ] Testes do gateway de pagamento fake (aprovações/falhas, assinaturas e compras)
- [ ] Testes de webhooks (futuros) para campanhas/financeiro

## 5. Automação e Observabilidade de Testes
- [ ] Pipeline CI (GitHub Actions/GitLab) rodando pytest + lint + cobertura mínima
- [ ] Job separado para testes e2e/frontend
- [ ] Relatórios de cobertura (pytest-cov + badge)
- [ ] Documentação de execução local (`README`/`CONTRIBUTING`)

## 6. Próximas Ações
1. Criar fixtures específicas para notificações, auditoria e mensagens (pytest) e marcar itens correspondentes.
2. Montar ambiente docker-compose de teste com worker Celery + Redis para validar tasks/WebSocket.
3. Definir stack de testes frontend (Playwright ou Cypress) e iniciar cobertura dos fluxos críticos.
4. Configurar pipeline CI com etapas separadas (backend, e2e) e gerar relatórios de cobertura.
5. Documentar rotina de execução (local/CI) e critérios de aprovação (100% das suites verdes).
