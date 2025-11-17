#!/usr/bin/env python3
"""
Script standalone para testar WAHA com 3 QR Codes.
Não depende do backend, apenas httpx.
"""

import asyncio
import httpx
import logging
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_waha")

# Configurações
WAHA_URL = "http://localhost:3000"
WAHA_API_KEY = "0c5bd2c0cf1b46548db200a2735679e2"
PROXY_URL = "socks5://b0d7c401317486d2c3e8__cr.br:f60a2f1e36dcd0b4@gw.dataimpulse.com:824"


def parse_proxy_url(proxy_url: str) -> dict:
    """Parse URL de proxy."""
    parsed = urlparse(proxy_url)
    return {
        "protocol": parsed.scheme or "socks5",
        "host": parsed.hostname,
        "port": parsed.port or 1080,
        "username": parsed.username,
        "password": parsed.password,
    }


async def configure_and_start_session(client: httpx.AsyncClient, test_num: int):
    """Configura proxy e inicia sessão WAHA."""
    session_name = "default"
    
    # Parse proxy
    proxy_parts = parse_proxy_url(PROXY_URL)
    
    # Configurar sessão com proxy
    payload = {
        "name": session_name,
        "config": {
            "proxy": {
                "server": f"{proxy_parts['protocol']}://{proxy_parts['host']}:{proxy_parts['port']}",
                "username": proxy_parts["username"],
                "password": proxy_parts["password"],
            }
        }
    }
    
    logger.info(f"[Teste {test_num}] Configurando sessão...")
    response = await client.put(f"/api/sessions/{session_name}", json=payload)
    response.raise_for_status()
    
    logger.info(f"[Teste {test_num}] Iniciando sessão...")
    response = await client.post(f"/api/sessions/{session_name}/start")
    response.raise_for_status()
    
    # Aguardar inicialização
    await asyncio.sleep(8)
    
    # Verificar status
    response = await client.get(f"/api/sessions/{session_name}")
    response.raise_for_status()
    data = response.json()
    
    logger.info(f"[Teste {test_num}] Status: {data.get('status')}")
    
    return data


async def stop_and_clean_session(client: httpx.AsyncClient):
    """Para e limpa sessão."""
    session_name = "default"
    
    try:
        response = await client.post(f"/api/sessions/{session_name}/stop")
        response.raise_for_status()
        logger.info("Sessão parada")
    except Exception as e:
        logger.warning(f"Erro ao parar sessão: {e}")
    
    await asyncio.sleep(3)


async def main():
    """Testa geração de 3 QR Codes."""
    
    headers = {"X-Api-Key": WAHA_API_KEY}
    
    async with httpx.AsyncClient(base_url=WAHA_URL, headers=headers, timeout=30) as client:
        
        results = []
        
        # =================================================================
        # TESTE 1: QR Code #1
        # =================================================================
        logger.info("=" * 80)
        logger.info("🔵 TESTE 1: Gerando QR Code #1")
        logger.info("=" * 80)
        
        try:
            session1 = await configure_and_start_session(client, 1)
            
            if session1.get("status") == "SCAN_QR_CODE":
                logger.info("✅ QR Code #1 GERADO! (disponível nos logs)")
                results.append({"test": 1, "status": "SUCCESS", "qr": "Nos logs do Docker"})
            else:
                logger.warning(f"⚠️ Status inesperado: {session1.get('status')}")
                results.append({"test": 1, "status": session1.get("status"), "qr": "N/A"})
            
            # Parar sessão
            await stop_and_clean_session(client)
            
        except Exception as e:
            logger.error(f"❌ Erro no Teste 1: {e}")
            results.append({"test": 1, "status": "ERROR", "error": str(e)})
        
        # =================================================================
        # TESTE 2: QR Code #2
        # =================================================================
        logger.info("=" * 80)
        logger.info("🟢 TESTE 2: Gerando QR Code #2")
        logger.info("=" * 80)
        
        try:
            session2 = await configure_and_start_session(client, 2)
            
            if session2.get("status") == "SCAN_QR_CODE":
                logger.info("✅ QR Code #2 GERADO! (disponível nos logs)")
                results.append({"test": 2, "status": "SUCCESS", "qr": "Nos logs do Docker"})
            else:
                logger.warning(f"⚠️ Status inesperado: {session2.get('status')}")
                results.append({"test": 2, "status": session2.get("status"), "qr": "N/A"})
            
            await stop_and_clean_session(client)
            
        except Exception as e:
            logger.error(f"❌ Erro no Teste 2: {e}")
            results.append({"test": 2, "status": "ERROR", "error": str(e)})
        
        # =================================================================
        # TESTE 3: QR Code #3
        # =================================================================
        logger.info("=" * 80)
        logger.info("🟡 TESTE 3: Gerando QR Code #3")
        logger.info("=" * 80)
        
        try:
            session3 = await configure_and_start_session(client, 3)
            
            if session3.get("status") == "SCAN_QR_CODE":
                logger.info("✅ QR Code #3 GERADO! (disponível nos logs)")
                results.append({"test": 3, "status": "SUCCESS", "qr": "Nos logs do Docker"})
            else:
                logger.warning(f"⚠️ Status inesperado: {session3.get('status')}")
                results.append({"test": 3, "status": session3.get("status"), "qr": "N/A"})
            
        except Exception as e:
            logger.error(f"❌ Erro no Teste 3: {e}")
            results.append({"test": 3, "status": "ERROR", "error": str(e)})
        
        # =================================================================
        # RESUMO FINAL
        # =================================================================
        logger.info("=" * 80)
        logger.info("📊 RESUMO DOS TESTES")
        logger.info("=" * 80)
        
        success_count = sum(1 for r in results if r.get("status") == "SUCCESS" or r.get("status") == "SCAN_QR_CODE")
        
        for result in results:
            status_icon = "✅" if result.get("status") in ["SUCCESS", "SCAN_QR_CODE"] else "❌"
            logger.info(f"{status_icon} Teste #{result['test']}: {result.get('status')}")
        
        logger.info(f"\n🎯 Total: {success_count}/3 QR Codes gerados com sucesso")
        
        if success_count > 0:
            logger.info("\n🔍 Para ver os QR Codes ASCII, execute:")
            logger.info("   docker logs waha 2>&1 | grep -A 35 '▄▄▄▄▄' | tail -40")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⚠️ Teste interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}", exc_info=True)
        exit(1)

