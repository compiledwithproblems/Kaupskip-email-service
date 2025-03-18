from pydantic_settings import BaseSettings
from typing import Optional
import secrets

class Settings(BaseSettings):
    # Service Info
    SERVICE_NAME: str = "Your Service"
    VERSION: str = "1.0.0"
    
    # Redis Settings
    REDIS_URL: str = "redis://redis:6379"
    
    # SMTP Settings
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)  # Generate a default secret key if not provided
    VERIFICATION_EXPIRY_HOURS: int = 24
    
    # Main App Integration
    MAIN_APP_URL: str = "http://localhost:8000"
    MAIN_APP_SECRET: str = secrets.token_urlsafe(32)  # Generate a default secret if not provided
    SITE_URL: str = "https://example.com"
    # Database Settings
    DATABASE_URL: str = "sqlite:///./email_service.db"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings() 