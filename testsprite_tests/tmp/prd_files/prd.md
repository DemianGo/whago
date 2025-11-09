# PRD - WHAGO: Plataforma de Mensagens em Massa via WhatsApp

## 1. VISÃO GERAL DO PRODUTO

### 1.1 Descrição
WHAGO é uma plataforma SaaS multi-usuário para envio de mensagens em massa via WhatsApp, utilizando a biblioteca Baileys. A plataforma permite que empresas gerenciem múltiplos chips de WhatsApp, enviem campanhas de mensagens para listas de contatos e monitorem resultados em tempo real.

### 1.2 Problema que Resolve
Empresas e profissionais precisam enviar mensagens em massa via WhatsApp de forma eficiente, gerenciar múltiplos números, controlar gastos e ter relatórios detalhados das campanhas, sem depender de soluções caras ou APIs oficiais limitadas.

### 1.3 Objetivo Principal
Criar uma plataforma completa, escalável e rentável que permita envio de mensagens em massa via WhatsApp com sistema de créditos, planos de assinatura e gerenciamento inteligente de chips.

---

## 2. ARQUITETURA TÉCNICA

### 2.1 Stack Tecnológico
- **Backend**: Python 3.11+ com FastAPI
- **Banco de Dados**: PostgreSQL (principal) + Redis (cache e filas)
- **Autenticação**: JWT tokens com refresh tokens
- **Frontend**: HTML5 + Tailwind CSS + Alpine.js
- **WhatsApp Engine**: Node.js + Baileys (serviço separado)
- **Comunicação Real-time**: WebSockets (FastAPI WebSocket)
- **Processamento Assíncrono**: Celery com Redis como broker
- **Armazenamento**: Sistema de arquivos local (sessões Baileys) + PostgreSQL (dados)

### 2.2 Estrutura de Diretórios
```
whago/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── plan.py
│   │   │   ├── chip.py
│   │   │   ├── campaign.py
│   │   │   ├── message.py
│   │   │   └── transaction.py
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── chips.py
│   │   │   ├── campaigns.py
│   │   │   ├── messages.py
│   │   │   ├── plans.py
│   │   │   └── dashboard.py
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── chip_service.py
│   │   │   ├── campaign_service.py
│   │   │   ├── billing_service.py
│   │   │   └── baileys_client.py
│   │   ├── middleware/
│   │   │   ├── auth_middleware.py
│   │   │   └── plan_limit_middleware.py
│   │   ├── schemas/
│   │   │   └── ... (Pydantic schemas)
│   │   └── utils/
│   │       ├── validators.py
│   │       ├── decorators.py
│   │       └── helpers.py
│   ├── tasks/
│   │   ├── celery_app.py
│   │   ├── message_tasks.py
│   │   └── chip_monitor_tasks.py
│   ├── requirements.txt
│   └── .env.example
├── baileys-service/
│   ├── src/
│   │   ├── index.js
│   │   ├── server.js
│   │   ├── controllers/
│   │   │   └── whatsapp.controller.js
│   │   ├── services/
│   │   │   ├── session.service.js
│   │   │   └── message.service.js
│   │   └── utils/
│   │       └── logger.js
│   ├── sessions/ (gitignored)
│   ├── package.json
│   └── .env.example
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   │   └── custom.css
│   │   ├── js/
│   │   │   ├── app.js
│   │   │   ├── auth.js
│   │   │   ├── chips.js
│   │   │   ├── campaigns.js
│   │   │   └── dashboard.js
│   │   └── images/
│   └── templates/
│       ├── base.html
│       ├── login.html
│       ├── register.html
│       ├── dashboard.html
│       ├── chips.html
│       ├── campaigns.html
│       ├── messages.html
│       ├── billing.html
│       └── plans.html
├── docker-compose.yml
├── README.md
└── .gitignore
```

---

## 3. SISTEMA DE USUÁRIOS E AUTENTICAÇÃO

### 3.1 Registro de Usuário
**Campos Obrigatórios:**
- Nome completo (2-100 caracteres)
- Email (validação com regex, único no sistema)
- Senha (mínimo 8 caracteres, 1 maiúscula, 1 número, 1 especial)
- Telefone (formato internacional, validação)
- Nome da empresa (opcional para FREE, obrigatório para BUSINESS/ENTERPRISE)
- CNPJ/CPF (opcional para FREE, obrigatório para BUSINESS/ENTERPRISE)

**Processo:**
1. Usuário preenche formulário de registro
2. Sistema valida dados em tempo real
3. Email de confirmação é enviado (verificação opcional no MVP)
4. Usuário é criado com plano FREE por padrão
5. Usuário recebe 100 créditos de boas-vindas
6. Redirecionamento para dashboard

**Validações:**
- Email único no sistema (mensagem: "Este email já está cadastrado")
- Senha forte (indicador visual de força da senha)
- Telefone válido (formato: +55 11 99999-9999)
- CNPJ válido (validação de dígitos verificadores)

### 3.2 Login
**Campos:**
- Email
- Senha
- Checkbox "Lembrar-me" (manter sessão por 30 dias)

**Processo:**
1. Usuário insere credenciais
2. Sistema valida e gera JWT access token (1 hora) e refresh token (7 dias)
3. Tokens armazenados em httpOnly cookies
4. Redirecionamento para dashboard
5. Middleware verifica token em todas as rotas protegidas

**Mensagens de Erro:**
- "Email ou senha incorretos" (não especificar qual está errado por segurança)
- "Conta não verificada. Verifique seu email" (se implementar verificação)
- "Sua conta está suspensa. Entre em contato com o suporte"

### 3.3 Recuperação de Senha
**Fluxo:**
1. Usuário clica em "Esqueci minha senha"
2. Insere email
3. Sistema envia email com link válido por 1 hora
4. Link contém token único
5. Usuário define nova senha
6. Todas as sessões anteriores são invalidadas

### 3.4 Perfil do Usuário
**Informações Editáveis:**
- Nome completo
- Telefone
- Nome da empresa
- CNPJ/CPJ
- Foto de perfil (upload, máx 2MB, formatos: jpg, png)
- Alterar senha (requer senha atual)

**Informações Somente Leitura:**
- Email (não pode ser alterado, por questões de segurança)
- Data de criação da conta
- Plano atual
- Créditos disponíveis

---

## 4. SISTEMA DE PLANOS E BILLING

