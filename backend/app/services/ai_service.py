"""
Serviço de integração com LLMs (Google Gemini).
"""
import os
import logging
import google.generativeai as genai
from typing import Optional

logger = logging.getLogger("whago.ai")

class AIService:
    def __init__(self):
        # Prioridade: Variável de ambiente > Hardcoded (fallback do usuário)
        self.api_key = os.getenv("GEMINI_API_KEY") or "AIzaSyB-xy1wUh7HyCFt1HcmzdTatOYw1pcSXPw"
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Usar gemini-pro ou flash dependendo da disponibilidade
                self.model = genai.GenerativeModel('gemini-pro') 
                logger.info("AI Service inicializado com Gemini Pro")
            except Exception as e:
                logger.error(f"Erro ao configurar AI Service: {e}")
                self.model = None
        else:
            self.model = None
            logger.warning("GEMINI_API_KEY não encontrada. Funcionalidades de IA estarão indisponíveis.")

    async def rewrite_text(self, text: str, tone: str = "formal") -> str:
        """
        Reescreve um texto usando IA com o tom especificado.
        """
        if not self.model:
            return text # Fallback para o original se não tiver chave

        prompt = f"""
        Você é um especialista em Copywriting para WhatsApp Marketing.
        
        Tarefa: Reescreva a mensagem abaixo.
        Objetivo: Melhorar a clareza, persuasão e evitar bloqueios (anti-spam).
        Tom desejado: {tone} (Ex: Amigável, Profissional, Urgente, Persuasivo).
        
        Mensagem original:
        "{text}"
        
        Retorne APENAS a nova mensagem reescrita, sem aspas, sem explicações e sem introduções.
        """
        
        try:
            # Executar em thread separada para não bloquear loop assíncrono
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Erro ao gerar texto com IA: {e}")
            return text # Fallback em caso de erro

    async def generate_spintax(self, text: str) -> str:
        """
        Gera variações Spintax para o texto fornecido.
        Exemplo: "Olá {amigo|cliente|parceiro}, tudo {bem|joia}?"
        """
        if not self.model:
            return text

        prompt = f"""
        Você é um especialista em Spintax para automação.
        
        Tarefa: Converta a mensagem abaixo para o formato Spintax.
        Formato: Use chaves {{}} e barras verticais | para variações. Ex: {{Olá|Oi|E aí}}
        
        Objetivo: Criar MÁXIMA variabilidade para evitar detecção de spam, mas mantendo o sentido original e a fluidez da leitura.
        
        Regras:
        1. Varie saudações, verbos, adjetivos e conectivos.
        2. Mantenha emojis se fizer sentido, variando-os também.
        3. NÃO altere URLs ou códigos.
        4. O texto resultante deve ser legível em qualquer combinação.

        Mensagem original:
        "{text}"

        Retorne APENAS o texto convertido em Spintax, sem explicações.
        """

        try:
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Erro ao gerar Spintax com IA: {e}")
            return text

# Instância global
ai_service = AIService()
