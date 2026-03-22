"""
Configuration management for Accounting Office API
Handles environment variables, database settings, and application configuration
"""

import os
from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Application
    app_name: str = "Accounting Office API"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    workers: int = 1

    # Database
    database_url: str = "sqlite:///./accounting.db"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30
    database_pool_recycle: int = 3600

    # CORS
    cors_origins: List[str] = [
        "http://localhost:3000", 
        "http://localhost:8000",
        "https://frontend-my-webapp.vercel.app"  # Add your Vercel frontend URL
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # Security
    bcrypt_rounds: int = 12
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Email (optional)
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_tls: bool = True

    # File Upload
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    upload_directory: str = "uploads"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        """Parse CORS origins from environment variable"""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_database_url(cls, v):
        """Build database URL from components if not provided"""
        if v and not v.startswith("sqlite"):
            return v

        # Default to SQLite for development
        return "sqlite:///./accounting.db"

    def get_database_url_async(self) -> str:
        """Get database URL for async operations"""
        if self.database_url.startswith("postgresql"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
        return self.database_url


# Global settings instance
settings = Settings()