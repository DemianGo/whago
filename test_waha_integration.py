#!/usr/bin/env python3
"""
Script para testar integração WAHA com geração de 3 QR Codes.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.waha_client import WAHAClient
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_waha")


async def test_qr_generation():
    """Testa geração de 3 QR Codes com WAHA + Proxy DataImpulse."""
    
    # Configuração do proxy DataImpulse
    PROXY_URL = "socks5://b0d7c401317486d2c3e8__cr.br:f60a2f1e36dcd0b4@gw.dataimpulse.com:824"
    
    waha = WAHAClient(
        base_url="http://localhost:3000",
        api_key="0c5bd2c0cf1b46548db200a2735679e2"
    )
    
    # Lista para armazenar resultados
    results = []
    
    try:
        # =================================================================
        # TESTE 1: Gerar QR Code 1
        # =================================================================
        logger.info("=" * 80)
        logger.info("🔵 TESTE 1: Gerando QR Code #1")
        logger.info("=" * 80)
        
        session1 = await waha.create_session(
            alias="test_user1",
            proxy_url=PROXY_URL,
            tenant_id="tenant_1",
            user_id="user_001",
        )
        
        logger.info(f"✅ Sessão 1 criada: {session1['session_id']}")
        logger.info(f"   Status: {session1['status']}")
        logger.info(f"   Proxy: {'Ativo' if session1.get('proxy_enabled') else 'Desativado'}")
        
        # Aguardar QR Code estar pronto
        await asyncio.sleep(8)
        
        qr1 = await waha.get_qr_code(session1["session_id"])
        logger.info(f"📱 QR Code 1: {qr1['message']}")
        logger.info(f"   Status da sessão: {qr1['status']}")
        
        results.append({
            "test": 1,
            "session_id": session1["session_id"],
            "status": qr1["status"],
            "qr_in_logs": qr1.get("qr_available_in_logs", False),
        })
        
        # Parar e limpar sessão 1
        logger.info("🔴 Parando sessão 1...")
        await waha.delete_session(session1["session_id"])
        await asyncio.sleep(5)
        
        # =================================================================
        # TESTE 2: Gerar QR Code 2
        # =================================================================
        logger.info("=" * 80)
        logger.info("🟢 TESTE 2: Gerando QR Code #2")
        logger.info("=" * 80)
        
        session2 = await waha.create_session(
            alias="test_user2",
            proxy_url=PROXY_URL,
            tenant_id="tenant_2",
            user_id="user_002",
        )
        
        logger.info(f"✅ Sessão 2 criada: {session2['session_id']}")
        logger.info(f"   Status: {session2['status']}")
        
        await asyncio.sleep(8)
        
        qr2 = await waha.get_qr_code(session2["session_id"])
        logger.info(f"📱 QR Code 2: {qr2['message']}")
        logger.info(f"   Status da sessão: {qr2['status']}")
        
        results.append({
            "test": 2,
            "session_id": session2["session_id"],
            "status": qr2["status"],
            "qr_in_logs": qr2.get("qr_available_in_logs", False),
        })
        
        # Parar e limpar sessão 2
        logger.info("🔴 Parando sessão 2...")
        await waha.delete_session(session2["session_id"])
        await asyncio.sleep(5)
        
        # =================================================================
        # TESTE 3: Gerar QR Code 3
        # =================================================================
        logger.info("=" * 80)
        logger.info("🟡 TESTE 3: Gerando QR Code #3")
        logger.info("=" * 80)
        
        session3 = await waha.create_session(
            alias="test_user3",
            proxy_url=PROXY_URL,
            tenant_id="tenant_3",
            user_id="user_003",
        )
        
        logger.info(f"✅ Sessão 3 criada: {session3['session_id']}")
        logger.info(f"   Status: {session3['status']}")
        
        await asyncio.sleep(8)
        
        qr3 = await waha.get_qr_code(session3["session_id"])
        logger.info(f"📱 QR Code 3: {qr3['message']}")
        logger.info(f"   Status da sessão: {qr3['status']}")
        
        results.append({
            "test": 3,
            "session_id": session3["session_id"],
            "status": qr3["status"],
            "qr_in_logs": qr3.get("qr_available_in_logs", False),
        })
        
        # =================================================================
        # RESUMO FINAL
        # =================================================================
        logger.info("=" * 80)
        logger.info("📊 RESUMO DOS TESTES")
        logger.info("=" * 80)
        
        for result in results:
            logger.info(f"Teste #{result['test']}: {result['status']} | QR nos logs: {result['qr_in_logs']}")
        
        # Verificar QR Codes nos logs do Docker
        logger.info("")
        logger.info("🔍 Para ver os QR Codes ASCII, execute:")
        logger.info("   docker logs waha | grep -A 35 '▄▄▄▄▄'")
        
        # Limpar última sessão
        await waha.delete_session(session3["session_id"])
        
    except Exception as e:
        logger.error(f"❌ Erro durante os testes: {e}", exc_info=True)
        raise
    
    finally:
        await waha.close()
        logger.info("✅ Cliente WAHA fechado")


if __name__ == "__main__":
    asyncio.run(test_qr_generation())

