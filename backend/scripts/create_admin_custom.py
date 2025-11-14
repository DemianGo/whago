#!/usr/bin/env python3
"""
Script para criar um admin customizado no sistema WHAGO.
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


async def create_custom_admin():
    """Cria um admin customizado"""
    
    email = "teste@gmail.com"
    password = "teste123"
    name = "Admin Teste"
    role = "super_admin"
    
    async with AsyncSessionLocal() as session:
        # Verificar se já existe
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"✅ Usuário já existe: {email}")
            
            # Atualizar senha se necessário
            existing_user.password_hash = pwd_context.hash(password)
            
            # Verificar se já tem registro de admin
            stmt = select(Admin).where(Admin.user_id == existing_user.id)
            result = await session.execute(stmt)
            existing_admin = result.scalar_one_or_none()
            
            if not existing_admin:
                admin = Admin(
                    user_id=existing_user.id,
                    role=role,
                    is_active=True
                )
                session.add(admin)
                await session.commit()
                print(f"✅ Registro de admin criado para: {email}")
            else:
                await session.commit()
                print(f"✅ Registro de admin já existe, senha atualizada")
            
            print("\n" + "="*60)
            print("✅ ADMIN ATUALIZADO COM SUCESSO!")
            print("="*60)
            print(f"Email: {email}")
            print(f"Senha: {password}")
            print(f"Role: {role}")
            print("="*60 + "\n")
            return
        
        # Criar usuário
        user = User(
            email=email,
            password_hash=pwd_context.hash(password),
            name=name,
            phone="+5511999999999",
            is_active=True,
            is_verified=True,
            plan_id=1  # Free plan
        )
        session.add(user)
        await session.flush()
        
        # Criar admin
        admin = Admin(
            user_id=user.id,
            role=role,
            is_active=True
        )
        session.add(admin)
        
        await session.commit()
        
        print("\n" + "="*60)
        print("✅ ADMIN CRIADO COM SUCESSO!")
        print("="*60)
        print(f"Email: {email}")
        print(f"Senha: {password}")
        print(f"Role: {role}")
        print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(create_custom_admin())
