"""
Cliente para integração com Smartproxy.

Gerencia conexões proxy e coleta estatísticas de uso.
"""

import httpx
from typing import Dict, Optional


class SmartproxyClient:
    """Cliente para Smartproxy (proxy residencial)."""

    def __init__(
        self,
        username: str,
        password: str,
        server: str = "proxy.smartproxy.net",
        port: int = 3120,
        api_key: Optional[str] = None,
    ):
        self.username = username
        self.password = password
        self.server = server
        self.port = port
        self.api_key = api_key
        self.base_url = f"http://{username}:{password}@{server}:{port}"

    def get_rotating_proxy_url(self, session_id: str) -> str:
        """
        Retorna URL com sticky session (IP fixo para o session_id).
        
        IMPORTANTE: Cada chip deve ter seu próprio session_id para manter
        o mesmo IP durante toda a vida do chip (simula humano real).
        
        Args:
            session_id: Identificador único (geralmente chip_id)
            
        Returns:
            URL completa do proxy com sticky session
        """
        return f"http://{self.username}-session-{session_id}:{self.password}@{self.server}:{self.port}"

    async def test_connection(self) -> bool:
        """
        Testa se proxy está funcionando.
        
        Returns:
            True se conexão OK, False caso contrário
        """
        try:
            proxies = {
                "http://": self.base_url,
                "https://": self.base_url,
            }
            async with httpx.AsyncClient(proxies=proxies, timeout=10) as client:
                response = await client.get("https://httpbin.org/ip")
                return response.status_code == 200
        except Exception:
            return False

    async def get_current_ip(self, session_id: Optional[str] = None) -> Optional[str]:
        """
        Retorna IP atual do proxy.
        
        Args:
            session_id: Se fornecido, usa sticky session
            
        Returns:
            IP do proxy ou None se falhar
        """
        try:
            proxy_url = (
                self.get_rotating_proxy_url(session_id)
                if session_id
                else self.base_url
            )
            proxies = {"http://": proxy_url, "https://": proxy_url}

            async with httpx.AsyncClient(proxies=proxies, timeout=10) as client:
                response = await client.get("https://httpbin.org/ip")
                if response.status_code == 200:
                    return response.json().get("origin")
        except Exception:
            pass
        return None

    async def get_usage_stats(self) -> Dict:
        """
        Consulta API Smartproxy para obter estatísticas de uso.
        
        NOTA: Implementação depende da API específica do Smartproxy.
        Atualmente retorna estrutura exemplo.
        
        Returns:
            Dicionário com estatísticas de uso
        """
        if not self.api_key:
            return {
                "traffic_used_bytes": 0,
                "error": "API key not configured",
            }

        try:
            # Exemplo de endpoint (ajustar conforme API real)
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    "https://api.smartproxy.com/v2/traffic/usage",
                    headers=headers,
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            return {"traffic_used_bytes": 0, "error": str(e)}

        return {"traffic_used_bytes": 0}

    @classmethod
    def from_credentials_dict(cls, credentials: Dict) -> "SmartproxyClient":
        """
        Cria instância a partir de dicionário de credenciais.
        
        Args:
            credentials: Dict com server, port, username, password, api_key
            
        Returns:
            Instância do SmartproxyClient
        """
        return cls(
            username=credentials.get("username", ""),
            password=credentials.get("password", ""),
            server=credentials.get("server", "proxy.smartproxy.net"),
            port=credentials.get("port", 3120),
            api_key=credentials.get("api_key"),
        )


__all__ = ["SmartproxyClient"]