### 4.1 Estrutura de Planos

#### **PLANO FREE**
**Preço:** R$ 0/mês
**Limites:**
- 1 chip simultâneo
- 500 mensagens/mês (500 créditos)
- 1 campanha ativa por vez
- 100 contatos por lista
- Sem suporte prioritário
- Retenção de dados: 30 dias
- Intervalo mínimo entre mensagens: 10 segundos
- Sem agendamento de campanhas
- Sem API access

**Chips:**
- Maturador de chips: NÃO disponível
- Rotação automática: NÃO disponível

#### **PLANO BUSINESS**
**Preço:** R$ 97/mês
**Limites:**
- Até 3 chips simultâneos
- 5.000 mensagens/mês (5.000 créditos inclusos)
- Campanhas ilimitadas
- 10.000 contatos por lista
- Suporte por email (resposta em até 24h)
- Retenção de dados: 90 dias
- Intervalo mínimo entre mensagens: 5 segundos
- Agendamento de campanhas
- Estatísticas avançadas
- Exportação de relatórios (CSV/PDF)
- Sem API access

**Chips:**
- Maturador de chips: DISPONÍVEL
- Rotação automática: DISPONÍVEL
- Configuração de aquecimento personalizada

#### **PLANO ENTERPRISE**
**Preço:** R$ 297/mês
**Limites:**
- Até 10 chips simultâneos (expansível sob consulta)
- 20.000 mensagens/mês (20.000 créditos inclusos)
- Campanhas ilimitadas
- Contatos ilimitados por lista
- Suporte prioritário por WhatsApp/Telegram (resposta em até 2h)
- Retenção de dados: ilimitada
- Intervalo mínimo entre mensagens: 3 segundos
- Agendamento avançado (múltiplos horários, fusos)
- Estatísticas em tempo real e analytics avançado
- Exportação de relatórios personalizados
- API access completa (REST API com rate limit de 1000 req/hora)
- Webhooks para eventos
- Multi-usuário (até 5 usuários na conta)
- White-label (sob consulta)

**Chips:**
- Maturador de chips: DISPONÍVEL com IA
- Rotação automática inteligente
- Análise de saúde do chip
- Alertas de possível banimento
- Backup automático de sessões

### 4.2 Sistema de Créditos

**Custo por Mensagem:**
- 1 crédito = 1 mensagem enviada com sucesso
- Mensagens falhadas NÃO consomem créditos
- Créditos inclusos no plano são resetados mensalmente
- Créditos comprados avulsos NÃO expiram

**Compra Avulsa de Créditos:**
- 1.000 créditos = R$ 30 (R$ 0,03/msg)
- 5.000 créditos = R$ 120 (R$ 0,024/msg) - economia de 20%
- 10.000 créditos = R$ 200 (R$ 0,02/msg) - economia de 33%
- 50.000 créditos = R$ 750 (R$ 0,015/msg) - economia de 50%

**Lógica de Consumo:**
1. Sistema usa primeiro os créditos inclusos no plano
2. Depois usa créditos comprados (FIFO - primeiro que entra, primeiro que sai)
3. Quando créditos acabam, campanhas são pausadas automaticamente
4. Usuário recebe notificação quando restam 10% dos créditos

### 4.3 Billing e Pagamentos

**Métodos de Pagamento:**
- Cartão de crédito (recorrente via Stripe/Mercado Pago)
- PIX (para compra de créditos avulsos)
- Boleto bancário (compra de créditos avulsos, 3 dias úteis)

**Ciclo de Faturamento:**
- Cobrança mensal na data de contratação
- Renovação automática
- 3 tentativas de cobrança em caso de falha
- Após 3 falhas: conta suspensa (acesso somente leitura)
- Downgrade automático para FREE após 7 dias de suspensão

**Upgrade/Downgrade:**
- **Upgrade**: imediato, cobrança proporcional (pro-rata)
- **Downgrade**: na próxima renovação, sem reembolso
- Créditos não utilizados permanecem disponíveis

**Notas Fiscais:**
- Geradas automaticamente após cada pagamento
- Enviadas por email
- Disponíveis para download no painel

---

## 5. GERENCIAMENTO DE CHIPS

### 5.1 Conexão de Chips

**Processo de Conexão:**
1. Usuário clica em "Adicionar Chip"
2. Sistema verifica limite do plano
3. Se dentro do limite, gera nova sessão no Baileys
4. QR Code é exibido em tempo real via WebSocket
5. QR Code atualiza automaticamente a cada 60 segundos
6. Usuário escaneia QR Code com WhatsApp
7. Após autenticação, chip fica "Conectado"
8. Sistema salva credenciais de sessão criptografadas

**Estados do Chip:**
- **Aguardando QR** (amarelo): aguardando escaneamento
- **Conectando** (azul): autenticando com WhatsApp
- **Conectado** (verde): operacional, pronto para enviar mensagens
- **Desconectado** (vermelho): perdeu conexão, necessita reconexão
- **Em Maturação** (laranja): chip novo em processo de aquecimento
- **Banido** (preto): chip foi banido pelo WhatsApp, inoperante
- **Manutenção** (cinza): pausado manualmente pelo usuário

**Informações do Chip:**
- Apelido (editável pelo usuário, ex: "Chip Vendas", "Chip Suporte")
- Número do WhatsApp (exibido após conexão)
- Status atual
- Data/hora da conexão
- Mensagens enviadas hoje
- Mensagens enviadas no mês
- Taxa de sucesso (%)
- Tempo de maturação (se aplicável)
- Histórico de eventos (últimas 50 ações)

**Ações Disponíveis:**
- **Reconectar**: gera novo QR code se desconectado
- **Pausar/Retomar**: pausa temporária sem desconectar
- **Desconectar**: remove sessão do Baileys
- **Excluir**: remove chip permanentemente (requer confirmação)
- **Ver Detalhes**: modal com estatísticas completas
- **Testar**: enviar mensagem de teste para o próprio número

### 5.2 Maturador de Chips (BUSINESS/ENTERPRISE)

**Objetivo:**
Simular comportamento humano natural em chips novos para evitar banimentos precoces, aquecendo gradualmente o número antes de uso em massa.

**Estratégia de Aquecimento:**

