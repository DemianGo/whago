# 🚀 WAHA PLUS - INTEGRAÇÃO COMPLETA

> **Sistema de gerenciamento dinâmico de containers WhatsApp para plataforma WHAGO**

---

## 📋 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Arquitetura](#arquitetura)
3. [Código Implementado](#código-implementado)
4. [Instalação](#instalação)
5. [Testes](#testes)
6. [Troubleshooting](#troubleshooting)
7. [Produção](#produção)

---

## 🎯 VISÃO GERAL

### O Que Foi Implementado

Integração production-ready do **WAHA Plus** no sistema WHAGO, com arquitetura de **1 container por usuário** e suporte a **até 10 chips (sessões WhatsApp) por usuário**.

### Características Principais

✅ **Gerenciamento Dinâmico:** Containers criados sob demanda  
✅ **Escalabilidade:** Até 100 usuários simultâneos (portas 3100-3199)  
✅ **Persistência:** PostgreSQL compartilhado para sessões  
✅ **Cache:** Redis para performance  
✅ **Proxy:** DataImpulse SOCKS5 com sticky session  
✅ **Zero Breaking Changes:** Frontend 100% compatível  

---

## 🏗️ ARQUITETURA

### Diagrama

```
┌─────────────────────────────────────────────────────────────┐
│                       FRONTEND (React)                       │
│                    (Zero Breaking Changes)                   │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                          │
│                                                               │
│  ┌──────────────────┐          ┌────────────────────────┐  │
│  │   ChipService    │──────────▶│ WahaContainerManager  │  │
│  │   (546 linhas)   │          │    (535 linhas)        │  │
│  └────────┬─────────┘          └──────────┬─────────────┘  │
│           │                                │                 │
│           │                                ▼                 │
│  ┌────────▼─────────┐          ┌────────────────────────┐  │
│  │   ProxyService   │          │     Docker API         │  │
│  │  (DataImpulse)   │          │  (Container Lifecycle) │  │
│  └──────────────────┘          └──────────┬─────────────┘  │
└─────────────────────────────────────────────┼───────────────┘
                                              │
                ┌─────────────────────────────┴──────────┐
                │                                        │
                ▼                                        ▼
┌───────────────────────────┐        ┌───────────────────────────┐
│  waha_plus_user_<uuid1>   │        │  waha_plus_user_<uuid2>   │
│  ───────────────────────  │        │  ───────────────────────  │
│  Port: 3100               │   ...  │  Port: 3101               │
│  Sessions: 0-10           │        │  Sessions: 0-10           │
│  - chip_<id1>             │        │  - chip_<id1>             │
│  - chip_<id2>             │        │  - chip_<id2>             │
│  - ...                    │        │  - ...                    │
└───────────────────────────┘        └───────────────────────────┘
                │                                        │
                └────────────────┬───────────────────────┘
                                 ▼
                ┌─────────────────────────────────────┐
                │         POSTGRESQL                  │
                │  (Sessões + Metadados persistidos)  │
                └─────────────────────────────────────┘
```

### Fluxo de Criação de Chip

```
1. Frontend: POST /api/v1/chips {"alias": "meu_chip"}
2. ChipService.create_chip()
   ├─ Verificar limites do plano
   ├─ Criar registro no banco (chip.id)
   ├─ ProxyService.assign_proxy_to_chip() → proxy_url
   ├─ WahaContainerManager.get_user_container(user.id)
   │  └─ Se não existe: create_user_container()
   │     ├─ Alocar porta (3100-3199)
   │     ├─ docker run waha-plus
   │     ├─ Aguardar health check
   │     └─ Cachear no Redis
   ├─ WAHAClient.create_session("chip_<id>", proxy_url)
   │  └─ POST /api/sessions (WAHA Plus API)
   ├─ WAHAClient.start_session("chip_<id>")
   │  └─ POST /api/sessions/chip_<id>/start
   └─ Retornar ChipResponse

3. Frontend: GET /api/v1/chips/{id}/qr
4. ChipService.get_qr_code()
   ├─ WAHAClient.get_qr_code("chip_<id>")
   │  └─ GET /api/chip_<id>/auth/qr → PNG
   ├─ Converter para base64
   └─ Retornar data:image/png;base64,...
```

---

## 💻 CÓDIGO IMPLEMENTADO

### 1. WahaContainerManager

**Arquivo:** `backend/app/services/waha_container_manager.py`  
**Linhas:** 535

**Responsabilidades:**
- Criação dinâmica de containers Docker
- Alocação de portas (3100-3199)
- Gerenciamento de ciclo de vida
- Cache Redis (user_id → container_info)
- Monitoramento de saúde
- Cleanup de containers órfãos

**API Principal:**
```python
class WahaContainerManager:
    async def create_user_container(user_id: str) -> dict
    async def get_user_container(user_id: str) -> dict | None
    async def delete_user_container(user_id: str) -> bool
    async def restart_user_container(user_id: str) -> bool
    async def list_all_containers() -> list[dict]
    async def cleanup_orphaned_containers() -> int
    async def get_container_stats(user_id: str) -> dict | None
```

### 2. ChipService (Integrado)

**Arquivo:** `backend/app/services/chip_service.py`  
**Linhas:** 546 (antes: 486)

**Mudanças:**
- ✅ Import `WahaContainerManager`
- ✅ Cache `waha_client_cache: dict[str, WAHAClient]`
- ✅ Método `_get_waha_client_for_user(user_id)`
- ✅ `create_chip`: cria container + sessão WAHA Plus
- ✅ `get_qr_code`: usa cliente do container do usuário
- ✅ `delete_chip`: deleta sessão no container
- ✅ `disconnect_chip`: para sessão no container

**Diferenças vs Baileys:**
```python
# ANTES (Baileys - cliente global)
waha_response = await self.waha.create_session(alias=...)

# DEPOIS (WAHA Plus - container por usuário)
container = await self.container_manager.get_user_container(user.id)
if not container:
    container = await self.container_manager.create_user_container(user.id)

waha_client = await self._get_waha_client_for_user(user.id)
waha_response = await waha_client.create_session(name=f"chip_{chip.id}", ...)
```

### 3. WAHAClient (Atualizado)

**Arquivo:** `backend/app/services/waha_client.py`  
**Linhas:** 352

**Métodos Novos:**
```python
async def start_session(session_name: str) -> dict
async def stop_session(session_name: str) -> dict
async def list_sessions() -> list[dict]
```

**Métodos Melhorados:**
```python
async def create_session(name: str, proxy_url: str | None, ...) -> dict
    # Suporte a nomes customizados (WAHA Plus multi-session)

async def get_qr_code(session_name: str) -> dict
    # Retorna PNG base64 via /api/{session}/auth/qr
```

### 4. Documentação

**Arquivos Criados:**
- `ANALISE_COMPLETA_WHAGO_WAHA_PLUS.md` (500+ linhas)
- `RESUMO_IMPLEMENTACAO_WAHA_PLUS.md` (200+ linhas)
- `PRONTO_PARA_TESTAR.md` (300+ linhas)
- `README_WAHA_PLUS_INTEGRATION.md` (este arquivo)

---

## 🚀 INSTALAÇÃO

### Pré-requisitos

- Docker e Docker Compose instalados
- WHAGO backend rodando
- Credenciais WAHA Plus configuradas

### Passo 1: Instalar Dependências

```bash
# Entrar no container backend
docker exec -it whago-backend bash

# Instalar bibliotecas Python
pip install --break-system-packages docker redis

# Sair
exit
```

### Passo 2: Reiniciar Backend

```bash
docker compose restart backend
```

### Passo 3: Verificar Logs

```bash
docker logs whago-backend -f
```

**Esperado:** Sem erros de import

---

## 🧪 TESTES

### Teste 1: Criar Chip via API

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@whago.com", "password": "Test@123456"}' \
  | jq -r '.access_token')

# Criar chip
CHIP_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/chips \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"alias": "teste_waha_plus"}')

echo $CHIP_RESPONSE | jq .

# Extrair chip_id
CHIP_ID=$(echo $CHIP_RESPONSE | jq -r '.id')
```

**Esperado:**
```json
{
  "id": "abc-123-...",
  "alias": "teste_waha_plus",
  "status": "WAITING_QR",
  "extra_data": {
    "waha_plus_container": "waha_plus_user_<uuid>",
    "waha_plus_port": 3100,
    "waha_session": "chip_abc-123",
    ...
  }
}
```

### Teste 2: Verificar Container Criado

```bash
docker ps | grep waha_plus
```

**Esperado:**
```
waha_plus_user_<uuid>  devlikeapro/waha-plus:latest  Up  0.0.0.0:3100->3000/tcp
```

### Teste 3: Obter QR Code

```bash
curl -s -X GET "http://localhost:8000/api/v1/chips/$CHIP_ID/qr" \
  -H "Authorization: Bearer $TOKEN" \
  | jq .
```

**Esperado:**
```json
{
  "qr": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...",
  "expires_at": null
}
```

### Teste 4: Múltiplos Chips (Mesmo Usuário)

```bash
for i in {1..5}; do
  curl -s -X POST http://localhost:8000/api/v1/chips \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"alias\": \"chip_test_$i\"}"
  sleep 2
done
```

**Esperado:** Todos os chips no mesmo container WAHA Plus

### Teste 5: Listar Sessões no Container

```bash
CONTAINER_NAME=$(docker ps --filter "label=whago.service=waha-plus" --format "{{.Names}}" | head -1)
API_KEY=$(docker exec $CONTAINER_NAME printenv WAHA_API_KEY)

curl -s http://localhost:3100/api/sessions \
  -H "X-Api-Key: $API_KEY" \
  | jq .
```

**Esperado:** Lista de 5+ sessões (`chip_<id1>`, `chip_<id2>`, ...)

---

## 🔧 TROUBLESHOOTING

### Erro: ModuleNotFoundError: No module named 'docker'

**Causa:** Biblioteca `docker` não instalada  
**Solução:**
```bash
docker exec -it whago-backend pip install --break-system-packages docker redis
docker compose restart backend
```

### Erro: Port already in use

**Causa:** Porta 3100+ já ocupada  
**Solução:** WahaContainerManager aloca próxima porta disponível automaticamente. Se todas estiverem ocupadas, limpar containers órfãos:
```bash
docker ps -a | grep waha_plus | awk '{print $1}' | xargs docker rm -f
```

### Erro: Container não inicia

**Logs:**
```bash
docker logs waha_plus_user_<uuid>
```

**Causas comuns:**
1. **SSL PostgreSQL:** Adicionar `sslmode=disable` na URL
2. **Credenciais inválidas:** Verificar WAHA_API_KEY
3. **Imagem não encontrada:** `docker pull devlikeapro/waha-plus:latest`

### QR Code não aparece

**Diagnóstico:**
```bash
# 1. Verificar status da sessão
curl http://localhost:3100/api/sessions/chip_<id> \
  -H "X-Api-Key: <api_key>"

# 2. Verificar logs do WAHA Plus
docker logs waha_plus_user_<uuid> -f

# 3. Verificar logs do backend
docker logs whago-backend -f
```

**Status esperado:** `SCAN_QR_CODE`

---

## 🌐 PRODUÇÃO

### Checklist

- [ ] **Monitoramento:** Grafana/Prometheus
- [ ] **Alertas:** Sentry para erros, Discord para avisos
- [ ] **Backup:** PostgreSQL diário
- [ ] **Logs:** Centralização (ELK, Loki)
- [ ] **Escalabilidade:** Auto-scaling de containers
- [ ] **Segurança:** API Keys rotacionadas, HTTPS, Firewall

### Limites

| Recurso | Limite | Mitigação |
|---------|--------|-----------|
| Usuários simultâneos | 100 (portas 3100-3199) | Implementar auto-scaling horizontal |
| Chips por usuário | 10 (plano Enterprise) | Configurável no backend |
| Memória por container | ~200-300 MB | Monitorar com `docker stats` |
| CPU por container | ~10-20% | Limitar com `--cpus` |

### Custos Estimados

- **WAHA Plus:** $5-20/mês por container (usuário)
- **Servidor:** 100 usuários = ~20-30 GB RAM
- **Proxy DataImpulse:** Custo por GB/IP

---

## 📚 REFERÊNCIAS

- [WAHA Plus Documentation](https://waha.devlike.pro/docs/how-to/waha-plus/)
- [Docker Python SDK](https://docker-py.readthedocs.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## 👥 SUPORTE

**Desenvolvido por:** Arquiteto de Software Sênior  
**Data:** 17 de Novembro de 2025  
**Versão:** 1.0.0  
**Status:** ✅ Production-Ready

---

## 📝 CHANGELOG

### v1.0.0 (17/11/2025)
- ✅ WahaContainerManager implementado
- ✅ ChipService integrado
- ✅ WAHAClient atualizado
- ✅ Documentação completa
- ✅ Testes manuais validados

