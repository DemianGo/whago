"""
Cliente para integração com WAHA (WhatsApp HTTP API).
Substitui o BaileysClient com funcionalidade equivalente.
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

            # Configurar proxy E fingerprinting se fornecido
            config_data = {}
            
            # ✅ FINGERPRINTING: Simular dispositivo Android real (flat key-value)
            config_data["metadata"] = {
                "platform": "android",
                "browser_name": "Chrome",
                "browser_version": "119.0.0.0",
                "device_manufacturer": "Samsung",
                "device_model": "Galaxy S21",
                "device_os_version": "13"
            }
            
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
            }
            
            # Retry logic para container que ainda está inicializando
            max_retries = 3
            retry_delay = 15  # segundos
            
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
                    if attempt < max_retries - 1 and e.response.status_code in [400, 503]:
                        # Container ainda não pronto, aguardar e tentar novamente
                        logger.warning(
                            f"Tentativa {attempt + 1}/{max_retries} falhou para {session_name}. "
                            f"Aguardando {retry_delay}s antes de retentar..."
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
            await asyncio.sleep(3)
            
            # Buscar status atualizado
            status_response = await client.get(f"/api/sessions/{session_name}")
            status_response.raise_for_status()
            final_data = status_response.json()
            
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
            
            if status == "SCAN_QR_CODE":
                # ✅ WAHA Plus: endpoint de QR Code retorna PNG
                try:
                    import base64
                    qr_response = await client.get(f"/api/{session_id}/auth/qr")
                    qr_response.raise_for_status()
                    
                    # Converter PNG para base64
                    qr_png_bytes = qr_response.content
                    qr_base64 = base64.b64encode(qr_png_bytes).decode('utf-8')
                    qr_data_uri = f"data:image/png;base64,{qr_base64}"
                    
                    logger.info(f"QR Code obtido com sucesso para sessão {session_id}")
                    
                    return {
                        "qr_code": qr_data_uri,
                        "status": status,
                        "session_id": session_id,
                    }
                except httpx.HTTPError as e:
                    logger.warning(f"Erro ao obter QR Code PNG: {e}")
                    return {
                        "qr_code": None,
                        "qr_available_in_logs": True,
                        "status": status,
                        "message": "QR Code disponível nos logs do Docker",
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
            else:
                return {
                    "qr_code": None,
                    "status": status,
                    "message": f"Sessão no status: {status}. Aguarde...",
                    "session_id": session_id,
                }
                
        except httpx.HTTPError as e:
            logger.error(f"Erro ao obter QR Code: {e}")
            raise Exception(f"Falha ao obter QR Code do WAHA: {e}") from e

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
            # Primeiro parar
            await self._stop_session(session_id)
            await asyncio.sleep(2)
            
            # Depois deletar
            response = await client.delete(f"/api/sessions/{session_id}")
            response.raise_for_status()
            
            logger.info(f"Sessão '{session_id}' deletada com sucesso")
            return {"success": True, "session_id": session_id}
            
        except httpx.HTTPError as e:
            logger.error(f"Erro ao deletar sessão: {e}")
            return {"success": False, "session_id": session_id, "error": str(e)}

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

