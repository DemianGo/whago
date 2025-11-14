"""
Coupon Model

Cupons de desconto para planos.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Coupon(Base):
    """
    Modelo de Cupom de Desconto
    """
    __tablename__ = "coupons"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)  # percentage, fixed
    discount_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Coupon {self.code}>"
    
    def is_valid(self) -> bool:
        """Verifica se cupom é válido"""
        now = datetime.utcnow()
        
        if not self.is_active:
            return False
        
        if now < self.valid_from:
            return False
        
        if self.valid_until and now > self.valid_until:
            return False
        
        if self.max_uses and self.times_used >= self.max_uses:
            return False
        
        return True

