"""
Endpoint para receber webhooks do WAHA Plus.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.chip import Chip, ChipStatus

logger = logging.getLogger("whago.waha_webhooks")

router = APIRouter(prefix="/api/v1/webhooks", tags=["WAHA Webhooks"])


@router.post("/waha", status_code=status.HTTP_200_OK)
async def receive_waha_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Recebe webhooks do WAHA Plus e atualiza status dos chips.
    
    Eventos possíveis:
    - session.status: Mudança de status (SCAN_QR_CODE, WORKING, FAILED, etc.)
    - message: Nova mensagem recebida
    - message.ack: Status de entrega de mensagem
    """
    try:
        payload = await request.json()
        logger.info(f"Webhook WAHA recebido: {payload.get('event')} | Session: {payload.get('session')}")
        
        event = payload.get("event")
        session_name = payload.get("session")
        data = payload.get("payload", {})
        
        if not session_name or not session_name.startswith("chip_"):
            logger.warning(f"Webhook ignorado - sessão inválida: {session_name}")
            return {"status": "ignored", "reason": "invalid_session"}
        
        # Extrair chip_id da sessão (formato: chip_{uuid})
        chip_id_str = session_name.replace("chip_", "")
        
        # Converter para UUID
        try:
            chip_uuid = UUID(chip_id_str)
        except ValueError:
            logger.error(f"Chip ID inválido (não é UUID): {chip_id_str} | Session: {session_name}")
            return {"status": "error", "reason": "invalid_chip_id"}
        
        # Buscar chip
        result = await db.execute(
            select(Chip).where(Chip.id == chip_uuid)
        )
        chip = result.scalar_one_or_none()
        
        if not chip:
            logger.warning(f"Chip não encontrado: {chip_uuid}")
            return {"status": "ignored", "reason": "chip_not_found"}
        
        # Atualizar status baseado no evento
        if event == "session.status":
            waha_status = data.get("status")
            logger.info(f"Chip {chip.id} | Status WAHA: {waha_status}")
            
            # Mapear status WAHA → status WHAGO
            if waha_status == "SCAN_QR_CODE":
                chip.status = ChipStatus.WAITING_QR
            elif waha_status in ["WORKING", "CONNECTED"]:
                chip.status = ChipStatus.CONNECTED
                chip.phone_number = data.get("me", {}).get("id")
            elif waha_status in ["FAILED", "STOPPED"]:
                chip.status = ChipStatus.DISCONNECTED
            
            chip.extra_data = chip.extra_data or {}
            chip.extra_data["waha_status"] = waha_status
            chip.extra_data["last_webhook"] = payload
            
            await db.commit()
            logger.info(f"Chip {chip.id} atualizado | Status: {chip.status}")
        
        elif event == "message":
            # Nova mensagem recebida
            logger.info(f"Mensagem recebida no chip {chip.id}: {data.get('from')}")
            # TODO: Processar mensagem recebida
        
        elif event == "message.ack":
            # Status de entrega de mensagem
            logger.info(f"ACK de mensagem no chip {chip.id}: {data.get('ack')}")
            # TODO: Atualizar status de mensagem enviada
        
        return {"status": "processed", "event": event, "session": session_name}
        
    except Exception as e:
        logger.error(f"Erro fatal no webhook WAHA: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

