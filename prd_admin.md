# PRD Admin - WHAGO: Painel Administrativo

## 1. VISÃO GERAL

### 1.1 Objetivo
Painel administrativo para gerenciar operações internas do WHAGO: usuários, planos, pagamentos, monitoramento e configurações globais.

### 1.2 Acesso
- URL: `/admin`
- Autenticação: Email/senha com role `admin`
- 2FA obrigatório

---

## 2. DASHBOARD ADMIN

### 2.1 KPIs Principais
- **Total Usuários**: Ativos / Inativos / Suspensos
- **MRR**: Receita recorrente mensal
- **Mensagens Enviadas Hoje/Mês**
- **Taxa de Churn**: % mensal
- **Novos Cadastros (7d/30d)**
- **Chips Conectados**: Total na plataforma

### 2.2 Gráficos
- Receita por plano (pizza)
- Crescimento de usuários (linha - 12 meses)
- Mensagens enviadas (barras - 30 dias)
- Distribuição por plano (barras)

### 2.3 Alertas
- Pagamentos falhos pendentes
- Usuários próximos ao limite
- Erros críticos de sistema
- Taxa de banimento alta

---

## 3. GERENCIAMENTO DE USUÁRIOS

### 3.1 Lista de Usuários
**Colunas:**
- ID | Nome | Email | Plano | Status | Créditos | Cadastro | Ações

**Filtros:**
- Por plano (FREE/BUSINESS/ENTERPRISE)
- Por status (ativo/suspenso/inativo)
- Por data de cadastro
- Busca por email/nome

**Ações em Massa:**
- Exportar para CSV
- Enviar email
- Suspender/Reativar

### 3.2 Detalhes do Usuário
**Informações:**
- Dados cadastrais completos
- Histórico de planos
- Saldo de créditos
- Chips conectados
- Campanhas criadas
- Histórico de pagamentos
- Logs de auditoria

**Ações:**
- Editar informações
- Alterar plano manualmente
- Adicionar/remover créditos
- Suspender/Reativar conta
- Resetar senha
- Fazer login como usuário (impersonate)
- Ver logs completos
- Excluir conta permanentemente

### 3.3 Criar Usuário Admin
- Email
- Nome
- Senha temporária
- Permissões (super-admin/financeiro/suporte)

---

## 4. GERENCIAMENTO DE PLANOS

### 4.1 Lista de Planos
- Planos ativos e inativos
- Editar preços e limites
- Criar novo plano

### 4.2 Editar Plano
**Campos:**
- Nome
- Slug
- Preço (R$/mês)
- Max chips
- Mensagens mensais
- Features (JSONB)
- Ativo/Inativo

**Validações:**
- Não permitir deletar plano com usuários ativos
- Notificar usuários se limites mudarem

### 4.3 Cupons de Desconto
- Criar cupom (código, % ou R$, validade)
- Listar cupons ativos/expirados
- Desativar cupom
- Ver uso do cupom

---

## 5. GERENCIAMENTO DE PAGAMENTOS

### 5.1 Transações
**Lista:**
- ID | Usuário | Tipo | Valor | Status | Gateway | Data

**Filtros:**
- Por gateway (Mercado Pago/Stripe/PayPal)
- Por status (pendente/aprovado/rejeitado)
- Por tipo (assinatura/créditos)
- Por período

**Ações:**
- Ver detalhes
- Estornar pagamento
- Reprocessar webhook
- Enviar nota fiscal

### 5.2 Assinaturas
- Listar todas assinaturas
- Status (ativa/cancelada/pendente)
- Próxima cobrança
- Cancelar manualmente
- Reativar assinatura

### 5.3 Configurações de Gateway
**Mercado Pago:**
- Access Token (sandbox/production)
- Public Key
- Webhook Secret
- Modo (sandbox/production)

**Stripe:**
- API Key
- Webhook Secret
- Publishable Key
- Modo

**PayPal:**
- Client ID
- Client Secret
- Webhook ID
- Modo

