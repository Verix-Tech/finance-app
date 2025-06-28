import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings and configuration."""
    
    # Database settings
    DATABASE_ENDPOINT: Optional[str] = None
    DATABASE_URL: Optional[str] = None
    DATABASE_USERNAME: Optional[str] = None
    DATABASE_PASSWORD: Optional[str] = None
    DATABASE_PORT: Optional[str] = None
    DATABASE: Optional[str] = None
    
    # Redis settings
    REDIS_SERVER: Optional[str] = None
    
    # Security settings
    SECRET_KEY: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Admin settings
    ADMIN_USERNAME: Optional[str] = None
    ADMIN_EMAIL: Optional[str] = None
    ADMIN_FULL_NAME: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None
    
    # Application settings
    APP_NAME: str = "Finance API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Response messages
    RESPONSE_SUCCESS: str = "Sucesso"
    DATABASE_ERROR: str = "erro ao inserir dados, verifique a consulta"
    SYNTAX_ERROR: str = "erro de sintaxe, verifique os valores"
    NO_SUBSCRIPTION: str = "cliente sem assinatura"
    CLIENT_NOT_EXISTS: str = "cliente não está cadastrado"
    TRANSACTION_NOT_EXISTS: str = "transação não existente"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings() 