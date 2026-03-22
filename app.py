"""
Minimal test FastAPI app
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import init_database, close_database_connections
from logging_config import setup_logging
from models import User, UserRole
from middleware import limiter, rate_limit_exceeded_handler, security_middleware, authentication_middleware
from slowapi.errors import RateLimitExceeded
import logging

print("Setting up logging...")
setup_logging()
logger = logging.getLogger("app.test")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting test API...")

    # Initialize database
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Cleanup
    logger.info("Shutting down test API...")
    await close_database_connections()

print("Creating FastAPI app...")

# FastAPI App
app = FastAPI(
    title=settings.app_name,
    description="Test API",
    version=settings.app_version,
    lifespan=lifespan
)

# Add middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.middleware("http")(security_middleware)
app.middleware("http")(authentication_middleware)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

print(f"App created: {app}")
print(f"Routes: {[route.path for route in app.routes if hasattr(route, 'path')]}")

@app.get("/")
async def root():
    """Root endpoint"""
    print("Root endpoint called")
    return {"message": "Hello from minimal app"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API is running"}

print("Routes after adding endpoints:", [route.path for route in app.routes if hasattr(route, 'path')])