**Fase 1 - Dia 1-3: Validação Inicial**
- 5-10 mensagens/dia
- Apenas para contatos salvos (agenda do chip)
- Intervalo: 2-5 horas entre mensagens
- Mensagens curtas e naturais (30-100 caracteres)
- Variação de horários (manhã, tarde, noite)

**Fase 2 - Dia 4-7: Aumento Gradual**
- 20-30 mensagens/dia
- Contatos salvos + números verificados
- Intervalo: 30-60 minutos entre mensagens
- Mensagens de tamanho variado
- Simular conversas (enviar, aguardar, responder)

**Fase 3 - Dia 8-14: Consolidação**
- 50-80 mensagens/dia
- Qualquer número válido
- Intervalo: 15-30 minutos entre mensagens
- Introduzir mídias (ocasionalmente)
- Padrões de uso realistas

**Fase 4 - Dia 15+: Produção**
- 100-200 mensagens/dia (conforme plano)
- Uso normal da plataforma
- Intervalo mínimo configurável
- Chip "maduro" e seguro

**Configurações Personalizáveis (ENTERPRISE):**
- Duração de cada fase
- Quantidade de mensagens por fase
- Intervalos entre mensagens
- Tipos de conteúdo permitidos por fase
- Números de teste para aquecimento (lista fornecida pelo usuário)

**Automação:**
- Sistema envia mensagens automaticamente durante maturação
- Templates de mensagens naturais pré-definidos
- Variação automática de conteúdo
- Relatório diário de progresso da maturação
- Alertas se comportamento anormal detectado

**Banco de Mensagens para Maturação:**
```
- "Oi! Tudo bem?"
- "Bom dia! Como você está?"
- "Opa, tudo certo?"
- "E aí, beleza?"
- "Olá! Espero que esteja bem."
- "Oi! Podemos conversar?"
- "Bom dia! Vamos marcar aquele café?"
- (+ 100 variações naturais)
```

**Indicadores de Saúde (ENTERPRISE):**
- Score de saúde do chip (0-100)
- Probabilidade de banimento (baixa/média/alta)
- Recomendações automáticas (reduzir volume, pausar, etc)

### 5.3 Rotação Automática de Chips (BUSINESS/ENTERPRISE)

**Objetivo:**
Distribuir envios entre múltiplos chips para reduzir risco de banimento e aumentar throughput.

**Estratégias de Rotação:**

**1. Round Robin (Padrão)**
- Chips são usados em sequência circular
- Chip 1 → Chip 2 → Chip 3 → Chip 1...
- Distribuição equilibrada de carga

**2. Baseada em Saúde (ENTERPRISE)**
- Chips com melhor score recebem mais mensagens
- Chips com score baixo entram em modo de recuperação
- Rebalanceamento automático

**3. Baseada em Horário**
- Chips específicos para horários específicos
- Ex: Chip 1 (manhã), Chip 2 (tarde), Chip 3 (noite)
- Configurável pelo usuário

**4. Aleatória Ponderada**
- Seleção aleatória com peso baseado em performance
- Reduz padrões detectáveis
- Maior naturalidade

**Configurações:**
- Estratégia de rotação (dropdown)
- Intervalo entre trocas de chip (1-60 minutos)
- Máximo de mensagens por chip antes de rotação (10-1000)
- Chips prioritários (ordem de preferência)
- Pausar chip automaticamente se taxa de falha > 10%

---

## 6. SISTEMA DE CAMPANHAS

### 6.1 Criação de Campanha

**Informações Básicas:**
- Nome da campanha (obrigatório, 3-100 caracteres)
- Descrição (opcional, até 500 caracteres)
- Tipo de campanha:
  - **Simples**: mesma mensagem para todos
  - **Personalizada**: mensagens com variáveis (nome, empresa, etc)
  - **A/B Test** (ENTERPRISE): 2 variações de mensagem para teste

**Upload de Contatos:**

**Formatos Aceitos:**
- CSV (.csv)
- TXT (.txt, um número por linha)
- Excel (.xlsx)

**Estrutura CSV Esperada:**
```csv
numero,nome,empresa,variavel1,variavel2
5511999999999,João Silva,Empresa X,valor1,valor2
5511988888888,Maria Santos,Empresa Y,valor3,valor4
```

**Validações:**
- Coluna "numero" é obrigatória
- Números devem estar no formato internacional (5511999999999)
- Números duplicados são removidos automaticamente
- Números inválidos são listados para correção
- Sistema remove automaticamente: espaços, hífens, parênteses
- Preview dos primeiros 10 contatos antes de confirmar
- Contagem total de contatos válidos

**Limites por Plano:**
- FREE: 100 contatos por lista
- BUSINESS: 10.000 contatos por lista
- ENTERPRISE: ilimitado

### 6.2 Composição da Mensagem

**Editor de Mensagem:**
- Campo de texto com contador de caracteres (0/4096)
- Preview em tempo real (simulando bubble do WhatsApp)
- Botões de formatação: **negrito**, _itálico_, ~riscado~, `monoespaçado`
- Inserir emoji (seletor de emojis)
- Variáveis dinâmicas (dropdown): {{nome}}, {{empresa}}, {{variavel1}}...

**Validações:**
- Mensagem não pode estar vazia
- Avisar se usar variáveis sem colunas correspondentes no CSV
- Máximo 4096 caracteres por mensagem
- Detectar palavras sensíveis (spam, golpe, etc) e avisar usuário

**Exemplos de Uso de Variáveis:**
```
Olá {{nome}}, tudo bem?

Somos da {{empresa}} e temos uma proposta especial para você!
```

**Mídia (BUSINESS/ENTERPRISE):**
- Upload de imagem (jpg, png, max 5MB)
- Upload de arquivo (pdf, doc, xls, max 10MB)
- Upload de áudio (mp3, ogg, max 5MB)
- Upload de vídeo (mp4, max 16MB - limitação do WhatsApp)
- Preview da mídia antes de enviar
- Legenda opcional para mídia (até 1024 caracteres)

### 6.3 Configurações de Envio

**Configurações Básicas:**
- **Chips a usar**: checkboxes para selecionar chips (respeitando limite do plano)
- **Intervalo entre mensagens**: slider (3-60 segundos)
  - FREE: mínimo 10s
  - BUSINESS: mínimo 5s
  - ENTERPRISE: mínimo 3s
- **Horário de envio**:
  - Enviar imediatamente
  - Agendar para data/hora específica (BUSINESS/ENTERPRISE)
  - Enviar em janela de horário (ex: 09:00-18:00)

