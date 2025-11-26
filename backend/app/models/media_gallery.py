from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class MediaGalleryItem(Base):
    __tablename__ = "media_gallery"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    filename: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255)) # Nome no disco
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    
    category: Mapped[str | None] = mapped_column(String(50), nullable=True) # Ex: 'image', 'video', 'audio'
    tags: Mapped[list[str] | None] = mapped_column(String, nullable=True) # Tags separadas por vírgula ou JSONB se fosse PG específico, mas String é mais compatível
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relacionamentos
    # user = relationship("User", back_populates="media_gallery")

