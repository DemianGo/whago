# ✅ Modo Sandbox do Mercado Pago - JÁ ATIVADO!

## 🎯 Status Atual

O modo **SANDBOX** do Mercado Pago já está **100% ATIVADO** e configurado no sistema!

---

## 📋 Configurações Atuais

### No `docker-compose.yml`:

```yaml
# Mercado Pago (Sandbox/Test)
MERCADOPAGO_ACCESS_TOKEN: "TEST-6266967508496749-102011-9d5e58c0bd298f8ef2dc5210014a9245-2937021508"
MERCADOPAGO_PUBLIC_KEY: "TEST-1007ffce-416a-49cc-8888-ded9dd8cf368"
MERCADOPAGO_WEBHOOK_SECRET: "mercadopago-webhook-secret"
MERCADOPAGO_MODE: "sandbox"
```

### Credenciais Sandbox:

- **Access Token:** `TEST-6266967508496749-102011-9d5e58c0bd298f8ef2dc5210014a9245-2937021508`
- **Public Key:** `TEST-1007ffce-416a-49cc-8888-ded9dd8cf368`
- **Modo:** `sandbox` ✅
- **Conta:** demianesobar@gmail.com

---

## ✅ Como Identificar que Está em Sandbox

1. **Access Token começa com `TEST-`** ✅
2. **Public Key começa com `TEST-`** ✅
3. **Variável `MERCADOPAGO_MODE: "sandbox"`** ✅

---

## 🧪 Como Testar Pagamentos (Sandbox)

### Passo 1: Acessar a Aplicação
```bash
# Abrir no navegador
http://localhost:8000/
```

### Passo 2: Selecionar um Plano
1. Clicar em "Assinar Agora" no **Plano Business**
2. Escolher **Mercado Pago**
3. Fazer login ou criar conta

### Passo 3: Usar Cartões de Teste

**⚠️ IMPORTANTE:** No sandbox, use APENAS cartões de teste do Mercado Pago!

#### Cartão para Pagamento APROVADO:
```
Número do Cartão: 5031 4332 1540 6351
Nome no Cartão: APRO
Validade: 11/25
CVV: 123
CPF: Qualquer CPF válido (ex: 12345678909)
```

#### Cartão para Pagamento REJEITADO:
```
Número do Cartão: 5031 4332 1540 6351
Nome no Cartão: OTHE
Validade: 11/25
CVV: 123
CPF: Qualquer CPF válido
```

#### Outros Cenários de Teste:
```
# Pagamento pendente
Nome: CONT

# Chamada para autorização
Nome: CALL

# Pagamento rejeitado por dados inválidos
Nome: FUND

# Pagamento rejeitado por valor alto
Nome: SECU
```

---

## 🔍 Verificar Status do Sandbox

Execute este comando para confirmar:

```bash
cd /home/liberai/whago
docker-compose exec backend python -c "
from app.config import settings
print('=== CONFIGURAÇÃO MERCADO PAGO ===')
print(f'Access Token: {settings.mercadopago_access_token[:20]}...')
print(f'Public Key: {settings.mercadopago_public_key[:20]}...')
print(f'É Sandbox? {\"SIM\" if settings.mercadopago_access_token.startswith(\"TEST-\") else \"NÃO\"}')
"
```

---

## 🎯 Fluxo Completo de Teste

### 1. Teste de Assinatura (Recorrente)

```bash
# 1. Fazer login ou criar conta
# 2. Acessar http://localhost:8000/
# 3. Selecionar "Plano Business"
# 4. Escolher "Mercado Pago"
# 5. Será redirecionado para Mercado Pago (sandbox)
# 6. Usar cartão APRO para aprovar
# 7. Aguardar redirecionamento
# 8. Verificar status em /billing
```

### 2. Teste de Compra de Créditos (One-time)

```bash
# 1. Fazer login
# 2. Acessar http://localhost:8000/billing
# 3. No card "Comprar créditos avulsos"
# 4. Digitar quantidade: 1000
# 5. Selecionar "Mercado Pago"
# 6. Clicar em "Comprar Créditos"
# 7. Será redirecionado para Mercado Pago (sandbox)
# 8. Usar cartão APRO para aprovar
# 9. Aguardar redirecionamento
# 10. Verificar créditos na sidebar
```

---

## 🧪 Teste via cURL

