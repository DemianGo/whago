# 🌐 PLANEJAMENTO: Sistema de Proxies Residenciais

## ✅ ANÁLISE DA CONFIGURAÇÃO SMARTPROXY

### Credenciais Fornecidas
```
Servidor: proxy.smartproxy.net
Porta: 3120
Username: smart-whagowhago
Password: FFxfa564fddfX
Região: Brasil (BR)
Tipo: Residencial com rotação automática
```

### API de Extração
```
Endpoint: https://www.smartproxy.org/web_v1/ip/get-ip-v3
App Key: cac7e3ca1eaabfcf71a70b02565b6700
Parâmetros: pt=9&num=20&cc=BR&life=30&format=txt&protocol=1
```

⚠️ **PROBLEMA ATUAL:** 
```json
{"code":202,"msg":"Please add IP in the allow list first"}
```

**SOLUÇÃO:** Adicionar IP do servidor WHAGO no painel Smartproxy (whitelist).

---

## 🎯 ESTRATÉGIA RECOMENDADA

### Usar PROXY ROTATIVO (não API de extração)

**Vantagens:**
- ✅ IP muda automaticamente a cada requisição/sessão
- ✅ Não precisa gerenciar pool de IPs manualmente
- ✅ Smartproxy cuida de health e rotação
- ✅ Sticky session mantém mesmo IP por chip (evita detecção WhatsApp)
- ✅ Mais simples de implementar

**Formato da URL:**
```javascript
// Proxy rotativo com sticky session (recomendado)
const proxyUrl = `http://smart-whagowhago-session-${chipId}:FFxfa564fddfX@proxy.smartproxy.net:3120`;

// Cada chip tem seu próprio "session ID", mantendo IP fixo durante vida do chip
```

---

## 📊 ARQUITETURA DO SISTEMA

### 1. Tabelas do Banco de Dados

```sql
-- Provedores de proxy (Smartproxy, etc)
CREATE TABLE proxy_providers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100) UNIQUE NOT NULL,
  provider_type VARCHAR(50) NOT NULL, -- 'residential', 'datacenter', 'mobile'
  credentials JSONB NOT NULL, -- { "server": "...", "port": 3120, "username": "...", "password": "...", "api_key": "..." }
  cost_per_gb NUMERIC(10,4) NOT NULL DEFAULT 25.00, -- R$/GB configurável
  region VARCHAR(10) DEFAULT 'BR',
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Pool de proxies (se usar API de extração) ou configuração rotativa
CREATE TABLE proxies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider_id UUID REFERENCES proxy_providers(id) ON DELETE CASCADE,
  proxy_type VARCHAR(50) NOT NULL, -- 'rotating', 'static'
  proxy_url TEXT NOT NULL, -- URL completa ou template com {chipId}
  region VARCHAR(10) DEFAULT 'BR',
  protocol VARCHAR(20) DEFAULT 'http', -- 'http', 'https', 'socks5'
  health_score INT DEFAULT 100, -- 0-100
  total_bytes_used BIGINT DEFAULT 0,
  is_active BOOLEAN DEFAULT true,
  last_health_check TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Associação chip <> proxy
CREATE TABLE chip_proxy_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chip_id UUID REFERENCES chips(id) ON DELETE CASCADE,
  proxy_id UUID REFERENCES proxies(id) ON DELETE SET NULL,
  session_identifier VARCHAR(255), -- Usado em sticky session
  assigned_at TIMESTAMP DEFAULT NOW(),
  released_at TIMESTAMP NULL,
  UNIQUE(chip_id) -- Um chip só tem um proxy por vez
);

-- Logs de tráfego (coleta via API a cada 5min)
CREATE TABLE proxy_usage_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  chip_id UUID REFERENCES chips(id) ON DELETE SET NULL,
  proxy_id UUID REFERENCES proxies(id) ON DELETE SET NULL,
  bytes_sent BIGINT DEFAULT 0,
  bytes_received BIGINT DEFAULT 0,
  total_bytes BIGINT DEFAULT 0, -- sent + received
  cost NUMERIC(10,4) DEFAULT 0, -- calculado: (total_bytes / 1GB) * cost_per_gb
  session_start TIMESTAMP NOT NULL,
  session_end TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_proxy_usage_user_month ON proxy_usage_logs(user_id, DATE_TRUNC('month', session_start));

