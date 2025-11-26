from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID, uuid4
from typing import List, Optional

from fastapi import UploadFile, HTTPException, status
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.media_gallery import MediaGalleryItem
from app.models.user import User
from app.schemas.media_gallery import MediaGalleryItemResponse

logger = logging.getLogger("whago.media_gallery")

MEDIA_GALLERY_SUBDIR = "gallery"

class MediaGalleryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _get_storage_path(self) -> Path:
        path = Path(settings.media_root) / MEDIA_GALLERY_SUBDIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _to_response(self, item: MediaGalleryItem) -> MediaGalleryItemResponse:
        return MediaGalleryItemResponse(
            id=item.id,
            filename=item.filename,
            content_type=item.content_type,
            size_bytes=item.size_bytes,
            created_at=item.created_at,
            category=item.category,
            tags=item.tags.split(",") if item.tags else [],
            url=f"/api/v1/media-gallery/{item.id}/file"
        )

    async def upload_media(
        self, 
        user: User, 
        file: UploadFile, 
        category: str | None = None,
        tags: list[str] | None = None
    ) -> MediaGalleryItemResponse:
        if not file:
            raise HTTPException(status_code=400, detail="Arquivo não fornecido.")
        
        content = await file.read()
        size = len(content)
        if size == 0:
            raise HTTPException(status_code=400, detail="Arquivo vazio.")
            
        # Validar tamanho (ex: 16MB)
        max_size = 16 * 1024 * 1024
        if size > max_size:
             raise HTTPException(status_code=413, detail="Arquivo excede o limite de 16MB.")

        # Salvar no disco
        storage_dir = self._get_storage_path()
        extension = Path(file.filename).suffix
        stored_name = f"{uuid4().hex}{extension}"
        file_path = storage_dir / stored_name
        
        file_path.write_bytes(content)
        
        # Salvar no BD
        tags_str = ",".join(tags) if tags else None
        
        item = MediaGalleryItem(
            user_id=user.id,
            filename=file.filename,
            stored_name=stored_name,
            content_type=file.content_type or "application/octet-stream",
            size_bytes=size,
            category=category,
            tags=tags_str
        )
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        
        return self._to_response(item)

    async def list_media(self, user: User, category: str | None = None) -> List[MediaGalleryItemResponse]:
        query = select(MediaGalleryItem).where(MediaGalleryItem.user_id == user.id)
        
        if category:
            query = query.where(MediaGalleryItem.category == category)
            
        query = query.order_by(MediaGalleryItem.created_at.desc())
        
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        return [self._to_response(item) for item in items]

    async def delete_media(self, user: User, media_id: UUID) -> None:
        item = await self.session.get(MediaGalleryItem, media_id)
        if not item or item.user_id != user.id:
            raise HTTPException(status_code=404, detail="Mídia não encontrada.")
            
        # Deletar arquivo
        file_path = self._get_storage_path() / item.stored_name
        if file_path.exists():
            file_path.unlink()
            
        await self.session.delete(item)
        await self.session.commit()

    async def get_media_file(self, user: User, media_id: UUID) -> tuple[Path, str, str]:
        """Retorna (path, filename, content_type)"""
        item = await self.session.get(MediaGalleryItem, media_id)
        if not item or item.user_id != user.id:
            raise HTTPException(status_code=404, detail="Mídia não encontrada.")
            
        file_path = self._get_storage_path() / item.stored_name
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Arquivo não encontrado no disco.")
            
        return file_path, item.filename, item.content_type

