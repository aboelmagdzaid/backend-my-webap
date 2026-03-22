"""
Database connection and session management
SQLAlchemy engine and session configuration
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator
import logging

from config import settings

logger = logging.getLogger(__name__)

# Synchronous engine for migrations and utilities
def create_sync_engine():
    """Create synchronous SQLAlchemy engine"""
    if settings.database_url.startswith("sqlite"):
        # SQLite specific configuration
        engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=settings.debug,
        )
    else:
        # PostgreSQL configuration
        engine = create_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            pool_recycle=settings.database_pool_recycle,
            echo=settings.debug,
        )

    return engine

# Asynchronous engine for FastAPI
def create_async_engine_instance():
    """Create asynchronous SQLAlchemy engine"""
    if settings.database_url.startswith("sqlite"):
        # SQLite doesn't support async, use aiosqlite
        try:
            import aiosqlite
            engine = create_async_engine(
                f"sqlite+aiosqlite:///./accounting.db",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=settings.debug,
            )
        except ImportError:
            # Fallback to sync engine for SQLite
            engine = create_async_engine(
                settings.database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=settings.debug,
            )
    else:
        # PostgreSQL async configuration
        engine = create_async_engine(
            settings.get_database_url_async(),
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            pool_recycle=settings.database_pool_recycle,
            echo=settings.debug,
        )

    return engine

# Global engines
sync_engine = create_sync_engine()
async_engine = create_async_engine_instance()

# Session factories
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    class_=AsyncSession
)

def get_db() -> Generator[Session, None, None]:
    """Dependency for synchronous database sessions"""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db() -> Generator[AsyncSession, None, None]:
    """Dependency for asynchronous database sessions"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def init_database():
    """Initialize database and create tables"""
    from models import Base

    logger.info("Initializing database...")
    try:
        Base.metadata.create_all(bind=sync_engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

async def close_database_connections():
    """Close database connections gracefully"""
    logger.info("Closing database connections...")

    await async_engine.dispose()
    sync_engine.dispose()

    logger.info("Database connections closed")