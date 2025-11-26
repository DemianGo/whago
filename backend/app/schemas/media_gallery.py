from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

class MediaGalleryItemBase(BaseModel):
    category: Optional[str] = None
    tags: Optional[list[str]] = None

class MediaGalleryItemCreate(MediaGalleryItemBase):
    pass

class MediaGalleryItemResponse(MediaGalleryItemBase):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    url: str

    model_config = ConfigDict(from_attributes=True)

class MediaGalleryListResponse(BaseModel):
    items: list[MediaGalleryItemResponse]
    total: int

