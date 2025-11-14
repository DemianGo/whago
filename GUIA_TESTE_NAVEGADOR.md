# 🧪 Guia de Teste no Navegador - Sistema de Pagamentos

## 🎯 Objetivo

Testar o fluxo completo de assinatura e compra de créditos através da interface do usuário.

---

## ✅ Pré-requisitos

1. ✅ Docker Compose rodando (`docker-compose up -d`)
2. ✅ Backend acessível em `http://localhost:8000`
3. ✅ Frontend acessível em `http://localhost:8000`
4. ✅ Credenciais Mercado Pago Sandbox configuradas

---

## 📝 Teste 1: Assinatura de Plano (Fluxo Completo)

### Passo 1: Acessar Home
1. Abrir navegador em: `http://localhost:8000/`
2. ✅ Verificar: Página Home carrega sem pedir login
3. ✅ Verificar: Três planos são exibidos (Free, Business, Enterprise)
4. ✅ Verificar: Preços estão corretos

### Passo 2: Selecionar Plano
1. Clicar em "Assinar Agora" no **Plano Business** (R$ 97/mês)
2. ✅ Verificar: Modal abre com título "Escolha a Forma de Pagamento"
3. ✅ Verificar: "Mercado Pago" aparece como opção
4. ✅ Verificar: Plano selecionado é mostrado: "Plano: Plano Business"

### Passo 3: Escolher Método de Pagamento
1. Selecionar "Mercado Pago"
2. Clicar em "Continuar"
3. ✅ Verificar: Mensagem aparece: "Você precisa estar logado"
4. ✅ Verificar: Redirecionamento automático para `/register`

### Passo 4: Criar Conta
1. Preencher formulário de registro:
   - **Nome:** Teste Pagamento
   - **Email:** teste.pagamento@example.com
   - **Telefone:** +5511999999999
   - **Senha:** SenhaForte123!
   - **Confirmar Senha:** SenhaForte123!
   - **Empresa:** (opcional)
   - **CPF/CNPJ:** (opcional)
2. Clicar em "Criar Conta"
3. ✅ Verificar: Conta é criada com sucesso
4. ✅ Verificar: Redirecionamento automático para `/billing?action=subscribe`

### Passo 5: Gerar Link de Pagamento
1. Aguardar processamento automático
2. ✅ Verificar: Mensagem "Gerando link de pagamento..." aparece
3. ✅ Verificar: Redirecionamento automático para Mercado Pago
4. ✅ Verificar: URL começa com `https://www.mercadopago.com.br/subscriptions/checkout`

### Passo 6: Simular Pagamento (Sandbox)
**⚠️ IMPORTANTE:** No ambiente sandbox, você **NÃO** deve usar cartão real!

1. Na página do Mercado Pago, usar **cartões de teste:**
   - **Cartão de Crédito (Aprovado):**
     - Número: `5031 4332 1540 6351`
     - Validade: `11/25`
     - CVV: `123`
     - Nome: `APRO`
   - **Cartão de Crédito (Rejeitado):**
     - Número: `5031 4332 1540 6351`
     - Validade: `11/25`
     - CVV: `123`
     - Nome: `OTHE`
2. Preencher dados e confirmar
3. ✅ Verificar: Pagamento é processado
4. ✅ Verificar: Retorno para a aplicação

### Passo 7: Verificar Status da Assinatura
1. Navegar para `/billing` (se não foi automático)
2. ✅ Verificar: Card "Assinatura atual" mostra:
   - **Plano ativo:** Plano Business
   - **Status:** Pendente (até webhook confirmar) ou Ativo (se webhook já processou)
   - **Gateway:** mercadopago
   - **Próxima renovação:** Data futura (30 dias)
3. ✅ Verificar: Botão "Cancelar Assinatura" aparece

---

## 💰 Teste 2: Compra de Créditos

### Passo 1: Acessar Billing (Logado)
1. Estar logado (pode usar conta criada no Teste 1)
2. Acessar: `http://localhost:8000/billing`
3. ✅ Verificar: Página carrega sem erros

### Passo 2: Configurar Compra
1. No card "Comprar créditos avulsos":
   - Campo "Quantidade de créditos": Digitar `1000`
   - ✅ Verificar: "Valor: R$ 100.00" é calculado automaticamente
   - Dropdown "Forma de pagamento": Selecionar "Mercado Pago"

### Passo 3: Confirmar Compra
1. Clicar em "Comprar Créditos"
2. ✅ Verificar: Botão muda para "Processando..."
3. ✅ Verificar: Mensagem "Gerando pagamento..." aparece
4. ✅ Verificar: Mensagem "Redirecionando para pagamento..." aparece
5. ✅ Verificar: Redirecionamento para Mercado Pago
6. ✅ Verificar: URL começa com `https://www.mercadopago.com.br/checkout/v1/redirect`