**Configurações Avançadas (BUSINESS/ENTERPRISE):**
- **Randomização de intervalo**: adicionar variação aleatória (±20%)
- **Pausar automaticamente se taxa de erro > X%** (configurável)
- **Retry automático**: tentar reenviar mensagens falhadas (1-3 tentativas)
- **Intervalo entre retries**: 30s, 1min, 5min, 15min, 30min, 1h
- **Parar campanha se créditos acabarem**: sim/não
- **Notificar quando campanha terminar**: email/push

**Agendamento Múltiplo (ENTERPRISE):**
- Configurar múltiplos horários de envio
- Ex: 09:00, 14:00, 18:00 (divide lista em 3 partes)
- Configurar dias da semana específicos
- Respeitar fusos horários diferentes

### 6.4 Preview e Confirmação

**Tela de Confirmação:**
- **Resumo da Campanha:**
  - Nome
  - Total de contatos válidos
  - Créditos necessários (1 por contato)
  - Créditos disponíveis atuais
  - Chips selecionados
  - Intervalo configurado
  - Tempo estimado de conclusão
  
- **Preview da Mensagem:**
  - Exemplo com dados reais do primeiro contato
  - Preview visual simulando WhatsApp

- **Avisos:**
  - "Esta campanha consumirá X créditos. Você tem Y créditos disponíveis."
  - "Tempo estimado: Z horas"
  - "Certifique-se de que os chips permanecerão conectados durante o envio"

**Botões:**
- **Voltar e Editar**: retorna para edição
- **Salvar como Rascunho**: salva sem iniciar
- **Iniciar Campanha**: inicia envio imediatamente (ou agenda)

### 6.5 Gerenciamento de Campanhas

**Lista de Campanhas:**
- Tabela com colunas:
  - Nome da campanha
  - Status (Rascunho, Agendada, Em andamento, Pausada, Concluída, Cancelada)
  - Progresso (barra: X/Y enviadas)
  - Taxa de sucesso (%)
  - Data de criação
  - Data de início/conclusão
  - Ações

**Status Possíveis:**
- **Rascunho** (cinza): salva, não iniciada
- **Agendada** (azul): aguardando data/hora configurada
- **Em Andamento** (verde animado): enviando mensagens
- **Pausada** (laranja): temporariamente pausada
- **Concluída** (verde): todas mensagens enviadas
- **Cancelada** (vermelho): interrompida pelo usuário
- **Erro** (vermelho): interrompida por erro crítico

**Ações Disponíveis:**
- **Ver Detalhes**: modal com estatísticas completas
- **Pausar/Retomar**: pausa temporária do envio
- **Cancelar**: interrompe definitivamente (requer confirmação)
- **Duplicar**: cria cópia para nova campanha
- **Exportar Relatório**: baixa CSV/PDF com resultados
- **Excluir**: remove campanha (apenas se rascunho/concluída)

**Filtros:**
- Por status
- Por data (hoje, últimos 7 dias, últimos 30 dias, personalizado)
- Por chip utilizado
- Busca por nome

---

## 7. MONITORAMENTO E RELATÓRIOS

### 7.1 Dashboard Principal

**Cards de Resumo (KPIs):**
- **Créditos Disponíveis**: número grande + barra de progresso + botão "Comprar Créditos"
- **Mensagens Enviadas Hoje**: número + comparação com ontem (% +/-)
- **Mensagens Enviadas no Mês**: número + comparação com mês anterior
- **Taxa de Sucesso Geral**: porcentagem + gráfico sparkline
- **Chips Conectados**: X/Y + indicador visual (verde/vermelho)
- **Campanhas Ativas**: número + botão "Ver Todas"

**Gráficos:**
1. **Mensagens por Dia (últimos 30 dias)**:
   - Gráfico de linha
   - Mostrar: enviadas, entregues, falhadas
   - Filtro: todos os chips, chip específico

2. **Distribuição de Status (Hoje)**:
   - Gráfico de pizza
   - Categorias: Enviadas, Entregues, Lidas, Falhadas

3. **Performance por Chip**:
   - Gráfico de barras horizontal
   - Métricas: mensagens enviadas, taxa de sucesso
   - Comparação entre chips

**Atividade Recente:**
- Lista das últimas 20 ações:
  - Mensagem enviada para +55119999999 via Chip 1 - há 2 minutos
  - Campanha "Black Friday" concluída - há 15 minutos
  - Chip 2 desconectado - há 1 hora
  - Compra de 1.000 créditos processada - há 3 horas
- Atualização em tempo real (WebSocket)

### 7.2 Detalhes da Campanha

**Estatísticas Gerais:**
- Total de contatos
- Mensagens enviadas
- Mensagens entregues (✓)
- Mensagens lidas (✓✓)
- Mensagens falhadas (❌)
- Taxa de sucesso (%)
- Taxa de abertura (%) - apenas mensagens lidas
- Duração total
- Créditos consumidos

**Timeline de Envio:**
- Gráfico de linha temporal mostrando velocidade de envio
- Eixo X: tempo (horas/minutos)
- Eixo Y: mensagens enviadas
- Marcadores de eventos (pausas, erros, retomadas)

**Distribuição por Chip:**
- Tabela mostrando contribuição de cada chip:
  - Nome do chip
  - Mensagens enviadas
  - Taxa de sucesso
  - Tempo médio de entrega

**Lista Detalhada de Mensagens:**
- Tabela paginada (50 por página):
  - Número destinatário (mascarado: +5511999***999)
  - Status (ícone: ⏳ enviando, ✓ entregue, ✓✓ lida, ❌ falhou)
  - Chip usado
  - Data/hora de envio
  - Tempo de entrega
  - Motivo da falha (se aplicável)
- Filtros: por status, por chip, por data
- Busca por número
- Exportar para CSV/Excel

**Motivos de Falha Comuns:**
- Número inválido
- Número não registrado no WhatsApp
- Bloqueado pelo destinatário
- Chip desconectado durante envio
- Timeout de rede
- Banimento detectado
- Erro desconhecido

### 7.3 Relatórios (BUSINESS/ENTERPRISE)

**Tipos de Relatório:**
1. **Relatório de Campanha**:
   - Todas as métricas da campanha
   - Gráficos de performance
   - Lista completa de mensagens

