# 🔍 Como Acessar o CRUD de Gateways

## 📍 Localização no Menu

O CRUD de Gateways está disponível no **menu lateral esquerdo** do painel admin.

---

## 🚀 Passo a Passo:

### 1️⃣ **Faça Login no Admin**
```
URL: http://localhost:8000/admin/login
Email: teste@gmail.com
Senha: teste123
```

### 2️⃣ **Procure no Menu Lateral Esquerdo**

O menu lateral está organizado assim:

```
┌─────────────────────────────┐
│   WHAGO                     │
│   Admin Panel               │
├─────────────────────────────┤
│ 📊 Dashboard                │
│ 👥 Usuários                 │
│ 📦 Planos                   │
│ 🎟️  Cupons                  │
│ 💵 Transações               │
│ 💳 Gateways de Pagamento ← AQUI!
│ 🛡️  Administradores         │
│ 📋 Logs                     │
│ ← Voltar ao Sistema         │
└─────────────────────────────┘
```

### 3️⃣ **Clique em "Gateways de Pagamento"**

Você será redirecionado para: `http://localhost:8000/admin/gateways`

---

## 🎯 URLs Diretas:

| Página | URL |
|--------|-----|
| **Login Admin** | http://localhost:8000/admin/login |
| **Gateways** | http://localhost:8000/admin/gateways |

---

## ✅ O que você verá:

### Página de Gateways:
- 💳 **Mercado Pago** (azul)
- 🅿️ **PayPal** (azul escuro)
- 💰 **Stripe** (roxo)

Cada um com:
- Status: ✅ Habilitado / ❌ Desabilitado
- Modo: 🧪 Sandbox / 💰 Produção
- Botão **"🛠️ Configurar"**

---

## 🔧 Para Configurar um Gateway:

1. Clique no botão **"🛠️ Configurar"** no card do gateway
2. Um modal se abrirá com:
   - Toggle para habilitar/desabilitar
   - Seletor de modo (Sandbox/Produção)
   - Campos para credenciais Sandbox (fundo amarelo)
   - Campos para credenciais Produção (fundo vermelho)
3. Preencha as credenciais necessárias
4. Clique em **"💾 Salvar Configuração"**
5. Mensagem de sucesso aparecerá

---

## 🐛 Problemas Comuns:

### ❌ Não vejo o link no menu
**Solução:** Certifique-se de que você está logado como admin:
```bash
Email: teste@gmail.com
Senha: teste123
```

### ❌ Página não carrega
**Solução:** Verifique se o backend está rodando:
```bash
docker-compose ps backend
```

### ❌ Erro 401 (Não autorizado)
**Solução:** Faça logout e login novamente:
1. Clique em "Sair" no canto superior direito
2. Faça login novamente

### ❌ Erro 403 (Acesso negado)
**Solução:** Apenas super_admin pode editar gateways. Verifique se você é super_admin.

---

## 🎨 Preview Visual do Menu:

```css
/* Menu Lateral Completo */

WHAGO Admin Panel
═══════════════════════════════

📊 Dashboard                    ← Página inicial
👥 Usuários                     ← Gerenciar usuários do sistema
📦 Planos                       ← Gerenciar planos de assinatura
🎟️  Cupons                      ← Criar cupons de desconto
💵 Transações                   ← Histórico de pagamentos
💳 Gateways de Pagamento        ← CRUD DE GATEWAYS (AQUI!)
🛡️  Administradores             ← Gerenciar admins
📋 Logs                         ← Auditoria de ações
← Voltar ao Sistema            ← Retorna ao dashboard normal
```

---

## 📱 Atalho de Teclado (Futuro):

Para facilitar, você pode digitar diretamente na URL:

```
http://localhost:8000/admin/gateways
```

Ou use o atalho (se estiver logado):
- Pressione `/` e digite "gateways"

---

## 🔐 Permissões:

| Ação | Permissão Necessária |
|------|---------------------|
| Ver gateways | Qualquer admin |
| Configurar gateways | super_admin |

---

## ✨ Recursos Disponíveis:

✅ Listar todos os gateways (GET)
✅ Ver detalhes de um gateway (GET)
✅ Atualizar configurações (PUT)
✅ Habilitar/Desabilitar gateway
✅ Alternar modo Sandbox/Produção
✅ Configurar credenciais Sandbox
✅ Configurar credenciais Produção
✅ Audit log de todas as alterações

---

**Pronto!** Agora você sabe exatamente onde encontrar o CRUD de Gateways! 🚀

Se ainda tiver problemas, verifique:
1. ✅ Backend rodando: `docker-compose ps`
2. ✅ Logged como admin: `teste@gmail.com`
3. ✅ URL correta: `http://localhost:8000/admin/gateways`

