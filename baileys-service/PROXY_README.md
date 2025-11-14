# 🌐 Módulo de Proxy - WHAGO Baileys Service

## 📋 Visão Geral

O módulo de proxy do WHAGO permite rotear todo o tráfego do Baileys através de proxies residenciais, resolvendo problemas de bloqueio do WhatsApp (erros 405, 515, etc).

**Características:**
- ✅ **Modular e isolado** - Não modifica código existente
- ✅ **Multi-provedor** - Suporta Smartproxy, IPRoyal, Bright Data, Oxylabs, etc
- ✅ **Plug & Play** - Habilita/desabilita via `.env`
- ✅ **Protocolo agnóstico** - HTTP, HTTPS, SOCKS5
- ✅ **Geo-targeting** - Escolha país do IP
- ✅ **Session sticky** - Mantém mesmo IP durante sessão
- ✅ **Diagnóstico integrado** - Endpoints para testar proxy

---

## 🚀 Configuração Rápida

### **1. Instalar dependências**

```bash
cd baileys-service
npm install
```

As dependências `https-proxy-agent` e `socks-proxy-agent` já estão no `package.json`.

### **2. Configurar variáveis de ambiente**

Edite o arquivo `.env` no diretório `baileys-service/`:

```bash
# Habilitar proxy
PROXY_ENABLED=true

# Tipo de proxy (http, https, socks5)
PROXY_TYPE=http

# Credenciais do Smartproxy (exemplo)
PROXY_HOST=gate.smartproxy.com
PROXY_PORT=7000
PROXY_USERNAME=seu_usuario_aqui
PROXY_PASSWORD=sua_senha_aqui

# Opcional: Escolher país
PROXY_COUNTRY=BR

# Opcional: Session ID (mantém mesmo IP)
PROXY_SESSION_ID=whago_session_1
```

### **3. Reiniciar serviço**

```bash
docker-compose restart baileys
```

### **4. Verificar status**

```bash
# Via API
curl http://localhost:3000/api/v1/proxy/status

# Ou verificar logs
docker logs whago-baileys
```

Você verá:
```
✅ Proxy HTTP/HTTPS inicializado: http://seu_usuario:****@gate.smartproxy.com:7000
```

---

## 🔧 Provedores Suportados

### **Smartproxy** (Recomendado)
```bash
PROXY_HOST=gate.smartproxy.com
PROXY_PORT=7000
PROXY_TYPE=http
PROXY_USERNAME=spxxxxxxxxx
PROXY_PASSWORD=sua_senha
```
- Dashboard: https://dashboard.smartproxy.com/
- Documentação: https://help.smartproxy.com/

### **IPRoyal**
```bash
PROXY_HOST=geo.iproyal.com
PROXY_PORT=12321
PROXY_TYPE=http
PROXY_USERNAME=seu_usuario
PROXY_PASSWORD=sua_senha
```
- Dashboard: https://iproyal.com/dashboard/
- Documentação: https://iproyal.com/documentation/

### **Bright Data** (ex-Luminati)
```bash
PROXY_HOST=brd.superproxy.io
PROXY_PORT=22225
PROXY_TYPE=http
PROXY_USERNAME=seu_usuario
PROXY_PASSWORD=sua_senha
```
- Dashboard: https://brightdata.com/cp/
- Documentação: https://docs.brightdata.com/

### **Oxylabs**
```bash
PROXY_HOST=pr.oxylabs.io
PROXY_PORT=7777
PROXY_TYPE=http
PROXY_USERNAME=seu_usuario
PROXY_PASSWORD=sua_senha
```
- Dashboard: https://dashboard.oxylabs.io/
- Documentação: https://developers.oxylabs.io/

---

## 🌍 Geo-Targeting (Escolher País)

A maioria dos provedores permite escolher o país do IP:

```bash
PROXY_COUNTRY=BR  # Brasil
PROXY_COUNTRY=US  # Estados Unidos
PROXY_COUNTRY=UK  # Reino Unido
PROXY_COUNTRY=DE  # Alemanha
```

**Formato do username (Smartproxy):**
```
seu_usuario-country-BR-session-whago_session_1
```

O módulo formata automaticamente!

---

## 🔒 Session Sticky (Manter mesmo IP)

Para manter o mesmo IP durante toda a sessão:

```bash
PROXY_SESSION_ID=whago_session_1
```

**Benefícios:**
- WhatsApp não detecta mudança de IP
- Mais estável para conexões longas
- Evita reconexões desnecessárias

**Quando mudar:**
- Se IP for bloqueado
- Para rotacionar IPs entre chips
- Para testar diferentes localizações

---

## 🧪 Testando o Proxy

### **1. Via API (Recomendado)**

```bash
# Verificar status
curl http://localhost:3000/api/v1/proxy/status

# Testar conexão
curl -X POST http://localhost:3000/api/v1/proxy/test
```

**Resposta esperada:**
```json
{
  "status": "ok",
  "message": "Proxy funcionando corretamente",
  "proxy": {
    "enabled": true,
    "type": "http",
    "host": "gate.smartproxy.com",
    "port": "7000",
    "username": "spxxxxxxxxx",
    "country": "BR",
    "url": "http://spxxxxxxxxx:****@gate.smartproxy.com:7000"
  }
}
```