-- Agregação mensal de custos (otimização)
CREATE TABLE user_proxy_costs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  month DATE NOT NULL, -- '2025-11-01'
  total_bytes BIGINT DEFAULT 0,
  total_cost NUMERIC(10,4) DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(user_id, month)
);

-- Adicionar campo no modelo Plan
ALTER TABLE plans ADD COLUMN proxy_gb_limit NUMERIC(10,2) DEFAULT 0.1; -- GB/mês
```

---

### 2. Modelos SQLAlchemy

**Arquivo:** `backend/app/models/proxy.py`

```python
from sqlalchemy import Column, String, Integer, Boolean, TIMESTAMP, ForeignKey, Numeric, BIGINT, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from ..database import Base

class ProxyProvider(Base):
    __tablename__ = "proxy_providers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    provider_type = Column(String(50), nullable=False)  # residential, datacenter, mobile
    credentials = Column(JSONB, nullable=False)
    cost_per_gb = Column(Numeric(10, 4), nullable=False, default=25.00)
    region = Column(String(10), default="BR")
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    proxies = relationship("Proxy", back_populates="provider", cascade="all, delete-orphan")

class Proxy(Base):
    __tablename__ = "proxies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("proxy_providers.id", ondelete="CASCADE"))
    proxy_type = Column(String(50), nullable=False)  # rotating, static
    proxy_url = Column(String, nullable=False)
    region = Column(String(10), default="BR")
    protocol = Column(String(20), default="http")
    health_score = Column(Integer, default=100)
    total_bytes_used = Column(BIGINT, default=0)
    is_active = Column(Boolean, default=True)
    last_health_check = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    provider = relationship("ProxyProvider", back_populates="proxies")
    assignments = relationship("ChipProxyAssignment", back_populates="proxy")

class ChipProxyAssignment(Base):
    __tablename__ = "chip_proxy_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chip_id = Column(UUID(as_uuid=True), ForeignKey("chips.id", ondelete="CASCADE"), unique=True)
    proxy_id = Column(UUID(as_uuid=True), ForeignKey("proxies.id", ondelete="SET NULL"))
    session_identifier = Column(String(255))
    assigned_at = Column(TIMESTAMP, default=datetime.utcnow)
    released_at = Column(TIMESTAMP)
    
    chip = relationship("Chip", back_populates="proxy_assignment")
    proxy = relationship("Proxy", back_populates="assignments")

