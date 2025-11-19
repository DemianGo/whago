"""
Rotas administrativas para chips.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models.user import User
from ..models.chip import Chip, ChipStatus

router = APIRouter(prefix="/api/v1/admin/chips", tags=["Admin - Chips"])


__all__ = ["router"]


@router.post("/clean-old-heatup-data")
async def clean_old_heatup_data(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Limpa dados antigos de heat-up de chips do usuário.
    
    Remove heat-up data de chips que:
    - Estão em status MATURING mas sem group_id (heat-up individual antigo)
    - Têm heat-up data inconsistente
    """
    # Buscar chips do usuário com heat-up data
    result = await session.execute(
        select(Chip).where(Chip.user_id == current_user.id)
    )
    chips = result.scalars().all()
    
    cleaned_count = 0
    fixed_count = 0
    
    for chip in chips:
        if not chip.extra_data:
            continue
        
        heat_up_data = chip.extra_data.get("heat_up")
        
        if not heat_up_data:
            continue
        
        # Caso 1: Chip em MATURING sem group_id (sistema antigo)
        if chip.status == ChipStatus.MATURING and not heat_up_data.get("group_id"):
            chip.status = ChipStatus.CONNECTED
            chip.extra_data.pop("heat_up", None)
            cleaned_count += 1
            continue
        
        # Caso 2: Heat-up data sem plan (incompleto)
        if not heat_up_data.get("plan"):
            chip.extra_data.pop("heat_up", None)
            cleaned_count += 1
            continue
        
        # Caso 3: Heat-up data com status inconsistente
        if heat_up_data.get("status") == "in_progress" and chip.status != ChipStatus.MATURING:
            chip.status = ChipStatus.MATURING
            fixed_count += 1
    
    await session.commit()
    
    return {
        "message": f"Limpeza concluída. {cleaned_count} chips limpos, {fixed_count} chips corrigidos.",
        "cleaned": cleaned_count,
        "fixed": fixed_count,
    }