### **2. Via Logs**

```bash
docker logs -f whago-baileys
```

Procure por:
```
✅ Proxy HTTP/HTTPS inicializado: http://...
[Session xxx] 🌐 Proxy habilitado: http://...
✅ Proxy funcionando! IP público: 123.45.67.89
```

### **3. Criar chip e verificar QR**

```bash
# Criar chip via API
curl -X POST http://localhost:8000/api/v1/chips \
  -H "Authorization: Bearer seu_token" \
  -H "Content-Type: application/json" \
  -d '{"alias": "Teste Proxy"}'
```

Se o QR aparecer, o proxy está funcionando! 🎉

---

## 🐛 Troubleshooting

### **Proxy não está sendo usado**

**Sintoma:** Logs mostram `🔓 Proxy desabilitado, conexão direta`

**Solução:**
1. Verifique `PROXY_ENABLED=true` no `.env`
2. Reinicie: `docker-compose restart baileys`
3. Verifique logs: `docker logs whago-baileys`

### **Erro: "Proxy habilitado mas credenciais incompletas"**

**Sintoma:** Proxy desabilita automaticamente

**Solução:**
1. Verifique se `PROXY_HOST`, `PROXY_PORT`, `PROXY_USERNAME`, `PROXY_PASSWORD` estão preenchidos
2. Não deixe espaços em branco
3. Não use aspas nas variáveis

### **Erro: "ECONNREFUSED" ou "ETIMEDOUT"**

**Sintoma:** Não consegue conectar ao proxy

**Solução:**
1. Verifique credenciais no dashboard do provedor
2. Confirme que o plano está ativo
3. Teste com `curl`:
   ```bash
   curl -x http://usuario:senha@gate.smartproxy.com:7000 https://api.ipify.org
   ```

### **QR não aparece mesmo com proxy**

**Sintoma:** Erro 405 persiste

**Solução:**
1. Aguarde 10-15 minutos (cooldown do WhatsApp)
2. Troque o `PROXY_SESSION_ID` para rotacionar IP
3. Verifique se o IP do proxy não está bloqueado:
   ```bash
   curl -X POST http://localhost:3000/api/v1/proxy/test
   ```

### **Erro 515 após login**

**Sintoma:** Conecta mas desconecta com erro 515

**Solução:**
1. O módulo já está configurado em "modo passivo"
2. Aguarde 10 minutos antes de nova tentativa
3. Use proxy de país diferente (ex: `PROXY_COUNTRY=US`)

---

## 📊 Monitoramento

### **Consumo de dados**

Monitore no dashboard do provedor:
- Smartproxy: https://dashboard.smartproxy.com/
- IPRoyal: https://iproyal.com/dashboard/

**Consumo típico:**
- 1 chip conectado: ~50-100MB/mês
- 10 chips + 1.000 msgs/dia: ~500MB-1GB/mês

### **Logs do módulo**

```bash
# Logs em tempo real
docker logs -f whago-baileys | grep -i proxy

# Filtrar por sessão específica
docker logs whago-baileys | grep "Session xxx"
```

---

## 🔄 Rotação de IPs

Para rotacionar IPs entre chips:

```bash
# Método 1: Mudar PROXY_SESSION_ID
PROXY_SESSION_ID=chip_1  # Para chip 1
PROXY_SESSION_ID=chip_2  # Para chip 2

# Método 2: Usar timestamp (IP diferente a cada reinício)
PROXY_SESSION_ID=whago_$(date +%s)
```

**Nota:** Requer reiniciar o serviço Baileys.

---

## 🛡️ Segurança

### **Não commitar credenciais**

O arquivo `.env` está no `.gitignore`. Nunca commite:
- `PROXY_USERNAME`
- `PROXY_PASSWORD`
- Credenciais de API

### **Usar variáveis de ambiente**

Em produção, use secrets do Docker/Kubernetes:

```yaml
# docker-compose.yml
services:
  baileys:
    environment:
      - PROXY_ENABLED=${PROXY_ENABLED}
      - PROXY_USERNAME=${PROXY_USERNAME}
      - PROXY_PASSWORD=${PROXY_PASSWORD}
```

---

## 📚 Referências

- **Baileys:** https://github.com/WhiskeySockets/Baileys
- **Smartproxy:** https://smartproxy.com/
- **IPRoyal:** https://iproyal.com/
- **Bright Data:** https://brightdata.com/
- **Oxylabs:** https://oxylabs.io/

---

## 🆘 Suporte

Se precisar de ajuda:

1. **Verifique logs:** `docker logs whago-baileys`
2. **Teste proxy:** `curl -X POST http://localhost:3000/api/v1/proxy/test`
3. **Consulte dashboard do provedor**
4. **Abra issue no GitHub** (sem expor credenciais!)

---

## 📝 Changelog

### v1.0.0 (2025-11-13)
- ✅ Módulo de proxy isolado e modular
- ✅ Suporte a HTTP, HTTPS, SOCKS5
- ✅ Geo-targeting e session sticky
- ✅ Endpoints de diagnóstico
- ✅ Documentação completa
- ✅ Compatível com múltiplos provedores

---

**Desenvolvido com ❤️ pela equipe WHAGO**

