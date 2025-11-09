# WHAGO - Plataforma de Mensagens em Massa via WhatsApp

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Node](https://img.shields.io/badge/node-18+-green)
![License](https://img.shields.io/badge/license-MIT-blue)

## 📋 Sobre o Projeto

WHAGO é uma plataforma SaaS completa para envio de mensagens em massa via WhatsApp, com gerenciamento multi-usuário, múltiplos chips simultâneos, sistema de créditos e maturador inteligente de chips.

### 🎯 Principais Features

- ✅ Multi-usuário com 3 planos (FREE, BUSINESS, ENTERPRISE)
- ✅ Até 10 chips simultâneos (dependendo do plano)
- ✅ Sistema de créditos e billing completo
- ✅ Maturador de chips com IA (evita banimentos)
- ✅ Rotação automática inteligente de chips
- ✅ Campanhas de envio em massa com agendamento
- ✅ Dashboard e relatórios em tempo real
- ✅ API REST completa (ENTERPRISE)
- ✅ Webhooks para integração
- ✅ Interface moderna com Tailwind CSS

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────┐
│           Frontend (HTML/JS)            │
│        Tailwind CSS + Alpine.js         │
└────────────────┬────────────────────────┘
                 │ HTTP/WebSocket
┌────────────────▼────────────────────────┐
│        Backend (FastAPI/Python)         │
│    JWT Auth + REST API + WebSockets    │
└────┬────────────────────────────┬───────┘
     │                            │
     ▼                            ▼
┌────────────┐            ┌──────────────┐
│ PostgreSQL │            │ Baileys Node │
│   + Redis  │            │   WhatsApp   │
└────────────┘            └──────────────┘
```

## 🚀 Instalação Rápida

### Pré-requisitos

- Docker e Docker Compose
- Python 3.11+
- Node.js 18+
- Git

### 1. Clone o Repositório

```bash
git clone https://github.com/seu-usuario/whago.git
cd whago
```

### 2. Configure as Variáveis de Ambiente

```bash
# Backend
cp backend/.env.example backend/.env

# Baileys Service
cp baileys-service/.env.example baileys-service/.env

# Edite os arquivos .env com suas credenciais
```

### 3. Inicie com Docker Compose

```bash
docker-compose up -d
```

### 4. Acesse a Aplicação

- Frontend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Baileys Service: http://localhost:3000

## 🛠️ Instalação Manual (Desenvolvimento)

### Backend (Python/FastAPI)

```bash
cd backend

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Rodar migrações
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Baileys Service (Node.js)

```bash
cd baileys-service

# Instalar dependências
npm install

# Iniciar serviço
npm run dev
```

### Banco de Dados

```bash
# PostgreSQL
docker run -d \
  --name whago-postgres \
  -e POSTGRES_DB=whago \
  -e POSTGRES_USER=whago \
  -e POSTGRES_PASSWORD=whago123 \
  -p 5432:5432 \
  postgres:15

# Redis
docker run -d \
  --name whago-redis \
  -p 6379:6379 \
  redis:7-alpine
```

### Celery Workers (Processamento Assíncrono)

```bash
cd backend

# Worker
celery -A tasks.celery_app worker --loglevel=info

# Beat (agendador)
celery -A tasks.celery_app beat --loglevel=info
```

## 📁 Estrutura do Projeto

```
whago/
├── backend/                # Backend Python/FastAPI
│   ├── app/
│   │   ├── models/        # SQLAlchemy models
│   │   ├── routes/        # Endpoints da API
│   │   ├── services/      # Lógica de negócio
│   │   ├── schemas/       # Pydantic schemas
│   │   └── middleware/    # Middleware customizado
│   ├── tasks/             # Celery tasks
│   └── requirements.txt
│
├── baileys-service/       # Serviço Node.js/Baileys
│   ├── src/
│   │   ├── controllers/
│   │   ├── services/
│   │   └── utils/
│   └── package.json
│
├── frontend/              # Frontend HTML/JS
│   ├── templates/         # Templates Jinja2
│   └── static/
│       ├── css/
│       └── js/
│
├── docker-compose.yml
├── .gitignore
├── prd.md                 # Documento de requisitos
└── README.md              # Este arquivo
```

## 🔧 Configuração

### Variáveis de Ambiente - Backend (.env)

```env
# Aplicação
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=seu-secret-key-super-seguro-aqui
API_HOST=0.0.0.0
API_PORT=8000

# Banco de Dados
DATABASE_URL=postgresql://whago:whago123@localhost:5432/whago

# Redis
REDIS_URL=redis://localhost:6379/0

# Baileys Service
BAILEYS_API_URL=http://localhost:3000
BAILEYS_API_KEY=baileys-secret-key-change-me

# Email (opcional no MVP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@whago.com
SMTP_PASSWORD=sua-senha-smtp

# Payment Gateway (opcional no MVP)
STRIPE_SECRET_KEY=sk_test_...
MERCADOPAGO_ACCESS_TOKEN=APP_USR-...

# Storage (opcional)
AWS_ACCESS_KEY_ID=seu-access-key
AWS_SECRET_ACCESS_KEY=seu-secret-key
AWS_S3_BUCKET=whago-storage

# Monitoramento (opcional)
SENTRY_DSN=https://...@sentry.io/...
```

### Variáveis de Ambiente - Baileys (.env)

```env
# Servidor
PORT=3000
NODE_ENV=development

# API Key para autenticação
API_KEY=baileys-secret-key-change-me

# Storage
SESSIONS_PATH=./sessions

# Logs
LOG_LEVEL=info
```

## 📚 Documentação da API

Após iniciar o backend, acesse:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Exemplos de Endpoints

#### Autenticação
```bash
# Registrar usuário
POST /api/v1/auth/register
{
  "email": "user@example.com",
  "password": "SenhaForte123!",
  "name": "João Silva",
  "phone": "+5511999999999"
}

# Login
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "SenhaForte123!"
}
```

#### Chips
```bash
# Listar chips
GET /api/v1/chips
Authorization: Bearer {token}

# Adicionar chip (retorna QR Code)
POST /api/v1/chips
Authorization: Bearer {token}
{
  "nickname": "Chip Vendas"
}
```

#### Campanhas
```bash
# Criar campanha
POST /api/v1/campaigns
Authorization: Bearer {token}
{
  "name": "Black Friday 2025",
  "message": "Olá {{nome}}! Temos ofertas especiais...",
  "contacts": [
    {"numero": "5511999999999", "nome": "João"},
    {"numero": "5511988888888", "nome": "Maria"}
  ],
  "chip_ids": [1, 2],
  "interval_seconds": 10
}

# Iniciar campanha
POST /api/v1/campaigns/{id}/start
Authorization: Bearer {token}
```

## 🧪 Testes

```bash
# Backend
cd backend
pytest

# Com cobertura
pytest --cov=app --cov-report=html

# Baileys Service
cd baileys-service
npm test
```

## 🚢 Deploy

### Docker (Recomendado)

```bash
# Build das imagens
docker-compose build

# Iniciar em produção
docker-compose -f docker-compose.prod.yml up -d
```

### Manual

1. Configure servidor Ubuntu 22.04 LTS
2. Instale dependências:
   ```bash
   sudo apt update
   sudo apt install python3.11 python3-pip nodejs npm nginx postgresql redis-server
   ```
3. Clone o repositório
4. Configure Nginx como reverse proxy
5. Use Systemd para gerenciar serviços
6. Configure SSL com Let's Encrypt

## 📊 Monitoramento

- **Logs**: `/var/log/whago/`
- **Métricas**: Prometheus + Grafana
- **Erros**: Sentry (configurar DSN no .env)
- **Uptime**: UptimeRobot

## 🔒 Segurança

- ✅ Senhas hasheadas com bcrypt
- ✅ JWT tokens com refresh
- ✅ Rate limiting por IP
- ✅ HTTPS obrigatório em produção
- ✅ Validação de inputs
- ✅ CORS configurado
- ✅ Headers de segurança
- ✅ Logs de auditoria

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## 📝 Roadmap

### MVP (v1.0) - 12 semanas
- [x] Autenticação e usuários
- [ ] Sistema de planos e billing
- [ ] Integração com Baileys
- [ ] Gerenciamento de chips
- [ ] Sistema de campanhas
- [ ] Dashboard e relatórios
- [ ] Maturador de chips

### v1.1 - Melhorias
- [ ] Multi-idioma (PT, EN, ES)
- [ ] App mobile
- [ ] Suporte a grupos
- [ ] Templates salvos
- [ ] Integração Zapier/Make

### v2.0 - Avançado
- [ ] IA para otimização de mensagens
- [ ] Chatbot automático
- [ ] Integração com CRMs
- [ ] White-label
- [ ] Marketplace de templates

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 💬 Suporte

- **Email**: suporte@whago.com
- **Documentação**: https://docs.whago.com
- **Discord**: https://discord.gg/whago

## 👥 Equipe

- **Desenvolvedor Principal**: Demian
- **Arquitetura**: Claude AI (Anthropic)

## 🙏 Agradecimentos

- [Baileys](https://github.com/WhiskeySockets/Baileys) - Biblioteca WhatsApp
- [FastAPI](https://fastapi.tiangolo.com/) - Framework Python
- [Tailwind CSS](https://tailwindcss.com/) - Framework CSS
- [Alpine.js](https://alpinejs.dev/) - Framework JS

---

**⚠️ Aviso Legal**: Este software é fornecido "como está", sem garantias. O uso desta ferramenta deve respeitar os Termos de Serviço do WhatsApp. Os desenvolvedores não se responsabilizam por banimentos ou uso indevido da plataforma.
