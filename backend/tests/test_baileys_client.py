"""
Testes unitários para o cliente Baileys.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import HTTPException, status

from app.services.baileys_client import BaileysClient


class _DummyAsyncClient:
    def __init__(self, *, response: httpx.Response | None = None, error: Exception | None = None):
        self._response = response
        self._error = error
        self.request_call: tuple[str, str, dict[str, str] | None, dict] | None = None

    async def __aenter__(self) -> "_DummyAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def request(self, method: str, url: str, *, headers: dict[str, str] | None = None, **kwargs) -> httpx.Response:
        self.request_call = (method, url, headers, kwargs)
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


@pytest.mark.asyncio
async def test_send_message_success(monkeypatch):
    request = httpx.Request("POST", "http://baileys/messages/send")
    response = httpx.Response(200, json={"status": "delivered"}, request=request)
    dummy_holder: dict[str, _DummyAsyncClient] = {}

    def _client_factory(*args, **kwargs) -> _DummyAsyncClient:
        dummy = _DummyAsyncClient(response=response)
        dummy_holder["client"] = dummy
        return dummy

    monkeypatch.setattr("app.services.baileys_client.httpx.AsyncClient", _client_factory)

    client = BaileysClient("http://baileys", "super-secret")
    payload = {"session_id": "abc", "to": "+551199999999", "message": "Olá"}

    result = await client.send_message(payload)

    assert result == {"status": "delivered"}
    method, url, headers, kwargs = dummy_holder["client"].request_call
    assert method == "POST"
    assert url == "http://baileys/messages/send"
    assert headers and headers["x-api-key"] == "super-secret"
    assert kwargs["json"] == payload


@pytest.mark.asyncio
async def test_send_message_handles_transport_error(monkeypatch):
    request = httpx.Request("POST", "http://baileys/messages/send")
    error = httpx.ConnectTimeout("timeout", request=request)

    def _client_factory(*args, **kwargs) -> _DummyAsyncClient:
        return _DummyAsyncClient(error=error)

    monkeypatch.setattr("app.services.baileys_client.httpx.AsyncClient", _client_factory)

    client = BaileysClient("http://baileys", "api-key")

    with pytest.raises(HTTPException) as excinfo:
        await client.send_message({"session_id": "abc"})

    assert excinfo.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "Baileys" in excinfo.value.detail


@pytest.mark.asyncio
async def test_send_message_handles_remote_error(monkeypatch):
    request = httpx.Request("POST", "http://baileys/messages/send")
    response = httpx.Response(502, text="failure", request=request)

    def _client_factory(*args, **kwargs) -> _DummyAsyncClient:
        return _DummyAsyncClient(response=response)

    monkeypatch.setattr("app.services.baileys_client.httpx.AsyncClient", _client_factory)

    client = BaileysClient("http://baileys", "api-key")

    with pytest.raises(HTTPException) as excinfo:
        await client.send_message({"session_id": "abc"})

    assert excinfo.value.status_code == status.HTTP_502_BAD_GATEWAY

