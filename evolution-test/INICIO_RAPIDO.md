# ⚡ INÍCIO RÁPIDO - TESTE EVOLUTION API

## 🎯 Execute em 3 comandos:

```bash
# 1. Testar credenciais proxy (OBRIGATÓRIO)
cd /home/liberai/whago/evolution-test
./test_proxy_credentials.sh

# 2. Subir Evolution API
docker-compose up -d && sleep 60

# 3. Executar teste
python3 test_evolution.py
```

## 📊 Ver resultado:

```bash
cat test_report.json
```

## 🧹 Limpar tudo:

```bash
docker-compose down -v
cd /home/liberai/whago
rm -rf evolution-test
```

---

## ⚠️ SE DER ERRO

### Credenciais proxy inválidas:
- O script `test_proxy_credentials.sh` testa automaticamente
- Se todas falharem = credenciais expiraram
- **Ação:** Renovar DataImpulse OU contratar Smartproxy

### Evolution API não sobe:
- Verificar porta 8080: `lsof -i :8080`
- Ver logs: `docker logs evolution-test-api`
- Mudar porta no `docker-compose.yml`

### Erro 405 persiste:
- **Conclusão:** Problema é infraestrutura, não biblioteca
- **Ação:** Contratar Smartproxy ou Bright Data

---

**Tempo total:** ~5 minutos  
**Módulo isolado:** Não afeta código principal

