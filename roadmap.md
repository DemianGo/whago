# 🗺️ Roadmap de Implementação - WHAGO

## 📋 Status Geral do Projeto

| Fase | Status | Progresso | Prazo |
|------|--------|-----------|-------|
| **MVP (v1.0)** | 🚧 Em Progresso | 0% | 12 semanas |
| **v1.1** | 📅 Planejado | 0% | +4 semanas |
| **v2.0** | 📅 Planejado | 0% | +8 semanas |

---

## 🎯 MVP - v1.0 (12 semanas)

### Semana 1-2: Setup e Infraestrutura
- [ ] Configurar ambiente de desenvolvimento
  - [ ] Docker e Docker Compose
  - [ ] PostgreSQL e Redis
  - [ ] Git e repositório
- [ ] Estrutura de pastas do projeto
- [ ] Configuração inicial do FastAPI
- [ ] Configuração inicial do Node.js/Baileys
- [ ] Setup de banco de dados (migrations)
- [ ] CI/CD básico

**Responsável**: DevOps/Backend  
**Entregáveis**: Ambiente rodando localmente, Docker compose funcional

---

### Semana 3-4: Sistema de Autenticação

#### Backend
- [ ] Models:
  - [ ] User model (SQLAlchemy)
  - [ ] Plan model
  - [ ] Session/Token model
- [ ] Routes:
  - [ ] POST /api/v1/auth/register
  - [ ] POST /api/v1/auth/login
  - [ ] POST /api/v1/auth/logout
  - [ ] POST /api/v1/auth/refresh
  - [ ] POST /api/v1/auth/forgot-password
  - [ ] POST /api/v1/auth/reset-password
- [ ] Services:
  - [ ] Hashing de senhas (bcrypt)
  - [ ] JWT token generation
  - [ ] Validações de senha forte
  - [ ] Validação de email/telefone

#### Frontend
- [ ] Tela de login
- [ ] Tela de registro (wizard 3 etapas)
- [ ] Tela de recuperação de senha
- [ ] Validações client-side
- [ ] Feedback visual de erros

**Responsável**: Backend + Frontend  
**Entregáveis**: Sistema completo de auth funcionando

---

### Semana 5-6: Sistema de Planos e Billing

#### Backend
- [ ] Models:
  - [ ] Plan model completo
  - [ ] Transaction model
  - [ ] Credit model
- [ ] Seed de planos (FREE, BUSINESS, ENTERPRISE)
- [ ] Routes:
  - [ ] GET /api/v1/plans (listar planos)
  - [ ] POST /api/v1/billing/upgrade
  - [ ] POST /api/v1/billing/credits/purchase
  - [ ] GET /api/v1/billing/transactions
  - [ ] GET /api/v1/user/credits
- [ ] Services:
  - [ ] Billing service
  - [ ] Credits management
  - [ ] Plan limits middleware
- [ ] Integração básica Stripe/Mercado Pago (mock no MVP)

#### Frontend
- [ ] Tela de planos (comparativo)
- [ ] Tela de billing e créditos
- [ ] Modal de upgrade de plano
- [ ] Histórico de transações
- [ ] Indicador de créditos no header

**Responsável**: Backend + Frontend  
**Entregáveis**: Sistema de planos e créditos funcional

---

### Semana 7-8: Integração com Baileys e Gerenciamento de Chips

#### Baileys Service
- [ ] Setup básico do servidor Express
- [ ] Integração com @whiskeysockets/baileys
- [ ] Sistema de sessões
- [ ] Geração de QR Code
- [ ] Autenticação via API Key
- [ ] WebSocket para QR Code em tempo real
- [ ] Endpoints:
  - [ ] POST /sessions/create
  - [ ] GET /sessions/:id/qr
  - [ ] GET /sessions/:id/status
  - [ ] DELETE /sessions/:id
  - [ ] POST /messages/send
  - [ ] GET /sessions/:id/info

#### Backend (Python)
- [ ] Models:
  - [ ] Chip model
  - [ ] ChipEvent model (log de eventos)