**Campos:**
- Ativar/Desativar gateway
- Alternar sandbox/production
- Testar conexão
- Ver logs de webhooks

---

## 6. MONITORAMENTO DO SISTEMA

### 6.1 Chips
- Total de chips na plataforma
- Por status (conectado/desconectado/banido)
- Lista de chips com problemas
- Taxa de sucesso por chip
- Ação: Desconectar chip forçadamente

### 6.2 Campanhas
- Campanhas ativas no momento
- Taxa de sucesso geral
- Campanhas com erro
- Ação: Pausar/cancelar campanha

### 6.3 Mensagens
- Total de mensagens (hoje/mês)
- Taxa de entrega geral
- Erros de envio (agrupados por tipo)
- Gráfico de mensagens por hora

### 6.4 Performance
- Latência de API (p50/p95/p99)
- Taxa de erro de requests
- Uso de recursos (CPU/RAM/Disco)
- Status de serviços (backend/baileys/redis/postgres)

### 6.5 Logs
- Filtrar por nível (info/warning/error)
- Filtrar por serviço
- Busca por texto
- Exportar logs

---

## 7. CONFIGURAÇÕES GLOBAIS

### 7.1 Sistema
- Nome da plataforma
- Logo/Favicon
- Email de contato
- URLs (frontend/backend/api)
- Timezone padrão
- Idioma padrão

### 7.2 Emails
- SMTP Host/Port/User/Password
- Templates de email (editar HTML)
- Testar envio de email

### 7.3 Limites Globais
- Max tentativas de login
- Tempo de sessão
- Rate limit global
- Max upload de arquivo

### 7.4 Notificações
- Webhook para alertas internos (Slack/Discord)
- Email para alertas críticos
- Threshold de alertas (% erro, usuários/hora)

### 7.5 Segurança
- Forçar 2FA para admins
- IPs permitidos para admin
- Logs de acesso admin
- Sessões ativas de admins

---

## 7. GERENCIAMENTO DE PROXIES

### 7.1 Visão Geral
Sistema de proxies residenciais para proteger IPs dos chips e evitar banimentos do WhatsApp. Custos configuráveis e contabilizados por usuário.

### 7.2 Provedores de Proxy
**Lista de Provedores:**
- Nome | Tipo | Custo/GB | Status | Ações

**Criar/Editar Provedor:**
- Nome (ex: "Smartproxy BR")
- Tipo: Residencial / Datacenter / Mobile
- Custo por GB (R$): configurável
- Credenciais:
  - URL do servidor (ex: `proxy.smartproxy.net`)
  - Porta (ex: `3120`)
  - Username
  - Password
  - API Key (para extração de IPs)
- Região padrão (BR, US, etc)
- Status: Ativo/Inativo

**Ações:**
- Testar conexão
- Ver uso total (GB)
- Ver custo acumulado
- Desativar/reativar

### 7.3 Pool de Proxies
**Lista de Proxies Ativos:**
- ID | Provedor | IP/URL | Região | Status | Health | Uso (GB) | Última Uso

**Tipos de Proxy:**
1. **Rotativo (Recomendado):** 
   - Mesmo endpoint, IP muda automaticamente
   - Sticky session: IP fixo por chip
   - Ex: `http://user-session-{chipId}:pass@proxy.smartproxy.net:3120`

2. **Pool Estático:**
   - Lista de IPs fixos extraídos via API
   - Rotação manual ou automática

**Cadastro Manual:**
- Provedor
- Proxy URL completa
- Região
- Protocolo (HTTP/HTTPS/SOCKS5)

**Extração via API:**
- Selecionar provedor com API configurada
- Quantidade de IPs
- Região
- Tempo de vida (minutos)
- Sistema extrai e cadastra automaticamente

### 7.4 Configurações de Uso
**Limites por Plano:**
- FREE: X GB/mês (configurável)
- BUSINESS: Y GB/mês
- ENTERPRISE: Z GB/mês

**Estratégias de Rotação:**
- Round-robin
- Health-based (prioriza proxies saudáveis)
- Geographic (chip BR usa proxy BR)
- Sticky session (chip fixo em proxy)

