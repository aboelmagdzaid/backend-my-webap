"""
Logging configuration for the application
Structured logging with different levels and handlers
"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Any

from config import settings


def setup_logging() -> None:
    """Setup logging configuration"""

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Logging configuration
    logging_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "json": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(funcName)s:%(lineno)d",
                "datefmt": "%Y-%m-%dT%H:%M:%SZ"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": "INFO",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "detailed",
                "filename": "logs/app.log",
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
                "level": "INFO"
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "detailed",
                "filename": "logs/error.log",
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
                "level": "ERROR"
            }
        },
        "loggers": {
            "app": {
                "handlers": ["console", "file", "error_file"],
                "level": settings.log_level.upper(),
                "propagate": False
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            },
            "uvicorn.error": {
                "handlers": ["console", "error_file"],
                "level": "ERROR",
                "propagate": False
            },
            "uvicorn.access": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            },
            "sqlalchemy": {
                "handlers": ["console", "file"],
                "level": "WARNING",
                "propagate": False
            }
        },
        "root": {
            "handlers": ["console", "file", "error_file"],
            "level": settings.log_level.upper()
        }
    }

    # Apply configuration
    logging.config.dictConfig(logging_config)

    # Set up specific loggers
    logger = logging.getLogger("app")
    logger.info("Logging configured successfully")

    if settings.debug:
        logger.info("Debug mode enabled")
    else:
        logger.info("Production mode enabled")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(f"app.{name}")