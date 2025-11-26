"""
Configurações da aplicação WHAGO Backend
"""
import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações centralizadas da aplicação"""
    
    # Aplicação
    app_name: str = "WHAGO"
    environment: str = "development"
    debug: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    secret_key: str = "your-secret-key-change-in-production"
    
    # Banco de Dados
    database_url: str = "postgresql://whago:whago123@postgres:5432/whago"
    
    # Redis
    redis_url: str = "redis://redis:6379/0"
    redis_campaign_updates_channel: str = "campaign_updates"
    
    # Celery
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"
    celery_task_default_queue: str = "whago_default"
    celery_task_queue_campaigns: str = "whago_campaigns"
    celery_task_soft_time_limit: int = 120
    
    # WAHA Service
    waha_api_url: str = "http://waha:3000"
    waha_api_key: str = "0c5bd2c0cf1b46548db200a2735679e2"
    
    # JWT
    jwt_secret_key: str = "your-jwt-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_minutes: int = 60 * 24 * 7
    password_reset_token_expire_minutes: int = 60
    
    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 100
    rate_limit_login_attempts: int = 5
    rate_limit_login_window_minutes: int = 15
    api_key_rate_limit_per_minute: int = 30

    # CORS
    cors_origins: str = '["http://localhost:3000","http://localhost:8000"]'
    cors_allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Logging
    log_level: str = "INFO"

    # Armazenamento de mídia
    media_upload_dir: str = "media_storage"
    media_root: str = "/app/storage"
    media_base_url: str = "/media"
    media_max_file_size_mb: int = 10
    media_allowed_content_types: List[str] = [
        "image/png",
        "image/jpeg",
        "image/gif",
        "application/pdf",
        "audio/mpeg",
        "audio/ogg",
        "video/mp4",
    ]
    
    # URLs
    api_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:8000"
    
    # Payment Gateways
    # Mercado Pago
    mercadopago_access_token: str = ""
    mercadopago_public_key: str = ""
    mercadopago_webhook_secret: str = ""
    
    # PayPal
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_webhook_id: str = ""
    paypal_mode: str = "sandbox"  # sandbox ou live
    
    # Stripe
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


def get_settings() -> Settings:
    """Retorna instância singleton das configurações"""
    return Settings()


settings = get_settings()