class ProxyUsageLog(Base):
    __tablename__ = "proxy_usage_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    chip_id = Column(UUID(as_uuid=True), ForeignKey("chips.id", ondelete="SET NULL"))
    proxy_id = Column(UUID(as_uuid=True), ForeignKey("proxies.id", ondelete="SET NULL"))
    bytes_sent = Column(BIGINT, default=0)
    bytes_received = Column(BIGINT, default=0)
    total_bytes = Column(BIGINT, default=0)
    cost = Column(Numeric(10, 4), default=0)
    session_start = Column(TIMESTAMP, nullable=False)
    session_end = Column(TIMESTAMP, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

class UserProxyCost(Base):
    __tablename__ = "user_proxy_costs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    month = Column(Date, nullable=False)
    total_bytes = Column(BIGINT, default=0)
    total_cost = Column(Numeric(10, 4), default=0)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

### 3. Services

**Arquivo:** `backend/app/services/proxy_service.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import httpx
from ..models.proxy import ProxyProvider, Proxy, ChipProxyAssignment
from ..models.chip import Chip

class ProxyService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_active_rotating_proxy(self, region: str = "BR") -> Optional[Proxy]:
        """Retorna proxy rotativo ativo."""
        result = await self.session.execute(
            select(Proxy)
            .where(Proxy.proxy_type == "rotating")
            .where(Proxy.region == region)
            .where(Proxy.is_active == True)
            .order_by(Proxy.health_score.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def assign_proxy_to_chip(self, chip: Chip) -> str:
        """Atribui proxy ao chip e retorna URL completa."""
        # Busca proxy rotativo
        proxy = await self.get_active_rotating_proxy()
        if not proxy:
            raise ValueError("Nenhum proxy ativo disponível")
        
        # Cria session identifier único
        session_id = f"chip-{chip.id}"
        
        # Cria assignment
        assignment = ChipProxyAssignment(
            chip_id=chip.id,
            proxy_id=proxy.id,
            session_identifier=session_id
        )
        self.session.add(assignment)
        await self.session.commit()
        
        # Gera URL com sticky session
        # Template: http://user-session-{session}:pass@server:port
        proxy_url = proxy.proxy_url.format(session=session_id)
        return proxy_url
    
    async def get_chip_proxy_url(self, chip_id: UUID) -> Optional[str]:
        """Retorna URL do proxy atribuído ao chip."""
        result = await self.session.execute(
            select(ChipProxyAssignment)
            .where(ChipProxyAssignment.chip_id == chip_id)
            .where(ChipProxyAssignment.released_at.is_(None))
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            return None
        
        proxy = await self.session.get(Proxy, assignment.proxy_id)
        return proxy.proxy_url.format(session=assignment.session_identifier)
    
    async def health_check_proxy(self, proxy: Proxy) -> int:
        """Testa saúde do proxy retornando score 0-100."""
        try:
            async with httpx.AsyncClient(proxies=proxy.proxy_url, timeout=10) as client:
                response = await client.get("https://httpbin.org/ip")
                if response.status_code == 200:
                    return 100
                return 50
        except:
            return 0
```

**Arquivo:** `backend/app/services/smartproxy_client.py`

```python
import httpx
from typing import Dict

class SmartproxyClient:
    def __init__(self, username: str, password: str, server: str = "proxy.smartproxy.net", port: int = 3120):
        self.username = username
        self.password = password
        self.server = server
        self.port = port
        self.base_url = f"http://{username}:{password}@{server}:{port}"
    
    def get_rotating_proxy_url(self, session_id: str) -> str:
        """Retorna URL com sticky session."""
        return f"http://{self.username}-session-{session_id}:{self.password}@{self.server}:{self.port}"
    
    async def get_usage_stats(self, api_key: str) -> Dict:
        """Consulta API para obter estatísticas de uso."""
        # Endpoint: https://api.smartproxy.com/v2/traffic/usage (exemplo)
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {api_key}"}
            response = await client.get(
                "https://api.smartproxy.com/v2/traffic/usage",
                headers=headers
            )
            return response.json()
    
    async def test_connection(self) -> bool:
        """Testa se proxy está funcionando."""
        try:
            proxies = {"http://": self.base_url, "https://": self.base_url}
            async with httpx.AsyncClient(proxies=proxies, timeout=10) as client:
                response = await client.get("https://httpbin.org/ip")
                return response.status_code == 200
        except:
            return False
```

---

### 4. Integração com Baileys

**Arquivo:** `baileys-service/src/server.js` (modificar)

```javascript
const { HttpsProxyAgent } = require('https-proxy-agent');
const { SocksProxyAgent } = require('socks-proxy-agent');

// Modificar função de conexão
router.post("/connect", async (req, res) => {
  const { sessionId, proxyUrl } = req.body; // ✅ Receber proxyUrl do backend
  
  if (!sessionId) {
    return res.status(400).json({ error: "sessionId obrigatório" });
  }
  
  try {
    const { state, saveCreds } = await useMultiFileAuthState(`./sessions/${sessionId}`);
    
    // ✅ Configurar proxy agent se fornecido
    const socketConfig = {};
    if (proxyUrl) {
      socketConfig.agent = new HttpsProxyAgent(proxyUrl);
      console.log(`[${sessionId}] Conectando via proxy: ${proxyUrl.split('@')[1]}`); // Log sem credenciais
    }
    
    const sock = makeWASocket({
      auth: state,
      printQRInTerminal: false,
      ...socketConfig, // ✅ Usa proxy
    });
    
    // ... resto do código
  }
});
```

**Instalar dependências no Baileys:**
```bash
cd baileys-service
npm install https-proxy-agent socks-proxy-agent
```

---

### 5. Task Celery para Monitoramento

**Arquivo:** `backend/tasks/proxy_monitor_tasks.py`

```python
from celery import shared_task
from sqlalchemy import select
from datetime import datetime, timezone
from ..database import AsyncSessionLocal
from ..models.proxy import ProxyUsageLog, UserProxyCost, Proxy
from ..models.chip import Chip
from ..services.smartproxy_client import SmartproxyClient

@shared_task
async def monitor_proxy_usage():
    """Task executada a cada 5 minutos para coletar uso de proxies."""
    async with AsyncSessionLocal() as session:
        # Busca chips conectados
        result = await session.execute(
            select(Chip).where(Chip.status == "connected")
        )
        chips = result.scalars().all()
        
        for chip in chips:
            # Busca assignment do chip
            assignment = chip.proxy_assignment
            if not assignment or not assignment.proxy:
                continue
            
            proxy = assignment.proxy
            provider = proxy.provider
            
            # Consulta API do provedor (Smartproxy)
            api_key = provider.credentials.get("api_key")
            if not api_key:
                continue
            
            smartproxy = SmartproxyClient(**provider.credentials)
            usage = await smartproxy.get_usage_stats(api_key)
            
            # Calcula bytes desde última coleta
            bytes_used = usage.get("traffic_used_bytes", 0)
            cost_per_gb = float(provider.cost_per_gb)
            cost = (bytes_used / (1024**3)) * cost_per_gb
            
            # Cria log
            log = ProxyUsageLog(
                user_id=chip.user_id,
                chip_id=chip.id,
                proxy_id=proxy.id,
                total_bytes=bytes_used,
                cost=cost,
                session_start=datetime.now(timezone.utc).replace(minute=0, second=0),
                session_end=datetime.now(timezone.utc)
            )
            session.add(log)
            
            # Atualiza agregação mensal
            await update_user_proxy_cost(session, chip.user_id, bytes_used, cost)
        
        await session.commit()

async def update_user_proxy_cost(session, user_id, bytes_delta, cost_delta):
    """Atualiza custo mensal agregado do usuário."""
    month = datetime.now(timezone.utc).replace(day=1)
    
    result = await session.execute(
        select(UserProxyCost)
        .where(UserProxyCost.user_id == user_id)
        .where(UserProxyCost.month == month.date())
    )
    cost_entry = result.scalar_one_or_none()
    
    if cost_entry:
        cost_entry.total_bytes += bytes_delta
        cost_entry.total_cost += cost_delta
    else:
        cost_entry = UserProxyCost(
            user_id=user_id,
            month=month.date(),
            total_bytes=bytes_delta,
            total_cost=cost_delta
        )
        session.add(cost_entry)
```

**Configurar Celery Beat:**
```python
# backend/tasks/celery_app.py
from celery.schedules import crontab

app.conf.beat_schedule = {
    'monitor-proxy-usage': {
        'task': 'tasks.proxy_monitor_tasks.monitor_proxy_usage',
        'schedule': 300.0,  # A cada 5 minutos
    },
}
```

---

### 6. Rotas Admin

**Arquivo:** `backend/app/routes/admin_proxies.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..dependencies.admin import get_current_admin
from ..models.proxy import ProxyProvider, Proxy
from ..schemas.proxy import ProxyProviderCreate, ProxyProviderResponse

router = APIRouter(prefix="/admin/proxies", tags=["Admin - Proxies"])

@router.get("/providers")
async def list_providers(
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    result = await db.execute(select(ProxyProvider))
    providers = result.scalars().all()
    return providers

@router.post("/providers")
async def create_provider(
    data: ProxyProviderCreate,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    provider = ProxyProvider(**data.dict())
    db.add(provider)
    await db.commit()
    return provider

@router.put("/providers/{provider_id}")
async def update_provider(
    provider_id: UUID,
    data: ProxyProviderCreate,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    provider = await db.get(ProxyProvider, provider_id)
    if not provider:
        raise HTTPException(404, "Provider não encontrado")
    
    for key, value in data.dict().items():
        setattr(provider, key, value)
    
    await db.commit()
    return provider

@router.post("/providers/{provider_id}/test")
async def test_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    provider = await db.get(ProxyProvider, provider_id)
    if not provider:
        raise HTTPException(404, "Provider não encontrado")
    
    from ..services.smartproxy_client import SmartproxyClient
    client = SmartproxyClient(**provider.credentials)
    success = await client.test_connection()
    
    return {"success": success, "message": "Conexão OK" if success else "Falha na conexão"}
```

---

### 7. Frontend Admin

**Arquivo:** `frontend/templates/admin_proxies.html`

```html
{% extends "base_admin.html" %}
{% block content %}
<div class="p-6">
  <h1 class="text-2xl font-bold mb-6">Gerenciamento de Proxies</h1>
  
  <button onclick="openCreateProviderModal()" class="btn-primary mb-4">
    + Novo Provedor
  </button>
  
  <div class="card">
    <table class="table">
      <thead>
        <tr>
          <th>Nome</th>
          <th>Tipo</th>
          <th>Custo/GB</th>
          <th>Região</th>
          <th>Status</th>
          <th>Ações</th>
        </tr>
      </thead>
      <tbody id="providers-table"></tbody>
    </table>
  </div>
</div>

<!-- Modal Criar/Editar -->
<div id="providerModal" class="modal" style="display:none;">
  <div class="modal-content">
    <h2>Configurar Provedor</h2>
    <form id="providerForm">
      <input type="text" name="name" placeholder="Nome (ex: Smartproxy BR)" required>
      <select name="provider_type">
        <option value="residential">Residencial</option>
        <option value="datacenter">Datacenter</option>
      </select>
      <input type="number" name="cost_per_gb" placeholder="Custo por GB (R$)" step="0.01" required>
      <input type="text" name="server" placeholder="Servidor (ex: proxy.smartproxy.net)" required>
      <input type="number" name="port" placeholder="Porta (ex: 3120)" required>
      <input type="text" name="username" placeholder="Username" required>
      <input type="password" name="password" placeholder="Password" required>
      <input type="text" name="api_key" placeholder="API Key (opcional)">
      <button type="submit">Salvar</button>
    </form>
  </div>
</div>

<script src="/static/js/admin_proxies.js"></script>
{% endblock %}
```

---

## 📅 CRONOGRAMA DE IMPLEMENTAÇÃO

### **Fase 1: Estrutura Base (2 dias)**
- [ ] Migration: criar tabelas
- [ ] Models: ProxyProvider, Proxy, ChipProxyAssignment, ProxyUsageLog, UserProxyCost
- [ ] Adicionar `proxy_gb_limit` no modelo `Plan`
- [ ] Schemas Pydantic

### **Fase 2: Integração Baileys (2 dias)**
- [ ] SmartproxyClient
- [ ] ProxyService
- [ ] Modificar Baileys para aceitar `proxyUrl`
- [ ] Atualizar ChipService para atribuir proxy ao conectar

### **Fase 3: Monitoramento (2 dias)**
- [ ] Task Celery: `monitor_proxy_usage`
- [ ] Configurar Celery Beat
- [ ] Testar coleta de dados via API Smartproxy

### **Fase 4: Admin e Frontend (2 dias)**
- [ ] Rotas admin: CRUD de providers/proxies
- [ ] Templates: `admin_proxies.html`
- [ ] JavaScript: `admin_proxies.js`
- [ ] Dashboard de uso

### **Fase 5: Limites e Cobrança (1 dia)**
- [ ] Middleware: `check_proxy_quota`
- [ ] Dashboard usuário: exibir uso
- [ ] Alertas (80%, 100%)
- [ ] Pacotes de GB avulsos

---

## ⚠️ PRÓXIMOS PASSOS

1. **Resolver erro 202 do Smartproxy:** Adicionar IP do servidor na whitelist
2. **Confirmar valores:**
   - Custo/GB: R$ 25,00? (configurável)
   - Limites: FREE=100MB, BUSINESS=1GB, ENTERPRISE=5GB?
3. **Iniciar implementação?** Criar migrations e models agora?

---

**STATUS:** ✅ Planejamento completo. Aguardando confirmação para iniciar.