2. **Relatório de Chips**:
   - Performance de cada chip em período
   - Comparativo entre chips
   - Recomendações de uso

3. **Relatório Financeiro**:
   - Créditos consumidos
   - Créditos comprados
   - ROI por campanha (se configurado)
   - Projeção de gastos

4. **Relatório Executivo** (ENTERPRISE):
   - Resumo geral do período
   - Principais KPIs
   - Tendências e insights
   - Recomendações estratégicas

**Formatos de Exportação:**
- PDF (formatado, com gráficos)
- CSV (dados brutos)
- Excel (formatado, múltiplas abas)
- JSON (API - ENTERPRISE)

**Agendamento de Relatórios (ENTERPRISE):**
- Enviar relatório automático por email
- Frequência: diária, semanal, mensal
- Tipos de relatório selecionáveis
- Destinatários (múltiplos emails)

---

## 8. SISTEMA DE NOTIFICAÇÕES

### 8.1 Notificações In-App

**Tipos de Notificação:**
- 🔔 Info (azul): informações gerais
- ✅ Sucesso (verde): ações concluídas com sucesso
- ⚠️ Aviso (amarelo): atenção necessária
- ❌ Erro (vermelho): erros críticos

**Eventos que Geram Notificações:**
- Campanha concluída
- Chip desconectado
- Créditos acabando (10%, 5%, 0%)
- Pagamento processado/falhou
- Novo recurso disponível
- Manutenção programada
- Chip possivelmente banido
- Taxa de falha alta em campanha

**Interface:**
- Ícone de sino no header com badge (contador de não lidas)
- Dropdown com últimas 10 notificações
- Marcar como lida individualmente
- Marcar todas como lidas
- Ver todas (página dedicada)
- Auto-dismiss após 5 segundos (exceto erros)

### 8.2 Notificações por Email

**Eventos:**
- Bem-vindo à WHAGO (após registro)
- Confirmação de email (se implementado)
- Campanha concluída (resumo de resultados)
- Créditos esgotados
- Pagamento processado com sucesso
- Falha no pagamento (tentativa de cobrança)
- Upgrade/downgrade de plano confirmado
- Nota fiscal disponível
- Relatório agendado (ENTERPRISE)

**Configurações:**
- Usuário pode ativar/desativar cada tipo
- Frequência de resumos (instantâneo, diário, semanal)

### 8.3 Webhooks (ENTERPRISE)

**Eventos Disponíveis:**
- `campaign.started`: campanha iniciada
- `campaign.completed`: campanha concluída
- `campaign.paused`: campanha pausada
- `campaign.cancelled`: campanha cancelada
- `message.sent`: mensagem enviada
- `message.delivered`: mensagem entregue
- `message.read`: mensagem lida
- `message.failed`: mensagem falhou
- `chip.connected`: chip conectado
- `chip.disconnected`: chip desconectado
- `credits.low`: créditos abaixo de threshold
- `payment.succeeded`: pagamento processado

**Configuração:**
- URL do webhook
- Secret para validação (HMAC)
- Eventos a receber (checkboxes)
- Teste de webhook (enviar evento fake)
- Logs de webhooks enviados (últimos 100)

**Payload Exemplo:**
```json
{
  "event": "campaign.completed",
  "timestamp": "2025-11-08T15:30:00Z",
  "data": {
    "campaign_id": "123",
    "campaign_name": "Black Friday",
    "total_messages": 1000,
    "successful": 987,
    "failed": 13,
    "duration_seconds": 3600
  }
}
```

---

## 9. API REST (ENTERPRISE)

### 9.1 Autenticação
- API Key gerada no painel
- Header: `Authorization: Bearer {api_key}`
- Rate limit: 1000 requisições/hora

### 9.2 Endpoints Principais

**Chips:**
- `GET /api/v1/chips` - listar chips
- `GET /api/v1/chips/{id}` - detalhes do chip
- `POST /api/v1/chips` - adicionar chip (retorna QR)
- `DELETE /api/v1/chips/{id}` - remover chip
- `POST /api/v1/chips/{id}/disconnect` - desconectar chip

**Campanhas:**
- `GET /api/v1/campaigns` - listar campanhas
- `GET /api/v1/campaigns/{id}` - detalhes da campanha
- `POST /api/v1/campaigns` - criar campanha
- `POST /api/v1/campaigns/{id}/start` - iniciar campanha
- `POST /api/v1/campaigns/{id}/pause` - pausar campanha
- `POST /api/v1/campaigns/{id}/cancel` - cancelar campanha
- `DELETE /api/v1/campaigns/{id}` - excluir campanha (apenas rascunhos)

**Mensagens:**
- `POST /api/v1/messages/send` - enviar mensagem única
- `GET /api/v1/messages/{id}` - status da mensagem

**Contatos:**
- `POST /api/v1/contacts/validate` - validar lista de números
- `POST /api/v1/contacts/upload` - upload de lista (CSV)

**Usuário:**
- `GET /api/v1/user/profile` - perfil do usuário
- `GET /api/v1/user/credits` - saldo de créditos
- `GET /api/v1/user/usage` - uso mensal

**Relatórios:**
- `GET /api/v1/reports/campaigns/{id}` - relatório de campanha
- `GET /api/v1/reports/chips/{id}` - relatório de chip
- `GET /api/v1/reports/usage` - relatório de uso

### 9.3 Documentação
- Swagger UI automática em `/api/docs`
- Exemplos de código em múltiplas linguagens
- Webhooks documentados
- Rate limits explicados

---

## 10. INTERFACE DO USUÁRIO (UI/UX)

### 10.1 Design System

**Cores Principais:**
- Primary: #10B981 (Verde - sucesso, ações principais)
- Secondary: #3B82F6 (Azul - informações, links)
- Accent: #8B5CF6 (Roxo - destaque, premium)
- Warning: #F59E0B (Amarelo - avisos)
- Danger: #EF4444 (Vermelho - erros, ações destrutivas)
- Success: #10B981 (Verde - confirmações)
- Gray Scale: #F9FAFB, #E5E7EB, #6B7280, #1F2937

**Tipografia:**
- Font: Inter (Google Fonts)
- Tamanhos:
  - Títulos principais (h1): 32px, bold
  - Títulos secundários (h2): 24px, semibold
  - Títulos terciários (h3): 20px, semibold
  - Corpo: 16px, regular
  - Small: 14px, regular
  - Caption: 12px, regular

