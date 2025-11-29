
import requests
import os
import json

# Simula o payload que o frontend envia
payload = {
    "text": "Ola vendedor tudo bem, seja bem vindo a solução pro para enviar mensagens para o whatsapp. Texto com errros propositais para ver se a ia corrigi.",
    "tone": "persuasive"
}

# Tenta bater no endpoint local do container (assumindo que o script rode dentro ou fora apontando para localhost:8000)
# Como vou rodar de fora, uso localhost:8000
url = "http://localhost:8000/api/v1/ai/rewrite"

# Mock de token (o backend pode exigir, mas vamos ver se o endpoint precisa de auth real ou se posso bypassar para teste rapido.
# O codigo do frontend usa localStorage.getItem('token').
# Vou precisar de um token valido ou desabilitar auth temporariamente no endpoint para teste,
# OU, melhor: vou instanciar o service diretamente num script python para testar a logica do service isolada, sem a camada HTTP/Auth.
# Mas o usuário pediu para simular o uso.

# Abordagem Híbrida:
# 1. Testar o AIService isolado (sem HTTP) para garantir que o Gemini devolve texto diferente.
# 2. Se o Service funcionar, o problema é na Rota ou no Frontend.

import asyncio
from app.services.ai_service import AIService

async def test_service():
    service = AIService()
    text = "Ola vendedor tudo bem, seja bem vindo a solução pro para enviar mensagens para o whatsapp. Texto com errros propositais."
    
    print(f"--- Teste Rewrite (Gemini 2.0 Flash) ---")
    print(f"Original: {text}")
    
    rewritten = await service.rewrite_text(text, tone="persuasive")
    
    print(f"Resultado: {rewritten}")
    
    if text == rewritten:
        print("FALHA: O texto retornado é IDÊNTICO ao original.")
    else:
        print("SUCESSO: O texto foi alterado.")

if __name__ == "__main__":
    asyncio.run(test_service())

