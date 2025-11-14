# Restaurar Backup do Banco de Dados

## Arquivo de Backup
- **Nome:** `backup_whago_20251114_094810.sql`
- **Tamanho:** 2.2 MB
- **Localização:** `/home/liberai/whago/`

## Como Restaurar

### 1. Copie o arquivo para o novo computador
```bash
scp backup_whago_20251114_094810.sql usuario@novo-servidor:/caminho/destino/
```

### 2. No novo servidor, com o Docker Compose rodando:
```bash
# Entre na pasta do projeto
cd /caminho/do/projeto

# Restaure o backup
docker-compose exec -T postgres psql -U whago whago < backup_whago_20251114_094810.sql
```

### 3. Alternativa: Restaurar antes de iniciar os containers
```bash
# Copie o backup para dentro do container
docker cp backup_whago_20251114_094810.sql whago-postgres:/tmp/

# Entre no container
docker-compose exec postgres bash

# Restaure
psql -U whago whago < /tmp/backup_whago_20251114_094810.sql
```

## Notas
- O backup contém todos os dados, tabelas, índices e constraints
- Certifique-se de que o banco de destino existe: `whago`
- Usuário do banco: `whago`
- O banco será sobrescrito se já existir

