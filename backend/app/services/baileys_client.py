"""
Cliente para o serviço Baileys (Node.js).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import httpx
from fastapi import HTTPException, status

from ..config import settings

logger = logging.getLogger("whago.baileys")


class BaileysClient:
    """Encapsula chamadas ao serviço Baileys."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}{path}"
        timeout = kwargs.pop("timeout", 30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.request(
                    method,
                    url,
                    headers=self._headers(),
                    **kwargs,
                )
            except httpx.RequestError as exc:
                logger.error("Falha ao comunicar com Baileys: %s", exc)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Serviço Baileys indisponível.",
                ) from exc

        if response.status_code >= 400:
            logger.warning("Erro do Baileys (%s): %s", response.status_code, response.text)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Baileys retornou erro.",
            )

        if response.content:
            return response.json()
        return None

    async def create_session(
        self, 
        alias: str, 
        proxy_url: str | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        preferred_manufacturer: str | None = None,
        timing_profile: str | None = None,
        activity_pattern: str | None = None
    ) -> dict[str, Any]:
        """
        Cria uma sessão Baileys com suporte completo ao Sistema Anti-Block.
        
        Args:
            alias: Nome/alias da sessão
            proxy_url: URL do proxy (opcional)
            tenant_id: ID do tenant para isolamento multi-tenant
            user_id: ID do usuário
            preferred_manufacturer: Fabricante preferido para fingerprint (Samsung, Motorola, Xiaomi, etc)
            timing_profile: Perfil de timing (very_slow, slow, normal, fast, very_fast, corporate, casual, distracted)
            activity_pattern: Padrão de atividade (corporate, night_owl, early_bird, balanced, casual, always_on)
        """
        payload = {"alias": alias}
        
        if proxy_url:
            payload["proxy_url"] = proxy_url
        if tenant_id:
            payload["tenant_id"] = tenant_id
        if user_id:
            payload["user_id"] = user_id
        if preferred_manufacturer:
            payload["preferred_manufacturer"] = preferred_manufacturer
        if timing_profile:
            payload["timing_profile"] = timing_profile
        if activity_pattern:
            payload["activity_pattern"] = activity_pattern
            
        return await self._request("POST", "/sessions/create", json=payload)

    async def delete_session(self, session_id: str) -> None:
        await self._request("DELETE", f"/sessions/{session_id}")

    async def disconnect_session(self, session_id: str) -> None:
        await self._request("POST", f"/sessions/{session_id}/disconnect")

    async def get_session(self, session_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/sessions/{session_id}")

    async def get_qr_code(self, session_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/sessions/{session_id}/qr")

    async def send_message(self, payload: dict[str, Any]) -> Any:
        return await self._request("POST", "/messages/send", json=payload)


@lru_cache(maxsize=1)
def get_baileys_client() -> BaileysClient:
    return BaileysClient(
        base_url=settings.baileys_api_url,
        api_key=settings.baileys_api_key,
    )


__all__ = ("BaileysClient", "get_baileys_client")


