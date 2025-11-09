from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    environment: str = Field(default="development", env="ENVIRONMENT")
    database_url: str = Field(default="postgresql://postgres:postgres@whago-postgres:5432/postgres", env="DATABASE_URL")
    redis_url: str = Field(default="redis://whago-redis:6379/0", env="REDIS_URL")
    backend_host: str = Field(default="0.0.0.0", env="BACKEND_HOST")
    backend_port: int = Field(default=8000, env="BACKEND_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")  # <-- ESSA LINHA É A CHAVE
    secret_key: str = Field(default="changeme", env="SECRET_KEY")
    cors_origins: str = Field(default="*", env="CORS_ORIGINS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
