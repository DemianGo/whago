# 📦 RESTAURAÇÃO DO BACKUP - WHAGO PRODUÇÃO

**Arquivo de Backup:** `backup_whago_production_20251118_010942.sql`  
**Data:** 18/11/2025 01:09:42  
**Tamanho:** 2.3 MB  
**Banco:** whago (PostgreSQL 15)

---

## 🚀 RESTAURAR EM PRODUÇÃO

### Opção 1: Servidor Linux (Docker)

```bash
# 1. Copiar backup para o servidor
scp backup_whago_production_20251118_010942.sql usuario@servidor:/root/

# 2. No servidor, restaurar
docker exec -i whago-postgres psql -U whago -d whago < backup_whago_production_20251118_010942.sql
```

---

### Opção 2: Servidor Linux (PostgreSQL nativo)

```bash
# 1. Copiar backup
scp backup_whago_production_20251118_010942.sql usuario@servidor:/root/

# 2. Restaurar
psql -U whago -d whago -h localhost < backup_whago_production_20251118_010942.sql
```

---

### Opção 3: Primeira instalação (criar banco novo)

```bash
# 1. Criar banco de dados
docker exec -i whago-postgres psql -U postgres -c "CREATE DATABASE whago;"
docker exec -i whago-postgres psql -U postgres -c "CREATE USER whago WITH PASSWORD 'whago123';"
docker exec -i whago-postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE whago TO whago;"

# 2. Restaurar backup
docker exec -i whago-postgres psql -U whago -d whago < backup_whago_production_20251118_010942.sql
```

---

## ⚠️ IMPORTANTE ANTES DE RESTAURAR

### 1. **Fazer backup do banco atual** (se já existe)
```bash
docker exec whago-postgres pg_dump -U whago -d whago > backup_antes_restore_$(date +%Y%m%d).sql
```

### 2. **Parar o backend** (evitar conflitos)
```bash
docker-compose stop backend celery
```

### 3. **Limpar banco atual** (opcional)
```bash
docker exec -i whago-postgres psql -U whago -d whago -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

### 4. **Restaurar**
```bash
docker exec -i whago-postgres psql -U whago -d whago < backup_whago_production_20251118_010942.sql
```

### 5. **Reiniciar serviços**
```bash
docker-compose up -d
```

---

## 📊 O QUE ESTÁ NO BACKUP

### Tabelas Incluídas:
- ✅ `users` (usuários + assinaturas)
- ✅ `plans` (planos)
- ✅ `chips` (chips/sessões)
- ✅ `proxies` (configuração de proxies)
- ✅ `campaigns` (campanhas)
- ✅ `messages` (mensagens)
- ✅ `transactions` (transações financeiras)
- ✅ `credit_ledger` (histórico de créditos)
- ✅ `payment_gateways` (gateways de pagamento)
- ✅ `api_keys` (chaves de API)
- ✅ Todas as outras tabelas do sistema

### Dados:
- ✅ Todos os usuários (incluindo `teste@teste.com` com 1M créditos)
- ✅ Todas as configurações
- ✅ Histórico completo
- ✅ Indexes e constraints
- ✅ Foreign keys

---

## 🔧 TROUBLESHOOTING

### Erro: "role whago does not exist"
```bash
docker exec -i whago-postgres psql -U postgres -c "CREATE USER whago WITH PASSWORD 'whago123' SUPERUSER;"
```

### Erro: "database whago does not exist"
```bash
docker exec -i whago-postgres psql -U postgres -c "CREATE DATABASE whago OWNER whago;"
```

### Erro: "password authentication failed"
```bash
# Verificar senha no docker-compose.yml
# POSTGRES_PASSWORD deve ser 'whago123'
```

### Verificar se restaurou corretamente
```bash
docker exec -i whago-postgres psql -U whago -d whago -c "SELECT COUNT(*) FROM users;"
docker exec -i whago-postgres psql -U whago -d whago -c "SELECT email, credits FROM users WHERE credits > 100000;"
```

---

## 🌐 CONFIGURAÇÕES PÓS-RESTAURAÇÃO

### 1. Atualizar URLs no backend
Editar `backend/.env`:
```bash
API_URL=https://seu-dominio.com
FRONTEND_URL=https://seu-dominio.com
```

### 2. Configurar Mercado Pago (Produção)
```bash
MERCADOPAGO_ACCESS_TOKEN=seu_token_producao
MERCADOPAGO_PUBLIC_KEY=sua_public_key_producao
```

### 3. Configurar Proxy DataImpulse
```bash
# Já está no banco, mas verificar se credenciais estão corretas
```

### 4. Reiniciar todos os serviços
```bash
docker-compose restart
```

---

## ✅ CHECKLIST

- [ ] Backup do banco atual (se existe)
- [ ] Parar backend e celery
- [ ] Copiar arquivo de backup para servidor
- [ ] Restaurar banco de dados
- [ ] Verificar tabelas restauradas
- [ ] Atualizar variáveis de ambiente
- [ ] Reiniciar serviços
- [ ] Testar login com `teste@teste.com`
- [ ] Verificar créditos (1.003.000)
- [ ] Testar criação de chip
- [ ] Configurar DNS (masswhatsapp.org)

---

## 📞 SUPORTE

Se tiver problemas na restauração:
1. Verificar logs: `docker logs whago-postgres`
2. Verificar logs backend: `docker logs whago-backend`
3. Verificar conexão: `docker exec whago-postgres psql -U whago -d whago -c "\dt"`

---

**Backup criado por:** Sistema WHAGO  
**Data:** 18/11/2025 01:09:42  
**Versão:** PostgreSQL 15.14  
**Status:** ✅ Pronto para produção


