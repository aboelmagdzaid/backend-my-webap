#!/usr/bin/env python3
"""
Development runner script for Accounting Office API
Handles database initialization and application startup
"""

import os
import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Main entry point"""
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("Starting Accounting Office API (Development)")

    # Check if .env exists
    if not Path('.env').exists():
        logger.warning(".env file not found. Using default settings.")
        logger.info("Copy .env.example to .env and configure your settings.")

    try:
        # Initialize database
        logger.info("Initializing database...")
        from database import init_database
        init_database()
        logger.info("Database initialized successfully")

        # Import and run the application
        logger.info("Starting FastAPI server...")
        from main import app
        import uvicorn

        # Get configuration
        from config import settings

        logger.info(f"Server will run on http://{settings.host}:{settings.port}")
        logger.info(f"API Documentation: http://{settings.host}:{settings.port}/docs")
        logger.info(f"Health Check: http://{settings.host}:{settings.port}/api/health")

        # Run the server
        uvicorn.run(
            "main:app",
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level,
            reload=settings.debug,
            workers=1  # Single worker for development
        )

    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()