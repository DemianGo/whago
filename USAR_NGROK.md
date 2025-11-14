# Como Usar Ngrok para Testes

## Instalar Ngrok
```bash
# Download em: https://ngrok.com/download
# Ou via snap:
sudo snap install ngrok
```

## Executar
```bash
ngrok http 8000
```

## Atualizar docker-compose.yml
Copie a URL do ngrok (ex: `https://abc123.ngrok.io`) e atualize:

```yaml
API_URL: "https://abc123.ngrok.io"
FRONTEND_URL: "https://abc123.ngrok.io"
```

## Reiniciar
```bash
docker-compose restart backend
```

Pronto! O Mercado Pago aceitará as URLs e redirecionará corretamente.

