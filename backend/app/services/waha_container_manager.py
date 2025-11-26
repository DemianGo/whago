"""
WahaContainerManager - Gerenciamento Dinâmico de Containers WAHA Plus

Responsabilidades:
- Criar container WAHA Plus dedicado por usuário
- Gerenciar ciclo de vida (start/stop/restart/delete)
- Alocar portas dinamicamente (3100-3199)
- Configurar volumes para persistência
- Monitorar saúde dos containers
- Cache em Redis
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import docker
from docker.errors import DockerException, NotFound
from redis import asyncio as aioredis

from ..config import settings

logger = logging.getLogger("whago.waha_container_manager")


class WahaContainerManager:
    """Gerenciador de containers WAHA Plus por usuário."""
    
    # Configurações
    IMAGE_NAME = "devlikeapro/waha-plus:latest"
    NETWORK_NAME = "whago_default"
    PORT_RANGE_START = 3100
    PORT_RANGE_END = 3199
    POSTGRES_URL_TEMPLATE = "postgresql://whago:whago123@postgres:5432/whago?sslmode=disable"
    WEBHOOK_URL_TEMPLATE = "http://backend:8000/api/v1/webhooks/waha"
    
    def __init__(self):
        """Inicializa o gerenciador."""
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client inicializado com sucesso")
        except DockerException as e:
            logger.error(f"Erro ao conectar ao Docker: {e}")
            raise
        
        # Redis para cache de mapeamentos user_id -> container_info
        self.redis_client: aioredis.Redis | None = None
    
    async def _get_redis(self) -> aioredis.Redis:
        """Obtém cliente Redis (lazy loading)."""
        if self.redis_client is None:
            self.redis_client = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client
    
    async def _get_available_port(self) -> int:
        """
        Encontra porta disponível no range 3100-3199.
        
        Returns:
            int: Porta disponível
            
        Raises:
            RuntimeError: Se não houver portas disponíveis
        """
        # Obter todas as portas em uso (INCLUINDO PARADOS)
        containers = self.docker_client.containers.list(all=True)
        used_ports = set()
        
        for container in containers:
            if container.name.startswith("waha_plus_user_"):
                # É seguro recarregar atributos para garantir dados de rede atualizados?
                # container.reload() # Pode ser lento, vamos confiar no list(all=True) por enquanto
                
                # Extrair porta mapeada (HostPort)
                # NetworkSettings -> Ports -> '3000/tcp' -> [{'HostIp': '0.0.0.0', 'HostPort': '3100'}]
                ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
                
                if not ports:
                    # Às vezes containers parados não mostram portas em NetworkSettings no list()
                    # Tentar parsing do HostConfig se necessário ou apenas pular
                    continue

                for port_mapping in ports.values():
                    if port_mapping:
                        for mapping in port_mapping:
                            if "HostPort" in mapping:
                                try:
                                    used_ports.add(int(mapping["HostPort"]))
                                except ValueError:
                                    pass
        
        # Encontrar primeira porta disponível
        for port in range(self.PORT_RANGE_START, self.PORT_RANGE_END + 1):
            if port not in used_ports:
                logger.info(f"Porta disponível encontrada: {port}")
                return port
        
        raise RuntimeError(
            f"Nenhuma porta disponível no range {self.PORT_RANGE_START}-{self.PORT_RANGE_END}. "
            f"Limite de {self.PORT_RANGE_END - self.PORT_RANGE_START + 1} usuários simultâneos atingido."
        )
    
    async def create_user_container(self, user_id: str) -> dict[str, Any]:
        """
        Cria container WAHA Plus dedicado para o usuário.
        
        Args:
            user_id: ID do usuário (UUID)
            
        Returns:
            dict: {
                "container_name": str,
                "container_id": str,
                "port": int,
                "base_url": str,
                "status": str
            }
            
        Raises:
            RuntimeError: Se container já existe ou erro na criação
        """
        logger.info(f"Criando container WAHA Plus para user_id: {user_id}")
        
        # Verificar se já existe
        existing = await self.get_user_container(user_id)
        if existing:
            logger.warning(f"Container já existe para user_id {user_id}: {existing['container_name']}")
            return existing
        
        # Alocar porta
        port = await self._get_available_port()
        
        # Nome do container
        container_name = f"waha_plus_user_{user_id}"
        
        # Volume para persistência
        volume_name = f"waha_plus_data_user_{user_id}"
        
        # API Key única por container
        api_key = f"waha_key_{user_id}"
        
        try:
            # Criar container
            container = self.docker_client.containers.run(
                image=self.IMAGE_NAME,
                name=container_name,
                detach=True,
                ports={"3000/tcp": port},
                environment={
                    "WAHA_API_KEY": api_key,
                    # "WHATSAPP_SESSIONS_POSTGRESQL_URL": self.POSTGRES_URL_TEMPLATE, # Desativado para evitar conflitos/locks. Usar SQLite local no volume.
                    "WHATSAPP_HOOK_URL": self.WEBHOOK_URL_TEMPLATE,
                    "WHATSAPP_HOOK_EVENTS": "*",
                    "WAHA_PRINT_QR": "false",

                    # OTIMIZAÇÕES DE RECURSOS (NOWEB - ECONOMIA EXTREMA)
                    "WHATSAPP_DEFAULT_ENGINE": "NOWEB",         # Uppercase (Necessário para WAHA Plus)
                    "WAHA_WORKER_ID": f"waha_worker_{user_id}", # Worker ID único por usuário
                    "WHATSAPP_RECONNECT_INTERVAL": "1000",      # 1 segundo
                    "WAHA_LOG_LEVEL": "DEBUG",                  # Aumentar logs para debug temporário
                    "WHATSAPP_RECONNECT_MAX_ATTEMPTS": "100",   # Tentar muitas vezes antes de desistir
                    "WHATSAPP_NOWEB_MARK_ONLINE_ON_CONNECT": "false", # Controle manual de presença (humanização)
                    # PROTEÇÃO CONTRA MEMORY LEAK (Mesmo usando NOWEB)
                    "WAHA_PUPPETEER_ARGS": "--no-sandbox --disable-gpu --disable-dev-shm-usage --disable-setuid-sandbox --single-process",
                },
                volumes={
                    volume_name: {"bind": "/app/.waha", "mode": "rw"}
                },
                network=self.NETWORK_NAME,
                restart_policy={"Name": "unless-stopped"},
                labels={
                    "whago.service": "waha-plus",
                    "whago.user_id": user_id,
                    "whago.managed": "true"
                }
            )
            
            logger.info(
                f"Container WAHA Plus criado com sucesso: {container_name} "
                f"(ID: {container.id[:12]}, Porta: {port})"
            )
            
            # Aguardar container estar pronto
            # OTIMIZAÇÃO: Reduzido de 180s para 5s. 
            # O frontend tratará a espera com status "STARTING" e "Lazy Creation".
            # Isso evita que a requisição de criação do chip dê timeout (gateway timeout).
            await self._wait_for_container_ready(container_name, port, timeout=5)
            
            # Recarregar container para obter IP atualizado
            container.reload()
            networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
            ip_address = None
            if "whago_default" in networks:
                ip_address = networks["whago_default"].get("IPAddress")
            if not ip_address and networks:
                ip_address = list(networks.values())[0].get("IPAddress")
            
            base_url_final = f"http://{ip_address}:3000" if ip_address else f"http://{container_name}:3000"

            container_info = {
                "container_name": container_name,
                "container_id": container.id,
                "port": port,
                "base_url": base_url_final,  # Acesso via IP para evitar erro de DNS
                "external_url": f"http://localhost:{port}",  # Acesso externo
                "api_key": api_key,
                "status": "running",
                "user_id": user_id,
            }
            
            # Cachear no Redis
            redis = await self._get_redis()
            await redis.setex(
                f"waha:container:{user_id}",
                86400,  # 24 horas
                str(container_info)
            )
            
            return container_info
            
        except DockerException as e:
            logger.error(f"Erro ao criar container para user_id {user_id}: {e}")
            # Tentar limpar se container foi parcialmente criado
            try:
                self.docker_client.containers.get(container_name).remove(force=True)
            except:
                pass
            raise RuntimeError(f"Falha ao criar container WAHA Plus: {e}") from e
    
    async def _wait_for_container_ready(
        self, 
        container_name: str, 
        port: int,
        timeout: int = 60
    ) -> bool:
        """
        Aguarda container estar pronto (API respondendo).
        
        Args:
            container_name: Nome do container
            port: Porta mapeada
            timeout: Timeout em segundos
            
        Returns:
            bool: True se pronto, False se timeout
        """
        import httpx
        
        logger.info(f"Aguardando container {container_name} ficar pronto...")
        
        # Tentar IP direto se possível (passado como argumento?)
        # Por enquanto usa container_name que deve resolver no DNS do Docker
        url = f"http://{container_name}:3000/api/version"
        
        for attempt in range(timeout):
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("tier") == "PLUS":
                            logger.info(
                                f"Container {container_name} pronto! "
                                f"(Versão: {data.get('version')}, Tentativa: {attempt + 1})"
                            )
                            return True
            except Exception:
                # Ainda não está pronto ou DNS ainda não propagou
                pass
            
            await asyncio.sleep(1)
        
        logger.warning(f"Timeout aguardando container {container_name} ficar pronto")
        return False
    
    async def get_user_container(self, user_id: str) -> dict[str, Any] | None:
        """
        Obtém informações do container do usuário.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            dict | None: Informações do container ou None se não existe
        """
        # Tentar cache Redis primeiro
        # Desabilitado para garantir consistência com estado real do Docker
        # try:
        #     redis = await self._get_redis()
        #     cached = await redis.get(f"waha:container:{user_id}")
        #     if cached:
        #         return eval(cached)  # Safe porque é nosso dado
        # except Exception as e:
        #     logger.warning(f"Erro ao acessar cache Redis: {e}")
        
        # Buscar no Docker
        container_name = f"waha_plus_user_{user_id}"
        
        try:
            container = self.docker_client.containers.get(container_name)
            
            # Extrair porta mapeada
            ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
            port_mapping = ports.get("3000/tcp", [{}])[0]
            port = int(port_mapping.get("HostPort", 0))
            
            # Extrair IP Address
            networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
            logger.info(f"DEBUG NETWORKS for {container_name}: {networks.keys()}")
            print(f"DEBUG NETWORKS for {container_name}: {networks.keys()}") # Force stdout
            
            ip_address = None
            if "whago_default" in networks:
                ip_address = networks["whago_default"].get("IPAddress")
            if not ip_address and networks:
                ip_address = list(networks.values())[0].get("IPAddress")
            
            logger.info(f"DEBUG IP for {container_name}: {ip_address}")
            print(f"DEBUG IP for {container_name}: {ip_address}") # Force stdout
            
            container_info = {
                "container_name": container_name,
                "container_id": container.id,
                "port": port,
                "base_url": f"http://{ip_address}:3000" if ip_address else f"http://{container_name}:3000",
                "external_url": f"http://localhost:{port}",
                "api_key": f"waha_key_{user_id}",
                "status": container.status,
                "user_id": user_id,
            }
            
            # Atualizar cache
            redis = await self._get_redis()
            await redis.setex(
                f"waha:container:{user_id}",
                86400,
                str(container_info)
            )
            
            return container_info
            
        except NotFound:
            return None
        except DockerException as e:
            logger.error(f"Erro ao buscar container para user_id {user_id}: {e}")
            return None
    
    async def delete_user_container(self, user_id: str) -> bool:
        """
        Remove container do usuário.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            bool: True se removido com sucesso
        """
        logger.info(f"Removendo container WAHA Plus para user_id: {user_id}")
        
        container_name = f"waha_plus_user_{user_id}"
        
        try:
            container = self.docker_client.containers.get(container_name)
            
            # Parar e remover
            container.stop(timeout=10)
            container.remove(v=True, force=True)  # v=True remove volumes
            
            logger.info(f"Container {container_name} removido com sucesso")
            
            # Limpar cache
            redis = await self._get_redis()
            await redis.delete(f"waha:container:{user_id}")
            
            return True
            
        except NotFound:
            logger.warning(f"Container {container_name} não encontrado")
            return False
        except DockerException as e:
            logger.error(f"Erro ao remover container {container_name}: {e}")
            return False
    
    async def restart_user_container(self, user_id: str) -> bool:
        """
        Reinicia container do usuário.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            bool: True se reiniciado com sucesso
        """
        logger.info(f"Reiniciando container WAHA Plus para user_id: {user_id}")
        
        container_name = f"waha_plus_user_{user_id}"
        
        try:
            container = self.docker_client.containers.get(container_name)
            container.restart(timeout=10)
            
            logger.info(f"Container {container_name} reiniciado com sucesso")
            
            # Invalidar cache
            redis = await self._get_redis()
            await redis.delete(f"waha:container:{user_id}")
            
            return True
            
        except NotFound:
            logger.warning(f"Container {container_name} não encontrado")
            return False
        except DockerException as e:
            logger.error(f"Erro ao reiniciar container {container_name}: {e}")
            return False
    
    async def list_all_containers(self) -> list[dict[str, Any]]:
        """
        Lista todos os containers WAHA Plus gerenciados.
        
        Returns:
            list: Lista de informações de containers
        """
        containers_info = []
        
        try:
            containers = self.docker_client.containers.list(
                filters={"label": "whago.service=waha-plus"}
            )
            
            for container in containers:
                user_id = container.labels.get("whago.user_id")
                
                # Extrair porta com segurança
                ports = container.attrs.get("NetworkSettings", {}).get("Ports") or {}
                port_mapping_list = ports.get("3000/tcp")
                
                port = 0
                if port_mapping_list and len(port_mapping_list) > 0:
                    port = int(port_mapping_list[0].get("HostPort", 0))
                
                # Extrair IP Address para evitar problemas de DNS
                networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
                ip_address = None
                # Priorizar rede padrão do projeto
                if "whago_default" in networks:
                    ip_address = networks["whago_default"].get("IPAddress")
                
                # Fallback
                if not ip_address and networks:
                    ip_address = list(networks.values())[0].get("IPAddress")

                # Base URL interna (IP se possível, senão nome)
                base_url = f"http://{ip_address}:3000" if ip_address else f"http://{container.name}:3000"

                containers_info.append({
                    "container_name": container.name,
                    "container_id": container.id,
                    "port": port,
                    "base_url": base_url,
                    "status": container.status,
                    "user_id": user_id,
                    "created": container.attrs.get("Created"),
                })
            
            logger.info(f"Listados {len(containers_info)} containers WAHA Plus")
            return containers_info
            
        except DockerException as e:
            logger.error(f"Erro ao listar containers: {e}")
            return []
    
    async def cleanup_orphaned_containers(self) -> int:
        """
        Remove containers órfãos (usuários deletados ou inativos > 30 dias).
        
        Returns:
            int: Número de containers removidos
        """
        logger.info("Iniciando limpeza de containers órfãos...")
        
        removed_count = 0
        containers = await self.list_all_containers()
        
        for container_info in containers:
            user_id = container_info.get("user_id")
            
            if not user_id:
                # Container sem user_id é órfão
                logger.warning(f"Container órfão encontrado: {container_info['container_name']}")
                if await self.delete_user_container(user_id or "unknown"):
                    removed_count += 1
        
        logger.info(f"Limpeza concluída: {removed_count} containers órfãos removidos")
        return removed_count
    
    async def get_container_stats(self, user_id: str) -> dict[str, Any] | None:
        """
        Obtém estatísticas de uso do container.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            dict | None: Estatísticas de CPU, memória, etc
        """
        container_name = f"waha_plus_user_{user_id}"
        
        try:
            container = self.docker_client.containers.get(container_name)
            stats = container.stats(stream=False)
            
            # Calcular uso de CPU e memória
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                       stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                          stats["precpu_stats"]["system_cpu_usage"]
            
            cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0
            
            memory_usage = stats["memory_stats"]["usage"]
            memory_limit = stats["memory_stats"]["limit"]
            memory_percent = (memory_usage / memory_limit) * 100.0
            
            # Calcular uso de rede (I/O)
            networks = stats.get("networks", {})
            rx_bytes = sum(n.get("rx_bytes", 0) for n in networks.values())
            tx_bytes = sum(n.get("tx_bytes", 0) for n in networks.values())
            
            return {
                "cpu_percent": round(cpu_percent, 2),
                "memory_usage_mb": round(memory_usage / 1024 / 1024, 2),
                "memory_limit_mb": round(memory_limit / 1024 / 1024, 2),
                "memory_percent": round(memory_percent, 2),
                "network_rx_bytes": rx_bytes,
                "network_tx_bytes": tx_bytes,
            }
            
        except (NotFound, DockerException) as e:
            logger.error(f"Erro ao obter stats do container {container_name}: {e}")
            return None


# Singleton
_manager: WahaContainerManager | None = None


def get_waha_container_manager() -> WahaContainerManager:
    """Retorna instância singleton do gerenciador."""
    global _manager
    if _manager is None:
        _manager = WahaContainerManager()
    return _manager


__all__ = ("WahaContainerManager", "get_waha_container_manager")