### Criar Assinatura:
```bash
cd /home/liberai/whago

# 1. Fazer login primeiro
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "seu_email@example.com",
    "password": "sua_senha"
  }' | jq -r '.tokens.access')

# 2. Criar assinatura
curl -s -X POST http://localhost:8000/api/v1/payments/subscriptions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "plan_id": 2,
    "payment_method": "mercadopago"
  }' | jq '.'
```

### Comprar Créditos:
```bash
curl -s -X POST http://localhost:8000/api/v1/payments/credits \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "credits": 1000,
    "payment_method": "mercadopago"
  }' | jq '.'
```

---

## 🔄 Como Alternar para Produção (Futuro)

Quando for para produção, você precisará:

### 1. Obter Credenciais de Produção
1. Acessar: https://www.mercadopago.com.br/developers/panel/app
2. Selecionar sua aplicação
3. Ir em "Credenciais de produção"
4. Copiar `Access Token` e `Public Key` (SEM o prefixo `TEST-`)

### 2. Atualizar docker-compose.yml
```yaml
# Mercado Pago (PRODUCTION)
MERCADOPAGO_ACCESS_TOKEN: "APP_USR-xxxxxxxx-xxxxxxxx"  # SEM TEST-
MERCADOPAGO_PUBLIC_KEY: "APP_USR-xxxxxxxx-xxxxxxxx"     # SEM TEST-
MERCADOPAGO_WEBHOOK_SECRET: "seu-webhook-secret"
MERCADOPAGO_MODE: "production"
```

### 3. Reiniciar Backend
```bash
docker-compose restart backend
```

---

## ⚠️ Limitações do Sandbox

### Webhooks Locais
**Problema:** Webhooks do Mercado Pago não conseguem alcançar `localhost`!

**Soluções:**

#### Opção 1: Ngrok (Recomendado para testes)
```bash
# Instalar ngrok
# https://ngrok.com/download

# Expor porta 8000
ngrok http 8000

# Você receberá uma URL tipo:
# https://abc123.ngrok.io

# Atualizar docker-compose.yml:
API_URL: "https://abc123.ngrok.io"
FRONTEND_URL: "https://abc123.ngrok.io"

# Reiniciar
docker-compose restart backend
```

#### Opção 2: Simular Webhook Manualmente
```bash
# Simular webhook de pagamento aprovado
curl -X POST http://localhost:8000/api/v1/payments/webhook/mercadopago \
  -H "Content-Type: application/json" \
  -d '{
    "type": "payment",
    "data": {
      "id": "123456789"
    },
    "action": "payment.created"
  }'
```

#### Opção 3: Deploy em Servidor Público
- Deploy no Heroku, AWS, Digital Ocean, etc.
- Mercado Pago conseguirá enviar webhooks

---

## 📊 Monitoramento de Testes

### Ver Logs do Backend:
```bash
docker-compose logs -f backend | grep -i "mercado\|payment"
```

### Ver Transações no Banco:
```bash
docker-compose exec postgres psql -U whago -d whago -c "
SELECT 
  id, 
  user_id, 
  type, 
  amount, 
  status, 
  payment_method,
  created_at 
FROM transactions 
ORDER BY created_at DESC 
LIMIT 10;
"
```

### Ver Assinaturas de Usuários:
```bash
docker-compose exec postgres psql -U whago -d whago -c "
SELECT 
  id, 
  email, 
  subscription_id, 
  subscription_status,
  subscription_gateway,
  next_billing_date
FROM users 
WHERE subscription_id IS NOT NULL;
"
```

---

## 🎉 Resumo

✅ **Modo Sandbox ATIVO**  
✅ **Credenciais Configuradas**  
✅ **Sistema Pronto para Testes**  
✅ **Cartões de Teste Disponíveis**  
✅ **Documentação Completa**

**Você pode começar a testar pagamentos agora mesmo!** 🚀

---

## 📚 Referências

- [Mercado Pago - Cartões de Teste](https://www.mercadopago.com.br/developers/pt/docs/your-integrations/test/cards)
- [Mercado Pago - Sandbox](https://www.mercadopago.com.br/developers/pt/docs/your-integrations/test/accounts)
- [Documentação WHAGO - Testes](./GUIA_TESTE_NAVEGADOR.md)

---

**Última Atualização:** 14/11/2025 - 18:45 BRT

