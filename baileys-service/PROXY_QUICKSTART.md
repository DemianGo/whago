# 🚀 Proxy - Guia Rápido (5 minutos)

## ✅ Você já tem as credenciais do Smartproxy?

**Sim?** Ótimo! Siga os passos abaixo.

**Não?** Acesse https://dashboard.smartproxy.com/ e copie suas credenciais.

---

## 📝 Passo 1: Editar `.env`

```bash
cd /home/liberai/whago/baileys-service
nano .env
```

Adicione ou edite estas linhas:

```bash
# Habilitar proxy
PROXY_ENABLED=true

# Tipo de proxy
PROXY_TYPE=http

# Credenciais do Smartproxy
PROXY_HOST=gate.smartproxy.com
PROXY_PORT=7000
PROXY_USERNAME=seu_usuario_aqui
PROXY_PASSWORD=sua_senha_aqui

# Opcional: Escolher país (BR = Brasil)
PROXY_COUNTRY=BR

# Opcional: Session ID (mantém mesmo IP)
PROXY_SESSION_ID=whago_session_1
```

**Salve e feche:** `Ctrl+X`, depois `Y`, depois `Enter`

---

## 🔄 Passo 2: Reiniciar serviço

```bash
cd /home/liberai/whago
docker-compose restart baileys
```

Aguarde 10 segundos.

---

## ✅ Passo 3: Verificar se funcionou

```bash
# Ver logs
docker logs whago-baileys | tail -20
```

Procure por:
```
✅ Proxy HTTP/HTTPS inicializado: http://seu_usuario:****@gate.smartproxy.com:7000
```

**OU**

```bash
# Testar via API
curl -X POST http://localhost:3000/api/v1/proxy/test
```

Resposta esperada:
```json
{
  "status": "ok",
  "message": "Proxy funcionando corretamente"
}
```

---

## 🎯 Passo 4: Criar chip e testar

Agora crie um chip normalmente via frontend ou API.

**Se o QR code aparecer = PROXY FUNCIONANDO! 🎉**

---

## 🐛 Problemas?

### QR não aparece

1. **Aguarde 10-15 minutos** (cooldown do WhatsApp)
2. **Troque o Session ID:**
   ```bash
   nano .env
   # Mude para: PROXY_SESSION_ID=whago_session_2
   docker-compose restart baileys
   ```

### Erro "Proxy habilitado mas credenciais incompletas"

1. Verifique se todas as variáveis estão preenchidas
2. Não deixe espaços em branco
3. Não use aspas nas variáveis

### Erro "ECONNREFUSED"

1. Verifique credenciais no dashboard do Smartproxy
2. Confirme que o plano está ativo
3. Teste com curl:
   ```bash
   curl -x http://usuario:senha@gate.smartproxy.com:7000 https://api.ipify.org
   ```

---

## 📚 Documentação Completa

Para configurações avançadas, consulte:
- `PROXY_README.md` - Documentação completa
- `proxy.env.example` - Exemplo de configuração
- `configure-proxy.sh` - Script interativo

---

## 🆘 Suporte Rápido

```bash
# Ver status do proxy
curl http://localhost:3000/api/v1/proxy/status

# Ver logs em tempo real
docker logs -f whago-baileys | grep -i proxy

# Desabilitar proxy (voltar ao normal)
nano .env
# Mude para: PROXY_ENABLED=false
docker-compose restart baileys
```

---

**Pronto! Seu WHAGO agora usa proxy residencial. 🌐**