**Espaçamento:**
- Sistema de espaçamento: 4px base (múltiplos de 4)
- Padding de cards: 24px
- Gap entre elementos: 16px
- Margin entre seções: 32px

**Componentes:**
- Botões: rounded-lg, padding 12px 24px, font-medium
  - Primary: bg-primary, text-white
  - Secondary: bg-white, border-gray-300, text-gray-700
  - Danger: bg-red-500, text-white
- Cards: bg-white, rounded-xl, shadow-sm, border-gray-200
- Inputs: border-gray-300, focus:border-primary, rounded-lg
- Badges: rounded-full, px-3 py-1, text-xs font-medium
- Modals: backdrop blur, centered, max-width 600px

### 10.2 Layout

**Estrutura:**
```
┌──────────────────────────────────────────┐
│  Header (Fixo)                           │
├───────┬──────────────────────────────────┤
│       │                                  │
│  Sidebar│     Conteúdo Principal        │
│ (Fixo) │                                 │
│       │                                  │
│       │                                  │
└───────┴──────────────────────────────────┘
```

**Header (altura: 64px):**
- Logo WHAGO (esquerda)
- Barra de pesquisa global (centro) - BUSINESS/ENTERPRISE
- Notificações (ícone sino + badge)
- Créditos disponíveis (badge verde)
- Menu do usuário (avatar + dropdown)

**Sidebar (largura: 260px):**
- Navegação principal:
  - 📊 Dashboard
  - 📱 Chips
  - 📢 Campanhas
  - 💬 Mensagens (log)
  - 📈 Relatórios (BUSINESS/ENTERPRISE)
  - 💳 Billing & Créditos
  - ⚙️ Configurações
  - 🔑 API (ENTERPRISE)
  - ❓ Ajuda & Suporte

- Footer da sidebar:
  - Badge do plano atual (FREE/BUSINESS/ENTERPRISE)
  - Botão "Fazer Upgrade" (se não ENTERPRISE)

**Responsividade:**
- Desktop (>1024px): layout completo
- Tablet (768-1024px): sidebar colapsável
- Mobile (<768px): sidebar vira drawer, header simplificado

### 10.3 Fluxos de Tela

**Tela: Login**
- Formulário centralizado
- Logo no topo
- Campos: Email, Senha
- Checkbox "Lembrar-me"
- Link "Esqueci minha senha"
- Botão "Entrar"
- Link "Criar conta" no rodapé

**Tela: Registro**
- Formulário em etapas (wizard):
  - Etapa 1: Dados pessoais (nome, email, senha, telefone)
  - Etapa 2: Dados da empresa (nome, CNPJ - opcional)
  - Etapa 3: Confirmação e termos
- Indicador de progresso (1 de 3, 2 de 3, 3 de 3)
- Botões "Voltar" e "Próximo"
- Validação em tempo real

**Tela: Dashboard**
- Grid de cards KPI (4 colunas)
- Gráficos (2 colunas)
- Tabela de atividades recentes
- CTA: "Criar Nova Campanha" (botão destacado)

**Tela: Chips**
- Botão "Adicionar Chip" (topo direita)
- Grid de cards de chips (3 colunas)
- Cada card mostra:
  - Status (badge colorido)
  - Apelido
  - Número (se conectado)
  - Estatísticas rápidas
  - Botões de ação
- Filtro por status (tabs: Todos, Conectados, Desconectados)

**Tela: Criar Campanha**
- Wizard com 4 etapas:
  1. Informações básicas
  2. Upload de contatos
  3. Composição da mensagem
  4. Configurações e confirmação
- Barra de progresso
- Botão "Salvar como Rascunho" sempre visível
- Preview fixo do lado direito (desktop)

**Tela: Campanhas**
- Filtros e busca no topo
- Tabela com colunas:
  - Nome
  - Status (badge)
  - Progresso (barra)
  - Taxa de sucesso
  - Data
  - Ações (ícones)
- Paginação no rodapé
- Botão "Nova Campanha" destacado

**Tela: Detalhes da Campanha**
- Header com nome e status
- Tabs:
  - Visão Geral (estatísticas e gráficos)
  - Mensagens (tabela detalhada)
  - Configurações (leitura)
- Botões de ação contextuais (pausar, cancelar, duplicar)

**Tela: Billing & Créditos**
- Card de plano atual (destaque)
- Comparativo de planos (tabela)
- Histórico de compras de créditos
- Notas fiscais (lista para download)
- Pacotes de créditos disponíveis para compra

**Tela: Configurações**
- Tabs:
  - Perfil (editar informações)
  - Segurança (alterar senha, 2FA - futuro)
  - Notificações (checkboxes de preferências)
  - Webhooks (ENTERPRISE)
  - API Keys (ENTERPRISE)
  - Perigos (excluir conta)

### 10.4 Estados e Feedbacks

**Loading States:**
- Skeleton loaders para tabelas e cards
- Spinners para ações (botões)
- Barra de progresso para uploads
- "Carregando..." com animação

**Empty States:**
- Ilustração + texto explicativo + CTA
- Ex: "Nenhum chip conectado ainda. Adicione seu primeiro chip para começar!"

**Error States:**
- Mensagem clara do erro
- Sugestão de ação
- Botão "Tentar Novamente"

**Success States:**
- Toast verde no canto superior direito
- Ícone de check
- Auto-dismiss após 3 segundos

**Confirmações:**
- Modal para ações destrutivas
- Texto claro do que será feito
- Botões "Cancelar" e "Confirmar"
- Botão de confirmar requer digitação de palavra-chave para ações críticas

---

## 11. SEGURANÇA E COMPLIANCE

### 11.1 Segurança de Dados

**Criptografia:**
- Senhas: bcrypt com salt (custo 12)
- Tokens JWT: HS256, chave secreta forte
- Credenciais de sessão Baileys: AES-256
- Comunicação: HTTPS obrigatório (TLS 1.2+)

**Proteções:**
- Rate limiting: 100 req/min por IP (login: 5 tentativas/15min)
- CORS configurado restritivamente
- Headers de segurança (Helmet.js / Secure-py)
- SQL Injection: uso de ORM (SQLAlchemy) com prepared statements
- XSS: sanitização de inputs, CSP headers
- CSRF: tokens em formulários