**Health Check:**
- Ping automático a cada X minutos
- Score de saúde (0-100)
- Desativar automaticamente se score < 30

### 7.5 Monitoramento de Uso
**Dashboard de Proxies:**
- Total de GB usado (hoje/mês)
- Custo total (hoje/mês)
- Uso por usuário (top 10)
- Uso por provedor
- Gráfico de consumo (últimos 30 dias)

**Logs de Uso:**
- Data/Hora | Usuário | Chip | Proxy | Bytes | Custo | Duração

**Alertas:**
- Usuário atingiu 90% do limite
- Proxy com health baixo
- Custo mensal acima do esperado
- Proxy inativo há X horas

### 7.6 Contabilização de Custos
**Regras:**
- Sistema coleta uso via API do provedor a cada 5 minutos
- Calcula custo: `(bytes / 1GB) * custo_por_gb`
- Registra em `proxy_usage_logs`
- Agrega em `user_proxy_costs` (mensal)

**Cobrança Extra (opcional):**
- Se usuário exceder limite do plano
- Pacotes avulsos de GB:
  - 1 GB = R$ X
  - 5 GB = R$ Y (desconto)
  - 10 GB = R$ Z (desconto)

**Transparência:**
- Usuário vê uso em tempo real no dashboard
- Notificação quando atingir 80% e 100% do limite
- Opção de pausar chips automaticamente se exceder

### 7.7 Integração com Chips
**Atribuição Automática:**
- Ao conectar chip, sistema atribui proxy automaticamente
- Critérios: região do chip, health, carga balanceada

**Atribuição Manual:**
- Admin pode forçar chip específico em proxy específico
- Útil para testes ou troubleshooting

**Rotação:**
- Sistema pode trocar proxy de chip automaticamente:
  - Se proxy cair (health < 30)
  - Se atingir limite de tempo (ex: 24h)
  - Se usuário solicitar "trocar proxy"

### 7.8 Relatórios
**Relatório de Custos:**
- Custo total por período
- Custo por usuário
- Custo por provedor
- Projeção de gastos

**Relatório de Performance:**
- Proxies com melhor uptime
- Proxies com melhor latência
- Taxa de sucesso de envios por proxy

**Exportação:**
- CSV/Excel com dados detalhados
- Filtros por período, usuário, provedor

---

## 8. RELATÓRIOS

### 8.1 Financeiro
- Receita por período
- Receita por plano
- Churn rate
- LTV médio
- Previsão de receita

### 8.2 Uso da Plataforma
- Usuários ativos (DAU/MAU)
- Mensagens enviadas
- Campanhas criadas
- Taxa de conversão (registro → primeiro envio)

### 8.3 Suporte
- Tickets abertos/resolvidos
- Tempo médio de resposta
- Usuários com mais tickets

### 8.4 Exportações
- CSV/Excel/PDF
- Agendar relatórios recorrentes (email)

---

## 9. AUDITORIA

### 9.1 Logs de Admin
- Ação | Admin | Timestamp | IP | Detalhes
- Ex: "Admin João alterou plano do usuário X"

### 9.2 Logs de Sistema
- Erros críticos
- Acessos suspeitos
- Mudanças de configuração

### 9.3 Retenção
- Logs mantidos por 1 ano
- Exportar para S3 após 90 dias

---

## 10. SUPORTE

### 10.1 Tickets
- Lista de tickets (aberto/em andamento/resolvido)
- Filtrar por usuário/prioridade/data
- Responder ticket (editor de texto rico)
- Atribuir para admin específico
- Mudar status/prioridade

### 10.2 Ações Rápidas
- Ver perfil do usuário
- Impersonar usuário
- Adicionar créditos de cortesia
- Suspender/reativar conta

---

## 11. INTERFACE

### 11.1 Layout
```
┌──────────────────────────────────────────┐
│  Header Admin (fixo)                     │
├───────┬──────────────────────────────────┤
│       │                                  │
│ Menu  │     Conteúdo                     │
│ Admin │                                  │
│       │                                  │
└───────┴──────────────────────────────────┘
```

