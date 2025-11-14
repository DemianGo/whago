"""
Payment Gateway Configuration Model

Permite configurar múltiplos gateways de pagamento via admin.
Suporta múltiplos ambientes (sandbox/production) por gateway.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class PaymentGatewayConfig(Base):
    """
    Configuração de gateways de pagamento.
    
    Permite alternar entre sandbox e produção via admin.
    """
    
    __tablename__ = "payment_gateway_configs"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    
    # Identificação
    gateway: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # mercadopago, paypal, stripe
    name: Mapped[str] = mapped_column(String(100))  # Nome amigável
    
    # Status
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active_mode_production: Mapped[bool] = mapped_column(Boolean, default=False)  # False = sandbox, True = production
    
    # Credenciais Sandbox
    sandbox_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sandbox_public_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sandbox_client_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sandbox_client_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sandbox_webhook_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Credenciais Production
    production_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    production_public_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    production_client_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    production_client_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    production_webhook_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Configurações adicionais (JSON)
    extra_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Metadados
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    
    def get_active_credentials(self) -> dict:
        """
        Retorna as credenciais ativas (sandbox ou production).
        """
        if self.is_active_mode_production:
            return {
                "access_token": self.production_access_token,
                "public_key": self.production_public_key,
                "client_id": self.production_client_id,
                "client_secret": self.production_client_secret,
                "webhook_secret": self.production_webhook_secret,
                "mode": "production",
            }
        else:
            return {
                "access_token": self.sandbox_access_token,
                "public_key": self.sandbox_public_key,
                "client_id": self.sandbox_client_id,
                "client_secret": self.sandbox_client_secret,
                "webhook_secret": self.sandbox_webhook_secret,
                "mode": "sandbox",
            }
    
    @property
    def sandbox_config(self) -> dict | None:
        """Retorna configuração sandbox"""
        if not self.sandbox_access_token:
            return None
        return {
            "access_token": self.sandbox_access_token,
            "public_key": self.sandbox_public_key,
            "client_id": self.sandbox_client_id,
            "client_secret": self.sandbox_client_secret,
            "webhook_secret": self.sandbox_webhook_secret,
        }
    
    @property
    def production_config(self) -> dict | None:
        """Retorna configuração production"""
        if not self.production_access_token:
            return None
        return {
            "access_token": self.production_access_token,
            "public_key": self.production_public_key,
            "client_id": self.production_client_id,
            "client_secret": self.production_client_secret,
            "webhook_secret": self.production_webhook_secret,
        }
    
    def __repr__(self) -> str:
        mode = "PRODUCTION" if self.is_active_mode_production else "SANDBOX"
        status = "ENABLED" if self.is_enabled else "DISABLED"
        return f"<PaymentGatewayConfig {self.gateway} [{mode}] [{status}]>"