**Logs de Auditoria:**
- Todas as ações sensíveis são logadas:
  - Login/logout
  - Alteração de senha
  - Conexão/desconexão de chips
  - Criação/exclusão de campanhas
  - Compras e pagamentos
  - Acessos à API
- Retenção: 1 ano (ENTERPRISE: ilimitado)

### 11.2 LGPD e Privacidade

**Dados Coletados:**
- Dados cadastrais (nome, email, telefone, CNPJ)
- Listas de contatos (números de WhatsApp)
- Logs de mensagens (metadados, não conteúdo)
- Dados de uso (campanhas, créditos)

**Direitos do Usuário:**
- Acessar seus dados (exportação em JSON)
- Corrigir dados (perfil editável)
- Deletar conta (processo de 7 dias com confirmação)
- Portabilidade (exportar tudo em formato padrão)

**Política de Retenção:**
- Dados de campanhas:
  - FREE: 30 dias
  - BUSINESS: 90 dias
  - ENTERPRISE: ilimitado
- Dados cadastrais: enquanto conta ativa
- Após exclusão de conta: 30 dias para possível recuperação, depois deletados permanentemente

**Cookies:**
- Essenciais: autenticação (JWT)
- Funcionais: preferências de idioma, tema
- Analytics: Google Analytics (opcional, opt-in)
- Banner de consentimento (LGPD/GDPR)

### 11.3 Termos e Políticas

**Documentos Legais:**
- Termos de Uso
- Política de Privacidade
- Política de Reembolso
- SLA (ENTERPRISE)

**Uso Aceitável:**
- Proibido: spam, fraude, conteúdo ilegal, pornografia, discurso de ódio
- Monitoramento: sistema detecta palavras-chave sensíveis e pode suspender contas
- Punições: aviso, suspensão temporária, banimento permanente

---

## 12. INFRAESTRUTURA E DEPLOYMENT

### 12.1 Requisitos de Servidor

**Ambiente de Desenvolvimento:**
- Docker + Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL 15
- Redis 7

**Ambiente de Produção:**
- Servidor VPS/Cloud (AWS, Azure, GCP, DigitalOcean)
- Mínimo: 4 vCPUs, 8GB RAM, 100GB SSD
- Recomendado (100+ usuários): 8 vCPUs, 16GB RAM, 250GB SSD
- Sistema Operacional: Ubuntu 22.04 LTS

### 12.2 Arquitetura de Deployment

**Componentes:**
1. **Nginx** (Reverse Proxy + Load Balancer)
2. **FastAPI Backend** (múltiplas instâncias via Gunicorn)
3. **Node.js Baileys Service** (múltiplas instâncias via PM2)
4. **PostgreSQL** (replicação master-slave)
5. **Redis** (cache + broker Celery)
6. **Celery Workers** (processamento assíncrono)

**Escalabilidade:**
- Horizontal: adicionar mais instâncias de backend/baileys
- Vertical: aumentar recursos de banco de dados
- Auto-scaling: baseado em CPU/memória (Kubernetes/Docker Swarm)

### 12.3 Monitoramento

**Métricas:**
- Uptime (meta: 99.9%)
- Tempo de resposta (meta: <200ms p95)
- Taxa de erro (meta: <0.1%)
- Uso de recursos (CPU, RAM, Disco)

**Ferramentas:**
- Prometheus + Grafana (métricas)
- Sentry (erros e exceções)
- LogStash/ELK (logs centralizados)
- UptimeRobot (monitoramento externo)

**Alertas:**
- Email/SMS para equipe técnica
- Eventos críticos: servidor down, banco inacessível, erro em 10% das mensagens

### 12.4 Backup e Recuperação

**Backup de Banco de Dados:**
- Diário: backup completo às 03:00 AM
- Retenção: 7 dias (diário), 4 semanas (semanal), 12 meses (mensal)
- Armazenamento: AWS S3 ou equivalente (criptografado)

**Backup de Sessões Baileys:**
- Incremental a cada 1 hora
- Retenção: 3 dias
- Crítico para não perder conexões dos chips

**Disaster Recovery:**
- RTO (Recovery Time Objective): 1 hora
- RPO (Recovery Point Objective): 24 horas
- Procedimento documentado de restore

---

## 13. ROADMAP E FUNCIONALIDADES FUTURAS

### 13.1 Fase 2 (Pós-MVP)

**Prioridade Alta:**
- Multi-idioma (PT-BR, EN, ES)
- Suporte a grupos do WhatsApp
- Agendamento recorrente de campanhas
- Templates de mensagens salvos
- Integração com Zapier/Make
- Sistema de tags para contatos
- Segmentação de listas (filtros avançados)

**Prioridade Média:**
- App mobile (React Native)
- Chatbot básico (respostas automáticas)
- Integração com CRMs (HubSpot, Pipedrive, RD Station)
- Suporte a outros canais (Telegram, Instagram)
- Teste A/B automático (vencedor continua enviando)
- Dashboard de cliente (white-label)

**Prioridade Baixa:**
- IA para otimização de mensagens
- Análise de sentimento das respostas
- Predição de melhor horário de envio
- Sistema de afiliados
- Marketplace de templates

### 13.2 Melhorias Técnicas

- Migração para microserviços (se escalar muito)
- Implementação de GraphQL (além do REST)
- WebRTC para preview de QR code mais rápido
- Machine Learning para detecção de banimento
- Kubernetes para orquestração
- Service mesh (Istio) para observabilidade

---

## 14. SUPORTE E ONBOARDING

### 14.1 Onboarding de Novos Usuários

**Primeira Experiência:**
1. Após registro, tour guiado (5 passos):
   - Bem-vindo! Você ganhou 100 créditos de boas-vindas
   - Conecte seu primeiro chip
   - Crie sua primeira campanha
   - Acompanhe os resultados
   - Explore recursos avançados (BUSINESS/ENTERPRISE)

2. Vídeos tutoriais curtos (1-2 min cada):
   - Como conectar um chip
   - Como criar uma campanha
   - Como interpretar relatórios

3. Documentação:
   - FAQ completo
   - Guia de boas práticas para evitar banimentos
   - Troubleshooting comum

### 14.2 Canais de Suporte

**FREE:**
- Base de conhecimento (self-service)
- FAQ
- Email: suporte@whago.com (resposta: 48-72h)

**BUSINESS:**
- Tudo do FREE +
- Suporte por email prioritário (resposta: 24h)
- Chat ao vivo (horário comercial)

