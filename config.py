"""
Configuration management for Accounting Office API
Handles environment variables, database settings, and application configuration
"""

import json
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    app_name: str = "Accounting Office API"
    app_version: str = "1.1.0"
    debug: bool = False
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    workers: int = 1

    database_url: str = "sqlite:///./accounting.db"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30
    database_pool_recycle: int = 3600

    cors_origins: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://frontend-my-webapp.vercel.app",
        "https://erp.aboelmagdzaid.online"
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: Union[List[str], str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    cors_allow_headers: Union[List[str], str] = ["*"]

    bcrypt_rounds: int = 12
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_tls: bool = True

    max_upload_size: int = 10 * 1024 * 1024
    upload_directory: str = "uploads"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            value = v.strip().lower()
            if value in {"1", "true", "yes", "on", "debug", "development", "dev"}:
                return True
            if value in {"0", "false", "no", "off", "release", "production", "prod"}:
                return False
        return bool(v)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            input_value = v.strip()
            if input_value.startswith("[") and input_value.endswith("]"):
                try:
                    decoded = json.loads(input_value)
                    if isinstance(decoded, list):
                        return [str(item).strip() for item in decoded if str(item).strip()]
                except json.JSONDecodeError:
                    pass
            return [i.strip() for i in input_value.split(",") if i.strip()]
        return v

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_database_url(cls, v):
        if v and not str(v).startswith("sqlite"):
            return v
        return "sqlite:///./accounting.db"

    @field_validator("cors_allow_methods", mode="before")
    @classmethod
    def assemble_cors_allow_methods(cls, v):
        if isinstance(v, str):
            value = v.strip()
            if not value:
                return ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
            if value.startswith("[") and value.endswith("]"):
                try:
                    decoded = json.loads(value)
                    if isinstance(decoded, list):
                        return [str(item).strip().upper() for item in decoded if str(item).strip()]
                except json.JSONDecodeError:
                    pass
            return [item.strip().upper() for item in value.split(",") if item.strip()]
        return v

    @field_validator("cors_allow_headers", mode="before")
    @classmethod
    def assemble_cors_allow_headers(cls, v):
        if isinstance(v, str):
            value = v.strip()
            if not value:
                return ["*"]
            if value.startswith("[") and value.endswith("]"):
                try:
                    decoded = json.loads(value)
                    if isinstance(decoded, list):
                        return [str(item).strip() for item in decoded if str(item).strip()]
                except json.JSONDecodeError:
                    pass
            if value == "*":
                return ["*"]
            return [item.strip() for item in value.split(",") if item.strip()]
        return v

    def get_database_url_async(self) -> str:
        if self.database_url.startswith("postgresql"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
        return self.database_url


settings = Settings()
