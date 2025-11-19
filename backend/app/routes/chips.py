"""
Rotas de gerenciamento de chips.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import AsyncSessionLocal, get_db
from ..dependencies.auth import authenticate_websocket, get_current_user
from ..models.user import User
from ..schemas.chip import (
    ChipCreate,
    ChipEventResponse,
    ChipHeatUpResponse,
    ChipHeatUpGroupRequest,
    ChipHeatUpGroupResponse,
    ChipQrResponse,
    ChipResponse,
)
from ..services.chip_service import ChipService


router = APIRouter(prefix="/api/v1/chips", tags=["Chips"])


def _context_from_request(request: Request) -> tuple[str | None, str | None]:
    user_agent = request.headers.get("user-agent")
    client_ip = request.client.host if request.client else None
    return user_agent, client_ip


@router.get("", response_model=list[ChipResponse])
async def list_chips(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ChipResponse]:
    service = ChipService(session)
    return await service.list_chips(current_user)


@router.post(
    "",
    response_model=ChipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_chip(
    payload: ChipCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ChipResponse:
    user_agent, client_ip = _context_from_request(request)
    service = ChipService(session)
    return await service.create_chip(
        current_user,
        payload,
        user_agent=user_agent,
        ip_address=client_ip,
    )


@router.get(
    "/{chip_id}",
    response_model=ChipResponse,
)
async def retrieve_chip(
    chip_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ChipResponse:
    service = ChipService(session)
    return await service.get_chip(current_user, chip_id)


@router.get(
    "/{chip_id}/events",
    response_model=list[ChipEventResponse],
)
async def list_chip_events(
    chip_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ChipEventResponse]:
    service = ChipService(session)
    return await service.get_chip_events(current_user, chip_id)


@router.get(
    "/{chip_id}/qr",
    response_model=ChipQrResponse,
)
async def get_chip_qr(
    chip_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ChipQrResponse:
    service = ChipService(session)
    return await service.get_qr_code(current_user, chip_id)


@router.post(
    "/{chip_id}/reconnect",
    response_model=ChipResponse,
)
async def reconnect_chip(
    chip_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ChipResponse:
    """Reconecta um chip desconectado, gerando novo QR Code."""
    user_agent, client_ip = _context_from_request(request)
    service = ChipService(session)
    return await service.reconnect_chip(current_user, chip_id, user_agent=user_agent, ip_address=client_ip)


@router.post(
    "/{chip_id}/disconnect",
    response_model=ChipResponse,
)
async def disconnect_chip(
    chip_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ChipResponse:
    service = ChipService(session)
    return await service.disconnect_chip(current_user, chip_id)


@router.post(
    "/{chip_id}/heat-up",
    response_model=ChipHeatUpResponse,
)
async def start_chip_heat_up(
    chip_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ChipHeatUpResponse:
    user_agent, client_ip = _context_from_request(request)
    service = ChipService(session)
    return await service.start_heat_up(
        current_user,
        chip_id,
        user_agent=user_agent,
        ip_address=client_ip,
    )


@router.post(
    "/heat-up/group",
    response_model=ChipHeatUpGroupResponse,
)
async def start_group_heat_up(
    request: Request,
    data: ChipHeatUpGroupRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ChipHeatUpGroupResponse:
    """Inicia aquecimento em grupo (2-10 chips conversando entre si)."""
    from app.services.chip_heat_up_service import ChipHeatUpService
    
    user_agent, client_ip = _context_from_request(request)
    service = ChipHeatUpService(session)
    return await service.start_group_heat_up(
        current_user,
        data,
        user_agent=user_agent,
        ip_address=client_ip,
    )


@router.post(
    "/{chip_id}/stop-heat-up",
)
async def stop_chip_heat_up(
    chip_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Para o aquecimento de um chip."""
    from app.services.chip_heat_up_service import ChipHeatUpService
    
    user_agent, client_ip = _context_from_request(request)
    service = ChipHeatUpService(session)
    return await service.stop_heat_up(
        current_user,
        chip_id,
        user_agent=user_agent,
        ip_address=client_ip,
    )