### Passo 4: Simular Pagamento
1. Usar cartão de teste (mesmo do Teste 1)
2. Confirmar pagamento
3. ✅ Verificar: Retorno para aplicação

### Passo 5: Verificar Créditos
**⚠️ NOTA:** Os créditos só serão adicionados após o webhook confirmar o pagamento!

1. Verificar sidebar: "X créditos"
2. Verificar "Histórico econômico" na página Billing
3. ✅ Verificar: Transação aparece no histórico

---

## ❌ Teste 3: Cancelar Assinatura

### Passo 1: Acessar Billing
1. Estar logado com usuário que tem assinatura ativa
2. Acessar: `http://localhost:8000/billing`

### Passo 2: Cancelar
1. Clicar em "Cancelar Assinatura"
2. ✅ Verificar: Confirmação é solicitada (confirm dialog)
3. Confirmar cancelamento
4. ✅ Verificar: Mensagem "Assinatura cancelada com sucesso!"
5. ✅ Verificar: Página recarrega automaticamente
6. ✅ Verificar: Status muda para "Cancelada"

---

## 🐛 Problemas Comuns e Soluções

### Problema: "Erro ao carregar planos"
**Solução:** Verificar se o backend está rodando e o banco de dados tem planos cadastrados.
```bash
docker-compose logs backend
docker-compose exec backend python -c "from app.database import SessionLocal; from app.models.plan import Plan; db = SessionLocal(); print(db.query(Plan).all())"
```

### Problema: "Método de pagamento não aparece"
**Solução:** Limpar cache do navegador (Ctrl+Shift+R) ou verificar console JavaScript (F12).

### Problema: Redirecionamento para `/undefined`
**Solução:** Verificar se o arquivo `app.js` tem o cache bust atualizado: `1763083452`

### Problema: "Erro ao criar assinatura"
**Solução:** Verificar logs do backend para detalhes:
```bash
docker-compose logs backend --tail 100
```

### Problema: Webhook não é recebido
**⚠️ LIMITAÇÃO LOCAL:** Webhooks do Mercado Pago não chegam em `localhost`!

**Soluções:**
1. **Ngrok (Recomendado para testes):**
   ```bash
   ngrok http 8000
   # Atualizar MERCADOPAGO_WEBHOOK_URL com a URL do ngrok
   ```
2. **Simulação Manual:** Enviar webhook manualmente via curl
3. **Deploy em servidor público:** Testar em ambiente com IP/domínio público

---

## 🔍 Verificação de Logs

### Backend
```bash
# Ver logs em tempo real
docker-compose logs -f backend

# Últimas 50 linhas
docker-compose logs backend --tail 50
```

### Console do Navegador
1. Pressionar `F12` para abrir DevTools
2. Aba "Console" para mensagens JavaScript
3. Aba "Network" para ver requisições HTTP

---

## ✅ Checklist de Validação

### Página Home (/)
- [ ] Carrega sem exigir login
- [ ] Três planos são exibidos
- [ ] Botões "Assinar Agora" funcionam
- [ ] Modal de pagamento abre
- [ ] Mercado Pago está disponível

### Registro (/register)
- [ ] Formulário aceita dados válidos
- [ ] Validações impedem dados inválidos
- [ ] Mensagens de erro são claras
- [ ] Redirecionamento após sucesso funciona
- [ ] Intenção de assinatura é preservada

### Billing (/billing)
- [ ] Requer autenticação
- [ ] Status de assinatura é exibido
- [ ] Compra de créditos funciona
- [ ] Cálculo de preço é correto (R$ 0,10/crédito)
- [ ] Botões estão funcionais

### Integrações
- [ ] Mercado Pago aceita pagamentos sandbox
- [ ] URLs de redirecionamento funcionam
- [ ] Transações são registradas no banco
- [ ] Logs não mostram erros 500

---

## 📞 Suporte

Se encontrar problemas:
1. Verificar logs do backend
2. Verificar console do navegador (F12)
3. Verificar se todas as variáveis de ambiente estão configuradas
4. Verificar se o Docker Compose está rodando

---

## 🎉 Conclusão

Após seguir este guia, você terá testado:
- ✅ Fluxo completo de assinatura
- ✅ Fluxo de compra de créditos
- ✅ Cancelamento de assinatura
- ✅ Integração com Mercado Pago Sandbox
- ✅ Interface de usuário completa

**Sistema 100% funcional e pronto para uso!** 🚀

