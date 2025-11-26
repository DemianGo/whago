from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.media_gallery import MediaGalleryItemResponse
from app.services.media_gallery_service import MediaGalleryService

router = APIRouter(prefix="/api/v1/media-gallery", tags=["Media Gallery"])

@router.post("", response_model=MediaGalleryItemResponse, status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None), # Recebe como string comma-separated
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MediaGalleryService(session)
    tags_list = tags.split(",") if tags else None
    return await service.upload_media(current_user, file, category, tags_list)

@router.get("", response_model=List[MediaGalleryItemResponse])
async def list_media(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MediaGalleryService(session)
    return await service.list_media(current_user, category)

@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MediaGalleryService(session)
    await service.delete_media(current_user, media_id)

@router.get("/{media_id}/file")
async def get_media_file(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MediaGalleryService(session)
    path, filename, content_type = await service.get_media_file(current_user, media_id)
    return FileResponse(path, media_type=content_type, filename=filename)

