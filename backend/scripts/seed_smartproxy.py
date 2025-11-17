"""
Script para cadastrar provedor Smartproxy e proxy rotativo inicial.

Uso: python -m scripts.seed_smartproxy
"""

import asyncio
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import AsyncSessionLocal
from app.models.proxy import ProxyProvider, Proxy


async def seed_smartproxy():
    """Cria provedor Smartproxy e proxy rotativo."""
    async with AsyncSessionLocal() as session:
        try:
            # Verificar se já existe
            from sqlalchemy import select
            result = await session.execute(
                select(ProxyProvider).where(ProxyProvider.name == "Smartproxy BR")
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"✅ Provedor Smartproxy BR já existe (ID: {existing.id})")
                provider_id = existing.id
            else:
                # Criar provedor
                provider = ProxyProvider(
                    name="Smartproxy BR",
                    provider_type="residential",
                    region="BR",
                    cost_per_gb=25.00,  # Ajustar conforme necessário
                    is_active=True,
                    credentials={
                        "server": "proxy.smartproxy.net",
                        "port": 3120,
                        "username": "smart-whagowhago",
                        "password": "FFxfa564fddfX",
                        "api_key": "cac7e3ca1eaabfcf71a70b02565b6700",
                    }
                )
                session.add(provider)
                await session.flush()
                print(f"✅ Provedor Smartproxy BR criado (ID: {provider.id})")
                provider_id = provider.id
            
            # Verificar se proxy rotativo já existe
            result = await session.execute(
                select(Proxy).where(
                    Proxy.provider_id == provider_id,
                    Proxy.proxy_type == "rotating"
                )
            )
            existing_proxy = result.scalar_one_or_none()
            
            if existing_proxy:
                print(f"✅ Proxy rotativo já existe (ID: {existing_proxy.id})")
            else:
                # Criar proxy rotativo
                # Template URL com {session} para sticky session
                proxy = Proxy(
                    provider_id=provider_id,
                    proxy_type="rotating",
                    proxy_url="http://smart-whagowhago-session-{session}:FFxfa564fddfX@proxy.smartproxy.net:3120",
                    region="BR",
                    protocol="http",
                    health_score=100,
                    is_active=True,
                )
                session.add(proxy)
                await session.flush()
                print(f"✅ Proxy rotativo criado (ID: {proxy.id})")
            
            await session.commit()
            print("\n✅ Seed concluído com sucesso!")
            print("\n📝 Informações:")
            print(f"   - Provedor: Smartproxy BR (residencial)")
            print(f"   - Região: Brasil")
            print(f"   - Custo: R$ 25,00/GB (ajustável na admin)")
            print(f"   - Tipo: Rotativo com sticky session")
            print(f"   - Status: Ativo")
            print("\n🔗 Acesse /admin/proxies para gerenciar")
            
        except Exception as exc:
            print(f"❌ Erro: {exc}")
            await session.rollback()
            raise


if __name__ == "__main__":
    print("🌐 Cadastrando Smartproxy...\n")
    asyncio.run(seed_smartproxy())

