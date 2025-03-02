import os
from enum import Enum
from typing import Optional
import torch
from pydantic_settings import BaseSettings

class EnvironmentEnum(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    ENVIRONMENT: EnvironmentEnum = EnvironmentEnum.DEVELOPMENT
    
    PROJECT_NAME: str = "AI API Server"
    
    APP_VERSION: str = "1.0.0"
    
    SERVER_HOST: str = "0.0.0.0"
    
    SERVER_PORT: int = 8080

    AUTO_RELOAD: bool = False
    
    DOCS_URL: str = "/docs"
    
    REDOC_URL: Optional[str] = "/redoc"
    
    SECRET_KEY: str = "your-secret-key-here"

    LOG_LEVEL: str = "INFO"

    MODEL_PATH: str = os.getenv("MODEL_PATH", "C:\\Users\\Janithpm\\Desktop\\sums-up-server\\ai\\summ-model")
    
    DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"
    
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "1000"))
    
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