@router.get(
    "/heat-up/preview-messages",
)
async def get_preview_messages(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Retorna preview das mensagens padrão de aquecimento."""
    from app.services.chip_heat_up_service import DEFAULT_MATURATION_MESSAGES
    
    return {
        "messages": DEFAULT_MATURATION_MESSAGES,
        "total": len(DEFAULT_MATURATION_MESSAGES)
    }


@router.get(
    "/{chip_id}/maturation-stats",
)
async def get_maturation_stats(
    chip_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Retorna estatísticas detalhadas de maturação de um chip."""
    from app.models.chip import Chip
    from sqlalchemy import select
    import logging
    
    logger = logging.getLogger("whago.maturation_stats")
    
    try:
        result = await session.execute(
            select(Chip).where(
                Chip.id == chip_id,
                Chip.user_id == current_user.id
            )
        )
        chip = result.scalar_one_or_none()
        
        if not chip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chip não encontrado."
            )
        
        logger.info(f"Buscando stats para chip {chip.alias} (ID: {chip_id})")
        
        heat_up_data = chip.extra_data.get("heat_up", {}) if chip.extra_data else {}
        
        logger.info(f"Heat-up data: {heat_up_data}")
        
        if not heat_up_data or heat_up_data.get("status") not in ["in_progress", "completed", "stopped"]:
            logger.info(f"Chip {chip.alias} nunca iniciou aquecimento")
            return {
                "chip_id": str(chip.id),
                "alias": chip.alias,
                "status": "never_started",
                "message": "Este chip nunca iniciou aquecimento."
            }
        
        from datetime import datetime, timezone
        
        started_at = heat_up_data.get("started_at")
        current_phase = heat_up_data.get("current_phase", 1)
        messages_sent = heat_up_data.get("messages_sent_in_phase", 0)
        plan = heat_up_data.get("plan", [])
        
        # Calcular tempo decorrido
        elapsed_hours = 0
        if started_at:
            try:
                start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                elapsed_hours = (datetime.now(timezone.utc) - start_time).total_seconds() / 3600
            except Exception as e:
                logger.error(f"Erro ao parsear started_at '{started_at}': {e}")
                elapsed_hours = 0
        
        # Calcular progresso total
        total_hours = sum(stage.get("duration_hours", 0) for stage in plan)
        progress_percent = min(100, (elapsed_hours / total_hours * 100)) if total_hours > 0 else 0
        
        # Determinar se está pronto
        is_ready = heat_up_data.get("status") == "completed" or elapsed_hours >= total_hours
        
        # Buscar histórico de mensagens
        message_history = heat_up_data.get("message_history", [])
        total_messages_sent = heat_up_data.get("total_messages_sent", 0)
        
        # Formatar últimas 10 mensagens para exibição
        recent_messages = []
        for msg in message_history[-10:]:
            try:
                timestamp = datetime.fromisoformat(msg["timestamp"].replace("Z", "+00:00"))
                recent_messages.append({
                    "time": timestamp.strftime("%d/%m %H:%M"),
                    "to": msg.get("to", "N/A"),
                    "message": msg.get("message", "")[:50],
                    "phase": msg.get("phase", current_phase)
                })
            except Exception as e:
                logger.error(f"Erro ao formatar mensagem: {e}")
        
        return {
            "chip_id": str(chip.id),
            "alias": chip.alias,
            "status": heat_up_data.get("status"),
            "current_phase": current_phase,
            "total_phases": len(plan),
            "messages_sent_in_phase": messages_sent,
            "total_messages_sent": total_messages_sent,
            "elapsed_hours": round(elapsed_hours, 2),
            "total_hours": total_hours,
            "progress_percent": round(progress_percent, 2),
            "is_ready_for_campaign": is_ready,
            "started_at": started_at,
            "completed_at": heat_up_data.get("completed_at"),
            "stopped_at": heat_up_data.get("stopped_at"),
            "group_id": heat_up_data.get("group_id"),
            "recent_messages": recent_messages,
            "recommendation": "Chip pronto para campanhas!" if is_ready else f"Aguarde mais {round(total_hours - elapsed_hours, 1)}h para conclusão."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas do chip {chip_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao carregar estatísticas: {str(e)}"
        )


@router.delete(
    "/{chip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_chip(
    chip_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    service = ChipService(session)
    await service.delete_chip(current_user, chip_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.websocket("/ws/{chip_id}/qr")
async def websocket_chip_qr(websocket: WebSocket, chip_id: str) -> None:
    await websocket.accept()
    async with AsyncSessionLocal() as session:
        try:
            user = await authenticate_websocket(websocket, session)
        except HTTPException as exc:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=exc.detail)
            return

        service = ChipService(session)
        try:
            chip_uuid = UUID(chip_id)
        except ValueError:
            await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA, reason="Chip inválido")
            return

        try:
            while True:
                qr_payload = await service.get_qr_code(user, chip_uuid)
                await websocket.send_json(qr_payload.model_dump())
                await asyncio.sleep(5)
        except HTTPException as exc:
            await websocket.send_json({"error": exc.detail})
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason=exc.detail)
        except WebSocketDisconnect:
            return