- [ ] Routes:
  - [ ] GET /api/v1/chips
  - [ ] POST /api/v1/chips
  - [ ] GET /api/v1/chips/:id
  - [ ] PUT /api/v1/chips/:id
  - [ ] DELETE /api/v1/chips/:id
  - [ ] POST /api/v1/chips/:id/disconnect
  - [ ] GET /api/v1/chips/:id/qr (WebSocket)
- [ ] Services:
  - [ ] Baileys client (comunicação com serviço Node)
  - [ ] Chip management service
  - [ ] WebSocket handler para QR codes
- [ ] Validações de limite de chips por plano

#### Frontend
- [ ] Tela de chips (grid de cards)
- [ ] Modal de adicionar chip
- [ ] Exibição de QR Code em tempo real
- [ ] Status visual dos chips (badges coloridos)
- [ ] Ações: reconectar, pausar, excluir
- [ ] Modal de detalhes do chip

**Responsável**: Backend + Node.js Dev + Frontend  
**Entregáveis**: Chips conectando via QR Code, gerenciamento completo

---

### Semana 9-10: Sistema de Campanhas

#### Backend
- [ ] Models:
  - [ ] Campaign model
  - [ ] Message model
  - [ ] Contact model
- [ ] Routes:
  - [ ] GET /api/v1/campaigns
  - [ ] POST /api/v1/campaigns
  - [ ] GET /api/v1/campaigns/:id
  - [ ] PUT /api/v1/campaigns/:id
  - [ ] DELETE /api/v1/campaigns/:id
  - [ ] POST /api/v1/campaigns/:id/start
  - [ ] POST /api/v1/campaigns/:id/pause
  - [ ] POST /api/v1/campaigns/:id/cancel
  - [ ] POST /api/v1/campaigns/contacts/upload
  - [ ] GET /api/v1/campaigns/:id/messages
- [ ] Services:
  - [ ] Campaign service
  - [ ] CSV parser (validação de contatos)
  - [ ] Message queue (Celery)
  - [ ] Message sender service
  - [ ] Rotação de chips
- [ ] Celery Tasks:
  - [ ] send_campaign_messages
  - [ ] process_message_batch
  - [ ] update_campaign_stats
  - [ ] retry_failed_messages

#### Frontend
- [ ] Tela de listagem de campanhas
- [ ] Wizard de criação (4 etapas)
  - [ ] Etapa 1: Informações básicas
  - [ ] Etapa 2: Upload de contatos
  - [ ] Etapa 3: Composição da mensagem
  - [ ] Etapa 4: Configurações e confirmação
- [ ] Editor de mensagem com preview
- [ ] Upload de CSV/TXT/Excel
- [ ] Validação de contatos em tempo real
- [ ] Preview da campanha antes de enviar
- [ ] Tela de detalhes da campanha
- [ ] Monitoramento em tempo real (WebSocket)
- [ ] Ações: pausar, cancelar, duplicar

**Responsável**: Backend + Frontend  
**Entregáveis**: Campanhas criando e enviando mensagens

---

### Semana 11-12: Dashboard, Relatórios e Finalização

#### Backend
- [ ] Routes:
  - [ ] GET /api/v1/dashboard/stats
  - [ ] GET /api/v1/dashboard/charts
  - [ ] GET /api/v1/reports/campaigns/:id
  - [ ] GET /api/v1/reports/chips/:id
  - [ ] GET /api/v1/reports/usage
- [ ] Services:
  - [ ] Dashboard aggregation service
  - [ ] Report generation service
  - [ ] Export to CSV/PDF
- [ ] Notificações in-app
- [ ] Sistema de logs de auditoria

#### Frontend
- [ ] Dashboard principal
  - [ ] Cards de KPIs
  - [ ] Gráficos (Chart.js)
  - [ ] Atividade recente
- [ ] Tela de mensagens (log detalhado)
- [ ] Tela de relatórios (BUSINESS/ENTERPRISE)
- [ ] Sistema de notificações
- [ ] Tela de configurações do usuário
- [ ] Tela de ajuda e suporte
- [ ] Responsividade mobile

