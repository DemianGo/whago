"""
Tasks para monitoramento e auto-cura (self-healing) da infraestrutura.
"""
import asyncio
import logging
from datetime import datetime, timezone

from app.services.waha_container_manager import WahaContainerManager
from app.services.waha_client import WAHAClient
from tasks.celery_app import celery_app

logger = logging.getLogger("whago.health_tasks")

@celery_app.task(name="check_containers_health")
def check_containers_health():
    """
    Verifica a saúde dos containers WAHA e reinicia os travados.
    Roda a cada 60 segundos.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_check_containers_health_async())
    finally:
        loop.close()

async def _check_containers_health_async():
    manager = WahaContainerManager()
    containers = await manager.list_all_containers()
    
    logger.info(f"🔍 Verificando saúde de {len(containers)} containers...")
    
    for container in containers:
        user_id = container.get("user_id")
        container_name = container.get("container_name")
        
        if not user_id:
            continue
            
        try:
            # Verificar status da API do WAHA (Health Check)
            # Usar o IP interno/porta do container
            base_url = container.get("base_url")
            api_key = container.get("api_key")
            
            if not base_url:
                # Tentar construir se não vier na lista
                port = container.get("port")
                base_url = f"http://localhost:{port}"
            
            # Timeout curto para não travar a task
            waha = WAHAClient(base_url=base_url, api_key=api_key)
            
            # Tentar pegar sessões. Se timeout ou erro 500 constante, está travado.
            # Mas o WAHA tem endpoint de health? Geralmente /api/sessions responde.
            # Se o container está "Running" no Docker mas a API não responde, é travamento.
            
            is_healthy = True
            try:
                # Tenta listar sessões (leve)
                await waha.get_sessions()
            except Exception as e:
                is_healthy = False
                logger.warning(f"⚠️ Container {container_name} não responde API: {e}")
            
            if not is_healthy:
                # Verificar há quanto tempo o container foi criado/iniciado
                # Se acabou de iniciar (< 60s), dá um desconto.
                # Mas Docker 'Created' é string.
                # Vamos assumir que se a task roda a cada 60s e falhou, na proxima se falhar de novo...
                # Melhor: Reiniciar se falhar. O restart do Docker é rápido.
                
                logger.warning(f"🔄 Reiniciando container travado: {container_name}")
                await manager.restart_user_container(user_id)
                
        except Exception as e:
            logger.error(f"Erro ao verificar container {container_name}: {e}")

