# 📦 INSTRUÇÕES DE SETUP - WHAGO

## 🎯 Como Organizar os Arquivos

Você acabou de baixar todos os arquivos base do projeto WHAGO. Siga estas instruções para organizá-los corretamente:

### 1️⃣ Crie a Estrutura de Pastas

```bash
mkdir -p whago
cd whago
mkdir -p backend/app baileys-service/src frontend/static frontend/templates
```

### 2️⃣ Organize os Arquivos Baixados

Coloque cada arquivo no lugar correto:

```
whago/
├── prd.md                          ← Cole aqui (raiz)
├── README.md                       ← Cole aqui (raiz)
├── roadmap.md                      ← Cole aqui (raiz)
├── .gitignore                      ← Cole aqui (raiz)
├── docker-compose.yml              ← Cole aqui (raiz)
│
├── backend/
│   ├── .env.example               ← Renomeie "backend.env.example" para isto
│   ├── requirements.txt           ← Cole aqui
│   └── Dockerfile                 ← Renomeie "backend.Dockerfile" para isto
│
└── baileys-service/
    ├── .env.example               ← Renomeie "baileys.env.example" para isto
    ├── package.json               ← Cole aqui
    └── Dockerfile                 ← Renomeie "baileys.Dockerfile" para isto
```

### 3️⃣ Configurar Variáveis de Ambiente

```bash
# Backend
cd backend
cp .env.example .env
# Edite o .env com suas configurações

# Baileys
cd ../baileys-service
cp .env.example .env
# Edite o .env com suas configurações

cd ..
```

### 4️⃣ Iniciar o Projeto

#### Opção A: Docker (Recomendado para começar rápido)

```bash
# Na raiz do projeto (pasta whago/)
docker-compose up -d
```

#### Opção B: Manual (Para desenvolvimento)

**Terminal 1 - Banco de Dados:**
```bash
# PostgreSQL
docker run -d --name whago-postgres \
  -e POSTGRES_DB=whago \
  -e POSTGRES_USER=whago \
  -e POSTGRES_PASSWORD=whago123 \
  -p 5432:5432 \
  postgres:15

# Redis
docker run -d --name whago-redis \
  -p 6379:6379 \
  redis:7-alpine
```

**Terminal 2 - Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Terminal 3 - Baileys:**
```bash
cd baileys-service
npm install
npm run dev
```

### 5️⃣ Próximos Passos

Agora você tem a estrutura base. Para implementar o código:

#### No Cursor IDE:

1. Abra a pasta `whago` no Cursor
2. Abra o chat do Claude (Ctrl+L ou Cmd+L)
3. Digite:

```
@prd.md @roadmap.md 

Vamos implementar o WHAGO seguindo o PRD e o roadmap. 

Comece pela Semana 1-2: Setup e Infraestrutura.

Crie os seguintes arquivos primeiro:
1. backend/app/__init__.py
2. backend/app/main.py
3. backend/app/config.py
4. backend/app/database.py
5. baileys-service/src/index.js
6. baileys-service/src/server.js

Implemente cada arquivo completo com todas as configurações necessárias.
```

4. O Claude irá gerar o código para você!

5. Continue pedindo módulo por módulo seguindo o roadmap.

---

## 🎨 Personalizações Importantes

Antes de começar, altere nos arquivos `.env`:

### Backend (.env)
```env
SECRET_KEY=cole-uma-chave-secreta-forte-aqui-min-32-chars
JWT_SECRET_KEY=cole-outra-chave-secreta-diferente
DATABASE_URL=postgresql://whago:whago123@localhost:5432/whago
```

### Baileys (.env)
```env
API_KEY=baileys-secret-mude-para-algo-seguro
```

---

## 📚 Documentação Importante

### Arquivos de Referência

- **prd.md**: Documento completo de requisitos (leia para entender o projeto)
- **README.md**: Instruções de instalação e uso
- **roadmap.md**: Cronograma de desenvolvimento (use para acompanhar progresso)

### Links Úteis

Depois que o projeto estiver rodando:
- Frontend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Baileys: http://localhost:3000

---

## 🆘 Resolução de Problemas

### Erro: "Port already in use"
```bash
# Descobrir qual processo está usando a porta
lsof -i :8000  # ou :3000, :5432, :6379
# Matar o processo
kill -9 <PID>
```

### Erro: "Database connection refused"
```bash
# Verificar se PostgreSQL está rodando
docker ps | grep postgres
# Se não estiver, iniciar:
docker start whago-postgres
```

### Erro: "Module not found" (Python)
```bash
# Reinstalar dependências
pip install -r requirements.txt --force-reinstall
```

### Erro: "Module not found" (Node)
```bash
# Limpar cache e reinstalar
rm -rf node_modules package-lock.json
npm install
```

---

## 🎯 Checklist de Verificação

Antes de começar a desenvolver, verifique:

- [ ] Python 3.11+ instalado (`python --version`)
- [ ] Node.js 18+ instalado (`node --version`)
- [ ] Docker instalado e rodando (`docker --version`)
- [ ] Git instalado (`git --version`)
- [ ] Cursor IDE instalado
- [ ] Todos os arquivos estão nos lugares corretos
- [ ] Arquivos .env criados e configurados
- [ ] PostgreSQL e Redis rodando (se Docker: `docker ps`)

---

## 💻 Comandos Úteis

```bash
# Ver logs do Docker
docker-compose logs -f

# Parar todos os containers
docker-compose down

# Rebuild após mudanças
docker-compose up -d --build

# Entrar no container do backend
docker exec -it whago-backend bash

# Executar migrations (quando implementadas)
docker exec -it whago-backend alembic upgrade head

# Ver logs do Celery
docker-compose logs -f celery-worker
```

---

## 🚀 Fluxo de Desenvolvimento Recomendado

1. **Semana 1-2**: Setup (você está aqui! ✅)
2. **Semana 3-4**: Implemente autenticação usando o PRD como referência
3. **Semana 5-6**: Sistema de planos e billing
4. **Semana 7-8**: Integração Baileys e chips
5. **Semana 9-10**: Campanhas e envio de mensagens
6. **Semana 11-12**: Dashboard e finalização

Use o arquivo `roadmap.md` para marcar ✅ cada item conforme você completa!

---

## 📞 Precisa de Ajuda?

Se tiver dúvidas durante o desenvolvimento:

1. Consulte o **prd.md** para entender a funcionalidade
2. Use o **@prd.md** no Cursor para o Claude ter contexto completo
3. Pergunte especificamente sobre o módulo que está desenvolvendo

Exemplo:
```
@prd.md Estou implementando o sistema de autenticação. 
Crie o arquivo backend/app/models/user.py completo com todas 
as validações mencionadas no PRD.
```

---

**Boa sorte com o desenvolvimento! 🎉**

Qualquer dúvida, releia o PRD - ele tem TODOS os detalhes que você precisa!
