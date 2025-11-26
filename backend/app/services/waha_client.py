"""
Cliente para integração com WAHA Plus (WhatsApp HTTP API).
Gerencia sessões WhatsApp através de containers Docker dinâmicos.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
import httpx

logger = logging.getLogger("whago.waha")


class WAHAClient:
    """Cliente para comunicação com WAHA API."""

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        api_key: str = "0c5bd2c0cf1b46548db200a2735679e2",
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Obtém ou cria cliente HTTP assíncrono."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"X-Api-Key": self.api_key},
            )
        return self._client

    async def get_sessions(self) -> list[dict[str, Any]]:
        """Obtém todas as sessões (Health Check)."""
        client = await self._get_client()
        response = await client.get("/api/sessions?all=true")
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        """Fecha o cliente HTTP."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def create_session(
        self,
        *,
        alias: str,
        proxy_url: str | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Cria uma nova sessão WAHA.
        
        Args:
            alias: Nome/alias da sessão (usado para identificação)
            proxy_url: URL do proxy SOCKS5/HTTP (formato: socks5://user:pass@host:port)
            tenant_id: ID do tenant (para multi-tenancy)
            user_id: ID do usuário
            **kwargs: Parâmetros adicionais (ignorados, mantidos para compatibilidade)
            
        Returns:
            Dict com session_id, status e outros dados da sessão
        """
        client = await self._get_client()
        
        # ✅ WAHA Plus: Usar alias como nome da sessão (suporte multi-sessão)
        # Cada chip tem sua própria sessão nomeada
        session_name = alias
        
        try:
            # Primeiro, verificar se já existe uma sessão
            try:
                response = await client.get(f"/api/sessions/{session_name}")
                if response.status_code == 200:
                    existing = response.json()
                    logger.info(f"Sessão '{session_name}' já existe com status: {existing.get('status')}")
                    
                    # Se estiver parada, vamos reconfigurar
                    if existing.get("status") in ["STOPPED", "FAILED"]:
                        await self._stop_session(session_name)
                        await asyncio.sleep(2)
            except httpx.HTTPStatusError:
                pass  # Sessão não existe, ok

            # Configurar proxy E fingerprinting dinâmico
            from .fingerprint_service import FingerprintService
            
            # Gerar fingerprint consistente baseado no alias (session_id)
            fingerprint = FingerprintService.get_fingerprint(alias)
            
            # ADAPTAÇÃO PARA NOWEB (BAILEYS)
            # Baileys não suporta metadata/headers complexos como WEBJS/Puppeteer
            # Ele suporta 'browser': ['Ubuntu', 'Chrome', '20.0.04']
            
            config_data = {}
            
            # Extrair dados para formato Baileys se disponível
            if fingerprint.get("metadata"):
                meta = fingerprint["metadata"]
                # Formato: [Descrição OS, Nome Browser, Versão]
                # Ex: ["Whago", "Chrome", "120.0.0"]
                # Se for Android, Baileys tem mode 'mobile' ou custom browser
                
                # Vamos usar um formato Desktop camuflado para estabilidade com NOWEB
                config_data["browser"] = [
                    "Mac OS", # OS Description
                    "Desktop", # Browser Name
                    meta.get("browser_version", "10.15.7") # Version
                ]
                
                # Se quisermos simular mobile com NOWEB, WAHA Plus pode ter config específica
                # Mas 'browser' customizado geralmente é suficiente para diferenciar sessões
            else:
                config_data = fingerprint # Fallback (mas provavelmente não será usado como está)

            if proxy_url:
                # Extrair componentes do proxy URL
                proxy_parts = self._parse_proxy_url(proxy_url)
                config_data["proxy"] = {
                    "server": f"{proxy_parts['protocol']}://{proxy_parts['host']}:{proxy_parts['port']}",
                    "username": proxy_parts.get("username"),
                    "password": proxy_parts.get("password"),
                }

            # Criar ou atualizar sessão
            payload = {
                "name": session_name,
                "config": config_data,
                "engine": "NOWEB", # Forçar NOWEB explicitamente (uppercase)
            }
            
            logger.debug(f"Payload enviado para WAHA create_session: {payload}")

            
            # Retry logic para container que ainda está inicializando
            max_retries = 10
            retry_delay = 2  # segundos (reduzido de 15s para ser mais ágil)
            
            for attempt in range(max_retries):
                try:
                    # Tentar PUT (atualizar)
                    response = await client.put(f"/api/sessions/{session_name}", json=payload)
                    if response.status_code not in [200, 201]:
                        # Se falhar, tentar POST (criar)
                        response = await client.post("/api/sessions", json=payload)
                    
                    response.raise_for_status()
                    session_data = response.json()
                    break  # Sucesso, sair do loop
                    
                except httpx.HTTPStatusError as e:
                    if attempt < max_retries - 1 and e.response.status_code in [400, 503, 502, 504]:
                        # Container ainda não pronto, aguardar e tentar novamente
                        # 400 as vezes é retornado quando engine ainda nao ta pronta
                        logger.warning(
                            f"Tentativa {attempt + 1}/{max_retries} falhou para {session_name} (Status {e.response.status_code}). "
                            f"Aguardando {retry_delay}s..."
                        )
                        await asyncio.sleep(retry_delay)
                    else:
                        # Última tentativa ou erro não recuperável
                        raise
            
            logger.info(
                f"Sessão WAHA configurada: {session_name} | "
                f"Proxy: {'Sim' if proxy_url else 'Não'} | "
                f"User: {user_id} | Tenant: {tenant_id}"
            )
            
            # Iniciar sessão (se não estiver já iniciando/iniciada)
            try:
                start_response = await client.post(f"/api/sessions/{session_name}/start")
                start_response.raise_for_status()
                start_data = start_response.json()
                logger.info(f"Sessão iniciada: {session_name} | Status: {start_data.get('status')}")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 422:
                    # Sessão já está iniciando/iniciada, apenas logar
                    logger.info(f"Sessão {session_name} já estava em andamento")
                else:
                    raise
            
            # Aguardar um pouco para a sessão inicializar
            # await asyncio.sleep(3) # Removido para agilizar retorno ao frontend
            
            # Buscar status atualizado
            try:
                status_response = await client.get(f"/api/sessions/{session_name}")
                if status_response.status_code == 200:
                    final_data = status_response.json()
                else:
                     final_data = {"status": "STARTING"}
            except Exception:
                 final_data = {"status": "STARTING"}
            
            # Session ID curto para caber no VARCHAR(100)
            import hashlib
            # Usar hash do alias completo para manter único mas curto
            alias_hash = hashlib.md5(f"{tenant_id}_{alias}".encode()).hexdigest()[:8]
            short_session_id = f"waha_{alias_hash}"
            
            return {
                "session_id": short_session_id,
                "sessionId": short_session_id,
                "status": final_data.get("status", "STARTING"),
                "waha_session": session_name,
                "alias": alias,
                "proxy_enabled": bool(proxy_url),
                "tenant_id": tenant_id,
                "user_id": user_id,
                "engine": final_data.get("engine", {}),
                "fingerprint": fingerprint,  # Retornar fingerprint usado
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Erro ao criar sessão WAHA: {e}")
            raise Exception(f"Falha na comunicação com WAHA: {e}") from e

    async def get_qr_code(self, session_id: str) -> dict[str, Any]:
        """
        Obtém o QR Code de uma sessão WAHA Plus.
        
        Args:
            session_id: Alias da sessão (ex: chip_<uuid>)
            
        Returns:
            Dict com qr_code (base64), status, etc.
        """
        client = await self._get_client()
        
        # ✅ WAHA Plus: usar o session_id (alias) passado como parâmetro
        # Cada chip tem seu próprio alias único (chip_<uuid>)
        
        try:
            # Verificar status da sessão
            response = await client.get(f"/api/sessions/{session_id}")
            response.raise_for_status()
            session_data = response.json()
            
            status = session_data.get("status", "UNKNOWN")
            
            # Auto-Recuperação: Se estiver parado ou falhou, tentar iniciar para destravar
            if status in ["STOPPED", "FAILED"]:
                try:
                    logger.info(f"Sessão {session_id} está {status}. Enviando comando de START para recuperar...")
                    await client.post(f"/api/sessions/{session_id}/start")
                    return {
                        "qr_code": None,
                        "status": "STARTING",
                        "message": "Reiniciando motor do WhatsApp... Aguarde o QR Code.",
                        "session_id": session_id,
                    }
                except Exception as e:
                    logger.warning(f"Falha ao tentar iniciar sessão {session_id}: {e}")

            # Tentar obter QR Code se status for SCAN_QR_CODE ou STARTING (Otimista)
            if status in ["SCAN_QR_CODE", "STARTING"]:
                # ✅ WAHA Plus: endpoint de QR Code retorna PNG
                try:
                    import base64
                    # Tentar buscar a imagem do QR Code mesmo se estiver STARTING
                    qr_response = await client.get(f"/api/{session_id}/auth/qr")
                    
                    # Se der erro 400/404/500, vai cair no except
                    qr_response.raise_for_status()
                    
                    # Converter PNG para base64
                    qr_png_bytes = qr_response.content
                    qr_base64 = base64.b64encode(qr_png_bytes).decode('utf-8')
                    qr_data_uri = f"data:image/png;base64,{qr_base64}"
                    
                    logger.info(f"QR Code obtido com sucesso para sessão {session_id} (Status: {status})")
                    
                    return {
                        "qr_code": qr_data_uri,
                        "status": status,
                        "session_id": session_id,
                    }
                except httpx.HTTPError as e:
                    # Se falhar e for STARTING, é normal, pede para aguardar
                    if status == "STARTING":
                         return {
                            "qr_code": None,
                            "status": status,
                            "message": "Iniciando motor do WhatsApp. Aguarde alguns segundos...",
                            "session_id": session_id,
                        }
                        
                    logger.warning(f"Erro ao obter QR Code PNG: {e}")
                    return {
                        "qr_code": None,
                        "qr_available_in_logs": True,
                        "status": status,
                        "message": "QR Code ainda não gerado ou disponível nos logs",
                        "session_id": session_id,
                    }
                    
            elif status in ["WORKING", "CONNECTED"]:
                return {
                    "qr_code": None,
                    "status": status,
                    "message": "Sessão já conectada, QR Code não necessário",
                    "session_id": session_id,
                    "phone": session_data.get("me", {}).get("id") if session_data.get("me") else None,
                }
            elif status == "STOPPED":
                # 🔄 AUTO-HEAL: Se estiver parada, forçar início
                try:
                    logger.info(f"Sessão {session_id} está STOPPED. Tentando iniciar automaticamente...")
                    await client.post(f"/api/sessions/{session_id}/start")
                    return {
                        "qr_code": None,
                        "status": "STARTING",
                        "message": "Sessão estava parada. Iniciando... Aguarde.",
                        "session_id": session_id,
                    }
                except Exception as e:
                    logger.error(f"Falha no Auto-Heal da sessão {session_id}: {e}")
                    return {
                        "qr_code": None,
                        "status": status,
                        "message": f"Sessão parada e falha ao iniciar: {str(e)}",
                        "session_id": session_id,
                    }
            else:
                return {
                    "qr_code": None,
                    "status": status,
                    "message": f"Sessão no status: {status}. Aguarde...",
                    "session_id": session_id,
                }
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "status": "NOT_FOUND",
                    "message": "Sessão não encontrada no WAHA.",
                    "session_id": session_id
                }
            logger.error(f"Erro ao obter QR Code (HTTPStatusError): {e}")
            return {
                "qr_code": None,
                "status": "UNAVAILABLE",
                "message": "Serviço indisponível temporariamente.",
                "session_id": session_id,
            }
        except httpx.HTTPError as e:
            logger.error(f"Erro ao obter QR Code (HTTPError): {e}")
            # Se for timeout ou conexão recusada, retornar status especial para frontend não quebrar
            return {
                "qr_code": None,
                "status": "UNAVAILABLE",
                "message": "O serviço do WhatsApp está inicializando ou indisponível. Tentando novamente...",
                "session_id": session_id,
            }
        except Exception as e:
            logger.error(f"Erro genérico ao obter QR Code: {e}")
            return {
                "qr_code": None,
                "status": "ERROR",
                "message": f"Erro interno: {str(e)}",
                "session_id": session_id,
            }

    async def get_session_status(self, session_id: str) -> dict[str, Any]:
        """
        Obtém status de uma sessão WAHA Plus.
        
        Args:
            session_id: Alias da sessão (ex: chip_<uuid>)
            
        Returns:
            Dict com status, dados da conexão, etc.
        """
        client = await self._get_client()
        
        # ✅ WAHA Plus: usar o session_id (alias) correto
        try:
            response = await client.get(f"/api/sessions/{session_id}")
            response.raise_for_status()
            data = response.json()
            
            return {
                "session_id": session_id,
                "status": data.get("status", "UNKNOWN"),
                "connected": data.get("status") in ["WORKING", "CONNECTED"],
                "me": data.get("me"),
                "engine": data.get("engine", {}),
            }
        except httpx.HTTPError as e:
            logger.error(f"Erro ao obter status da sessão: {e}")
            return {
                "session_id": session_id,
                "status": "ERROR",
                "connected": False,
                "error": str(e),
            }

    async def _stop_session(self, session_name: str) -> None:
        """Para uma sessão WAHA."""
        client = await self._get_client()
        try:
            response = await client.post(f"/api/sessions/{session_name}/stop")
            response.raise_for_status()
            logger.info(f"Sessão '{session_name}' parada com sucesso")
        except httpx.HTTPError as e:
            logger.warning(f"Erro ao parar sessão '{session_name}': {e}")

    async def delete_session(self, session_id: str) -> dict[str, Any]:
        """
        Deleta uma sessão WAHA Plus.
        
        Args:
            session_id: Alias da sessão (ex: chip_<uuid>)
            
        Returns:
            Dict com resultado da operação
        """
        client = await self._get_client()
        
        # ✅ WAHA Plus: usar o session_id (alias) correto
        try:
            # Primeiro parar (Tentar 3 vezes)
            for _ in range(3):
                try:
                    await self._stop_session(session_id)
                    await asyncio.sleep(1)
                    break
                except httpx.HTTPError:
                    await asyncio.sleep(1)
            
            # Depois deletar
            response = await client.delete(f"/api/sessions/{session_id}")
            response.raise_for_status()
            
            logger.info(f"Sessão '{session_id}' deletada com sucesso")
            return {"success": True, "session_id": session_id}
            
        except httpx.HTTPError as e:
            # Se der 404, já foi deletada
            if e.response.status_code == 404:
                return {"success": True, "session_id": session_id, "message": "Already deleted"}
                
            logger.error(f"Erro ao deletar sessão: {e}")
            return {"success": False, "session_id": session_id, "error": str(e)}

    async def send_typing(self, session_id: str, chat_id: str) -> None:
        """Envia status 'digitando...' para o chat."""
        client = await self._get_client()
        try:
            await client.post(
                "/api/startTyping",
                json={"session": session_id, "chatId": chat_id}
            )
        except httpx.HTTPError:
            pass  # Ignorar erros de typing (feature visual apenas)

    async def stop_typing(self, session_id: str, chat_id: str) -> None:
        """Para status 'digitando...'."""
        client = await self._get_client()
        try:
            await client.post(
                "/api/stopTyping",
                json={"session": session_id, "chatId": chat_id}
            )
        except httpx.HTTPError:
            pass

    async def mark_seen(self, session_id: str, chat_id: str) -> None:
        """Marca chat como lido (visualizado)."""
        client = await self._get_client()
        try:
            # WAHA Plus usa /api/sendSeen
            await client.post(
                "/api/sendSeen",
                json={"session": session_id, "chatId": chat_id}
            )
        except httpx.HTTPError:
            pass  # Ignorar erros de visualização

    async def set_presence(self, session_id: str, available: bool = True) -> None:
        """
        Define status de presença (Online/Offline).
        available=True -> Online
        available=False -> Offline
        """
        client = await self._get_client()
        # Tentar endpoints específicos primeiro (comum em algumas versões do WAHA Plus)
        endpoint = "/api/sendPresenceAvailable" if available else "/api/sendPresenceUnavailable"
        
        try:
            response = await client.post(
                endpoint,
                json={"session": session_id}
            )
            
            # Se endpoint específico não existe (404), tentar endpoint genérico padrão WAHA
            if response.status_code == 404:
                fallback_endpoint = "/api/sendPresence"
                payload = {
                    "session": session_id,
                    "presence": "available" if available else "unavailable"
                }
                await client.post(fallback_endpoint, json=payload)
                
        except httpx.HTTPError as e:
            # Logar aviso mas não bloquear fluxo principal
            logger.warning(f"Falha não-bloqueante ao definir presença ({endpoint}): {e}")
            pass

    async def send_reaction(self, session_id: str, message_id: str, emoji: str) -> None:
        """Envia reação (emoji) para uma mensagem."""
        client = await self._get_client()
        try:
            await client.post(
                "/api/sendReaction",
                json={
                    "session": session_id,
                    "messageId": message_id,
                    "text": emoji
                }
            )
        except httpx.HTTPError:
            pass

    async def send_message(
        self,
        session_id: str,
        to: str,
        text: str,
    ) -> dict[str, Any]:
        """
        Envia uma mensagem de texto via WAHA Plus.
        
        Args:
            session_id: Alias da sessão (ex: chip_<uuid>)
            to: Número de telefone no formato internacional (ex: 5511999999999)
            text: Conteúdo da mensagem
            
        Returns:
            Dict com resultado do envio
        """
        client = await self._get_client()
        
        try:
            # Garantir formato correto do número (sem + @ ou sufixos)
            phone = to.replace("+", "").replace("@s.whatsapp.net", "").replace("@c.us", "").replace("@", "")
            
            payload = {
                "session": session_id,
                "chatId": f"{phone}@c.us",
                "text": text,
            }
            
            logger.info(f"📨 Enviando para WAHA: session={session_id}, chatId={phone}@c.us")
            
            response = await client.post(
                "/api/sendText",
                json=payload
            )
            
            if response.status_code != 200:
                error_body = response.text
                logger.error(f"❌ WAHA retornou {response.status_code}: {error_body}")
            
            response.raise_for_status()
            
            logger.info(f"Mensagem enviada com sucesso via sessão {session_id} para {phone}")
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            raise Exception(f"Falha ao enviar mensagem via WAHA: {e}") from e

    def _parse_proxy_url(self, proxy_url: str) -> dict[str, Any]:
        """Parse URL de proxy no formato protocol://[user:pass@]host:port"""
        from urllib.parse import urlparse
        
        parsed = urlparse(proxy_url)
        
        return {
            "protocol": parsed.scheme or "socks5",
            "host": parsed.hostname,
            "port": parsed.port or 1080,
            "username": parsed.username,
            "password": parsed.password,
        }


# Instância global (singleton pattern)
_waha_client: WAHAClient | None = None


def get_waha_client() -> WAHAClient:
    """Retorna instância global do cliente WAHA."""
    from ..config import settings
    
    global _waha_client
    if _waha_client is None:
        _waha_client = WAHAClient(
            base_url=settings.waha_api_url,
            api_key=settings.waha_api_key,
        )
    return _waha_client


async def cleanup_waha_client() -> None:
    """Fecha conexões do cliente WAHA."""
    global _waha_client
    if _waha_client:
        await _waha_client.close()
        _waha_client = None

