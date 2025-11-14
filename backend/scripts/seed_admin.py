#!/usr/bin/env python3
"""
Script para criar o primeiro admin do sistema WHAGO.
Uso: python scripts/seed_admin.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from passlib.context import CryptContext
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.admin import Admin

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_super_admin():
    """Cria o super admin inicial"""
    
    email = "admin@whago.com"
    password = "Admin@2024"
    name = "Super Admin"
    
    async with AsyncSessionLocal() as session:
        # Verificar se já existe
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"✅ Admin já existe: {email}")
            
            # Verificar se já tem registro de admin
            stmt = select(Admin).where(Admin.user_id == existing_user.id)
            result = await session.execute(stmt)
            existing_admin = result.scalar_one_or_none()
            
            if not existing_admin:
                admin = Admin(
                    user_id=existing_user.id,
                    role="super_admin",
                    is_active=True
                )
                session.add(admin)
                await session.commit()
                print(f"✅ Registro de admin criado para: {email}")
            else:
                print(f"✅ Registro de admin já existe")
            
            return
        
        # Criar usuário
        user = User(
            email=email,
            password_hash=pwd_context.hash(password),
            name=name,
            phone="+5511999999999",
            is_active=True,
            email_verified=True,
            plan_id=1  # Free plan
        )
        session.add(user)
        await session.flush()
        
        # Criar admin
        admin = Admin(
            user_id=user.id,
            role="super_admin",
            is_active=True
        )
        session.add(admin)
        
        await session.commit()
        
        print("\n" + "="*60)
        print("✅ SUPER ADMIN CRIADO COM SUCESSO!")
        print("="*60)
        print(f"Email: {email}")
        print(f"Senha: {password}")
        print("\n⚠️  IMPORTANTE: Altere a senha após o primeiro login!")
        print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(create_super_admin())

