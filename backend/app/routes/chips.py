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
    ChipQrResponse,
    ChipResponse,
)
from ..services.chip_service import ChipService


router = APIRouter(prefix="/api/v1/chips", tags=["Chips"])


def _context_from_request(request: Request) -> tuple[str | None, str | None]:
    user_agent = request.headers.get("user-agent")
    client_ip = request.client.host if request.client else None
    return user_agent, client_ip


@router.get("/", response_model=list[ChipResponse])
async def list_chips(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ChipResponse]:
    service = ChipService(session)
    return await service.list_chips(current_user)


@router.post(
    "/",
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


@router.delete(
    "/{chip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_chip(
    chip_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    service = ChipService(session)
    await service.delete_chip(current_user, chip_id)


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



