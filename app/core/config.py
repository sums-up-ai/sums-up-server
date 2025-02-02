from pydantic import PostgresDsn, RedisDsn, AnyUrl
from pydantic_settings import BaseSettings
from enum import Enum
from typing import Optional, List

class EnvironmentEnum(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    ENVIRONMENT: EnvironmentEnum = EnvironmentEnum.DEVELOPMENT
    
    PROJECT_NAME: str = "AI API Server"
    APP_VERSION: str = "1.0.0"
    
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    
    DOCS_URL: str = "/docs"
    REDOC_URL: Optional[str] = "/redoc"
    
    SECRET_KEY: str = "your-secret-key-here"

    # Add LOG_LEVEL here
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
