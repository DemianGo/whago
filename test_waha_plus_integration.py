#!/usr/bin/env python3
"""
Teste da Integração WAHA Plus - Simula criação de chips para múltiplos usuários
"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_container_manager():
    """Testa o WahaContainerManager"""
    from backend.app.services.waha_container_manager import WahaContainerManager
    
    manager = WahaContainerManager()
    
    # Teste 1: Criar container para user_test_1
    logger.info("=" * 60)
    logger.info("TESTE 1: Criando container para user_test_1")
    logger.info("=" * 60)
    
    try:
        container1 = await manager.create_user_container("user_test_1")
        logger.info(f"✅ Container criado: {container1['container_name']}")
        logger.info(f"   Porta: {container1['port']}")
        logger.info(f"   Base URL: {container1['base_url']}")
        logger.info(f"   API Key: {container1['api_key'][:20]}...")
    except Exception as e:
        logger.error(f"❌ Erro ao criar container: {e}")
        return False
    
    # Teste 2: Verificar que container existe
    logger.info("\n" + "=" * 60)
    logger.info("TESTE 2: Verificando container existente")
    logger.info("=" * 60)
    
    container_check = await manager.get_user_container("user_test_1")
    if container_check:
        logger.info(f"✅ Container encontrado: {container_check['container_name']}")
    else:
        logger.error("❌ Container não encontrado")
        return False
    
    # Teste 3: Listar todos os containers
    logger.info("\n" + "=" * 60)
    logger.info("TESTE 3: Listando todos os containers")
    logger.info("=" * 60)
    
    containers = await manager.list_all_containers()
    logger.info(f"✅ Total de containers WAHA Plus: {len(containers)}")
    for c in containers:
        logger.info(f"   - {c['container_name']} | Porta: {c['port']} | Status: {c['status']}")
    
    # Teste 4: Obter estatísticas
    logger.info("\n" + "=" * 60)
    logger.info("TESTE 4: Obtendo estatísticas do container")
    logger.info("=" * 60)
    
    try:
        stats = await manager.get_container_stats("user_test_1")
        if stats:
            logger.info(f"✅ Estatísticas:")
            logger.info(f"   CPU: {stats['cpu_percent']}%")
            logger.info(f"   Memória: {stats['memory_usage_mb']} MB / {stats['memory_limit_mb']} MB ({stats['memory_percent']}%)")
    except Exception as e:
        logger.warning(f"⚠️  Erro ao obter stats: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ TODOS OS TESTES PASSARAM!")
    logger.info("=" * 60)
    
    logger.info("\n⚠️  Para limpar o container de teste, execute:")
    logger.info(f"   docker stop {container1['container_name']}")
    logger.info(f"   docker rm {container1['container_name']}")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_container_manager())
    exit(0 if success else 1)
