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
    "/heat-up/global-stats",
)
async def get_global_maturation_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Retorna estatísticas globais de todos os chips em aquecimento."""
    from app.models.chip import Chip, ChipStatus
    from sqlalchemy import select, func, or_
    import logging
    
    logger = logging.getLogger("whago.global_stats")
    
    try:
        # Buscar todos os chips em maturação
        result = await session.execute(
            select(Chip).where(
                Chip.user_id == current_user.id,
                or_(
                    Chip.status == ChipStatus.MATURING,
                    func.jsonb_extract_path_text(Chip.extra_data, 'heat_up', 'status') == 'in_progress'
                )
            )
        )
        chips = result.scalars().all()
        
        active_chips = []
        total_messages_today = 0
        groups = set()
        
        for chip in chips:
            heat_up = chip.extra_data.get("heat_up", {})
            # Contar apenas os que estão em progresso e realmente conectados
            is_heat_active = heat_up.get("status") == "in_progress"
            
            # Se status do chip não for CONNECTED ou CONNECTING, considerar pausado no monitoramento visual
            # Isso evita o "3 conectados, 2 reais"
            if is_heat_active and chip.status in [ChipStatus.CONNECTED, ChipStatus.CONNECTING]:
                groups.add(heat_up.get("group_id"))
                total_messages_today += heat_up.get("messages_sent_in_phase", 0) # Simplificado
                
                # Calcular próxima execução (mesma lógica do individual)
                next_execution = "-"
                last_execution = heat_up.get("last_execution")
                status_emoji = "🔥"
                
                # ... (lógica simplificada de tempo) ...
                
                active_chips.append({
                    "id": str(chip.id),
                    "alias": chip.alias,
                    "phone": chip.phone_number,
                    "phase": heat_up.get("current_phase", 1),
                    "total_messages": heat_up.get("total_messages_sent", 0),
                    "group_id": heat_up.get("group_id"),
                    "last_activity": last_execution,
                })
        
        return {
            "total_active_chips": len(active_chips),
            "total_groups": len(groups),
            "total_messages_sent": sum(c["total_messages"] for c in active_chips),
            "chips": active_chips
        }
            
    except Exception as e:
        logger.error(f"Erro ao buscar stats globais: {e}", exc_info=True)
        return {"error": str(e)}


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
        
        from datetime import datetime, timezone, timedelta
        
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
        
        # Formatar últimas 20 mensagens para exibição (aumentado para ver conversas)
        recent_messages = []
        # Inverter para mostrar mais recentes primeiro
        for msg in reversed(message_history[-20:]):
            try:
                timestamp = datetime.fromisoformat(msg["timestamp"].replace("Z", "+00:00"))
                recent_messages.append({
                    "time": timestamp.strftime("%H:%M:%S"), # Mais detalhado
                    "to": msg.get("to", "N/A"),
                    "message": msg.get("message", ""),
                    "phase": msg.get("phase", current_phase),
                    "type": msg.get("type", "sent") # sent ou reply
                })
            except Exception as e:
                logger.error(f"Erro ao formatar mensagem: {e}")
        
        # Calcular próxima execução estimada
        # Baseado na última execução + intervalo médio da fase atual
        next_execution = "Calculando..."
        last_execution = heat_up_data.get("last_execution")
        if last_execution and heat_up_data.get("status") == "in_progress":
            try:
                last_time = datetime.fromisoformat(last_execution.replace("Z", "+00:00"))
                # Intervalo aproximado (ex: Fase 1 = 3-6 min -> média 4.5 min)
                # Recalcular intervalo baseado na fase
                intervals_map = {1: 4.5, 2: 2.25, 3: 1.5, 4: 1.1, 5: 0.75} # em minutos
                avg_interval_min = intervals_map.get(current_phase, 3)
                
                next_time = last_time + timedelta(minutes=avg_interval_min)
                now = datetime.now(timezone.utc)
                
                if next_time > now:
                     time_diff = next_time - now
                     mins = int(time_diff.total_seconds() / 60)
                     secs = int(time_diff.total_seconds() % 60)
                     next_execution = f"Em ~{mins}m {secs}s"
                else:
                     next_execution = "A qualquer momento..."
            except Exception:
                next_execution = "Em breve"

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
            "next_execution": next_execution,
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