**ENTERPRISE:**
- Tudo do BUSINESS +
- Suporte por WhatsApp/Telegram (resposta: 2h)
- Gerente de conta dedicado
- Onboarding personalizado
- Sessões de treinamento

### 14.3 Recursos de Ajuda

**Centro de Ajuda:**
- Pesquisa inteligente
- Categorias: Primeiros Passos, Chips, Campanhas, Billing, Técnico
- Artigos passo-a-passo com screenshots
- Vídeos embarcados

**Comunidade (Futuro):**
- Fórum de usuários
- Compartilhamento de templates
- Casos de sucesso
- Votação de features

---

## 15. MÉTRICAS DE SUCESSO DO PRODUTO

### 15.1 KPIs de Negócio

**Aquisição:**
- Cadastros/mês (meta: crescimento de 20% MoM)
- Taxa de conversão do site (meta: 5%)
- CAC (Custo de Aquisição de Cliente) (meta: < R$ 50)

**Ativação:**
- % de usuários que conectam 1 chip em 24h (meta: 70%)
- % de usuários que criam 1 campanha em 7 dias (meta: 50%)
- Tempo até primeira mensagem enviada (meta: < 15 min)

**Retenção:**
- Taxa de churn mensal (meta: < 5%)
- DAU/MAU ratio (meta: > 30%)
- % de usuários ativos após 30 dias (meta: 60%)

**Receita:**
- MRR (Monthly Recurring Revenue) (meta: crescimento de 15% MoM)
- ARPU (Average Revenue Per User) (meta: R$ 150)
- LTV (Lifetime Value) (meta: R$ 1.800)
- Taxa de upgrade FREE → BUSINESS (meta: 10%)
- Taxa de upgrade BUSINESS → ENTERPRISE (meta: 5%)

**Produto:**
- Mensagens enviadas/mês (crescimento constante)
- Taxa de sucesso média (meta: > 95%)
- NPS (Net Promoter Score) (meta: > 50)

### 15.2 KPIs Técnicos

- Uptime (meta: 99.9%)
- Latência p95 (meta: < 200ms)
- Taxa de erro de API (meta: < 0.1%)
- Tempo de processamento de mensagens (meta: < 5s)
- Taxa de sucesso de conexão de chips (meta: > 98%)

---

## 16. CONSIDERAÇÕES FINAIS

### 16.1 Diferenciais Competitivos

1. **Maturador de Chips Inteligente**: Único no mercado a aquecer chips automaticamente
2. **Multi-chip Real**: Não é simulação, são múltiplas sessões reais do WhatsApp
3. **Rotação Inteligente**: Algoritmo preditivo de saúde dos chips
4. **Transparência**: Usuário vê exatamente o que acontece com cada mensagem
5. **Preço Justo**: Planos acessíveis sem taxas ocultas
6. **Sem Dependência de API Oficial**: Mais barato e flexível

### 16.2 Riscos e Mitigações

**Risco: Banimentos em Massa**
- Mitigação: Maturador de chips, limites de envio, educação do usuário

**Risco: Mudanças no WhatsApp**
- Mitigação: Equipe dedicada a manter Baileys atualizado, monitoramento constante

**Risco: Concorrência**
- Mitigação: Inovação constante, foco em UX, comunidade forte

**Risco: Questões Legais (Uso Indevido)**
- Mitigação: Termos de uso claros, monitoramento de palavras-chave, processo de denúncia

### 16.3 Próximos Passos para Implementação

1. ~~**Semana 1-2**: Setup de infraestrutura e banco de dados~~ ✅
2. ~~**Semana 3-4**: Desenvolvimento do sistema de autenticação e usuários~~ ✅
3. ~~**Semana 5-6**: Sistema de Planos e Billing~~ ✅
4. ~~**Semana 7-8**: Integração com Baileys e gerenciamento de chips~~ ✅
5. **Semana 9-10**: Dashboard, relatórios e billing
   - [x] Implementar serviços e rotas de campanhas (criar/listar/detalhar/start/pausar)
   - [x] Configurar fila de envio (Celery/worker) e WebSocket de acompanhamento
   - [x] Integrar disparo real com Baileys, limites por plano e monitoramento em tempo real
6. **Semana 11**: Testes, correções, ajustes de UX
7. **Semana 12**: Deploy, documentação, onboarding

**Equipe Mínima:**
- 1 Fullstack Developer (Python + Node.js + Frontend)
- 1 DevOps (infra, deployment, monitoramento)
- 1 Designer/UX (part-time, para ajustes visuais)
- 1 QA (testes manuais e automação básica)

---

## ANEXOS

### A. Estrutura de Banco de Dados (Principais Tabelas)

```sql
-- Usuários
users (
  id, email, password_hash, name, phone, company_name, 
  document, plan_id, credits, created_at, updated_at
)

-- Planos
plans (
  id, name, price, max_chips, monthly_messages, 
  features (JSONB), created_at
)

-- Chips
chips (
  id, user_id, nickname, phone_number, status, 
  session_data (encrypted), health_score, 
  messages_today, messages_month, created_at, updated_at
)

-- Campanhas
campaigns (
  id, user_id, name, description, status, 
  message_template, total_contacts, 
  sent_count, delivered_count, read_count, failed_count,
  settings (JSONB), created_at, started_at, completed_at
)

-- Mensagens
messages (
  id, campaign_id, chip_id, recipient_number, 
  content, status, sent_at, delivered_at, 
  read_at, failed_reason
)

-- Transações
transactions (
  id, user_id, type (purchase/subscription), 
  amount, credits, status, payment_method, 
  created_at, processed_at
)

-- Logs de auditoria
audit_logs (
  id, user_id, action, entity_type, entity_id, 
  details (JSONB), ip_address, created_at
)
```

### B. Variáveis de Ambiente (.env)

```env
# Backend
ENVIRONMENT=production
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:pass@localhost/whago
REDIS_URL=redis://localhost:6379/0

# Baileys Service
BAILEYS_API_URL=http://localhost:3000
BAILEYS_API_KEY=baileys-secret-key

# Payment Gateways
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
MERCADOPAGO_ACCESS_TOKEN=APP_USR-...

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@whago.com
SMTP_PASSWORD=your-password

# Storage
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=whago-backups

# Monitoring
SENTRY_DSN=https://...@sentry.io/...
```

---

**FIM DO PRD**
