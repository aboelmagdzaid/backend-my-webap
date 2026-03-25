"""
Logging configuration for the application
Structured logging with different levels and handlers
"""

import logging
import logging.config
import sys
from typing import Dict, Any

from config import settings


def setup_logging() -> None:
    """Setup logging configuration"""

    # Logging configuration — console only (Railway captures stdout)
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
            }
        },
        "loggers": {
            "app": {
                "handlers": ["console"],
                "level": settings.log_level.upper() if settings.debug else "WARNING",
                "propagate": False
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False
            },
            "uvicorn.error": {
                "handlers": ["console"],
                "level": "ERROR",
                "propagate": False
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False
            },
            "sqlalchemy.engine": {
                "handlers": ["console"],
                "level": "ERROR",
                "propagate": False
            }
        },
        "root": {
            "handlers": ["console"],
            "level": settings.log_level.upper() if settings.debug else "ERROR"
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