#### Testes e Deploy
- [ ] Testes unitários (backend)
- [ ] Testes de integração
- [ ] Testes E2E (básicos)
- [ ] Documentação da API (Swagger)
- [ ] Deploy em ambiente de staging
- [ ] Testes de carga
- [ ] Correção de bugs críticos
- [ ] Deploy em produção

**Responsável**: Full Team  
**Entregáveis**: MVP completo em produção

---

## 🔄 v1.1 - Melhorias Pós-MVP (4 semanas)

### Funcionalidades Adicionais
- [ ] Multi-idioma (PT-BR, EN, ES)
- [ ] Suporte a grupos do WhatsApp
- [ ] Agendamento recorrente de campanhas
- [ ] Templates de mensagens salvos
- [ ] Sistema de tags para contatos
- [ ] Segmentação avançada de listas
- [ ] Exportação avançada de relatórios
- [ ] Melhorias de UX baseadas em feedback

### Maturador de Chips (BUSINESS/ENTERPRISE)
- [ ] Sistema de maturação automática
  - [ ] Fase 1: Validação inicial (Dia 1-3)
  - [ ] Fase 2: Aumento gradual (Dia 4-7)
  - [ ] Fase 3: Consolidação (Dia 8-14)
  - [ ] Fase 4: Produção (Dia 15+)
- [ ] Banco de mensagens naturais
- [ ] Score de saúde do chip
- [ ] Alertas de possível banimento
- [ ] Dashboard de maturação

### Rotação Inteligente (Aprimoramento)
- [ ] Estratégia Round Robin
- [ ] Estratégia baseada em saúde
- [ ] Estratégia baseada em horário
- [ ] Estratégia aleatória ponderada
- [ ] Configurações avançadas de rotação

---

## 🚀 v2.0 - Features Avançadas (8 semanas)

### Integrações
- [ ] Zapier/Make
- [ ] HubSpot
- [ ] Pipedrive
- [ ] RD Station
- [ ] Google Sheets
- [ ] Webhooks avançados

### IA e Automação
- [ ] IA para otimização de mensagens
- [ ] Análise de sentimento das respostas
- [ ] Predição de melhor horário de envio
- [ ] Chatbot básico (respostas automáticas)
- [ ] Sugestões de templates

### Mobile
- [ ] App React Native
- [ ] Notificações push
- [ ] Gestão simplificada mobile
- [ ] QR Code scan pelo app

### Outros Canais
- [ ] Suporte a Telegram
- [ ] Suporte a Instagram DM (experimental)
- [ ] SMS (integração com gateways)

### Enterprise Features
- [ ] Multi-usuário (permissões e roles)
- [ ] White-label
- [ ] API GraphQL
- [ ] SSO (Single Sign-On)
- [ ] Auditoria avançada
- [ ] SLA garantido

---

## 📊 Métricas de Acompanhamento

### Desenvolvimento
- [ ] Cobertura de testes: >80%
- [ ] Performance API: <200ms p95
- [ ] Zero vulnerabilidades críticas
- [ ] Documentação completa

### Negócio (Pós-lançamento)
- [ ] 100 usuários cadastrados (primeiro mês)
- [ ] 10% conversão FREE → BUSINESS
- [ ] NPS > 50
- [ ] Uptime > 99.5%

---

## 🐛 Backlog de Bugs/Issues

*A ser preenchido durante o desenvolvimento*

---

## 💡 Ideias Futuras (Backlog)

- [ ] Sistema de afiliados
- [ ] Marketplace de templates
- [ ] Análise de concorrência (benchmarking)
- [ ] Teste A/B automático avançado
- [ ] Gamificação
- [ ] Programa de fidelidade
- [ ] Integração com CRMs brasileiros (Agendor, Moskit)
- [ ] Integração com ERPs
- [ ] API de verificação de números
- [ ] Sistema de blacklist compartilhado

---

## 📝 Notas de Atualização

| Data | Versão | Descrição | Responsável |
|------|--------|-----------|-------------|
| 2025-11-08 | - | Roadmap inicial criado | Demian |

---

**Última atualização**: 08/11/2025  
**Próxima revisão**: Semanal (toda segunda-feira)
