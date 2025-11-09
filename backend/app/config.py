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
    
    # Baileys Service
    baileys_api_url: str = "http://baileys:3000"
    baileys_api_key: str = "baileys-secret-key-dev"
    
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

    # CORS
    cors_origins: str = '["http://localhost:3000","http://localhost:8000"]'
    cors_allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Logging
    log_level: str = "INFO"
    
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