### 11.2 Menu
- 📊 Dashboard
- 👥 Usuários
- 💳 Planos
- 💰 Pagamentos
- 🔌 Gateways
- 🌐 Proxies
- 📱 Chips
- 📢 Campanhas
- 📊 Relatórios
- 🎫 Suporte
- ⚙️ Configurações
- 📋 Logs
- 🔐 Admins

### 11.3 Cores
- Usar tema diferente do painel do usuário
- Cores: Azul escuro (#1E3A8A) + Cinza (#6B7280)
- Badge "ADMIN" sempre visível

---

## 12. PERMISSÕES

### 12.1 Roles
**Super Admin:**
- Acesso total
- Gerenciar outros admins
- Configurações críticas

**Financeiro:**
- Ver/editar pagamentos
- Relatórios financeiros
- Gerenciar planos/cupons
- Ver usuários (read-only)

**Suporte:**
- Ver usuários
- Editar créditos/planos
- Responder tickets
- Ver logs de usuário
- Impersonar usuários

### 12.2 Controle
- Cada ação verifica permissão
- Logs detalhados de ações admin

---

## 13. SEGURANÇA

### 13.1 Autenticação
- 2FA obrigatório (TOTP)
- IPs whitelisted (opcional)
- Sessão expira em 2h
- Logout automático após inatividade

### 13.2 Auditoria
- Toda ação é logada
- IP e user agent registrados
- Alertas para ações críticas

### 13.3 Proteções
- Rate limit mais restrito
- CSRF tokens
- Confirmação para ações destrutivas

---

## 14. IMPLEMENTAÇÃO

### 14.1 Backend
**Rotas:**
- `POST /api/v1/admin/auth/login`
- `GET /api/v1/admin/users`
- `GET /api/v1/admin/users/:id`
- `PUT /api/v1/admin/users/:id`
- `POST /api/v1/admin/users/:id/impersonate`
- `GET /api/v1/admin/plans`
- `PUT /api/v1/admin/plans/:id`
- `GET /api/v1/admin/transactions`
- `POST /api/v1/admin/transactions/:id/refund`
- `GET /api/v1/admin/gateways`
- `PUT /api/v1/admin/gateways/:gateway`
- `GET /api/v1/admin/stats/dashboard`
- `GET /api/v1/admin/logs`

**Middleware:**
- `require_admin()` - verifica role admin
- `require_permission(action)` - verifica permissão específica
- `log_admin_action()` - registra ação

### 14.2 Frontend
- Rota: `/admin/*`
- Templates separados (base_admin.html)
- JavaScript: admin.js
- CSS: admin.css (tema azul escuro)

### 14.3 Banco de Dados
**Tabela: admins**
```sql
CREATE TABLE admins (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  role VARCHAR(50), -- super_admin, financeiro, suporte
  permissions JSONB,
  created_at TIMESTAMP,
  created_by UUID REFERENCES admins(id)
);
```

**Tabela: admin_audit_logs**
```sql
CREATE TABLE admin_audit_logs (
  id UUID PRIMARY KEY,
  admin_id UUID REFERENCES admins(id),
  action VARCHAR(100),
  entity_type VARCHAR(50),
  entity_id UUID,
  details JSONB,
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMP
);
```

---

## 15. PRIORIZAÇÃO

### Fase 1 (MVP Admin):
- [x] Autenticação admin
- [x] Dashboard básico
- [x] Lista/detalhe de usuários
- [x] Editar planos
- [x] Ver transações
- [x] Configurar gateways
- [x] **CRUD de Proxies** ✅

### Fase 2:
- [ ] Relatórios completos
- [ ] Sistema de tickets
- [ ] Cupons de desconto
- [ ] Impersonar usuário

### Fase 3:
- [ ] Logs avançados
- [ ] Múltiplos admins com permissões
- [ ] Webhooks internos
- [ ] Dashboard avançado

---

**FIM DO PRD ADMIN**

