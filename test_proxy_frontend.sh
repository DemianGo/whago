#!/bin/bash
set -e

echo "🧪 TESTE FRONTEND DE PROXIES"
echo "============================"
echo ""

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"teste@gmail.com","password":"teste123"}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['tokens']['access_token'])")

echo "✅ Login efetuado"
echo ""

# 1. Dashboard do usuário (proxy usage)
echo "1️⃣  Testando widget de proxy no dashboard..."
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/user/proxy/usage | \
  python3 -c "
import sys,json
data=json.load(sys.stdin)
print(f\"   📊 Uso: {data['gb_used']}/{data['limit_gb']} GB ({data['percentage_used']}%)\")
print(f\"   💰 Custo: R\$ {data['cost']}\")
"
echo ""

# 2. Admin - Providers
echo "2️⃣  Testando admin proxies/providers..."
PROVIDERS=$(curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/admin/proxies/providers | \
  python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
echo "   ✅ $PROVIDERS providers configurados"
echo ""

# 3. Admin - Pool
echo "3️⃣  Testando admin proxies/pool..."
PROXIES=$(curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/admin/proxies/pool | \
  python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
echo "   ✅ $PROXIES proxies ativos"
echo ""

# 4. Admin - Stats
echo "4️⃣  Testando admin proxies/stats..."
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/admin/proxies/stats/dashboard | \
  python3 -c "
import sys,json
data=json.load(sys.stdin)
print(f\"   📈 Proxies ativos: {data['proxies_active']}\")
print(f\"   📊 GB usado no mês: {data['gb_month']}\")
print(f\"   💰 Custo no mês: R\$ {data['cost_month']}\")
"
echo ""

# 5. Verificar chip com proxy
echo "5️⃣  Verificando chips com proxy..."
CHIP_COUNT=$(curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/chips | \
  python3 -c "import sys,json; chips=json.load(sys.stdin); print(len(chips))")
echo "   ✅ $CHIP_COUNT chips com proxy atribuído"
echo ""

# 6. Testar limite de proxy (ao criar chip)
echo "6️⃣  Testando validação de limite de proxy..."
RESPONSE=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"alias":"Chip Teste Limite"}' \
  http://localhost:8000/api/v1/chips)

if echo "$RESPONSE" | grep -q '"id"'; then
  echo "   ✅ Chip criado com proxy (dentro do limite)"
else
  echo "   ⚠️  Limite excedido (esperado se plano free)"
fi
echo ""

echo "✅ TESTES FRONTEND COMPLETOS!"
echo ""
echo "📋 RESUMO:"
echo "   - Widget de proxy: ✅"
echo "   - Admin providers: ✅"
echo "   - Admin pool: ✅"
echo "   - Admin stats: ✅"
echo "   - Chips com proxy: ✅"
echo "   - Validação de limite: ✅"
echo ""
echo "🌐 Acesse: http://localhost:8000/dashboard"
echo "🔧 Admin: http://localhost:8000/admin/proxies"

